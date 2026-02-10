#!/usr/bin/env python3
"""
E2E Test Suite for AgentGateway Rug Pull Security Guard

Tests detection of tool definition changes (rug pull attacks) where an MCP server
changes its tool definitions after initial baseline establishment.

Tests 1-13: Core rug pull behavior (session vs global scope, baseline, detection)
Tests 14-22: Mutation mode coverage (description, schema, remove, add)

The guard detects 4 change types with configurable risk weights:
  - description change (default weight 2)
  - schema change      (default weight 3)
  - tool removal        (default weight 3)
  - tool addition       (default weight 1)

Blocking occurs when cumulative risk_score >= risk_threshold (default 5).

Each mutation mode uses a dedicated gateway route with its own target name,
so the guard tracks a separate baseline per mode. This avoids the permanent
server blocking that would otherwise prevent sequential mode testing.

Test Configuration:
- Gateway: http://localhost:8080
- Rug Pull MCP Server: http://localhost:8020/mcp
- Routes: /rug-pull (core), /rug-pull-desc, /rug-pull-schema,
          /rug-pull-remove, /rug-pull-add (per-mode)

Usage:
    python tests/e2e_rug_pull_guard_test.py
    GATEWAY_URL=http://localhost:8080 python tests/e2e_rug_pull_guard_test.py

Transport Selection:
    MCP_TRANSPORT=streamable python tests/e2e_rug_pull_guard_test.py
    MCP_TRANSPORT=sse python tests/e2e_rug_pull_guard_test.py
"""

import asyncio
import os
import sys
from datetime import datetime

from mcp_client import create_mcp_client, TestResults

# Default route for rug pull guard tests
DEFAULT_ROUTE = "rug-pull"


async def _reset_rug_pull_state(gateway_url: str, route: str, transport: str, label: str = ""):
    """Forcibly reset both session and global rug pull state on the MCP server.

    Opens a fresh session on the given route, calls reset_session_rug and
    reset_global_rug, then closes.  Silently swallows errors so it never
    breaks the test flow.
    """
    tag = f" ({label})" if label else ""
    try:
        async with create_mcp_client(gateway_url, route=route, transport=transport) as c:
            await c.initialize(client_name="rug-pull-e2e-test")
            r1 = await c.call_tool("reset_session_rug", {})
            r2 = await c.call_tool("reset_global_rug", {})
            ok = r1.get("success") and r2.get("success")
            if not ok:
                print(f"    [reset{tag}] session={r1.get('success')} global={r2.get('success')}")
    except Exception as e:
        print(f"    [reset{tag}] exception: {e}")


async def test_rug_pull_guard(gateway_url: str, route: str, results: TestResults, transport: str = "sse"):
    """Test rug pull security guard functionality."""
    print("\n" + "=" * 60)
    print("RUG PULL SECURITY GUARD TESTS")
    print("=" * 60)
    print(f"Route: /{route} -> localhost:8020/mcp")
    print(f"Transport: {transport}")
    print("Tests baseline establishment, change detection, session vs global scope\n")

    # Test 1: Connectivity
    print("[Test 1: Connectivity]")
    async with create_mcp_client(gateway_url, route=route, transport=transport) as client:
        conn_result = await client.test_connection()
        if conn_result["success"]:
            results.add_pass("Endpoint reachable", f"Status: {conn_result['status_code']}")
        else:
            results.add_fail("Endpoint connectivity", conn_result.get("error", "Unknown"))
            return

    # Test 2: Initialize and reset state
    print("\n[Test 2: Initialize & Reset State]")
    async with create_mcp_client(gateway_url, route=route, transport=transport) as client:
        init_result = await client.initialize(client_name="rug-pull-e2e-test")
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
    async with create_mcp_client(gateway_url, route=route, transport=transport) as client:
        await client.initialize(client_name="rug-pull-e2e-test")

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
    # NOTE: Do NOT reset rug pull state here. Each initialize() calls
    # reset_all_security_guards() which clears baselines synchronously, then
    # spawns a background establish_security_baselines() task.  Adding a
    # _reset_rug_pull_state() before this would spawn a SECOND background task
    # that races with Test 7's own baseline task, causing sporadic score-15
    # failures when the stale task's malicious baseline overwrites the fresh one.
    print("\n[Test 7: New Session After Session Rug]")
    async with create_mcp_client(gateway_url, route=route, transport=transport) as client2:
        await client2.initialize(client_name="rug-pull-e2e-test")
        tools_new_session = await client2.list_tools()

        if tools_new_session["success"]:
            results.add_pass(
                "New session established fresh baseline",
                "Session-level rug doesn't affect new sessions"
            )
        else:
            if tools_new_session.get("blocked"):
                results.add_warning("New session blocked - may be residual global state")
            results.add_fail("New session baseline", tools_new_session.get("error", "Unknown"))

    # Tests 8-11: Global rug pull detection (single session)
    #
    # Why single session: the gateway calls reset_all_security_guards() on every
    # initialize(), which is a GLOBAL operation — it wipes ALL server baselines,
    # not just the new session's.  A two-client test (Client A baseline, Client B
    # triggers rug) fails because Client B's initialize() destroys Client A's
    # baseline.  Using one session avoids this; the guard doesn't care who
    # triggered the rug — it just compares tools against baseline.
    print("\n[Test 8: Reset for Global Rug Test]")
    async with create_mcp_client(gateway_url, route=route, transport=transport) as client3:
        await client3.initialize(client_name="rug-pull-e2e-test")
        reset_result = await client3.call_tool("reset_global_rug", {})
        if reset_result["success"]:
            results.add_pass("State reset for global test")
        else:
            results.add_warning(f"Reset failed: {reset_result.get('error', 'Unknown')}")

        # Test 9: Establish baseline (clean tools)
        print("\n[Test 9: Establish Baseline for Global Rug Test]")
        baseline = await client3.list_tools()
        if not baseline["success"]:
            results.add_fail("Global rug baseline", baseline.get("error", "Unknown"))
            return
        results.add_pass(
            "Baseline established",
            f"Tools: {[t.get('name') for t in baseline.get('tools', [])]}"
        )

        # Test 10: Trigger global rug pull (changes MCP server for ALL sessions)
        print("\n[Test 10: Trigger Global Rug Pull]")
        global_trigger = await client3.call_tool("get_global_weather", {"location": "test"})
        if global_trigger["success"]:
            results.add_pass("Global rug triggered (get_global_weather)")
        else:
            results.add_fail("Trigger global rug", global_trigger.get("error", "Unknown"))
            return

        # Test 11: Detect global rug pull
        # Guard compares current tools (modified by global rug) against baseline
        print("\n[Test 11: Detect Global Rug Pull]")
        tools_after_rug = await client3.list_tools()

        if tools_after_rug.get("blocked") or not tools_after_rug["success"]:
            results.add_pass(
                "Global rug pull DETECTED",
                "Guard blocked: tools changed from baseline"
            )
        else:
            results.add_fail(
                "Global rug pull detection",
                "Should detect tools changed but they passed through"
            )

    # NOTE: Do NOT reset rug pull state here — same background task race as
    # between tests 6→7.  Test 12's initialize() handles the guard reset.

    # Test 12: New session after global rug
    # Note: A NEW session connecting after global rug would see corrupted tools
    # as its baseline - this is expected behavior (guard can't know the "original" state)
    print("\n[Test 12: New Session After Global Rug (expected: establishes new baseline)]")
    async with create_mcp_client(gateway_url, route=route, transport=transport) as client_c:
        await client_c.initialize(client_name="rug-pull-e2e-test")
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
    await _reset_rug_pull_state(gateway_url, route, transport, "core cleanup")
    results.add_pass("Cleanup complete")

    # ------------------------------------------------------------------
    # Tests 14-22: Mutation mode coverage
    # Each mode uses a SEPARATE gateway route (different target name)
    # so the guard tracks an independent baseline per mode.
    # ------------------------------------------------------------------
    await test_rug_pull_modes(gateway_url, route, results, transport)


# Mapping from mutation mode to its dedicated gateway route.
# Each route points to the same MCP server (port 8020) but with a different
# target name, so the rug pull guard tracks a separate baseline per mode.
MODE_ROUTES = {
    "description": "rug-pull-desc",
    "schema": "rug-pull-schema",
    "remove": "rug-pull-remove",
    "add": "rug-pull-add",
}


async def _test_single_mode(
    gateway_url: str,
    core_route: str,
    results: TestResults,
    transport: str,
    mode: str,
    test_num: int,
    expect_blocked: bool,
):
    """Helper: reset state, set mode, trigger rug pull, verify outcome.

    Uses a mode-specific route so the guard tracks an independent baseline,
    avoiding interference from core tests or other modes.

    Args:
        core_route: The main rug-pull route (used for setup tool calls).
        mode: Mutation mode to test (description, schema, remove, add).
        test_num: Starting test number for display.
        expect_blocked: Whether the guard should block tools/list after rug pull.
    """
    mode_route = MODE_ROUTES[mode]
    label = f"mode={mode}"
    block_label = "BLOCKED" if expect_blocked else "ALLOWED"

    # Step A: Reset server and set mode (via mode route — tool calls don't
    # trigger the rug pull guard, only tools/list responses do)
    print(f"\n[Test {test_num}: Setup {label}]")
    async with create_mcp_client(gateway_url, route=mode_route, transport=transport) as setup:
        await setup.initialize(client_name="rug-pull-e2e-test")
        reset = await setup.call_tool("reset_global_rug", {})
        if not reset["success"]:
            results.add_warning(f"Reset failed for {label}: {reset.get('error', '')[:80]}")

        mode_result = await setup.call_tool("set_rug_pull_mode", {"mode": mode})
        if mode_result["success"]:
            results.add_pass(f"Mode set to '{mode}'")
        else:
            results.add_fail(f"Set mode '{mode}'", mode_result.get("error", "Unknown"))
            return

    # Step B: New session on mode route — baseline, trigger, verify
    print(f"\n[Test {test_num + 1}: {label} -> expect {block_label}]")
    async with create_mcp_client(gateway_url, route=mode_route, transport=transport) as client:
        await client.initialize(client_name="rug-pull-e2e-test")

        # Check server state before baseline
        status = await client.call_tool("get_rug_status", {})
        if status["success"]:
            print(f"    Server state before baseline: {status['result']}")

        # Establish baseline (guard sees benign tools for this target name)
        baseline = await client.list_tools()
        if not baseline["success"]:
            results.add_fail(f"{label} baseline", baseline.get("error", "Unknown"))
            return

        baseline_names = [t.get("name", "?") for t in baseline.get("tools", [])]
        print(f"    Baseline tools ({len(baseline_names)}): {baseline_names}")

        # Trigger rug pull (tool call — guard doesn't process this)
        trigger = await client.call_tool("get_weather", {"location": "test"})
        if not trigger["success"]:
            results.add_fail(f"{label} trigger", trigger.get("error", "Unknown"))
            return

        # Check server state after trigger
        status2 = await client.call_tool("get_rug_status", {})
        if status2["success"]:
            print(f"    Server state after trigger: {status2['result']}")

        # Verify detection (guard compares modified tools against baseline)
        after_rug = await client.list_tools()
        was_blocked = after_rug.get("blocked") or not after_rug["success"]

        if not was_blocked:
            after_names = [t.get("name", "?") for t in after_rug.get("tools", [])]
            print(f"    Post-rug tools ({len(after_names)}): {after_names}")

        if expect_blocked:
            if was_blocked:
                results.add_pass(
                    f"{label}: tools/list BLOCKED (score >= threshold)",
                    f"Guard detected {mode} changes (baseline: {baseline_names})"
                )
            else:
                after_names = [t.get("name", "?") for t in after_rug.get("tools", [])]
                results.add_fail(
                    f"{label}: expected BLOCKED",
                    f"Tools passed through: {after_names}"
                )
        else:
            if not was_blocked:
                after_names = [t.get("name", "?") for t in after_rug.get("tools", [])]
                results.add_pass(
                    f"{label}: tools/list ALLOWED (score < threshold)",
                    f"Guard tolerated {mode} change (tools: {after_names})"
                )
            else:
                error = after_rug.get("error", "blocked")
                results.add_fail(
                    f"{label}: expected ALLOWED but was BLOCKED",
                    f"Guard over-blocked: {str(error)[:120]}"
                )

    # Forcibly reset after mode test
    await _reset_rug_pull_state(gateway_url, mode_route, transport, label)


async def test_rug_pull_modes(
    gateway_url: str,
    route: str,
    results: TestResults,
    transport: str,
):
    """Tests 14-22: Exercise each mutation mode to cover all 4 guard change types.

    Each mode uses a dedicated gateway route with a unique target name, so
    the rug pull guard tracks an independent baseline per mode. This allows
    mode tests to run after core tests without interference.

    Risk scoring with default weights (threshold=5):
      description: 3 tools x weight 2 = score 6 -> BLOCKED
      schema:      2 tools x weight 3 = score 6 -> BLOCKED
      remove:      1 tool  x weight 3 = score 3 -> ALLOWED (under threshold)
      add:         1 tool  x weight 1 = score 1 -> ALLOWED (under threshold)
    """
    print("\n" + "=" * 60)
    print("RUG PULL MUTATION MODE TESTS")
    print("=" * 60)
    print("Each mode uses a separate gateway route (isolated guard baseline):")
    print("  description (weight 2) - expect BLOCKED (3 changes = score 6)")
    print("  schema      (weight 3) - expect BLOCKED (2 changes = score 6)")
    print("  remove      (weight 3) - expect ALLOWED (1 removal = score 3)")
    print("  add         (weight 1) - expect ALLOWED (1 addition = score 1)")
    print()

    # Mode "description": 3 description changes -> score 6 >= 5 -> BLOCKED
    await _test_single_mode(
        gateway_url, route, results, transport,
        mode="description", test_num=14, expect_blocked=True,
    )

    # Mode "schema": 2 schema changes -> score 6 >= 5 -> BLOCKED
    await _test_single_mode(
        gateway_url, route, results, transport,
        mode="schema", test_num=16, expect_blocked=True,
    )

    # Mode "remove": 1 tool removed -> score 3 < 5 -> ALLOWED
    await _test_single_mode(
        gateway_url, route, results, transport,
        mode="remove", test_num=18, expect_blocked=False,
    )

    # Mode "add": 1 tool added -> score 1 < 5 -> ALLOWED
    await _test_single_mode(
        gateway_url, route, results, transport,
        mode="add", test_num=20, expect_blocked=False,
    )

    # Test 22: Final reset — mode back to "all", all state cleared
    print("\n[Test 22: Reset Mode to Default]")
    await _reset_rug_pull_state(gateway_url, route, transport, "final cleanup")
    results.add_pass("Mode reset to 'all' (default)")


async def run_tests(transport: str = "sse"):
    """Run rug pull guard E2E tests."""
    gateway_url = os.environ.get("GATEWAY_URL", "http://localhost:8080")
    route = os.environ.get("MCP_ROUTE", DEFAULT_ROUTE)

    print("=" * 60)
    print("AgentGateway Rug Pull Guard - E2E Test Suite")
    print("=" * 60)
    print(f"\nGateway: {gateway_url}")
    print(f"Route: /{route}")
    print(f"Transport: {transport}")
    print(f"Started: {datetime.now().isoformat()}")

    results = TestResults()

    try:
        await test_rug_pull_guard(gateway_url, route, results, transport)
    except Exception as e:
        results.add_fail("Test execution", str(e))
        import traceback
        print(f"\nException details:\n{traceback.format_exc()}")

    print(f"\nCompleted: {datetime.now().isoformat()}")
    results.print_summary()

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="E2E Rug Pull Guard Test Suite")
    parser.add_argument(
        "--transport", "-t",
        choices=["sse", "streamable"],
        default=os.environ.get("MCP_TRANSPORT", "streamable"),
        help="MCP transport type (default: streamable, or MCP_TRANSPORT env var)"
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
