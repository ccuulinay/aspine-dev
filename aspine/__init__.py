"""
Aspine - Python-native async + multiprocessing hybrid caching system

Aspine 2.0 provides a high-performance in-memory cache with:
- Asyncio for client-side concurrency
- Multiprocessing for server-side data isolation
- Queue-based communication between layers
- LRU eviction and TTL support
- Optional disk persistence
- Pub/sub for cache invalidation
"""

__version__ = '2.0.0'
__license__ = 'MIT'

# Core exports
from aspine.core.client import AspineClient, AspineError, ConnectionError, TimeoutError
from aspine.core.cache_storage import CacheStorage

# Convenience functions
from aspine.core.client import create_client

__all__ = [
    'AspineClient',
    'AspineError',
    'ConnectionError',
    'TimeoutError',
    'CacheStorage',
    'create_client',
]
