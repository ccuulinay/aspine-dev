# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyRedisAsync is a proof-of-concept asynchronous, in-memory key-value datastore for Python, inspired by Redis. It's implemented as a single file (`pyredis_async.py`) with zero external dependencies.

## Key Architecture

### Core Components

1. **CacheEngine Class** (lines 8-159): Main in-memory storage engine
   - Uses `dict` for O(1) key lookups
   - Uses `heapq` for TTL-based key expiration
   - Thread-safe with `asyncio.Lock`
   - Background expiration task (`_proactive_expire`)

2. **CommandParser Class** (lines 160-247): Redis-like command parsing
   - Supports: SET, GET, DEL, TTL, INCR, DECR, SAVE, INFO
   - Text-based protocol (space-separated commands)

3. **TCP Server** (lines 248-313): Async server on port 6379
   - Handles multiple concurrent clients
   - Auto-saves every 60 seconds

### Key Design Patterns

- **Async-first**: All operations are async using `asyncio`
- **Zero dependencies**: Uses only Python standard library
- **Atomic operations**: Uses `asyncio.Lock` for thread safety
- **Proactive expiration**: Background task cleans up expired keys
- **Atomic persistence**: Save uses temp file + atomic rename

## Common Commands

### Running the Server
```bash
python pyredis_async.py
```

### Testing with netcat
```bash
nc localhost 6379
SET key value
GET key
DEL key
TTL key
INCR counter
INFO
```

### Development Workflow

Since this is a single-file POC with no build system:
1. Directly edit `pyredis_async.py`
2. Test by running the server and using netcat/redis-cli
3. Test embedded usage by importing `CacheEngine` in other scripts

### Key Implementation Details

- **Persistence**: Uses `pickle` to serialize `_data` and `_expire_heap`
- **TTL Management**: Proactive (background) + reactive (on access) expiration
- **Memory Efficiency**: Uses `__slots__` in classes
- **Error Handling**: Comprehensive error handling for all operations
- **Type Safety**: Full type hints throughout

## Important Notes

- This is a POC, not production-ready (no tests, CI/CD, packaging)
- Default port is 6379 (same as Redis)
- Auto-saves to `dump.rdb` every 60 seconds when running as server
- Supports both embedded usage and standalone server modes