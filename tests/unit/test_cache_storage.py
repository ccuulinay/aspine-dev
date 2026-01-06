"""
Unit tests for CacheStorage
"""
import asyncio
import pytest
import tempfile
import os
from pathlib import Path

from aspine.core.cache_storage import CacheStorage


class TestCacheStorage:
    """Test suite for CacheStorage."""

    @pytest.fixture
    async def cache(self):
        """Create a cache instance for testing."""
        cache = CacheStorage(max_size=10)
        await cache.start()
        yield cache
        await cache.stop()

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        """Test setting and getting a value."""
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache):
        """Test setting a value with TTL."""
        await cache.set("key2", "value2", ttl=1)
        result = await cache.get("key2")
        assert result == "value2"

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache):
        """Test that TTL expiration works."""
        await cache.set("key3", "value3", ttl=1)
        await asyncio.sleep(1.1)
        result = await cache.get("key3")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """Test deleting a key."""
        await cache.set("key4", "value4")
        result = await cache.delete("key4")
        assert result == 1

        # Verify deleted
        result = await cache.get("key4")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache):
        """Test deleting a nonexistent key."""
        result = await cache.delete("nonexistent")
        assert result == 0

    @pytest.mark.asyncio
    async def test_exists(self, cache):
        """Test exists method."""
        await cache.set("key5", "value5")
        assert await cache.exists("key5") is True

        assert await cache.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_ttl(self, cache):
        """Test TTL retrieval."""
        # Key with TTL
        await cache.set("key6", "value6", ttl=60)
        ttl = await cache.ttl("key6")
        assert ttl > 0
        assert ttl <= 60

        # Key without TTL
        await cache.set("key7", "value7")
        ttl = await cache.ttl("key7")
        assert ttl == -1

        # Nonexistent key
        ttl = await cache.ttl("nonexistent")
        assert ttl == -2

    @pytest.mark.asyncio
    async def test_list(self, cache):
        """Test listing keys."""
        await cache.set("key8", "value8")
        await cache.set("key9", "value9")
        await cache.set("key10", "value10")

        keys = await cache.list()
        assert "key8" in keys
        assert "key9" in keys
        assert "key10" in keys

    @pytest.mark.asyncio
    async def test_list_with_pattern(self, cache):
        """Test listing keys with pattern matching."""
        await cache.set("user:1", "value1")
        await cache.set("user:2", "value2")
        await cache.set("post:1", "value3")

        user_keys = await cache.list(pattern="user:*")
        assert len(user_keys) == 2
        assert "user:1" in user_keys
        assert "user:2" in user_keys

        post_keys = await cache.list(pattern="post:*")
        assert len(post_keys) == 1
        assert "post:1" in post_keys

    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """Test clearing all data."""
        await cache.set("key11", "value11")
        await cache.set("key12", "value12")

        assert len(await cache.list()) == 2

        await cache.clear()
        assert len(await cache.list()) == 0

    @pytest.mark.asyncio
    async def test_lru_eviction(self, cache):
        """Test LRU eviction when exceeding max_size."""
        # Cache has max_size=10
        for i in range(15):
            await cache.set(f"key{i}", f"value{i}")

        # Should only have last 10 keys
        keys = await cache.list()
        assert len(keys) == 10
        assert "key0" not in keys
        assert "key14" in keys

    @pytest.mark.asyncio
    async def test_lru_access_order(self, cache):
        """Test that LRU updates access order."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Access key1 to make it most recently used
        await cache.get("key1")

        # Set 7 more keys to trigger eviction
        for i in range(4, 11):
            await cache.set(f"key{i}", f"value{i}")

        # key1 should still exist (most recently used)
        assert await cache.exists("key1") is True
        # key2 should be evicted (oldest)
        assert await cache.exists("key2") is False

    @pytest.mark.asyncio
    async def test_info(self, cache):
        """Test info method."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        info = await cache.info()
        assert info['keys'] == 2
        assert 'memory_usage' in info
        assert 'uptime' in info
        assert 'max_size' in info

    @pytest.mark.asyncio
    async def test_save_and_load(self):
        """Test saving and loading from disk."""
        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_cache.rdb")

            # Create cache and add data
            cache1 = CacheStorage(max_size=10, persist_path=filepath)
            await cache1.start()
            await cache1.set("key1", "value1")
            await cache1.set("key2", "value2")
            await cache1.stop()

            # Create new cache and load
            cache2 = CacheStorage(max_size=10, persist_path=filepath)
            await cache2.start()
            result1 = await cache2.get("key1")
            result2 = await cache2.get("key2")
            await cache2.stop()

            assert result1 == "value1"
            assert result2 == "value2"

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, cache):
        """Test concurrent operations."""
        tasks = []
        for i in range(10):
            tasks.append(cache.set(f"key{i}", f"value{i}"))

        await asyncio.gather(*tasks)

        # Verify all were set
        for i in range(10):
            result = await cache.get(f"key{i}")
            assert result == f"value{i}"

    @pytest.mark.asyncio
    async def test_update_existing_key(self, cache):
        """Test updating an existing key."""
        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"

        # Update same key
        await cache.set("key1", "value2")
        assert await cache.get("key1") == "value2"

    @pytest.mark.asyncio
    async def test_update_existing_key_with_ttl(self, cache):
        """Test updating an existing key with new TTL."""
        await cache.set("key1", "value1")
        await cache.set("key1", "value2", ttl=60)

        # Check TTL is updated
        ttl = await cache.ttl("key1")
        assert ttl > 0

        # Check value is updated
        assert await cache.get("key1") == "value2"

    @pytest.mark.asyncio
    async def test_complex_value_types(self, cache):
        """Test storing complex value types."""
        test_values = [
            {"nested": {"data": "value"}},
            [1, 2, 3, 4, 5],
            "simple string",
            123,
            45.67,
            True,
            None,
        ]

        for i, value in enumerate(test_values):
            await cache.set(f"key{i}", value)
            result = await cache.get(f"key{i}")
            assert result == value
