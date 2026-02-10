#!/usr/bin/env python3
"""
E2E Test Suite for AgentGateway Security Guards

Tests all security guards against local MCP servers:
- PII Guard: Detects/redacts/blocks PII in tool responses
- Tool Poisoning Guard: Blocks poisoned tool descriptions
- Rug Pull Guard: Detects tool definition changes mid-session

Test Configuration:
- Gateway: http://localhost:8080
- PII MCP: http://localhost:8000/mcp (via /pii-test route)
- Tool Poisoning MCP: http://localhost:8010/mcp (via /poison route)
- Rug Pull MCP: http://localhost:8020/mcp (via /rug-pull route)

Usage:
    python tests/e2e_security_guards_test.py
    GATEWAY_URL=http://localhost:8080 python tests/e2e_security_guards_test.py

Transport Selection:
    python tests/e2e_security_guards_test.py                        # Streamable HTTP (default)
    python tests/e2e_security_guards_test.py --transport sse        # SSE transport
    python tests/e2e_security_guards_test.py --transport all        # Run with all transports
"""

import asyncio
import os
import sys
from datetime import datetime

# Import shared MCP client library
from mcp_client import TestResults

# Import guard-specific test suites
from e2e_pii_guard_test import test_pii_guard
from e2e_tool_poisoning_guard_test import test_tool_poisoning_guard
from e2e_rug_pull_guard_test import test_rug_pull_guard


async def run_tests(transport: str = "streamable"):
    """Run all security guard E2E tests.

    Args:
        transport: MCP transport type - "streamable" or "sse"
    """
    gateway_url = os.environ.get("GATEWAY_URL", "http://localhost:8080")

    print("=" * 60)
    print("AgentGateway Security Guards - E2E Test Suite")
    print("=" * 60)
    print(f"\nGateway: {gateway_url}")
    print(f"Transport: {transport}")
    print(f"Started: {datetime.now().isoformat()}")

    results = TestResults()

    # Each guard test is wrapped individually so one failure doesn't skip the rest.
    guards = [
        ("PII (mask)",       lambda: test_pii_guard(gateway_url, "pii-test", results, transport, expect_mode="mask")),
        ("PII (reject)",     lambda: test_pii_guard(gateway_url, "pii-test-reject", results, transport, expect_mode="reject")),
        ("Tool Poisoning",   lambda: test_tool_poisoning_guard(gateway_url, "poison", results, transport)),
        ("Rug Pull",         lambda: test_rug_pull_guard(gateway_url, "rug-pull", results, transport)),
    ]

    for name, test_fn in guards:
        try:
            await test_fn()
        except Exception as e:
            results.add_fail(f"{name} test execution", str(e))
            import traceback
            print(f"\n{name} exception details:\n{traceback.format_exc()}")

    print(f"\nCompleted: {datetime.now().isoformat()}")
    results.print_summary()

    return results


async def run_all_transports():
    """Run tests with all supported transport protocols."""
    transports = ["sse", "streamable"]
    all_passed = True

    for transport in transports:
        print("\n" + "#" * 70)
        print(f"# Running tests with {transport.upper()} transport")
        print("#" * 70)

        results = await run_tests(transport)
        if results.failed > 0:
            all_passed = False

    return all_passed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="E2E Security Guards Test Suite")
    parser.add_argument(
        "--transport", "-t",
        choices=["sse", "streamable", "all"],
        default="streamable",
        help="MCP transport type (default: streamable)"
    )
    args = parser.parse_args()

    if args.transport == "all":
        success = asyncio.run(run_all_transports())
    else:
        results = asyncio.run(run_tests(args.transport))
        success = results.failed == 0

    sys.exit(0 if success else 1)
