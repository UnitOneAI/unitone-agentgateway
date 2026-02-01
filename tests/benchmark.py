#!/usr/bin/env python3
"""
AgentGateway Benchmark Tool

Measures performance of MCP routes with configurable concurrency.
Use to compare performance with/without security guards enabled.

Usage:
    python tests/benchmark.py --route /pii-test --requests 100 --concurrency 10
    python tests/benchmark.py --route /pii-test --output results.json

Environment Variables:
    GATEWAY_URL: Gateway base URL (default: http://localhost:8080)
"""

import argparse
import asyncio
import json
import os
import statistics
import time
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from mcp_client import create_mcp_client, MCPClientBase


@dataclass
class BenchmarkResult:
    """Benchmark metrics result."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate: float

    latency_min_ms: float
    latency_max_ms: float
    latency_avg_ms: float
    latency_stddev_ms: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float

    throughput_rps: float
    total_duration_sec: float

    errors: Dict[str, int]


def calculate_percentile(data: List[float], percentile: float) -> float:
    """Calculate percentile value from sorted data."""
    if not data:
        return 0.0
    k = (len(data) - 1) * (percentile / 100)
    f = int(k)
    c = f + 1 if f + 1 < len(data) else f
    return data[f] + (k - f) * (data[c] - data[f]) if c != f else data[f]


def calculate_metrics(
    latencies: List[float],
    errors: List[str],
    total_duration: float
) -> BenchmarkResult:
    """Calculate benchmark metrics from raw results."""
    total = len(latencies) + len(errors)
    successful = len(latencies)
    failed = len(errors)

    # Convert to milliseconds and sort for percentile calculation
    latencies_ms = sorted([lat * 1000 for lat in latencies])

    if latencies_ms:
        latency_min = min(latencies_ms)
        latency_max = max(latencies_ms)
        latency_avg = statistics.mean(latencies_ms)
        latency_stddev = statistics.stdev(latencies_ms) if len(latencies_ms) > 1 else 0.0
        latency_p50 = calculate_percentile(latencies_ms, 50)
        latency_p95 = calculate_percentile(latencies_ms, 95)
        latency_p99 = calculate_percentile(latencies_ms, 99)
    else:
        latency_min = latency_max = latency_avg = latency_stddev = 0.0
        latency_p50 = latency_p95 = latency_p99 = 0.0

    error_counts = dict(Counter(errors))
    throughput = total / total_duration if total_duration > 0 else 0.0

    return BenchmarkResult(
        total_requests=total,
        successful_requests=successful,
        failed_requests=failed,
        error_rate=failed / total if total > 0 else 0.0,
        latency_min_ms=round(latency_min, 2),
        latency_max_ms=round(latency_max, 2),
        latency_avg_ms=round(latency_avg, 2),
        latency_stddev_ms=round(latency_stddev, 2),
        latency_p50_ms=round(latency_p50, 2),
        latency_p95_ms=round(latency_p95, 2),
        latency_p99_ms=round(latency_p99, 2),
        throughput_rps=round(throughput, 2),
        total_duration_sec=round(total_duration, 2),
        errors=error_counts
    )


async def execute_operation(
    client: MCPClientBase,
    operation: str,
    tool_name: Optional[str] = None,
    tool_args: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[str]]:
    """Execute a single MCP operation and return success/error."""
    try:
        if operation == "initialize":
            result = await client.initialize(client_name="benchmark-client")
        elif operation == "tools/list":
            result = await client.list_tools()
        elif operation == "tools/call":
            if not tool_name:
                return False, "tool_name required for tools/call"
            result = await client.call_tool(tool_name, tool_args or {})
        else:
            return False, f"Unknown operation: {operation}"

        if result.get("success"):
            return True, None
        else:
            return False, result.get("error", "Unknown error")[:100]
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:80]}"


async def run_benchmark(
    gateway_url: str,
    route: str,
    transport: str,
    operation: str,
    num_requests: int,
    concurrency: int,
    warmup_requests: int = 10,
    tool_name: Optional[str] = None,
    tool_args: Optional[Dict[str, Any]] = None
) -> BenchmarkResult:
    """Run benchmark with concurrent requests using pre-initialized client pool."""
    latencies: List[float] = []
    errors: List[str] = []
    lock = asyncio.Lock()

    # Normalize route (ensure it starts with /)
    if not route.startswith("/"):
        route = "/" + route

    # Create a pool of pre-initialized clients (one per concurrency slot)
    # This eliminates connection setup overhead from measurements
    clients: List[MCPClientBase] = []
    client_locks: List[asyncio.Lock] = []

    print(f"  Initializing {concurrency} client connections...")
    for i in range(concurrency):
        client = create_mcp_client(gateway_url, route, transport)
        if operation != "initialize":
            init_result = await client.initialize(client_name=f"benchmark-pool-{i}")
            if not init_result.get("success"):
                await client.close()
                # Close already created clients
                for c in clients:
                    await c.close()
                raise RuntimeError(f"Failed to initialize client {i}: {init_result.get('error')}")
        clients.append(client)
        client_locks.append(asyncio.Lock())

    print(f"  Client pool ready.")

    async def single_request(request_id: int, record: bool = True):
        # Round-robin client selection
        client_idx = request_id % concurrency
        client = clients[client_idx]
        client_lock = client_locks[client_idx]

        # Serialize access to each client (MCP sessions are stateful)
        async with client_lock:
            start = time.perf_counter()
            success, error = await execute_operation(client, operation, tool_name, tool_args)
            elapsed = time.perf_counter() - start

            if record:
                async with lock:
                    if success:
                        latencies.append(elapsed)
                    else:
                        errors.append(error or "Unknown error")

    # Warmup phase - run requests without recording metrics
    if warmup_requests > 0:
        print(f"  Warmup: {warmup_requests} requests...")
        warmup_tasks = [single_request(i, record=False) for i in range(warmup_requests)]
        await asyncio.gather(*warmup_tasks, return_exceptions=True)

    # Main benchmark
    print(f"  Benchmarking: {num_requests} requests...")
    total_start = time.perf_counter()
    tasks = [single_request(i, record=True) for i in range(num_requests)]
    await asyncio.gather(*tasks, return_exceptions=True)
    total_duration = time.perf_counter() - total_start

    # Cleanup client pool
    for client in clients:
        await client.close()

    return calculate_metrics(latencies, errors, total_duration)


def print_results(
    result: BenchmarkResult,
    route: str,
    operation: str,
    transport: str,
    gateway_url: str,
    concurrency: int
):
    """Print benchmark results to console."""
    print("\n" + "=" * 60)
    print("AgentGateway Benchmark Results")
    print("=" * 60)
    print(f"Gateway:       {gateway_url}")
    print(f"Route:         {route}")
    print(f"Operation:     {operation}")
    print(f"Transport:     {transport}")
    print(f"Requests:      {result.total_requests}")
    print(f"Concurrency:   {concurrency}")
    print("-" * 60)
    print("LATENCY (ms)")
    print(f"  Min:         {result.latency_min_ms}")
    print(f"  Max:         {result.latency_max_ms}")
    print(f"  Avg:         {result.latency_avg_ms}")
    print(f"  Stddev:      {result.latency_stddev_ms}")
    print(f"  P50:         {result.latency_p50_ms}")
    print(f"  P95:         {result.latency_p95_ms}")
    print(f"  P99:         {result.latency_p99_ms}")
    print("-" * 60)
    print("THROUGHPUT")
    print(f"  Total time:  {result.total_duration_sec}s")
    print(f"  Requests/s:  {result.throughput_rps}")
    print("-" * 60)
    print("RELIABILITY")
    success_pct = (result.successful_requests / result.total_requests * 100) if result.total_requests > 0 else 0
    fail_pct = (result.failed_requests / result.total_requests * 100) if result.total_requests > 0 else 0
    print(f"  Success:     {result.successful_requests}/{result.total_requests} ({success_pct:.1f}%)")
    print(f"  Failed:      {result.failed_requests}/{result.total_requests} ({fail_pct:.1f}%)")

    if result.errors:
        print("\n  Error breakdown:")
        for error, count in sorted(result.errors.items(), key=lambda x: -x[1]):
            print(f"    {error}: {count}")

    print("=" * 60)


def save_json(
    result: BenchmarkResult,
    route: str,
    operation: str,
    transport: str,
    gateway_url: str,
    concurrency: int,
    output_path: str
):
    """Save benchmark results to JSON file."""
    output = {
        "metadata": {
            "route": route,
            "operation": operation,
            "transport": transport,
            "gateway_url": gateway_url,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_requests": result.total_requests,
            "concurrency": concurrency
        },
        "latency_ms": {
            "min": result.latency_min_ms,
            "max": result.latency_max_ms,
            "avg": result.latency_avg_ms,
            "stddev": result.latency_stddev_ms,
            "p50": result.latency_p50_ms,
            "p95": result.latency_p95_ms,
            "p99": result.latency_p99_ms
        },
        "throughput": {
            "total_duration_sec": result.total_duration_sec,
            "requests_per_sec": result.throughput_rps
        },
        "reliability": {
            "successful": result.successful_requests,
            "failed": result.failed_requests,
            "error_rate": round(result.error_rate, 4),
            "errors": result.errors
        }
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_path}")


async def main():
    parser = argparse.ArgumentParser(
        description="AgentGateway Benchmark Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic benchmark
  python benchmark.py --route /pii-test

  # High concurrency benchmark
  python benchmark.py --route /pii-test --requests 500 --concurrency 50

  # Save results to JSON
  python benchmark.py --route /pii-test --output results.json

  # Benchmark specific operation
  python benchmark.py --route /pii-test --operation tools/call --tool-name generate_pii
        """
    )

    parser.add_argument(
        "--route", "-r",
        required=True,
        help="Route to benchmark (e.g., pii-test, poison, rug-pull)"
    )
    parser.add_argument(
        "--requests", "-n",
        type=int,
        default=100,
        help="Total number of requests (default: 100)"
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=10,
        help="Number of concurrent requests (default: 10)"
    )
    parser.add_argument(
        "--gateway", "-g",
        default=os.environ.get("GATEWAY_URL", "http://localhost:8080"),
        help="Gateway URL (default: GATEWAY_URL env or http://localhost:8080)"
    )
    parser.add_argument(
        "--transport", "-t",
        choices=["sse", "streamable"],
        default="streamable",
        help="MCP transport type (default: streamable)"
    )
    parser.add_argument(
        "--operation", "-o",
        choices=["initialize", "tools/list", "tools/call"],
        default="tools/list",
        help="MCP operation to benchmark (default: tools/list)"
    )
    parser.add_argument(
        "--tool-name",
        help="Tool name for tools/call operation"
    )
    parser.add_argument(
        "--tool-args",
        default="{}",
        help="Tool arguments as JSON string for tools/call operation (default: {})"
    )
    parser.add_argument(
        "--output",
        help="Output file path for JSON results"
    )
    parser.add_argument(
        "--warmup", "-w",
        type=int,
        default=10,
        help="Number of warmup requests before benchmark (default: 10)"
    )

    args = parser.parse_args()

    # Parse tool args
    tool_args = {}
    if args.tool_args:
        try:
            tool_args = json.loads(args.tool_args)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON for --tool-args: {e}")
            print(f"Received: {repr(args.tool_args)}")
            print("Tip: On Windows, use: --tool-args \"{\\\"key\\\": \\\"value\\\"}\"")
            return 1

    # Validate tools/call requirements
    if args.operation == "tools/call" and not args.tool_name:
        print("Error: --tool-name required for tools/call operation")
        return 1

    print("=" * 60)
    print("AgentGateway Benchmark")
    print("=" * 60)
    print(f"Gateway:     {args.gateway}")
    print(f"Route:       {args.route}")
    print(f"Operation:   {args.operation}")
    print(f"Transport:   {args.transport}")
    print(f"Requests:    {args.requests}")
    print(f"Concurrency: {args.concurrency}")
    print(f"Warmup:      {args.warmup}")
    print("-" * 60)

    try:
        result = await run_benchmark(
            gateway_url=args.gateway,
            route=args.route,
            transport=args.transport,
            operation=args.operation,
            num_requests=args.requests,
            concurrency=args.concurrency,
            warmup_requests=args.warmup,
            tool_name=args.tool_name,
            tool_args=tool_args
        )

        print_results(
            result=result,
            route=args.route,
            operation=args.operation,
            transport=args.transport,
            gateway_url=args.gateway,
            concurrency=args.concurrency
        )

        if args.output:
            save_json(
                result=result,
                route=args.route,
                operation=args.operation,
                transport=args.transport,
                gateway_url=args.gateway,
                concurrency=args.concurrency,
                output_path=args.output
            )

        return 0 if result.error_rate < 0.5 else 1

    except Exception as e:
        print(f"\nBenchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
