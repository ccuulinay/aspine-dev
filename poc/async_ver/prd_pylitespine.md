# Role
You are a Principal Python Software Engineer specializing in high-concurrency systems and asynchronous programming.
# Objective
Develop PyRedisAsync, a high-performance, in-memory key-value store using Pure Python 3.10+. This application must serve as a drop-in cache replacement similar to Redis but optimized for Python's modern async capabilities.
# Core Constraints
 * No External Dependencies: Use only the Python Standard Library.
 * Architecture: Single-threaded Event Loop pattern (using asyncio) to handle thousands of concurrent connections without the overhead of thread context switching.
 * Type Hinting: Use strict type hints (typing module) for all function signatures.
# Technical Implementation Details
## 1. Data Structures & Performance
 * Main Store: Use a standard dict for O(1) lookups.
 * Expiration Heap: Use heapq to manage TTL (Time-To-Live). Store tuples of (expiry_timestamp, key) to allow O(1) access to the "next item to expire" rather than scanning the entire database.
 * Optimization: Use slots for any class definitions (like a CacheItem class) to reduce memory footprint.
## 2. Concurrency & Networking
 * Use asyncio.start_server for the TCP server.
 * Implement a custom async context manager (async with) for handling client connections to ensure sockets are closed gracefully even during exceptions.
 * Use asyncio.Lock for critical sections if atomic operations (like INCR) require protection, though the single-threaded nature of the event loop handles most data race conditions naturally.
## 3. Persistence (Snapshotting)
 * Implement a background task using asyncio.create_task that periodically saves the cache state to disk.
 * Format: Binary pickle format.
 * Safety: Write to a temporary file first, then use os.replace (atomic move) to overwrite the main dump file to prevent corruption during crashes.
## 4. Feature Set (Redis-like Commands)
The server must interpret a text-based protocol (space-separated) and support:
 * SET key value [EX seconds]
 * GET key
 * DEL key
 * TTL key
 * INCR key / DECR key
 * SAVE (trigger manual snapshot)
 * INFO (return stats: number of keys, memory usage, uptime)
## 5. Expiration Strategy (The "Lazy + Proactive" Approach)
 * Lazy: On GET, check if the key is expired. If yes, delete and return nil.
 * Proactive (Heap-based): Run a background coroutine loop. It should peek at the top of the heapq. If the (time, key) tuple indicates the time has passed, pop it and delete the key. If the time hasn't passed, await asyncio.sleep() for the difference.
# Deliverables
Produce a single file named pyredis_async.py containing:
 * The CacheEngine class.
 * The CommandParser class.
 * The Server startup logic.
 * Robust error handling (try/except blocks) for malformed client data.
Do not simplify the code. Write production-ready, clean, and documented code suitable for a high-load environment.
