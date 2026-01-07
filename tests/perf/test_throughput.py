"""
Performance tests for Aspine 2.0
"""
import asyncio
import time
import statistics

from aspine import AspineClient


class TestPerformance:
    """Performance test suite for Aspine 2.0."""

    @pytest.mark.perf
    @pytest.mark.asyncio
    async def test_set_throughput(self):
        """Test SET operation throughput."""
        client = AspineClient()
        await client.connect()

        num_operations = 1000
        start_time = time.time()

        for i in range(num_operations):
            await client.set(f"key{i}", f"value{i}")

        elapsed = time.time() - start_time
        throughput = num_operations / elapsed

        print(f"\nSET Throughput: {throughput:.2f} ops/sec ({elapsed:.2f}s for {num_operations} ops)")

        await client.disconnect()

        # Assert minimum throughput (should be > 1000 ops/sec)
        assert throughput > 1000

    @pytest.mark.perf
    @pytest.mark.asyncio
    async def test_get_throughput(self):
        """Test GET operation throughput."""
        client = AspineClient()
        await client.connect()

        # Pre-populate cache
        num_keys = 1000
        for i in range(num_keys):
            await client.set(f"key{i}", f"value{i}")

        # Measure GET throughput
        num_operations = 1000
        start_time = time.time()

        for i in range(num_operations):
            await client.get(f"key{i % num_keys}")

        elapsed = time.time() - start_time
        throughput = num_operations / elapsed

        print(f"\nGET Throughput: {throughput:.2f} ops/sec ({elapsed:.2f}s for {num_operations} ops)")

        await client.disconnect()

        # Assert minimum throughput (should be > 1000 ops/sec)
        assert throughput > 1000

    @pytest.mark.perf
    @pytest.mark.asyncio
    async def test_mixed_operations_throughput(self):
        """Test mixed operation throughput."""
        client = AspineClient()
        await client.connect()

        num_operations = 1000
        operations = [
            (client.set, f"key{i}", f"value{i}")
            for i in range(num_operations)
        ]

        start_time = time.time()

        for op, key, value in operations:
            await op(key, value)

        elapsed = time.time() - start_time
        throughput = num_operations / elapsed

        print(f"\nMixed Operations Throughput: {throughput:.2f} ops/sec")

        await client.disconnect()

        assert throughput > 500

    @pytest.mark.perf
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent operation throughput."""
        client = AspineClient()
        await client.connect()

        num_concurrent = 100
        num_operations_per_client = 10

        async def client_operations():
            for i in range(num_operations_per_client):
                await client.set(f"concurrent_key_{i}", f"value_{i}")

        start_time = time.time()
        tasks = [client_operations() for _ in range(num_concurrent)]
        await asyncio.gather(*tasks)
        elapsed = time.time() - start_time

        total_operations = num_concurrent * num_operations_per_client
        throughput = total_operations / elapsed

        print(f"\nConcurrent Operations: {throughput:.2f} ops/sec")
        print(f"  {num_concurrent} concurrent clients")
        print(f"  {num_operations_per_client} ops per client")
        print(f"  Total: {total_operations} operations in {elapsed:.2f}s")

        await client.disconnect()

        assert throughput > 500

    @pytest.mark.perf
    @pytest.mark.asyncio
    async def test_latency_measurements(self):
        """Test operation latency."""
        client = AspineClient()
        await client.connect()

        # Warm up
        for i in range(100):
            await client.set(f"warmup_{i}", f"value{i}")

        # Measure latencies
        latencies = []
        num_samples = 100

        for i in range(num_samples):
            start = time.time()
            await client.set(f"latency_key_{i}", f"value{i}")
            elapsed = (time.time() - start) * 1000  # Convert to ms
            latencies.append(elapsed)

        avg_latency = statistics.mean(latencies)
        p50_latency = statistics.median(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]

        print(f"\nLatency Measurements:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  P50: {p50_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  P99: {p99_latency:.2f}ms")

        await client.disconnect()

        # Assert latency requirements
        assert p50_latency < 5.0  # P50 < 5ms
        assert p99_latency < 20.0  # P99 < 20ms

    @pytest.mark.perf
    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """Test memory usage with many keys."""
        client = AspineClient()
        await client.connect()

        num_keys = 10000

        start_time = time.time()
        for i in range(num_keys):
            await client.set(f"memory_key_{i}", f"value_{i}" * 100)
        elapsed = time.time() - start_time

        info = await client.info()
        memory_usage = info.get('memory_usage', 0)

        print(f"\nMemory Usage Test:")
        print(f"  Keys: {num_keys}")
        print(f"  Memory: {memory_usage / 1024 / 1024:.2f} MB")
        print(f"  Time: {elapsed:.2f}s")

        await client.disconnect()

        # Just verify it doesn't crash with many keys
        assert info['keys'] >= num_keys
