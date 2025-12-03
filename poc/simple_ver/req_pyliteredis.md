# Role
You are a Senior Python Backend Engineer and Systems Architect. Your task is to design and implement a robust, high-performance in-memory key-value store (cache server) using pure Python.
# Objective
Build a standalone application named PyRedisLite. It must function as a TCP server that mimics the core behavior of Redis. The goal is to create a lightweight drop-in replacement for basic caching needs without requiring the actual Redis binary or any external Python dependencies (no pip install).
# Constraints & Technical Requirements
 * Pure Python: You must use only the Python Standard Library (e.g., socket, threading, time, collections, heapq). No external packages.
 * Concurrency: The server must handle multiple concurrent client connections. Use threading or socketserver.ThreadingTCPServer.
 * Thread Safety: Since this is a shared state application, you must ensure all data operations are thread-safe using threading.Lock or RLock.
 * Protocol: Implement a simple text-based line protocol (similar to Redis).
   * Clients send commands as space-separated strings (e.g., SET mykey 100).
   * Server responds with text (e.g., OK, (nil), ERROR).
# Functional Specifications
## 1. Core Data Store
 * Implement a central Key-Value store using a Python dictionary.
 * Keys must be strings; values can be strings or integers.
## 2. Expiration & TTL (Time-To-Live)
 * Implement support for volatile keys (keys that expire).
 * Expiration Strategy: You must implement a hybrid approach:
   * Passive Expiration: Check if a key is expired when a client attempts to GET it. If expired, delete it and return nil.
   * Active Expiration: Implement a background thread (daemon) that wakes up periodically (e.g., every 1 second) to scan and clean up expired keys to free memory.
## 3. Required Commands
Implement the logic for the following commands:
 * SET key value: Store a key.
 * SET key value EX seconds: Store a key with an expiration time in seconds.
 * GET key: Retrieve a value. Return (nil) if not found or expired.
 * DEL key: Remove a key immediately.
 * EXISTS key: Return 1 if key exists, 0 otherwise.
 * TTL key: Return remaining time to live in seconds, -1 if no expiry, -2 if not found.
 * INCR key: Atomically increment a value (assume value is an integer).
 * FLUSHALL: Clear the entire cache.
# Output Deliverables
Please provide a single, complete, and runnable Python file named pyredis_lite.py. The file should include:
