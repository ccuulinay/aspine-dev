#!/usr/bin/env python3
"""
Simple example of using PyRedisAsyncClient.

This script shows basic usage patterns for the client.
"""

import asyncio
from pyredis_async_client import create_client


async def main():
    """Demonstrate basic client usage."""

    # Create and connect client
    print("Connecting to PyRedisAsync server...")
    client = await create_client()

    try:
        # Basic SET/GET
        await client.set("greeting", "Hello from PyRedisAsyncClient!")
        value = await client.get("greeting")
        print(f"Greeting: {value}")

        # Counter operations
        await client.set("visits", "0")  # Initialize counter
        visits = await client.incr("visits")
        print(f"Visit count: {visits}")

        visits = await client.incr("visits")
        print(f"Visit count after increment: {visits}")

        # TTL example
        await client.set("session", "user123", expire=5)
        print("Session set with 5 second TTL")

        # Check TTL
        ttl = await client.ttl("session")
        print(f"Session TTL: {ttl} seconds")

        # Get session value
        session = await client.get("session")
        print(f"Session value: {session}")

        # Wait a bit and check again
        print("Waiting 6 seconds for session to expire...")
        await asyncio.sleep(6)

        expired_session = await client.get("session")
        print(f"Session after expiration: {expired_session}")

        # Show server info
        print("\nServer Information:")
        info = await client.info()
        for key, value in info.items():
            print(f"  {key}: {value}")

    finally:
        # Always disconnect when done
        await client.disconnect()
        print("\nDisconnected from server")


if __name__ == "__main__":
    print("PyRedisAsyncClient Example")
    print("=" * 30)
    asyncio.run(main())