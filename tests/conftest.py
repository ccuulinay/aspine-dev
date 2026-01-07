"""
Shared test fixtures for Aspine 2.0
"""
import asyncio
import pytest
import tempfile
import os

from aspine import AspineClient


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
async def temp_persist_file():
    """Create a temporary persistence file for tests."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".rdb") as tmp:
        filepath = tmp.name

    yield filepath

    # Cleanup
    if os.path.exists(filepath):
        os.unlink(filepath)


@pytest.fixture
async def sample_client():
    """Create a client with sample data."""
    client = AspineClient(max_size=100)
    await client.connect()

    # Add sample data
    await client.set("user:1", {"name": "Alice", "age": 30})
    await client.set("user:2", {"name": "Bob", "age": 25})
    await client.set("counter", 42)
    await client.set("cached_result", {"data": "expensive_computation_result"}, ttl=60)

    yield client

    await client.disconnect()
