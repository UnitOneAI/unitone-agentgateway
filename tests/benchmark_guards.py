#!/usr/bin/env python3
"""
Guard Performance Benchmark — E2E Comparison

Compares end-to-end latency of PII guard (native) vs WASM prompt-injection
guard by sending the same MCP operations through different gateway routes.

Prerequisites:
    1. Start the PII test server:
       cd testservers && uvicorn mcp_test_server.fastmcp_server:mcp.streamable_http_app --host 0.0.0.0 --port 8000

    2. Start the gateway with benchmark config:
       cargo run -F wasm-guards -- --config configs/benchmark_guards.yaml

    3. Run the benchmark:
       python tests/benchmark_guards.py

Routes tested (see configs/benchmark_guards.yaml):
    /bench-baseline  → no guards (baseline)
    /bench-pii       → PII guard only (native)
    /bench-wasm-pi   → WASM prompt-injection guard only
    /bench-both      → PII + WASM prompt-injection
"""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from mcp_client import create_mcp_client, MCPClientBase


# ── Scenarios ────────────────────────────────────────────────────────────────

# Default routes (match configs/benchmark_guards.yaml)
ROUTES = {
    "baseline":    "/bench-baseline",
    "pii_guard":   "/bench-pii",
    "wasm_pi":     "/bench-wasm-pi",
    "both_guards": "/bench-both",
}

TOOL_SCENARIOS = [
    {
        "name": "generate_credit_card",
        "tool": "generate_pii",
        "args": {"pii_type": "credit_card"},
        "description": "Single credit card PII generation",
    },
    {
        "name": "generate_full_record",
        "tool": "generate_full_record",
        "args": {},
        "description": "Full record (personal + identity + financial)",
    },
    {
        "name": "generate_text_with_email",
        "tool": "generate_text_with_pii",
        "args": {"pii_type": "email"},
        "description": "Lorem ipsum text with embedded email",
    },
    {
        "name": "generate_bulk_50",
        "tool": "generate_bulk_pii",
        "args": {"pii_type": "personal", "count": 50},
        "description": "Bulk: 50 personal PII records (large payload)",
    },
    {
        "name": "tools_list",
        "tool": None,   # special: will use list_tools()
        "args": {},
        "description": "tools/list (guard scans tool descriptions)",
    },
]


# ── Result types ─────────────────────────────────────────────────────────────

@dataclass
class LatencyStats:
    min_ms: float = 0.0
    max_ms: float = 0.0
    avg_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    count: int = 0       # total requests with measured latency (allowed + blocked)
    allowed: int = 0     # guard allowed the request
    blocked: int = 0     # guard blocked (denied) the request — still measured
    errors: int = 0      # transport/connection errors — not measured

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "avg_ms": round(self.avg_ms, 2),
            "p50_ms": round(self.p50_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "count": self.count,
            "allowed": self.allowed,
            "blocked": self.blocked,
            "errors": self.errors,
        }


@dataclass
class ScenarioResult:
    scenario: str
    description: str
    route_results: Dict[str, LatencyStats] = field(default_factory=dict)


def percentile(data: List[float], pct: float) -> float:
    if not data:
        return 0.0
    k = (len(data) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(data) - 1)
    return data[f] + (k - f) * (data[c] - data[f])


def compute_stats(
    latencies_ms: List[float], allowed: int, blocked: int, errors: int
) -> LatencyStats:
    if not latencies_ms:
        return LatencyStats(errors=errors, count=0)
    s = sorted(latencies_ms)
    return LatencyStats(
        min_ms=s[0],
        max_ms=s[-1],
        avg_ms=sum(s) / len(s),
        p50_ms=percentile(s, 50),
        p95_ms=percentile(s, 95),
        p99_ms=percentile(s, 99),
        count=len(s),
        allowed=allowed,
        blocked=blocked,
        errors=errors,
    )


# ── Benchmark runner ─────────────────────────────────────────────────────────

async def bench_route(
    gateway_url: str,
    route: str,
    transport: str,
    tool_name: Optional[str],
    tool_args: Dict[str, Any],
    iterations: int,
    warmup: int,
) -> LatencyStats:
    """Run a single benchmark scenario against a single route."""
    client = create_mcp_client(gateway_url, route, transport)

    # Initialize MCP session
    try:
        init_result = await client.initialize(client_name="guard-bench")
    except Exception as e:
        await client.close()
        return LatencyStats(errors=iterations, count=0)
    if not init_result.get("success"):
        await client.close()
        return LatencyStats(errors=iterations, count=0)

    latencies: List[float] = []
    allowed = 0
    blocked = 0
    errors = 0

    # Warmup
    for _ in range(warmup):
        try:
            if tool_name is None:
                await client.list_tools()
            else:
                await client.call_tool(tool_name, tool_args)
        except Exception:
            pass

    # Measured iterations
    for _ in range(iterations):
        start = time.perf_counter()
        try:
            if tool_name is None:
                result = await client.list_tools()
            else:
                result = await client.call_tool(tool_name, tool_args)
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            # Record latency for both allowed and blocked requests —
            # the guard still ran either way, and that's what we measure.
            latencies.append(elapsed_ms)
            if result.get("success"):
                allowed += 1
            else:
                blocked += 1
        except Exception:
            errors += 1

    await client.close()
    return compute_stats(latencies, allowed, blocked, errors)


async def run_all(
    gateway_url: str,
    transport: str,
    iterations: int,
    warmup: int,
    routes: Dict[str, str],
    scenarios: List[Dict[str, Any]],
) -> List[ScenarioResult]:
    """Run all scenarios across all routes."""
    results: List[ScenarioResult] = []

    for scenario in scenarios:
        name = scenario["name"]
        desc = scenario["description"]
        tool = scenario["tool"]
        args = scenario["args"]

        print(f"\n--- Scenario: {desc} ---")
        sr = ScenarioResult(scenario=name, description=desc)

        for label, route in routes.items():
            sys.stdout.write(f"  {label:15s} ... ")
            sys.stdout.flush()

            stats = await bench_route(
                gateway_url=gateway_url,
                route=route,
                transport=transport,
                tool_name=tool,
                tool_args=args,
                iterations=iterations,
                warmup=warmup,
            )
            sr.route_results[label] = stats

            if stats.count > 0:
                status = f"{stats.allowed} ok"
                if stats.blocked > 0:
                    status += f", {stats.blocked} blocked"
                if stats.errors > 0:
                    status += f", {stats.errors} err"
                print(f"avg={stats.avg_ms:7.1f}ms  p50={stats.p50_ms:7.1f}ms  "
                      f"p95={stats.p95_ms:7.1f}ms  p99={stats.p99_ms:7.1f}ms  "
                      f"({status})")
            else:
                print(f"FAILED ({stats.errors} errors)")

        results.append(sr)

    return results


# ── Reporting ────────────────────────────────────────────────────────────────

def print_comparison(results: List[ScenarioResult]):
    """Print a summary comparison table."""
    print("\n" + "=" * 90)
    print("GUARD BENCHMARK COMPARISON")
    print("=" * 90)

    for sr in results:
        baseline = sr.route_results.get("baseline")
        if not baseline or baseline.count == 0:
            print(f"\n  {sr.description}: baseline unavailable, skipping comparison")
            continue

        print(f"\n  {sr.description}")
        print(f"  {'Route':<15s}  {'Avg (ms)':>10s}  {'P50 (ms)':>10s}  {'P95 (ms)':>10s}  "
              f"{'P99 (ms)':>10s}  {'Overhead':>12s}  {'OK':>4s}  {'Blk':>4s}")
        print(f"  {'-'*15}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*12}  {'-'*4}  {'-'*4}")

        for label in ["baseline", "pii_guard", "wasm_pi", "both_guards"]:
            stats = sr.route_results.get(label)
            if not stats:
                continue

            if label == "baseline" or baseline.avg_ms == 0:
                overhead = ""
            else:
                diff = stats.avg_ms - baseline.avg_ms
                pct = (diff / baseline.avg_ms) * 100 if baseline.avg_ms > 0 else 0
                overhead = f"+{diff:.1f} ({pct:+.0f}%)"

            print(f"  {label:<15s}  {stats.avg_ms:10.1f}  {stats.p50_ms:10.1f}  "
                  f"{stats.p95_ms:10.1f}  {stats.p99_ms:10.1f}  {overhead:>12s}  "
                  f"{stats.allowed:4d}  {stats.blocked:4d}")

    print("\n" + "=" * 90)


def save_results(results: List[ScenarioResult], output_path: str):
    """Save results as JSON."""
    out = []
    for sr in results:
        entry = {
            "scenario": sr.scenario,
            "description": sr.description,
            "routes": {k: v.to_dict() for k, v in sr.route_results.items()},
        }
        out.append(entry)

    with open(output_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved to {output_path}")


# ── Main ─────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(
        description="Guard Performance Benchmark — PII vs WASM prompt-injection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Prerequisites:
  1. Start PII test server:  cd testservers && uvicorn mcp_test_server.fastmcp_server:mcp.streamable_http_app --host 0.0.0.0 --port 8000
  2. Start gateway:          cargo run -F wasm-guards -- --config configs/benchmark_guards.yaml
  3. Run benchmark:          python tests/benchmark_guards.py

Examples:
  python tests/benchmark_guards.py                          # Default: 50 iterations
  python tests/benchmark_guards.py -n 200 --warmup 20       # More iterations
  python tests/benchmark_guards.py --output results.json    # Save JSON results
  python tests/benchmark_guards.py --routes pii_guard wasm_pi  # Subset of routes
        """,
    )
    parser.add_argument(
        "-n", "--iterations",
        type=int,
        default=50,
        help="Requests per scenario per route (default: 50)",
    )
    parser.add_argument(
        "-w", "--warmup",
        type=int,
        default=5,
        help="Warmup requests before measurement (default: 5)",
    )
    parser.add_argument(
        "-g", "--gateway",
        default=os.environ.get("GATEWAY_URL", "http://localhost:8080"),
        help="Gateway URL (default: $GATEWAY_URL or http://localhost:8080)",
    )
    parser.add_argument(
        "-t", "--transport",
        choices=["streamable", "sse"],
        default="streamable",
        help="MCP transport (default: streamable)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Save results to JSON file",
    )
    parser.add_argument(
        "--routes",
        nargs="+",
        choices=list(ROUTES.keys()),
        help="Only test specific routes (default: all)",
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        choices=[s["name"] for s in TOOL_SCENARIOS],
        help="Only test specific scenarios (default: all)",
    )

    args = parser.parse_args()

    routes = {k: ROUTES[k] for k in (args.routes or ROUTES.keys())}
    scenarios = [s for s in TOOL_SCENARIOS if not args.scenarios or s["name"] in args.scenarios]

    print("=" * 90)
    print("Guard Performance Benchmark")
    print("=" * 90)
    print(f"Gateway:     {args.gateway}")
    print(f"Transport:   {args.transport}")
    print(f"Iterations:  {args.iterations}")
    print(f"Warmup:      {args.warmup}")
    print(f"Routes:      {', '.join(routes.keys())}")
    print(f"Scenarios:   {', '.join(s['name'] for s in scenarios)}")

    results = await run_all(
        gateway_url=args.gateway,
        transport=args.transport,
        iterations=args.iterations,
        warmup=args.warmup,
        routes=routes,
        scenarios=scenarios,
    )

    print_comparison(results)

    if args.output:
        save_results(results, args.output)


if __name__ == "__main__":
    asyncio.run(main())
