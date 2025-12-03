import asyncio
from typing import Optional, Union


class PyRedisAsyncClient:
    """
    A Python client for connecting to PyRedisAsync standalone server.

    This client provides an async interface to interact with the PyRedisAsync
    server, supporting all the major commands like SET, GET, DEL, TTL, etc.
    """

    def __init__(self, host: str = 'localhost', port: int = 6379):
        """
        Initialize the client.

        Args:
            host: Server host address (default: localhost)
            port: Server port (default: 6379)
        """
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to the PyRedisAsync server."""
        if self._connected:
            return

        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            self._connected = True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the server."""
        if self.writer and not self.writer.is_closing():
            self.writer.close()
            await self.writer.wait_closed()
        self._connected = False
        self.reader = None
        self.writer = None

    async def _send_command(self, command: str) -> str:
        """
        Send a command to the server and return the response.

        Args:
            command: The command string to send

        Returns:
            The server response as a string

        Raises:
            ConnectionError: If not connected to server
        """
        if not self._connected or not self.writer:
            raise ConnectionError("Not connected to server")

        # Ensure command ends with newline
        if not command.endswith('\r\n'):
            command += '\r\n'

        try:
            self.writer.write(command.encode())
            await self.writer.drain()

            # Read response
            response = await self.reader.read(1024)
            if not response:
                raise ConnectionError("Connection closed by server")

            return response.decode().strip()

        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Error communicating with server: {e}")

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """
        Set a key-value pair with optional expiration.

        Args:
            key: The key to set
            value: The value to store
            expire: Optional TTL in seconds

        Returns:
            True if successful, False otherwise
        """
        if expire is not None:
            command = f"SET {key} {value} EX {expire}"
        else:
            command = f"SET {key} {value}"

        response = await self._send_command(command)
        return response == "OK"

    async def get(self, key: str) -> Optional[str]:
        """
        Get the value for a key.

        Args:
            key: The key to retrieve

        Returns:
            The value as string, or None if key doesn't exist
        """
        response = await self._send_command(f"GET {key}")

        if response == "(nil)":
            return None
        return response

    async def delete(self, key: str) -> int:
        """
        Delete a key.

        Args:
            key: The key to delete

        Returns:
            1 if key was deleted, 0 if key didn't exist
        """
        response = await self._send_command(f"DEL {key}")
        # Response format: ":1" or ":0"
        return int(response[1:]) if response.startswith(':') else 0

    async def ttl(self, key: str) -> int:
        """
        Get the remaining TTL for a key.

        Args:
            key: The key to check

        Returns:
            TTL in seconds, -1 if key has no expiry, -2 if key doesn't exist
        """
        response = await self._send_command(f"TTL {key}")
        # Response format: ":-2", ":-1", or ":<seconds>"
        return int(response[1:]) if response.startswith(':') else -2

    async def incr(self, key: str) -> int:
        """
        Increment the integer value of a key by 1.

        Args:
            key: The key to increment

        Returns:
            The new value after increment
        """
        response = await self._send_command(f"INCR {key}")
        # Response format: ":<value>"
        return int(response[1:]) if response.startswith(':') else 0

    async def decr(self, key: str) -> int:
        """
        Decrement the integer value of a key by 1.

        Args:
            key: The key to decrement

        Returns:
            The new value after decrement
        """
        response = await self._send_command(f"DECR {key}")
        # Response format: ":<value>"
        return int(response[1:]) if response.startswith(':') else 0

    async def save(self) -> bool:
        """
        Save the current database to disk.

        Returns:
            True if successful, False otherwise
        """
        response = await self._send_command("SAVE")
        return response == "OK"

    async def info(self) -> dict:
        """
        Get server information and statistics.

        Returns:
            Dictionary containing server info
        """
        response = await self._send_command("INFO")

        info_dict = {}
        for line in response.split('\r\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                # Try to convert numeric values
                try:
                    if '.' in value:
                        info_dict[key] = float(value)
                    else:
                        info_dict[key] = int(value)
                except ValueError:
                    info_dict[key] = value

        return info_dict

    async def ping(self) -> bool:
        """
        Check if the server is responsive.

        Returns:
            True if server responds
        """
        try:
            # Send a simple GET command to test connection
            await self._send_command("GET __ping_test__")
            return True
        except:
            return False

    def __enter__(self):
        """Context manager entry (for sync usage)."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures disconnection."""
        if self._connected:
            # We can't await in __exit__, so we'll schedule the disconnect
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule the disconnect
                    asyncio.create_task(self.disconnect())
                else:
                    # Run the disconnect
                    loop.run_until_complete(self.disconnect())
            except:
                pass


# Convenience function for quick usage
async def create_client(host: str = 'localhost', port: int = 6379) -> PyRedisAsyncClient:
    """
    Create and connect a PyRedisAsync client.

    Args:
        host: Server host address
        port: Server port

    Returns:
        Connected PyRedisAsyncClient instance
    """
    client = PyRedisAsyncClient(host, port)
    await client.connect()
    return client