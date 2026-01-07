# Aspine 2.0

[![PyPI version](https://badge.fury.io/py/aspine.svg)](https://badge.fury.io/py/aspine)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Aspine is a **Python-native async + multiprocessing hybrid caching system** that provides high-performance in-memory data storage with zero external dependencies.

## ✨ What's New in 2.0

Aspine 2.0 is a major rewrite that introduces:

- 🚀 **Async-first API** - Modern async/await patterns with context managers
- 🔄 **Hybrid Architecture** - Asyncio for concurrency + Multiprocessing for data isolation
- 📊 **Smart Caching** - LRU eviction with configurable TTL
- 💾 **Optional Persistence** - Automatic save/load for crash recovery
- 📡 **Pub/Sub** - Cache invalidation notifications
- 🎯 **Performance Optimized** - Target: ≤0.5ms GET latency, ≥75k ops/sec
- 🛠️ **Rich CLI** - Typer-based CLI with daemon mode

## 🎯 Quick Start

### Installation

```bash
pip install aspine
```

### Basic Usage (v2.0 Async API)

```python
import asyncio
from aspine import AspineClient

async def main():
    # Use async context manager
    async with AspineClient() as client:
        # Set values
        await client.set("user:1", {"name": "Alice", "age": 30})
        await client.set("counter", 42, ttl=60)  # TTL in seconds

        # Get values
        user = await client.get("user:1")
        print(user)  # {'name': 'Alice', 'age': 30}

        # Batch operations
        await client.mset({
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        })

        async for value in client.mget("key1", "key2", "key3"):
            print(value)

asyncio.run(main())
```

### Starting the Server (CLI)

**Foreground Mode (Blocking):**
```bash
aspine server --port 5116
```

**Background Daemon Mode:**
```bash
aspine server --daemon --port 5116 --persist --log-file /var/log/aspine.log
```

**With Persistence:**
```bash
aspine server --daemon --persist --max-size 10000
```

### Getting Server Info

```bash
aspine info --host localhost --port 5116
```

## 📚 API Reference

### AspineClient

The main client class for async operations.

#### Connection

```python
# Context manager (recommended)
async with AspineClient() as client:
    await client.set("key", "value")

# Manual connection
client = AspineClient()
await client.connect()
# ... use client ...
await client.disconnect()
```

#### Core Operations

| Operation | Method | Description |
|-----------|--------|-------------|
| Set | `await client.set(key, value, ttl=None)` | Store a value with optional TTL |
| Get | `await client.get(key)` | Retrieve a value |
| Delete | `await client.delete(key)` | Delete a key |
| Exists | `await client.exists(key)` | Check if key exists |
| TTL | `await client.ttl(key)` | Get remaining TTL |
| List | `await client.list(pattern=None)` | List all keys (with pattern) |
| Clear | `await client.clear()` | Clear all data |

#### Batch Operations

```python
# Batch set
await client.mset({"key1": "val1", "key2": "val2"}, ttl=60)

# Batch get (async iterator)
async for value in client.mget("key1", "key2", "key3"):
    print(value)
```

#### Persistence

```python
# Save to disk
await client.save("/path/to/cache.rdb")

# Load from disk
await client.load("/path/to/cache.rdb")
```

#### Pub/Sub

```python
# Subscribe to cache invalidation
async for event in client.subscribe("my_key"):
    print(f"Key invalidated: {event['key']}")
```

#### Server Information

```python
info = await client.info()
print(info)
# Output: {'keys': 10, 'memory_usage': 1024, 'uptime': 3600, ...}
```

## 🛠️ CLI Reference

### Server Commands

#### Start Server (Foreground)
```bash
aspine server [OPTIONS]

Options:
  --host TEXT                   Server host address  [default: 127.0.0.1]
  --port INTEGER                Server port  [default: 5116]
  --authkey TEXT                Authentication key  [default: 123456]
  --daemon                      Run as background daemon
  --persist                     Enable disk persistence
  --log-level [DEBUG|INFO|WARNING|ERROR]
                                Logging level  [default: INFO]
  --log-file FILENAME           Log file path
  --pid-file FILENAME           PID file path
  --max-size INTEGER            Maximum cache size  [default: 1000]
```

#### Start Server (Daemon)
```bash
aspine server --daemon --persist --log-file /var/log/aspine.log
```

### Management Commands

#### Get Server Info
```bash
aspine info --host localhost --port 5116
```

#### Stop Daemon Server
```bash
aspine stop --pid-file /var/run/aspine/aspine.pid

# Force kill
aspine stop --force
```

#### Clear Cache
```bash
aspine clear --yes  # Skip confirmation
```

## 🔄 Migration Guide (v1.x → v2.0)

Aspine 2.0 introduces breaking changes for a cleaner, more modern API.

### API Changes

| v1.x (Sync) | v2.0 (Async) | Notes |
|-------------|--------------|-------|
| `client = AspineClient()` | `async with AspineClient() as client:` | Context manager required |
| `client.connect()` | Automatic in context manager | No explicit connect needed |
| `client.set(key, val)` | `await client.set(key, val)` | Now async |
| `client.get(key)` | `await client.get(key)` | Now async |
| `client.is_exist(key)` | `await client.exists(key)` | Renamed for clarity |
| Blocking calls | Async/await pattern | All operations async |

### Example Migration

#### v1.x Code (Old)
```python
from aspine import AspineClient

# Create and connect
client = AspineClient()
client.connect()

# Use cache
client.set("key", "value")
value = client.get("key")
exists = client.is_exist("key")
keys = client.list()
```

#### v2.0 Code (New)
```python
import asyncio
from aspine import AspineClient

async def main():
    # Use context manager
    async with AspineClient() as client:
        # Use cache (now async!)
        await client.set("key", "value")
        value = await client.get("key")
        exists = await client.exists("key")
        keys = await client.list()

asyncio.run(main())
```

### New Features in v2.0

- **TTL Support**: Set expiration time for keys
- **LRU Eviction**: Automatic eviction of least recently used keys
- **Batch Operations**: `mset()` and `mget()` for efficiency
- **Pub/Sub**: Subscribe to cache invalidation events
- **Persistence**: Save/load cache to disk
- **Rich CLI**: Modern command-line interface with daemon mode
- **Performance**: Optimized for high throughput and low latency

## 🏗️ Architecture

Aspine 2.0 uses a hybrid async/multiprocessing architecture:

```
┌─────────────────────────────────────────┐
│         Asyncio Event Loop               │
│  (Client-side Concurrency & I/O)        │
└────────────┬────────────────────────────┘
             │ Queue Communication
             │ (multiprocessing.Queue)
             ▼
┌─────────────────────────────────────────┐
│      Multiprocessing Server             │
│  (Data Isolation & Persistence)         │
│                                         │
│  ┌──────────────────────────────┐       │
│  │   CacheStorage Layer        │       │
│  │  - LRU Eviction             │       │
│  │  - TTL Support               │       │
│  │  - Optional Persistence     │       │
│  └──────────────────────────────┘       │
└─────────────────────────────────────────┘
```

### Key Components

1. **AsyncMPBridge** - Async interface to multiprocessing server
2. **CacheStorage** - Smart cache with LRU and TTL
3. **Queue Protocol** - Message-based communication
4. **Pub/Sub System** - Cache invalidation broadcasting

## 📊 Performance

Target performance metrics (v2.0):

- **GET Latency**: ≤0.5ms (p50), ≤2ms (p99)
- **SET Latency**: ≤1ms (p50)
- **Throughput**: ≥75k ops/sec
- **Memory**: ≤150MB for 10k cached items

### Running Performance Tests

```bash
# Install test dependencies
pip install aspine[dev]

# Run performance tests
pytest tests/perf/test_throughput.py -v -m perf
```

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install aspine[dev]

# Run all tests
pytest tests/

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v

# Run with coverage
pytest tests/ --cov=aspine --cov-report=html
```

### Test Structure

```
tests/
├── unit/               # Unit tests (mocked dependencies)
│   ├── test_cache_storage.py
│   └── ...
├── integration/        # Integration tests (real processes)
│   ├── test_async_client.py
│   └── ...
├── perf/              # Performance tests
│   ├── test_throughput.py
│   └── ...
└── conftest.py        # Shared fixtures
```

## 🔒 Security

Aspine 2.0 uses a simple authentication key mechanism:

```python
# Server
aspine server --authkey "your-secret-key"

# Client
async with AspineClient(authkey="your-secret-key") as client:
    ...
```

**Note**: For production use, consider:
- Running behind a reverse proxy with TLS
- Using network-level security
- Implementing application-level authentication

## 🚀 Deployment

### Docker

```dockerfile
FROM python:3.11-slim

RUN pip install aspine

CMD ["aspine", "server", "--daemon", "--persist", "--log-level", "info"]
```

### Systemd Service

```ini
# /etc/systemd/system/aspine.service
[Unit]
Description=Aspine Cache Server
After=network.target

[Service]
Type=simple
User=aspine
ExecStart=/usr/local/bin/aspine server --daemon --persist --log-file /var/log/aspine.log
Restart=always

[Install]
WantedBy=multi-user.target
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aspine
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aspine
  template:
    metadata:
      labels:
        app: aspine
    spec:
      containers:
      - name: aspine
        image: aspine:latest
        args: ["server", "--daemon", "--persist"]
        ports:
        - containerPort: 5116
```

## 📈 Use Cases

### Caching

```python
from aspine import AspineClient

async def get_user(user_id):
    # Check cache first
    async with AspineClient() as client:
        cached = await client.get(f"user:{user_id}")
        if cached:
            return cached

    # Cache miss - fetch from database
    user = await fetch_from_database(user_id)

    # Store in cache
    async with AspineClient() as client:
        await client.set(f"user:{user_id}", user, ttl=3600)

    return user
```

### Session Store

```python
async def get_session(session_id):
    async with AspineClient() as client:
        session = await client.get(f"session:{session_id}")
        if session:
            return session
    return None
```

### Rate Limiting

```python
async def check_rate_limit(user_id, action):
    key = f"rate:{user_id}:{action}"
    async with AspineClient() as client:
        count = await client.get(key) or 0
        if count >= 10:
            return False
        await client.set(key, count + 1, ttl=60)
        return True
```

## 🐛 Troubleshooting

### Connection Refused

```
ConnectionError: Failed to connect
```

**Solution**: Make sure the server is running:
```bash
aspine server --daemon
```

### Timeout Errors

```
TimeoutError: Get operation timed out after 5.0s
```

**Solution**: Increase timeout or check server responsiveness:
```python
client = AspineClient(timeout=10.0)
```

### Permission Errors (Daemon Mode)

```
PermissionError: [Errno 13] Permission denied
```

**Solution**: Run with appropriate permissions or use custom paths:
```bash
aspine server --daemon --pid-file ~/aspine.pid
```

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md).

### Development Setup

```bash
# Clone repository
git clone https://github.com/ccuulinay/aspine-dev.git
cd aspine-dev

# Install in development mode
pip install -e .[dev]

# Run tests
pytest

# Run performance tests
pytest tests/perf/ -m perf
```

## 📝 License

MIT License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- Inspired by Redis and Memcached
- Built with Python's asyncio and multiprocessing
- Powered by typer for CLI

## 📚 Documentation

- [API Reference](https://aspine.readthedocs.io/)
- [Architecture Guide](docs/architecture.md)
- [Performance Tuning](docs/performance.md)
- [Migration Guide](docs/migration.md)

## 📦 What's Next

See our [roadmap](ROADMAP.md) for upcoming features:

- v2.1: Token-based authentication, distributed cache
- v2.2: TLS encryption, rate limiting
- v2.3: Redis protocol compatibility, database integration

---

**Aspine 2.0** - Fast, Simple, Pythonic Caching
