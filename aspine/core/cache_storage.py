"""
Aspine 2.0 - Cache Storage Layer
Smart caching with LRU eviction and TTL support
"""
import asyncio
import heapq
import pickle
import time
import os
from typing import Any, Dict, List, Optional, Tuple


class CacheStorage:
    """
    High-performance in-memory cache with LRU eviction and TTL support.

    This storage layer provides:
    - LRU (Least Recently Used) eviction policy
    - TTL (Time To Live) for automatic expiration
    - Optional persistence to disk
    - Memory usage optimization
    """

    __slots__ = (
        '_data', '_access_order', '_expire_heap', '_lock',
        '_start_time', '_task', '_max_size', '_persist_path',
        '_access_count'
    )

    def __init__(
        self,
        max_size: int = 1000,
        persist_path: Optional[str] = None
    ):
        """
        Initialize cache storage.

        Args:
            max_size: Maximum number of keys before LRU eviction
            persist_path: Optional path for disk persistence
        """
        self._data: Dict[str, Any] = {}
        self._access_order: List[str] = []  # For LRU tracking
        self._expire_heap: List[Tuple[float, str]] = []  # (expire_time, key)
        self._access_count: Dict[str, int] = {}  # Access frequency tracking
        self._lock = asyncio.Lock()
        self._start_time = time.time()
        self._task: Optional[asyncio.Task] = None
        self._max_size = max_size
        self._persist_path = persist_path

    async def start(self):
        """Start background tasks (proactive expiration, persistence)."""
        self._task = asyncio.create_task(self._proactive_expire())

    async def stop(self):
        """Stop background tasks and save if persistence enabled."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._persist_path:
            await self.save(self._persist_path)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set a key-value pair with optional TTL.

        Args:
            key: The key to set
            value: The value to store
            ttl: Time to live in seconds (optional)
        """
        async with self._lock:
            # Add/Update access tracking
            if key in self._data:
                # Update existing key - move to end (most recent)
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                self._access_count[key] = self._access_count.get(key, 0) + 1
            else:
                # New key
                self._access_order.append(key)
                self._access_count[key] = 1

            # Set value
            self._data[key] = value

            # Handle expiration
            if ttl:
                expire_at = time.time() + ttl
                heapq.heappush(self._expire_heap, (expire_at, key))

            # LRU eviction if over capacity
            await self._evict_lru_if_needed()

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value by key, updating LRU tracking.

        Args:
            key: The key to retrieve

        Returns:
            The value if found, None otherwise
        """
        async with self._lock:
            # Check expiration first
            await self._remove_expired_key(key)

            if key not in self._data:
                return None

            # Update LRU tracking
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            self._access_count[key] = self._access_count.get(key, 0) + 1

            return self._data[key]

    async def delete(self, key: str) -> int:
        """
        Delete a key.

        Args:
            key: The key to delete

        Returns:
            1 if deleted, 0 if not found
        """
        async with self._lock:
            if key not in self._data:
                return 0

            # Remove from all tracking structures
            del self._data[key]

            if key in self._access_order:
                self._access_order.remove(key)

            if key in self._access_count:
                del self._access_count[key]

            # Remove from expire heap
            self._expire_heap = [(exp_time, k) for exp_time, k in self._expire_heap if k != key]
            heapq.heapify(self._expire_heap)

            return 1

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        async with self._lock:
            await self._remove_expired_key(key)
            return key in self._data

    async def ttl(self, key: str) -> int:
        """
        Get remaining TTL for a key.

        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        async with self._lock:
            if key not in self._data:
                return -2

            for expire_at, heap_key in self._expire_heap:
                if heap_key == key:
                    remaining = int(expire_at - time.time())
                    return max(remaining, 0)

            return -1

    async def list(self, pattern: Optional[str] = None) -> List[str]:
        """
        List all keys, optionally matching a pattern.

        Args:
            pattern: Optional glob pattern to filter keys

        Returns:
            List of matching keys
        """
        async with self._lock:
            # Remove expired keys
            await self._remove_expired_keys()

            keys = list(self._data.keys())

            if pattern:
                # Simple glob matching
                import fnmatch
                keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]

            return keys

    async def clear(self) -> None:
        """Clear all data from cache."""
        async with self._lock:
            self._data.clear()
            self._access_order.clear()
            self._access_count.clear()
            self._expire_heap.clear()

    async def save(self, filepath: str) -> None:
        """
        Save cache to disk.

        Args:
            filepath: Path to save the cache
        """
        async with self._lock:
            temp_filepath = f"{filepath}.tmp"
            data_to_save = {
                'data': self._data,
                'expire_heap': self._expire_heap,
                'access_order': self._access_order,
                'access_count': self._access_count,
                'max_size': self._max_size,
            }

            with open(temp_filepath, "wb") as f:
                pickle.dump(data_to_save, f)

            os.replace(temp_filepath, filepath)

    async def load(self, filepath: str) -> bool:
        """
        Load cache from disk.

        Args:
            filepath: Path to load the cache from

        Returns:
            True if loaded successfully, False if file doesn't exist
        """
        if not os.path.exists(filepath):
            return False

        async with self._lock:
            with open(filepath, "rb") as f:
                data_to_load = pickle.load(f)

            self._data = data_to_load.get('data', {})
            self._expire_heap = data_to_load.get('expire_heap', [])
            self._access_order = data_to_load.get('access_order', [])
            self._access_count = data_to_load.get('access_count', {})
            self._max_size = data_to_load.get('max_size', 1000)

            # Re-heapify expire_heap
            heapq.heapify(self._expire_heap)

            return True

    async def info(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache information
        """
        async with self._lock:
            await self._remove_expired_keys()

            return {
                'keys': len(self._data),
                'max_size': self._max_size,
                'memory_usage': self._get_memory_usage(),
                'uptime': int(time.time() - self._start_time),
                'avg_access_count': sum(self._access_count.values()) / max(len(self._access_count), 1),
            }

    def _get_memory_usage(self) -> int:
        """Calculate approximate memory usage."""
        return sum(
            len(str(k)) + len(str(v))
            for k, v in self._data.items()
        )

    async def _proactive_expire(self) -> None:
        """Background task to proactively remove expired keys."""
        while True:
            try:
                async with self._lock:
                    await self._remove_expired_keys()

                # Sleep until next expiration
                if self._expire_heap:
                    sleep_for = self._expire_heap[0][0] - time.time()
                    if sleep_for > 0:
                        await asyncio.sleep(sleep_for)
                else:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue
                await asyncio.sleep(1)

    async def _remove_expired_keys(self) -> None:
        """Remove all expired keys."""
        now = time.time()
        while self._expire_heap and self._expire_heap[0][0] < now:
            _, key = heapq.heappop(self._expire_heap)
            if key in self._data:
                del self._data[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                if key in self._access_count:
                    del self._access_count[key]

    async def _remove_expired_key(self, key: str) -> None:
        """Remove a specific key if expired."""
        now = time.time()
        for expire_at, heap_key in self._expire_heap:
            if heap_key == key and expire_at < now:
                # Key is expired, remove it
                if key in self._data:
                    del self._data[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                if key in self._access_count:
                    del self._access_count[key]

                # Remove from heap
                self._expire_heap = [(exp_time, k) for exp_time, k in self._expire_heap if k != key]
                heapq.heapify(self._expire_heap)
                break

    async def _evict_lru_if_needed(self) -> None:
        """Evict least recently used keys if over capacity."""
        while len(self._data) > self._max_size:
            await self._evict_one_lru()

    async def _evict_one_lru(self) -> None:
        """Evict one least recently used key."""
        if not self._access_order:
            return

        # Get least recently used key (first in list)
        key_to_evict = self._access_order[0]

        # Remove from all structures
        del self._data[key_to_evict]
        del self._access_count[key_to_evict]
        self._access_order.pop(0)

        # Remove from expire heap
        self._expire_heap = [(exp_time, k) for exp_time, k in self._expire_heap if k != key_to_evict]
        heapq.heapify(self._expire_heap)
