"""
Integration tests for AspineClient with real async/MP bridge
"""
import asyncio
import pytest
import tempfile
import os

from aspine import AspineClient


class TestAspineClient:
    """Integration test suite for AspineClient."""

    @pytest.fixture
    async def client(self):
        """Create a client instance for testing."""
        client = AspineClient(max_size=10)
        await client.connect()
        yield client
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with AspineClient() as client:
            await client.set("key1", "value1")
            result = await client.get("key1")
            assert result == "value1"

        # Client should be disconnected after context exit

    @pytest.mark.asyncio
    async def test_set_and_get(self, client):
        """Test basic set and get operations."""
        await client.set("key1", "value1")
        result = await client.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, client):
        """Test setting value with TTL."""
        await client.set("key2", "value2", ttl=1)
        result = await client.get("key2")
        assert result == "value2"

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, client):
        """Test TTL expiration."""
        await client.set("key3", "value3", ttl=1)
        await asyncio.sleep(1.1)
        result = await client.get("key3")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, client):
        """Test delete operation."""
        await client.set("key4", "value4")
        deleted = await client.delete("key4")
        assert deleted == 1

        # Verify deleted
        result = await client.get("key4")
        assert result is None

    @pytest.mark.asyncio
    async def test_exists(self, client):
        """Test exists operation."""
        await client.set("key5", "value5")
        assert await client.exists("key5") is True
        assert await client.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_ttl(self, client):
        """Test TTL retrieval."""
        await client.set("key6", "value6", ttl=60)
        ttl = await client.ttl("key6")
        assert ttl > 0 and ttl <= 60

        await client.set("key7", "value7")
        ttl = await client.ttl("key7")
        assert ttl == -1

    @pytest.mark.asyncio
    async def test_list(self, client):
        """Test list operation."""
        await client.set("key8", "value8")
        await client.set("key9", "value9")
        keys = await client.list()
        assert "key8" in keys
        assert "key9" in keys

    @pytest.mark.asyncio
    async def test_clear(self, client):
        """Test clear operation."""
        await client.set("key10", "value10")
        await client.set("key11", "value11")

        await client.clear()
        keys = await client.list()
        assert len(keys) == 0

    @pytest.mark.asyncio
    async def test_mget(self, client):
        """Test batch get operation."""
        await client.set("key1", "value1")
        await client.set("key2", "value2")
        await client.set("key3", "value3")

        values = []
        async for value in client.mget("key1", "key2", "key3"):
            values.append(value)

        assert values == ["value1", "value2", "value3"]

    @pytest.mark.asyncio
    async def test_mset(self, client):
        """Test batch set operation."""
        pairs = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        }

        await client.mset(pairs)

        for key, value in pairs.items():
            result = await client.get(key)
            assert result == value

    @pytest.mark.asyncio
    async def test_info(self, client):
        """Test info operation."""
        await client.set("key1", "value1")
        await client.set("key2", "value2")

        info = await client.info()
        assert info['keys'] >= 2
        assert 'memory_usage' in info
        assert 'uptime' in info

    @pytest.mark.asyncio
    async def test_persistence(self):
        """Test save and load operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.rdb")

            # Create client with persistence
            client1 = AspineClient(persist_path=filepath)
            await client1.connect()
            await client1.set("key1", "value1")
            await client1.set("key2", "value2")
            await client1.save(filepath)
            await client1.disconnect()

            # Create new client and load
            client2 = AspineClient(persist_path=filepath)
            await client2.connect()
            result1 = await client2.get("key1")
            result2 = await client2.get("key2")
            await client2.disconnect()

            assert result1 == "value1"
            assert result2 == "value2"

    @pytest.mark.asyncio
    async def test_lru_eviction(self, client):
        """Test LRU eviction."""
        # Client has max_size=10
        for i in range(15):
            await client.set(f"key{i}", f"value{i}")

        # Should only have last 10 keys
        keys = await client.list()
        assert len(keys) <= 10
        assert "key14" in keys
        # Old keys may be evicted
        assert "key0" not in keys

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, client):
        """Test concurrent operations."""
        async def set_and_get(key):
            await client.set(key, f"value_{key}")
            result = await client.get(key)
            return result == f"value_{key}"

        # Run 20 concurrent operations
        tasks = [set_and_get(f"key{i}") for i in range(20)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)

    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        """Test error handling."""
        # Test timeout (very small timeout)
        client.timeout = 0.001
        try:
            await client.set("key1", "value1")
            # Should raise TimeoutError
            assert False, "Should have raised TimeoutError"
        except Exception as e:
            assert "timeout" in str(e).lower()

    @pytest.mark.asyncio
    async def test_complex_value_types(self, client):
        """Test storing complex value types."""
        test_values = [
            {"nested": {"data": "value"}},
            [1, 2, 3, 4, 5],
            "simple string",
            123,
            45.67,
            True,
        ]

        for i, value in enumerate(test_values):
            await client.set(f"key{i}", value)
            result = await client.get(f"key{i}")
            assert result == value

    @pytest.mark.asyncio
    async def test_subscribe(self, client):
        """Test pub/sub functionality."""
        # Set a key with invalidation
        await client.set("key1", "value1", invalidate=True)

        # Subscribe to the key
        subscribe_task = asyncio.create_task(
            client.subscribe("key1")
        )

        # Wait a bit for subscription to be set up
        await asyncio.sleep(0.1)

        # Set the key again to trigger invalidation
        await client.set("key1", "value2", invalidate=True)

        # Wait for invalidation event
        event_task = asyncio.wait_for(subscribe_task.__anext__(), timeout=2.0)
        event = await event_task

        assert event['key'] == "key1"

        # Clean up
        subscribe_task.cancel()
