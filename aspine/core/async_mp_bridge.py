"""
Aspine 2.0 - Async/MP Bridge Layer
Bridges asyncio client layer with multiprocessing storage layer
"""
import asyncio
import multiprocessing as mp
from multiprocessing.queues import Queue
from typing import Any, Dict, Optional, Callable, List
import uuid
import time
from dataclasses import dataclass
from enum import Enum
import logging

from .cache_storage import CacheStorage

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages in the queue communication protocol."""
    GET = "get"
    SET = "set"
    DELETE = "delete"
    EXISTS = "exists"
    TTL = "ttl"
    LIST = "list"
    CLEAR = "clear"
    INFO = "info"
    SAVE = "save"
    LOAD = "load"
    INVALIDATE = "invalidate"  # pub/sub
    HEARTBEAT = "heartbeat"
    SHUTDOWN = "shutdown"


@dataclass
class QueueMessage:
    """Message format for queue-based communication."""
    type: MessageType
    key: Optional[str] = None
    value: Any = None
    client_id: str = ""
    request_id: str = ""
    ttl: Optional[int] = None
    pattern: Optional[str] = None
    filepath: Optional[str] = None


@dataclass
class QueueResponse:
    """Response format from queue communication."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    request_id: str = ""


class StorageProcess(mp.Process):
    """
    Multiprocessing storage worker.

    Runs CacheStorage in a separate process and handles
    queue-based requests from the async bridge.
    """

    def __init__(
        self,
        request_queue: Queue,
        response_queues: Dict[str, Queue],
        broadcast_queue: Queue,
        max_size: int = 1000,
        persist_path: Optional[str] = None,
    ):
        super().__init__()
        self.request_queue = request_queue
        self.response_queues = response_queues
        self.broadcast_queue = broadcast_queue
        self.max_size = max_size
        self.persist_path = persist_path
        self.cache_storage: Optional[CacheStorage] = None

    def run(self):
        """Main process loop."""
        # Set up cache storage
        asyncio.run(self._run_server())

    async def _run_server(self):
        """Run the storage server with async cache."""
        self.cache_storage = CacheStorage(
            max_size=self.max_size,
            persist_path=self.persist_path
        )

        # Load from disk if persistence enabled
        if self.persist_path:
            await self.cache_storage.load(self.persist_path)

        await self.cache_storage.start()

        try:
            # Main request processing loop
            while True:
                try:
                    # Non-blocking queue check
                    if not self.request_queue.empty():
                        message = self.request_queue.get(timeout=0.1)
                        await self._handle_message(message)
                    else:
                        await asyncio.sleep(0.01)  # Small sleep to prevent busy-wait

                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Storage process error: {e}")
        finally:
            await self.cache_storage.stop()

    async def _handle_message(self, message: QueueMessage):
        """Handle a single message from the queue."""
        try:
            response = QueueResponse(
                success=True,
                request_id=message.request_id
            )

            if message.type == MessageType.GET:
                result = await self.cache_storage.get(message.key)
                response.data = result

            elif message.type == MessageType.SET:
                await self.cache_storage.set(message.key, message.value, message.ttl)
                response.data = True

            elif message.type == MessageType.DELETE:
                result = await self.cache_storage.delete(message.key)
                response.data = result

            elif message.type == MessageType.EXISTS:
                result = await self.cache_storage.exists(message.key)
                response.data = result

            elif message.type == MessageType.TTL:
                result = await self.cache_storage.ttl(message.key)
                response.data = result

            elif message.type == MessageType.LIST:
                result = await self.cache_storage.list(message.pattern)
                response.data = result

            elif message.type == MessageType.CLEAR:
                await self.cache_storage.clear()
                response.data = True

            elif message.type == MessageType.INFO:
                result = await self.cache_storage.info()
                response.data = result

            elif message.type == MessageType.SAVE:
                filepath = message.filepath or self.persist_path
                if filepath:
                    await self.cache_storage.save(filepath)
                    response.data = True
                else:
                    response.success = False
                    response.error = "No persist path configured"

            elif message.type == MessageType.LOAD:
                filepath = message.filepath or self.persist_path
                if filepath:
                    result = await self.cache_storage.load(filepath)
                    response.data = result
                else:
                    response.success = False
                    response.error = "No persist path configured"

            elif message.type == MessageType.INVALIDATE:
                # Broadcast cache invalidation to subscribers
                invalidate_msg = QueueMessage(
                    type=MessageType.INVALIDATE,
                    key=message.key,
                    request_id=message.request_id
                )
                try:
                    self.broadcast_queue.put(invalidate_msg)
                except Exception as e:
                    logger.error(f"Broadcast error: {e}")

            elif message.type == MessageType.HEARTBEAT:
                response.data = "ok"

            elif message.type == MessageType.SHUTDOWN:
                response.data = "shutting_down"
                # Send response before shutting down
                if message.client_id and message.client_id in self.response_queues:
                    try:
                        self.response_queues[message.client_id].put(response)
                    except Exception:
                        pass
                # Break to trigger shutdown
                return

            else:
                response.success = False
                response.error = f"Unknown message type: {message.type}"

            # Send response to client
            if message.client_id and message.client_id in self.response_queues:
                try:
                    self.response_queues[message.client_id].put(response)
                except Exception as e:
                    logger.error(f"Error sending response: {e}")

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            # Send error response
            error_response = QueueResponse(
                success=False,
                error=str(e),
                request_id=message.request_id
            )
            if message.client_id and message.client_id in self.response_queues:
                try:
                    self.response_queues[message.client_id].put(error_response)
                except Exception:
                    pass


class AsyncMPBridge:
    """
    Async interface to the multiprocessing storage.

    This class provides an async API that communicates with
    the StorageProcess via queues.
    """

    def __init__(
        self,
        max_size: int = 1000,
        persist_path: Optional[str] = None,
    ):
        self.max_size = max_size
        self.persist_path = persist_path
        self.request_queue: Optional[Queue] = None
        self.response_queues: Dict[str, Queue] = {}
        self.broadcast_queue: Optional[Queue] = None
        self.storage_process: Optional[StorageProcess] = None
        self._subscribers: Dict[str, List[Callable]] = {}

    async def start(self):
        """Start the bridge and storage process."""
        # Create queues
        self.request_queue = Queue()
        self.broadcast_queue = Queue()

        # Create and start storage process
        self.storage_process = StorageProcess(
            request_queue=self.request_queue,
            response_queues=self.response_queues,
            broadcast_queue=self.broadcast_queue,
            max_size=self.max_size,
            persist_path=self.persist_path,
        )

        self.storage_process.start()

        # Start broadcast listener
        asyncio.create_task(self._broadcast_listener())

        # Give process time to start
        await asyncio.sleep(0.1)

    async def stop(self):
        """Stop the bridge and storage process."""
        # Send shutdown message
        if self.request_queue:
            shutdown_msg = QueueMessage(
                type=MessageType.SHUTDOWN,
                request_id=str(uuid.uuid4())
            )
            try:
                self.request_queue.put(shutdown_msg)
            except Exception:
                pass

        # Wait for process to finish
        if self.storage_process:
            self.storage_process.join(timeout=2)

        # Cleanup
        self.response_queues.clear()
        self._subscribers.clear()

    def _create_client_queues(self, client_id: str) -> Queue:
        """Create response queue for a client."""
        response_queue = Queue()
        self.response_queues[client_id] = response_queue
        return response_queue

    def _cleanup_client_queues(self, client_id: str):
        """Cleanup client queues."""
        if client_id in self.response_queues:
            del self.response_queues[client_id]
        if client_id in self._subscribers:
            del self._subscribers[client_id]

    async def _send_request(
        self,
        message: QueueMessage,
        timeout: float = 5.0
    ) -> QueueResponse:
        """
        Send a request and wait for response.

        Args:
            message: The message to send
            timeout: Timeout in seconds

        Returns:
            The response

        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        if not self.request_queue:
            raise RuntimeError("Bridge not started")

        client_id = message.client_id or str(uuid.uuid4())
        message.client_id = client_id

        # Create response queue for this client if needed
        if client_id not in self.response_queues:
            self._create_client_queues(client_id)

        response_queue = self.response_queues[client_id]

        # Send request
        try:
            self.request_queue.put(message)
        except Exception as e:
            self._cleanup_client_queues(client_id)
            raise RuntimeError(f"Failed to send request: {e}")

        # Wait for response with timeout
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(response_queue.get),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            self._cleanup_client_queues(client_id)
            raise asyncio.TimeoutError(f"Request timed out after {timeout}s")

        # Cleanup
        self._cleanup_client_queues(client_id)

        if not response.success:
            raise RuntimeError(response.error or "Unknown error")

        return response

    async def _broadcast_listener(self):
        """Listen for broadcast messages."""
        while True:
            try:
                if self.broadcast_queue and not self.broadcast_queue.empty():
                    message = self.broadcast_queue.get(timeout=0.1)
                    await self._handle_broadcast(message)
                else:
                    await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Broadcast listener error: {e}")
                await asyncio.sleep(0.1)

    async def _handle_broadcast(self, message: QueueMessage):
        """Handle a broadcast message."""
        if message.type == MessageType.INVALIDATE:
            # Notify all subscribers
            for callback in self._subscribers.get(message.key, []):
                try:
                    await callback(message.key)
                except Exception as e:
                    logger.error(f"Subscriber callback error: {e}")

    # Public API

    async def get(self, key: str) -> Optional[Any]:
        """Get a value by key."""
        message = QueueMessage(
            type=MessageType.GET,
            key=key,
            request_id=str(uuid.uuid4())
        )
        response = await self._send_request(message)
        return response.data

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        invalidate: bool = False
    ) -> bool:
        """Set a key-value pair."""
        message = QueueMessage(
            type=MessageType.SET,
            key=key,
            value=value,
            ttl=ttl,
            request_id=str(uuid.uuid4())
        )
        await self._send_request(message)

        # Send invalidation broadcast if requested
        if invalidate:
            invalidate_msg = QueueMessage(
                type=MessageType.INVALIDATE,
                key=key,
                request_id=str(uuid.uuid4())
            )
            try:
                self.request_queue.put(invalidate_msg)
            except Exception as e:
                logger.error(f"Failed to send invalidation: {e}")

        return True

    async def delete(self, key: str) -> int:
        """Delete a key."""
        message = QueueMessage(
            type=MessageType.DELETE,
            key=key,
            request_id=str(uuid.uuid4())
        )
        response = await self._send_request(message)
        return response.data

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        message = QueueMessage(
            type=MessageType.EXISTS,
            key=key,
            request_id=str(uuid.uuid4())
        )
        response = await self._send_request(message)
        return response.data

    async def ttl(self, key: str) -> int:
        """Get TTL for a key."""
        message = QueueMessage(
            type=MessageType.TTL,
            key=key,
            request_id=str(uuid.uuid4())
        )
        response = await self._send_request(message)
        return response.data

    async def list(self, pattern: Optional[str] = None) -> List[str]:
        """List keys, optionally matching pattern."""
        message = QueueMessage(
            type=MessageType.LIST,
            pattern=pattern,
            request_id=str(uuid.uuid4())
        )
        response = await self._send_request(message)
        return response.data

    async def clear(self) -> bool:
        """Clear all data."""
        message = QueueMessage(
            type=MessageType.CLEAR,
            request_id=str(uuid.uuid4())
        )
        await self._send_request(message)
        return True

    async def info(self) -> Dict[str, Any]:
        """Get cache information."""
        message = QueueMessage(
            type=MessageType.INFO,
            request_id=str(uuid.uuid4())
        )
        response = await self._send_request(message)
        return response.data

    async def save(self, filepath: Optional[str] = None) -> bool:
        """Save cache to disk."""
        message = QueueMessage(
            type=MessageType.SAVE,
            filepath=filepath,
            request_id=str(uuid.uuid4())
        )
        await self._send_request(message)
        return True

    async def load(self, filepath: Optional[str] = None) -> bool:
        """Load cache from disk."""
        message = QueueMessage(
            type=MessageType.LOAD,
            filepath=filepath,
            request_id=str(uuid.uuid4())
        )
        response = await self._send_request(message)
        return response.data

    async def subscribe(self, key: str) -> asyncio.Queue:
        """
        Subscribe to invalidation events for a key.

        Args:
            key: The key to subscribe to

        Returns:
            AsyncQueue that receives invalidation events
        """
        queue = asyncio.Queue()

        async def callback(k):
            if k == key:
                await queue.put({"key": k, "timestamp": time.time()})

        if key not in self._subscribers:
            self._subscribers[key] = []
        self._subscribers[key].append(callback)

        return queue
