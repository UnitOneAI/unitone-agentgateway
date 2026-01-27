#!/usr/bin/env python3
"""
E2E Test Suite for AgentGateway Tool Poisoning Security Guard

Tests detection and blocking of poisoned tool descriptions.

Test Configuration:
- Gateway: http://localhost:8080
- Tool Poisoning MCP Server: http://localhost:8010/mcp (via /poison route)

Usage:
    python tests/e2e_tool_poisoning_guard_test.py
    GATEWAY_URL=http://localhost:8080 python tests/e2e_tool_poisoning_guard_test.py

Transport Selection:
    python tests/e2e_tool_poisoning_guard_test.py                        # Streamable HTTP (default)
    python tests/e2e_tool_poisoning_guard_test.py --transport sse        # SSE transport
"""

import asyncio
import os
import sys
from datetime import datetime

from mcp_client import create_mcp_client, TestResults

# Default route for tool poisoning guard tests
DEFAULT_ROUTE = "poison"


async def test_tool_poisoning_guard(gateway_url: str, route: str, results: TestResults, transport: str = "sse"):
    """Test tool poisoning security guard functionality."""
    print("\n" + "=" * 60)
    print("TOOL POISONING SECURITY GUARD TESTS")
    print("=" * 60)
    print(f"Route: /{route} -> localhost:8010/mcp")
    print(f"Transport: {transport}")
    print("Expected: Guard should detect and block poisoned tool descriptions\n")

    async with create_mcp_client(gateway_url, route=route, transport=transport) as client:
        # Test 1: Connectivity
        print("[Test 1: Connectivity]")
        conn_result = await client.test_connection()
        if conn_result["success"]:
            results.add_pass("Endpoint reachable", f"Status: {conn_result['status_code']}")
        else:
            results.add_fail("Endpoint connectivity", conn_result.get("error", "Unknown"))
            return

        # Test 2: Initialize session
        print("\n[Test 2: Initialize Session]")
        init_result = await client.initialize(client_name="tool-poisoning-e2e-test")
        if init_result["success"]:
            server_name = init_result.get("server_info", {}).get("serverInfo", {}).get("name", "unknown")
            session_id = init_result.get("session_id") or client.session_header
            results.add_pass("Session initialized", f"Server: {server_name}, Session: {session_id}")
        else:
            results.add_fail("Session initialization", init_result.get("error", "Unknown"))
            return

        # Test 3: List tools - should be blocked if tools have poisoned descriptions
        print("\n[Test 3: List Tools (expect BLOCKED if poisoned)]")
        tools_result = await client.list_tools()

        if tools_result.get("blocked"):
            results.add_pass(
                "Tools list BLOCKED by guard",
                "Guard detected poisoned tool descriptions"
            )
        elif tools_result["success"]:
            # Tools passed through - analyze what we got
            tools = tools_result.get("tools", [])
            tool_names = [t.get("name", "?") for t in tools[:5]]

            # Check if any tool descriptions contain suspicious patterns
            suspicious_patterns = [
                "ignore previous",
                "disregard",
                "override",
                "bypass",
                "system prompt",
                "jailbreak",
                "<script>",
                "eval(",
                "exec(",
            ]

            poisoned_tools = []
            for tool in tools:
                desc = tool.get("description", "").lower()
                for pattern in suspicious_patterns:
                    if pattern in desc:
                        poisoned_tools.append(tool.get("name", "unknown"))
                        break

            if poisoned_tools:
                results.add_warning(
                    f"Potentially poisoned tools passed through: {poisoned_tools}"
                )
                results.add_fail(
                    "Tool poisoning detection",
                    f"Expected guard to block poisoned tools: {poisoned_tools}"
                )
            else:
                results.add_pass(
                    "Tools list retrieved",
                    f"Found {len(tools)} tools: {tool_names}"
                )
                results.add_warning(
                    "Guard may not be active or test server may not have poisoned tools"
                )
        else:
            # Some other error - check if it's guard-related
            error = tools_result.get("error", "Unknown")
            if any(kw in error.lower() for kw in ["poison", "blocked", "guard", "security", "malicious"]):
                results.add_pass("Tools blocked by guard", f"Guard response: {error[:100]}")
            else:
                results.add_fail("List tools", error)

        # Test 4: Try to call a tool (if tools were listed)
        if tools_result["success"] and tools_result.get("tools"):
            print("\n[Test 4: Call Tool (if available)]")
            tools = tools_result.get("tools", [])
            if tools:
                first_tool = tools[0]
                tool_name = first_tool.get("name", "unknown")

                # Try to call the tool with empty/default arguments
                call_result = await client.call_tool(tool_name, {})

                if call_result["success"]:
                    results.add_pass(
                        f"Tool '{tool_name}' called",
                        "Tool executed (guard allows tool calls)"
                    )
                elif call_result.get("blocked"):
                    results.add_pass(
                        f"Tool '{tool_name}' blocked",
                        "Guard blocked tool invocation"
                    )
                else:
                    # Could be invalid arguments, not necessarily a failure
                    error = call_result.get("error", "Unknown")
                    if "argument" in error.lower() or "parameter" in error.lower():
                        results.add_pass(
                            f"Tool '{tool_name}' requires arguments",
                            "Tool call rejected due to missing arguments (expected)"
                        )
                    else:
                        results.add_warning(f"Tool call failed: {error[:100]}")
        else:
            print("\n[Test 4: Skipped - no tools available]")
            results.add_warning("Skipped tool call test - no tools available")

        # Test 5: Verify guard is active by checking for specific patterns
        print("\n[Test 5: Guard Configuration Check]")
        # The presence of blocking behavior indicates the guard is working
        if tools_result.get("blocked"):
            results.add_pass(
                "Guard is active",
                "Tool poisoning guard successfully blocking malicious content"
            )
        else:
            results.add_warning(
                "Guard may not be configured or test server lacks poisoned tools"
            )


async def run_tests(transport: str = "sse"):
    """Run tool poisoning guard E2E tests."""
    gateway_url = os.environ.get("GATEWAY_URL", "http://localhost:8080")
    route = os.environ.get("MCP_ROUTE", DEFAULT_ROUTE)

    print("=" * 60)
    print("AgentGateway Tool Poisoning Guard - E2E Test Suite")
    print("=" * 60)
    print(f"\nGateway: {gateway_url}")
    print(f"Route: /{route}")
    print(f"Transport: {transport}")
    print(f"Started: {datetime.now().isoformat()}")

    results = TestResults()

    try:
        await test_tool_poisoning_guard(gateway_url, route, results, transport)
    except Exception as e:
        results.add_fail("Test execution", str(e))
        import traceback
        print(f"\nException details:\n{traceback.format_exc()}")

    print(f"\nCompleted: {datetime.now().isoformat()}")
    results.print_summary()

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="E2E Tool Poisoning Guard Test Suite")
    parser.add_argument(
        "--transport", "-t",
        choices=["sse", "streamable"],
        default="streamable",
        help="MCP transport type (default: streamable)"
    )
    parser.add_argument(
        "--route", "-r",
        default=os.environ.get("MCP_ROUTE", DEFAULT_ROUTE),
        help=f"MCP route path (default: {DEFAULT_ROUTE})"
    )
    args = parser.parse_args()

    if args.route != DEFAULT_ROUTE:
        os.environ["MCP_ROUTE"] = args.route

    results = asyncio.run(run_tests(args.transport))
    sys.exit(0 if results.failed == 0 else 1)
