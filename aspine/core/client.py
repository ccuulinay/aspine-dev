"""
Aspine 2.0 - Async Client
Pythonic async client with context managers and pub/sub support
"""
import asyncio
from typing import Any, Dict, List, Optional, AsyncIterator
import logging

from .async_mp_bridge import AsyncMPBridge

logger = logging.getLogger(__name__)


class AspineError(Exception):
    """Base exception for Aspine errors."""
    pass


class ConnectionError(AspineError):
    """Raised when connection to server fails."""
    pass


class TimeoutError(AspineError):
    """Raised when an operation times out."""
    pass


class AuthError(AspineError):
    """Raised when authentication fails."""
    pass


class CacheMiss(AspineError):
    """Raised when a key is not found."""
    pass


class AspineClient:
    """
    Aspine 2.0 Async Client.

    Provides a Pythonic async interface to the Aspine cache server.

    Example usage:
        async with AspineClient() as client:
            await client.set("key", "value")
            value = await client.get("key")
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5116,
        authkey: str = "123456",
        max_size: int = 1000,
        persist_path: Optional[str] = None,
        timeout: float = 5.0,
    ):
        """
        Initialize the client.

        Args:
            host: Server host address
            port: Server port
            authkey: Authentication key
            max_size: Maximum cache size before LRU eviction
            persist_path: Optional path for disk persistence
            timeout: Default timeout for operations
        """
        self.host = host
        self.port = port
        self.authkey = authkey
        self.max_size = max_size
        self.persist_path = persist_path
        self.timeout = timeout

        self._bridge: Optional[AsyncMPBridge] = None
        self._connected = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self):
        """
        Connect to the Aspine server.

        Raises:
            ConnectionError: If connection fails
        """
        if self._connected:
            return

        try:
            # In v2.0, we're using async/MP bridge instead of multiprocessing manager
            # The bridge handles its own server process management
            self._bridge = AsyncMPBridge(
                max_size=self.max_size,
                persist_path=self.persist_path,
            )

            await self._bridge.start()
            self._connected = True

        except Exception as e:
            raise ConnectionError(f"Failed to connect: {e}")

    async def disconnect(self):
        """Disconnect from the server."""
        if not self._connected or not self._bridge:
            return

        try:
            await self._bridge.stop()
            self._connected = False
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        invalidate: bool = False,
    ) -> bool:
        """
        Set a key-value pair.

        Args:
            key: The key to set
            value: The value to store
            ttl: Time to live in seconds (optional)
            invalidate: Whether to broadcast invalidation (for pub/sub)

        Returns:
            True if successful

        Raises:
            ConnectionError: If not connected
        """
        if not self._connected:
            raise ConnectionError("Not connected to server")

        try:
            await asyncio.wait_for(
                self._bridge.set(key, value, ttl, invalidate),
                timeout=self.timeout
            )
            return True
        except asyncio.TimeoutError:
            raise TimeoutError(f"Set operation timed out after {self.timeout}s")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value by key.

        Args:
            key: The key to retrieve

        Returns:
            The value if found, None otherwise

        Raises:
            ConnectionError: If not connected
            TimeoutError: If operation times out
        """
        if not self._connected:
            raise ConnectionError("Not connected to server")

        try:
            result = await asyncio.wait_for(
                self._bridge.get(key),
                timeout=self.timeout
            )
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Get operation timed out after {self.timeout}s")

    async def delete(self, key: str) -> int:
        """
        Delete a key.

        Args:
            key: The key to delete

        Returns:
            1 if deleted, 0 if not found

        Raises:
            ConnectionError: If not connected
            TimeoutError: If operation times out
        """
        if not self._connected:
            raise ConnectionError("Not connected to server")

        try:
            result = await asyncio.wait_for(
                self._bridge.delete(key),
                timeout=self.timeout
            )
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Delete operation timed out after {self.timeout}s")

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists.

        Args:
            key: The key to check

        Returns:
            True if key exists, False otherwise

        Raises:
            ConnectionError: If not connected
            TimeoutError: If operation times out
        """
        if not self._connected:
            raise ConnectionError("Not connected to server")

        try:
            result = await asyncio.wait_for(
                self._bridge.exists(key),
                timeout=self.timeout
            )
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Exists operation timed out after {self.timeout}s")

    async def ttl(self, key: str) -> int:
        """
        Get remaining TTL for a key.

        Args:
            key: The key to check

        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist

        Raises:
            ConnectionError: If not connected
            TimeoutError: If operation times out
        """
        if not self._connected:
            raise ConnectionError("Not connected to server")

        try:
            result = await asyncio.wait_for(
                self._bridge.ttl(key),
                timeout=self.timeout
            )
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"TTL operation timed out after {self.timeout}s")

    async def list(self, pattern: Optional[str] = None) -> List[str]:
        """
        List all keys, optionally matching a pattern.

        Args:
            pattern: Optional glob pattern to filter keys

        Returns:
            List of matching keys

        Raises:
            ConnectionError: If not connected
            TimeoutError: If operation times out
        """
        if not self._connected:
            raise ConnectionError("Not connected to server")

        try:
            result = await asyncio.wait_for(
                self._bridge.list(pattern),
                timeout=self.timeout
            )
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"List operation timed out after {self.timeout}s")

    async def clear(self) -> bool:
        """
        Clear all data from cache.

        Returns:
            True if successful

        Raises:
            ConnectionError: If not connected
            TimeoutError: If operation times out
        """
        if not self._connected:
            raise ConnectionError("Not connected to server")

        try:
            await asyncio.wait_for(
                self._bridge.clear(),
                timeout=self.timeout
            )
            return True
        except asyncio.TimeoutError:
            raise TimeoutError(f"Clear operation timed out after {self.timeout}s")

    async def info(self) -> Dict[str, Any]:
        """
        Get cache information and statistics.

        Returns:
            Dictionary with cache information

        Raises:
            ConnectionError: If not connected
            TimeoutError: If operation times out
        """
        if not self._connected:
            raise ConnectionError("Not connected to server")

        try:
            result = await asyncio.wait_for(
                self._bridge.info(),
                timeout=self.timeout
            )
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Info operation timed out after {self.timeout}s")

    async def save(self, filepath: Optional[str] = None) -> bool:
        """
        Save cache to disk.

        Args:
            filepath: Optional filepath (uses default if not provided)

        Returns:
            True if successful

        Raises:
            ConnectionError: If not connected
            TimeoutError: If operation times out
        """
        if not self._connected:
            raise ConnectionError("Not connected to server")

        try:
            await asyncio.wait_for(
                self._bridge.save(filepath),
                timeout=self.timeout
            )
            return True
        except asyncio.TimeoutError:
            raise TimeoutError(f"Save operation timed out after {self.timeout}s")

    async def load(self, filepath: Optional[str] = None) -> bool:
        """
        Load cache from disk.

        Args:
            filepath: Optional filepath (uses default if not provided)

        Returns:
            True if loaded successfully, False if file doesn't exist

        Raises:
            ConnectionError: If not connected
            TimeoutError: If operation times out
        """
        if not self._connected:
            raise ConnectionError("Not connected to server")

        try:
            result = await asyncio.wait_for(
                self._bridge.load(filepath),
                timeout=self.timeout
            )
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Load operation timed out after {self.timeout}s")

    async def mget(self, *keys: str) -> AsyncIterator[Any]:
        """
        Get multiple values in batch (async iterator).

        Args:
            keys: Keys to retrieve

        Yields:
            Values for each key (in order)

        Example:
            async for value in client.mget("key1", "key2", "key3"):
                print(value)
        """
        if not self._connected:
            raise ConnectionError("Not connected to server")

        for key in keys:
            try:
                value = await asyncio.wait_for(
                    self._bridge.get(key),
                    timeout=self.timeout
                )
                yield value
            except asyncio.TimeoutError:
                raise TimeoutError(f"MGet operation timed out after {self.timeout}s")

    async def mset(self, pairs: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Set multiple key-value pairs in batch.

        Args:
            pairs: Dictionary of key-value pairs to set
            ttl: Optional TTL for all pairs

        Returns:
            True if successful

        Raises:
            ConnectionError: If not connected
            TimeoutError: If operation times out
        """
        if not self._connected:
            raise ConnectionError("Not connected to server")

        try:
            for key, value in pairs.items():
                await asyncio.wait_for(
                    self._bridge.set(key, value, ttl),
                    timeout=self.timeout
                )
            return True
        except asyncio.TimeoutError:
            raise TimeoutError(f"MSet operation timed out after {self.timeout}s")

    async def subscribe(self, key: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Subscribe to cache invalidation events for a key.

        Args:
            key: The key to subscribe to

        Yields:
            Dictionary with 'key' and 'timestamp'

        Example:
            async for event in client.subscribe("my_key"):
                print(f"Key invalidated: {event['key']}")
        """
        if not self._connected:
            raise ConnectionError("Not connected to server")

        try:
            queue = await asyncio.wait_for(
                self._bridge.subscribe(key),
                timeout=self.timeout
            )

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield event
                except asyncio.TimeoutError:
                    # Check if still connected
                    if not self._connected:
                        break
        except asyncio.TimeoutError:
            raise TimeoutError(f"Subscribe operation timed out after {self.timeout}s")


# Convenience function
async def create_client(
    host: str = "127.0.0.1",
    port: int = 5116,
    authkey: str = "123456",
    max_size: int = 1000,
    persist_path: Optional[str] = None,
    timeout: float = 5.0,
) -> AspineClient:
    """
    Create and connect an Aspine client.

    Args:
        host: Server host address
        port: Server port
        authkey: Authentication key
        max_size: Maximum cache size
        persist_path: Optional persistence path
        timeout: Default timeout

    Returns:
        Connected AspineClient instance
    """
    client = AspineClient(
        host=host,
        port=port,
        authkey=authkey,
        max_size=max_size,
        persist_path=persist_path,
        timeout=timeout,
    )
    await client.connect()
    return client
