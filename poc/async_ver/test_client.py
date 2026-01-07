#!/usr/bin/env python3
"""
Test script for PyRedisAsyncClient.

This script demonstrates how to use the client to connect to a PyRedisAsync server
and perform various operations.
"""

import asyncio
import sys
from pyredis_async_client import PyRedisAsyncClient, create_client


async def test_basic_operations():
    """Test basic SET/GET operations."""
    print("=== Testing Basic Operations ===")

    client = await create_client()

    try:
        # Test SET and GET
        print("Setting key 'name' to 'PyRedisAsync'...")
        success = await client.set("name", "PyRedisAsync")
        print(f"SET successful: {success}")

        value = await client.get("name")
        print(f"GET 'name': {value}")

        # Test non-existent key
        value = await client.get("nonexistent")
        print(f"GET 'nonexistent': {value}")

        # Test DELETE
        deleted = await client.delete("name")
        print(f"DELETE 'name': {deleted} (1 = deleted, 0 = not found)")

        # Verify deletion
        value = await client.get("name")
        print(f"GET 'name' after deletion: {value}")

    finally:
        await client.disconnect()


async def test_ttl_operations():
    """Test TTL and expiration operations."""
    print("\n=== Testing TTL Operations ===")

    client = await create_client()

    try:
        # Set key with TTL
        print("Setting key 'temp' with 2 second TTL...")
        await client.set("temp", "This will expire", expire=2)

        # Check TTL
        ttl = await client.ttl("temp")
        print(f"TTL of 'temp': {ttl} seconds")

        # Get value before expiration
        value = await client.get("temp")
        print(f"Value before expiration: {value}")

        # Wait for expiration
        print("Waiting 3 seconds for expiration...")
        await asyncio.sleep(3)

        # Check after expiration
        ttl = await client.ttl("temp")
        print(f"TTL of 'temp' after expiration: {ttl}")

        value = await client.get("temp")
        print(f"Value after expiration: {value}")

    finally:
        await client.disconnect()


async def test_numeric_operations():
    """Test INCR and DECR operations."""
    print("\n=== Testing Numeric Operations ===")

    client = await create_client()

    try:
        # Test INCR
        print("Testing INCR...")
        value1 = await client.incr("counter")
        print(f"INCR 'counter': {value1}")

        value2 = await client.incr("counter")
        print(f"INCR 'counter' again: {value2}")

        # Test DECR
        value3 = await client.decr("counter")
        print(f"DECR 'counter': {value3}")

        # Test on non-existent key
        value = await client.incr("new_counter")
        print(f"INCR 'new_counter': {value}")

    finally:
        await client.disconnect()


async def test_info_and_save():
    """Test INFO and SAVE commands."""
    print("\n=== Testing INFO and SAVE ===")

    client = await create_client()

    try:
        # Add some data first
        await client.set("key1", "value1")
        await client.set("key2", "value2")

        # Test INFO
        info = await client.info()
        print("Server INFO:")
        for key, value in info.items():
            print(f"  {key}: {value}")

        # Test SAVE
        print("\nTesting SAVE...")
        success = await client.save()
        print(f"SAVE successful: {success}")

    finally:
        await client.disconnect()


async def test_connection_management():
    """Test connection management and error handling."""
    print("\n=== Testing Connection Management ===")

    # Test manual connect/disconnect
    client = PyRedisAsyncClient()
    print(f"Initial connected state: {client._connected}")

    await client.connect()
    print(f"After connect: {client._connected}")

    # Test ping
    pong = await client.ping()
    print(f"Ping successful: {pong}")

    await client.disconnect()
    print(f"After disconnect: {client._connected}")

    # Test with context manager (will auto-disconnect)
    print("\nTesting with context manager...")
    async with create_client() as client:
        value = await client.get("test_key")
        print(f"Context manager test: {value}")
    print("Context manager auto-disconnected")


async def run_all_tests():
    """Run all test functions."""
    print("Starting PyRedisAsyncClient tests...")
    print("Make sure the PyRedisAsync server is running on localhost:6379")
    print("=" * 60)

    try:
        # Test basic operations
        await test_basic_operations()

        # Test TTL operations
        await test_ttl_operations()

        # Test numeric operations
        await test_numeric_operations()

        # Test info and save
        await test_info_and_save()

        # Test connection management
        await test_connection_management()

        print("\n" + "=" * 60)
        print("All tests completed successfully!")

    except Exception as e:
        print(f"\nTest failed with error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    # Check if server is likely running
    import socket

    def check_server_running():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', 6379))
            sock.close()
            return result == 0
        except:
            return False

    if not check_server_running():
        print("Warning: PyRedisAsync server doesn't appear to be running on localhost:6379")
        print("Please start the server first with: python pyredis_async.py")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)

    # Run tests
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)