#!/usr/bin/env python3
"""
E2E Test Suite for AgentGateway Security Guards

Tests tool_poisoning and rug_pull security guards against local MCP servers.

Test Configuration:
- Gateway: http://localhost:8080
- Tool Poisoning MCP: http://localhost:8010/mcp (via /poison route)
- Rug Pull MCP: http://localhost:8020/mcp (via /rug-pull route)

Usage:
    python tests/e2e_security_guards_test.py
    GATEWAY_URL=http://localhost:8080 python tests/e2e_security_guards_test.py

Transport Selection:
    MCP_TRANSPORT=streamable python tests/e2e_security_guards_test.py  # Streamable HTTP (default)
    MCP_TRANSPORT=sse python tests/e2e_security_guards_test.py         # SSE transport
"""

import asyncio
import os
import sys
from datetime import datetime

# Import shared MCP client library
from mcp_client import create_mcp_client, TestResults


async def test_tool_poisoning(gateway_url: str, results: TestResults, transport: str = "streamable"):
    """Test tool poisoning security guard."""
    print("\n" + "=" * 60)
    print("TOOL POISONING GUARD TESTS")
    print("=" * 60)
    print(f"Route: /poison -> localhost:8010")
    print(f"Transport: {transport}")
    print("Expected: Guard should block poisoned tool descriptions\n")

    async with create_mcp_client(gateway_url, route="poison", transport=transport) as client:
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
        init_result = await client.initialize(client_name="security-guards-e2e-test")
        if init_result["success"]:
            server_name = init_result.get("server_info", {}).get("serverInfo", {}).get("name", "unknown")
            session_id = init_result.get("session_id") or client.session_header
            results.add_pass("Session initialized", f"Server: {server_name}, Session: {session_id}")
        else:
            results.add_fail("Session initialization", init_result.get("error", "Unknown"))
            return

        # Test 3: List tools - should be blocked
        print("\n[Test 3: List Tools (expect BLOCKED)]")
        tools_result = await client.list_tools()

        if tools_result.get("blocked"):
            results.add_pass(
                "Tools list BLOCKED by guard",
                f"Guard detected poisoned tool descriptions"
            )
        elif tools_result["success"]:
            # Tools passed through - guard may not be active or patterns not matched
            tools = tools_result.get("tools", [])
            tool_names = [t.get("name", "?") for t in tools[:5]]
            results.add_warning(
                f"Tools passed through (guard may not be blocking): {tool_names}"
            )
            results.add_fail(
                "Tool poisoning detection",
                "Expected guard to block poisoned tools but they passed through"
            )
        else:
            # Some other error
            error = tools_result.get("error", "Unknown")
            if "poison" in error.lower() or "blocked" in error.lower() or "guard" in error.lower():
                results.add_pass("Tools blocked", f"Guard response: {error[:100]}")
            else:
                results.add_fail("List tools", error)


async def test_rug_pull(gateway_url: str, results: TestResults, transport: str = "streamable"):
    """Test rug pull security guard."""
    print("\n" + "=" * 60)
    print("RUG PULL GUARD TESTS")
    print("=" * 60)
    print(f"Route: /rug-pull -> localhost:8020")
    print(f"Transport: {transport}")
    print("Tests baseline establishment, change detection, session vs global scope\n")

    ROUTE = "rug-pull"

    # Test 1: Connectivity
    print("[Test 1: Connectivity]")
    async with create_mcp_client(gateway_url, route=ROUTE, transport=transport) as client:
        conn_result = await client.test_connection()
        if conn_result["success"]:
            results.add_pass("Endpoint reachable", f"Status: {conn_result['status_code']}")
        else:
            results.add_fail("Endpoint connectivity", conn_result.get("error", "Unknown"))
            return

    # Test 2: Initialize and reset state
    print("\n[Test 2: Initialize & Reset State]")
    async with create_mcp_client(gateway_url, route=ROUTE, transport=transport) as client:
        init_result = await client.initialize(client_name="security-guards-e2e-test")
        if not init_result["success"]:
            results.add_fail("Session initialization", init_result.get("error", "Unknown"))
            return
        session_id = init_result.get("session_id") or client.session_header
        results.add_pass("Session initialized", f"Session: {session_id}")

        # Reset global state for clean test
        reset_result = await client.call_tool("reset_global_rug", {})
        if reset_result["success"]:
            results.add_pass("Global state reset")
        else:
            results.add_warning(f"Could not reset state: {reset_result.get('error', 'Unknown')}")

    # Test 3: Baseline establishment
    print("\n[Test 3: Baseline Establishment]")
    async with create_mcp_client(gateway_url, route=ROUTE, transport=transport) as client:
        await client.initialize(client_name="security-guards-e2e-test")

        tools_result = await client.list_tools()
        if tools_result["success"]:
            tools = tools_result.get("tools", [])
            tool_names = [t.get("name", "?") for t in tools]
            results.add_pass(
                "Baseline established",
                f"Tools: {', '.join(tool_names)}"
            )
        else:
            results.add_fail("Baseline establishment", tools_result.get("error", "Unknown"))
            return

        # Test 4: Unchanged tools pass
        print("\n[Test 4: Unchanged Tools Pass]")
        tools_result2 = await client.list_tools()
        if tools_result2["success"]:
            results.add_pass("Unchanged tools allowed")
        else:
            if tools_result2.get("blocked"):
                results.add_fail("Unchanged detection", "Guard incorrectly blocked unchanged tools")
            else:
                results.add_fail("Second list", tools_result2.get("error", "Unknown"))

        # Test 5: Trigger session rug pull
        print("\n[Test 5: Trigger Session Rug Pull]")
        trigger_result = await client.call_tool("get_weather", {"location": "test"})
        if trigger_result["success"]:
            results.add_pass("get_weather called (triggers session rug)")
        else:
            results.add_fail("Trigger session rug", trigger_result.get("error", "Unknown"))
            return

        # Test 6: Detect session rug pull
        print("\n[Test 6: Detect Session Rug Pull]")
        tools_after_rug = await client.list_tools()
        if tools_after_rug.get("blocked") or not tools_after_rug["success"]:
            error = tools_after_rug.get("error", "blocked")
            results.add_pass(
                "Session rug pull DETECTED",
                f"Guard blocked after tool changes: {str(error)[:100]}"
            )
        else:
            results.add_fail(
                "Session rug pull detection",
                "Expected guard to block but tools passed through"
            )

    # Test 7: New session after session rug (should get fresh baseline)
    print("\n[Test 7: New Session After Session Rug]")
    async with create_mcp_client(gateway_url, route=ROUTE, transport=transport) as client2:
        await client2.initialize(client_name="security-guards-e2e-test")
        tools_new_session = await client2.list_tools()

        if tools_new_session["success"]:
            results.add_pass(
                "New session established fresh baseline",
                "Session-level rug doesn't affect new sessions"
            )
        else:
            # Could be blocked if global state was affected
            if tools_new_session.get("blocked"):
                results.add_warning("New session blocked - may be residual global state")
            results.add_fail("New session baseline", tools_new_session.get("error", "Unknown"))

    # Test 8: Reset and test global rug pull
    print("\n[Test 8: Reset for Global Rug Test]")
    async with create_mcp_client(gateway_url, route=ROUTE, transport=transport) as client3:
        await client3.initialize(client_name="security-guards-e2e-test")
        reset_result = await client3.call_tool("reset_global_rug", {})
        if reset_result["success"]:
            results.add_pass("State reset for global test")
        else:
            results.add_warning(f"Reset failed: {reset_result.get('error', 'Unknown')}")

    # Test 9-11: Global rug pull detection
    # The key insight: baseline is established per-session when tools/list is first called.
    # Global rug pull changes MCP server's response for ALL clients.
    # Detection: A session that established baseline BEFORE the rug pull should detect
    # the change when it calls tools/list AFTER the rug pull.
    print("\n[Test 9: Cross-Session Global Rug Pull Detection]")
    print("  Setting up: Client A establishes baseline, Client B triggers global rug,")
    print("  Client A detects change on next tools/list")

    # Client A: establish baseline with clean tools
    client_a = create_mcp_client(gateway_url, route=ROUTE, transport=transport)
    await client_a.client.__aenter__()
    await client_a.initialize(client_name="security-guards-e2e-test")

    baseline_a = await client_a.list_tools()
    if not baseline_a["success"]:
        results.add_fail("Client A baseline", baseline_a.get("error", "Unknown"))
        await client_a.close()
        return
    results.add_pass("Client A established baseline", f"Tools: {[t.get('name') for t in baseline_a.get('tools', [])]}")

    # Client B: trigger global rug pull (changes MCP server for everyone)
    print("\n[Test 10: Trigger Global Rug via Client B]")
    async with create_mcp_client(gateway_url, route=ROUTE, transport=transport) as client_b:
        await client_b.initialize(client_name="security-guards-e2e-test")
        global_trigger = await client_b.call_tool("get_global_weather", {"location": "test"})
        if global_trigger["success"]:
            results.add_pass("Client B triggered global rug (get_global_weather)")
        else:
            results.add_fail("Trigger global rug", global_trigger.get("error", "Unknown"))
            await client_a.close()
            return

    # Client A: should detect the rug pull (tools changed from baseline)
    print("\n[Test 11: Client A Detects Global Rug Pull]")
    tools_after_rug = await client_a.list_tools()
    await client_a.close()

    if tools_after_rug.get("blocked") or not tools_after_rug["success"]:
        results.add_pass(
            "Client A DETECTED global rug pull",
            f"Guard blocked: tools changed from baseline"
        )
    else:
        results.add_fail(
            "Global rug pull detection",
            "Client A should detect tools changed but they passed through"
        )

    # Note: A NEW session connecting after global rug would see corrupted tools
    # as its baseline - this is expected behavior (guard can't know the "original" state)
    print("\n[Test 12: New Session After Global Rug (expected: establishes new baseline)]")
    async with create_mcp_client(gateway_url, route=ROUTE, transport=transport) as client_c:
        await client_c.initialize(client_name="security-guards-e2e-test")
        new_baseline = await client_c.list_tools()

        if new_baseline["success"]:
            results.add_pass(
                "New session establishes baseline (as expected)",
                "Guard cannot detect rug for sessions without prior baseline"
            )
        else:
            # This might happen if guard has some global state
            results.add_warning(f"New session blocked: {new_baseline.get('error', 'Unknown')}")

    # Test 13: Cleanup
    print("\n[Test 13: Cleanup]")
    async with create_mcp_client(gateway_url, route=ROUTE, transport=transport) as cleanup_client:
        await cleanup_client.initialize(client_name="security-guards-e2e-test")
        cleanup = await cleanup_client.call_tool("reset_global_rug", {})
        if cleanup["success"]:
            results.add_pass("Cleanup complete")
        else:
            results.add_warning(f"Cleanup failed: {cleanup.get('error', 'Unknown')}")


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

    try:
        await test_tool_poisoning(gateway_url, results, transport)
        await test_rug_pull(gateway_url, results, transport)
    except Exception as e:
        results.add_fail("Test execution", str(e))
        import traceback
        print(f"\nException details:\n{traceback.format_exc()}")

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
        default=os.environ.get("MCP_TRANSPORT", "streamable"),
        help="MCP transport type (default: streamable, or MCP_TRANSPORT env var)"
    )
    args = parser.parse_args()

    if args.transport == "all":
        success = asyncio.run(run_all_transports())
    else:
        results = asyncio.run(run_tests(args.transport))
        success = results.failed == 0

    sys.exit(0 if success else 1)
