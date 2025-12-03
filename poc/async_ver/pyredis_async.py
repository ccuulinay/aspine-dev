import asyncio
import heapq
import time
import os
import pickle
from typing import Any, Dict, List, Optional, Tuple

class CacheEngine:
    """
    A high-performance, in-memory key-value store.
    """
    __slots__ = ('_data', '_expire_heap', '_lock', '_start_time', '_task')

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._expire_heap: List[Tuple[float, str]] = []
        self._lock = asyncio.Lock()
        self._start_time = time.time()
        self._task = asyncio.create_task(self._proactive_expire())

    async def _proactive_expire(self) -> None:
        """
        Proactively expires keys in the background.
        """
        while True:
            async with self._lock:
                await self._remove_expired_keys()
            
            if self._expire_heap:
                sleep_for = self._expire_heap[0][0] - time.time()
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
            else:
                await asyncio.sleep(1)

    async def save(self, filename: str) -> None:
        """
        Saves the cache state to a file.
        """
        async with self._lock:
            temp_filename = f"{filename}.tmp"
            with open(temp_filename, "wb") as f:
                pickle.dump(self._data, f)
                pickle.dump(self._expire_heap, f)
            os.replace(temp_filename, filename)

    async def load(self, filename: str) -> None:
        """
        Loads the cache state from a file.
        """
        if not os.path.exists(filename):
            return
        async with self._lock:
            with open(filename, "rb") as f:
                self._data = pickle.load(f)
                self._expire_heap = pickle.load(f)

    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        """
        Sets a key-value pair with an optional expiration time.
        """
        async with self._lock:
            self._data[key] = value
            if expire:
                expire_at = time.time() + expire
                heapq.heappush(self._expire_heap, (expire_at, key))

    async def get(self, key: str) -> Optional[Any]:
        """
        Gets the value for a key, checking for expiration.
        """
        async with self._lock:
            # The proactive cleaner handles most cases, but a check on get is good for items that expire between checks
            await self._remove_expired_keys()
            return self._data.get(key)
    
    async def delete(self, key: str) -> int:
        """
        Deletes a key.
        """
        async with self._lock:
            if key in self._data:
                del self._data[key]
                # Also remove from expire heap if it's there
                self._expire_heap = [(ts, k) for ts, k in self._expire_heap if k != key]
                heapq.heapify(self._expire_heap)
                return 1
            return 0

    async def ttl(self, key: str) -> int:
        """
        Returns the time-to-live for a key.
        """
        async with self._lock:
            if key not in self._data:
                return -2 # Not found
            
            for expire_at, heap_key in self._expire_heap:
                if heap_key == key:
                    return int(expire_at - time.time())
            
            return -1 # No expiry

    async def incr(self, key: str) -> int:
        """
        Increments the integer value of a key by one.
        """
        async with self._lock:
            try:
                current_value = int(self._data.get(key, 0))
                current_value += 1
                self._data[key] = str(current_value)
                return current_value
            except (ValueError, TypeError):
                raise ValueError("value is not an integer or out of range")

    async def decr(self, key: str) -> int:
        """
        Decrements the integer value of a key by one.
        """
        async with self._lock:
            try:
                current_value = int(self._data.get(key, 0))
                current_value -= 1
                self._data[key] = str(current_value)
                return current_value
            except (ValueError, TypeError):
                raise ValueError("value is not an integer or out of range")

    async def info(self) -> Dict[str, Any]:
        """
        Returns information about the cache.
        """
        return {
            "keys": len(self._data),
            "memory_usage": self._get_memory_usage(),
            "uptime": int(time.time() - self._start_time),
        }
    
    def _get_memory_usage(self) -> int:
        # This is a rough estimate of memory usage.
        # For a more accurate measure, a library like pympler would be needed.
        return sum(
            len(str(k)) + len(str(v)) for k, v in self._data.items()
        )

    async def _remove_expired_keys(self) -> None:
        """
        Removes expired keys from the data store.
        """
        now = time.time()
        while self._expire_heap and self._expire_heap[0][0] < now:
            _, key = heapq.heappop(self._expire_heap)
            if key in self._data:
                # To be absolutely sure, we should also check the key's expiry time directly if we stored it
                # but with the heap, this is the most efficient way.
                del self._data[key]


class CommandParser:
    """
    Parses commands from the client.
    """

    def __init__(self, cache: CacheEngine):
        self._cache = cache

    async def parse(self, data: str) -> str:
        """
        Parses a command and returns the result.
        """
        parts = data.strip().split()
        if not parts:
            return "ERROR: No command specified\r\n"

        command = parts[0].upper()
        args = parts[1:]

        try:
            if command == "SET":
                if len(args) < 2:
                    return "ERROR: Not enough arguments for SET\r\n"
                key, value = args[0], args[1]
                expire = None
                if len(args) > 3 and args[2].upper() == "EX":
                    try:
                        expire = int(args[3])
                    except (ValueError, IndexError):
                        return "ERROR: Invalid expire value\r\n"
                await self._cache.set(key, value, expire)
                return "OK\r\n"
            
            elif command == "GET":
                if len(args) != 1:
                    return "ERROR: Incorrect number of arguments for GET\r\n"
                key = args[0]
                value = await self._cache.get(key)
                if value is None:
                    return "(nil)\r\n"
                return f"{value}\r\n"

            elif command == "DEL":
                if len(args) != 1:
                    return "ERROR: Incorrect number of arguments for DEL\r\n"
                key = args[0]
                result = await self._cache.delete(key)
                return f":{result}\r\n"
            
            elif command == "TTL":
                if len(args) != 1:
                    return "ERROR: Incorrect number of arguments for TTL\r\n"
                key = args[0]
                ttl = await self._cache.ttl(key)
                return f":{ttl}\r\n"

            elif command == "INCR":
                if len(args) != 1:
                    return "ERROR: Incorrect number of arguments for INCR\r\n"
                key = args[0]
                result = await self._cache.incr(key)
                return f":{result}\r\n"

            elif command == "DECR":
                if len(args) != 1:
                    return "ERROR: Incorrect number of arguments for DECR\r\n"
                key = args[0]
                result = await self._cache.decr(key)
                return f":{result}\r\n"

            elif command == "SAVE":
                await self._cache.save("dump.rdb")
                return "OK\r\n"
            
            elif command == "INFO":
                info_data = await self._cache.info()
                # Simple string format for info
                return "\r\n".join(f"{k}:{v}" for k, v in info_data.items()) + "\r\n"

            else:
                return f"ERROR: Unknown command '{command}'\r\n"

        except Exception as e:

            return f"ERROR: {e}\r\n"

        

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, parser: CommandParser):
    """
    Handles a client connection.
    """
    addr = writer.get_extra_info('peername')
    print(f"Accepted connection from {addr}")
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                break
            
            message = data.decode()
            response = await parser.parse(message)
            writer.write(response.encode())

            await writer.drain()
    except asyncio.CancelledError:
        print(f"Connection from {addr} cancelled.")
    except Exception as e:
        print(f"An error occurred with client {addr}: {e}")
    finally:
        print(f"Closing connection from {addr}")
        writer.close()
        await writer.wait_closed()

        

async def main():
    """
    Main function to start the server.
    """
    cache = CacheEngine()
    await cache.load("dump.rdb")
    parser = CommandParser(cache)

    async def client_connected_cb(reader, writer):
        await handle_client(reader, writer, parser)

    server = await asyncio.start_server(
        client_connected_cb, '127.0.0.1', 6379)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    # Periodic save
    async def periodic_save():
        while True:
            await asyncio.sleep(60) # Save every 60 seconds
            print("Periodically saving database...")
            await cache.save("dump.rdb")
            print("Save complete.")

    save_task = asyncio.create_task(periodic_save())

    async with server:
        await server.serve_forever()

        

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down server.")

        