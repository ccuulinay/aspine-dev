# PyRedisAsync

An asynchronous, in-memory key-value datastore for Python, inspired by Redis. This project provides a lightweight, dependency-free, and high-performance cache using Python's `asyncio` library.

## Key Features

- **Pure Python:** No external dependencies, uses only the Python standard library.
- **Asynchronous Core:** Built on `asyncio` for high-concurrency non-blocking operations.
- **Redis-like API:** Implements familiar commands like `SET`, `GET`, `DEL`, `INCR`, etc.
- **Key Expiration (TTL):** Supports time-to-live on keys for automatic data expiry.
- **Data Persistence:** Can save the in-memory database to a file and load it back on startup.
- **Thread Safe:** Uses `asyncio.Lock` to ensure atomic operations.
- **TCP Server Included:** Comes with a ready-to-run TCP server that listens for Redis-like commands.

## How to Use

`PyRedisAsync` is contained in a single file (`pyredis_async.py`) and can be used in two ways: as a standalone server or as an embedded cache engine in your application.

### As an Embedded Cache Engine

You can directly use the `CacheEngine` class in your `asyncio` application.

1.  **Copy `pyredis_async.py`** into your project directory.
2.  **Use the `CacheEngine` class** in your code as shown below.

#### Basic Usage

Here is a simple example of using the cache engine.

```python
import asyncio
from pyredis_async import CacheEngine

async def main():
    # Initialize the cache engine
    cache = CacheEngine()

    # Set a value
    await cache.set("mykey", "Hello, Async World!")
    print("Set 'mykey' to 'Hello, Async World!'")

    # Get a value
    value = await cache.get("mykey")
    print(f"Got value for 'mykey': {value}")

    # Delete the key
    deleted_count = await cache.delete("mykey")
    print(f"Deleted {deleted_count} key(s)")

    # Try to get the deleted key
    value = await cache.get("mykey")
    print(f"Value for 'mykey' after deletion: {value}")

if __name__ == "__main__":
    asyncio.run(main())
```

#### Key Expiration (TTL)

You can set a Time-To-Live (TTL) in seconds when setting a key.

```python
import asyncio
from pyredis_async import CacheEngine

async def main():
    cache = CacheEngine()

    # Set a key that expires in 2 seconds
    await cache.set("ephemeral", "This will disappear soon", expire=2)
    print("Set 'ephemeral' with a 2-second TTL")

    # Get it immediately
    value = await cache.get("ephemeral")
    print(f"Value immediately after set: {value}")

    # Wait for 3 seconds
    print("Waiting for 3 seconds...")
    await asyncio.sleep(3)

    # Try to get it again
    value = await cache.get("ephemeral")
    print(f"Value after 3 seconds: {value}")

if __name__ == "__main__":
    asyncio.run(main())
```

#### Persistence

You can save the current state of the cache to a file and load it back later.

```python
import asyncio
from pyredis_async import CacheEngine

DB_FILE = "my_cache.db"

async def demo_save():
    print("--- Saving Data ---")
    cache = CacheEngine()
    await cache.set("persistent_key", "This data will be saved")
    await cache.set("another_key", "So will this")
    
    # Save state to file
    await cache.save(DB_FILE)
    print(f"Cache state saved to {DB_FILE}")

async def demo_load():
    print("\n--- Loading Data ---")
    new_cache = CacheEngine()
    
    # Load state from file
    await new_cache.load(DB_FILE)
    print(f"Cache state loaded from {DB_FILE}")

    # Access the loaded data
    value = await new_cache.get("persistent_key")
    print(f"Value of 'persistent_key': {value}")
    
    value = await new_cache.get("another_key")
    print(f"Value of 'another_key': {value}")


async def main():
    await demo_save()
    await demo_load()

if __name__ == "__main__":
    asyncio.run(main())
```

### As a Standalone Server

The script can be run directly to start a TCP server that listens on port `6379`, mimicking a Redis server.

1.  **Run the script from your terminal:**
    ```bash
    python pyredis_async.py
    ```

2.  **Connect with a Redis client** (like `redis-cli`) or any TCP client (like `netcat` or `telnet`).

    ```bash
    # Using netcat
    $ nc localhost 6379

    # Now type Redis commands
    SET name "PyRedisAsync"
    OK

    GET name
    PyRedisAsync

    INCR counter
    :1

    INCR counter
    :2

    TTL name
    :-1
    
    DEL counter
    :1
    ```

## Supported Commands

The `CacheEngine` class provides the following async methods:

-   `set(key, value, expire=None)`: Sets a key-value pair. `expire` is in seconds.
-   `get(key)`: Retrieves a value for a key. Returns `None` if not found or expired.
-   `delete(key)`: Deletes a key. Returns `1` if deleted, `0` otherwise.
-   `ttl(key)`: Returns the remaining time-to-live for a key. (`-1` for no expiry, `-2` for non-existent key).
-   `incr(key)`: Increments the integer value of a key by 1.
-   `decr(key)`: Decrements the integer value of a key by 1.
-   `save(filename)`: Saves the cache state to a file.
-   `load(filename)`: Loads the cache state from a file.
-   `info()`: Returns a dictionary with cache statistics.
