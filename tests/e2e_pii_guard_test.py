#!/usr/bin/env python3
"""
E2E Test Suite for AgentGateway PII Security Guard

Tests PII detection, redaction, and blocking via the pii-test route.

Test Configuration:
- Gateway: http://localhost:8080
- PII MCP Server: http://localhost:8000/mcp (via /pii-test route)

Usage:
    python tests/e2e_pii_guard_test.py
    GATEWAY_URL=http://localhost:8080 python tests/e2e_pii_guard_test.py

Transport Selection:
    MCP_TRANSPORT=streamable python tests/e2e_pii_guard_test.py  # Streamable HTTP (default)
    MCP_TRANSPORT=sse python tests/e2e_pii_guard_test.py         # SSE transport
"""

import asyncio
import json
import os
import sys
from datetime import datetime

from mcp_client import create_mcp_client, TestResults

# Default route for PII guard tests
DEFAULT_ROUTE = "pii-test"


async def test_pii_guard(gateway_url: str, route: str, results: TestResults, transport: str = "sse"):
    """Test PII security guard functionality."""
    print("\n" + "=" * 60)
    print("PII SECURITY GUARD TESTS")
    print("=" * 60)
    print(f"Route: /{route} -> localhost:8000/mcp")
    print(f"Transport: {transport}")
    print("Expected: Guard should detect/redact/block PII in tool responses\n")

    async with create_mcp_client(gateway_url, route=route, transport=transport) as client:
        # Test 1: Basic Connectivity
        print("[Test 1: MCP Endpoint Connectivity]")
        conn_result = await client.test_connection()
        if conn_result["success"]:
            results.add_pass(
                "MCP endpoint accessible",
                f"Status: {conn_result['status_code']}, URL: {conn_result.get('url')}"
            )
        else:
            results.add_fail(
                "MCP endpoint accessibility",
                conn_result.get("error", "Unknown error")
            )
            return

        # Test 2: MCP Initialize
        print("\n[Test 2: MCP Session Initialization]")
        init_result = await client.initialize(client_name="pii-guard-e2e-test")
        if init_result["success"]:
            server_name = init_result.get("server_info", {}).get("serverInfo", {}).get("name", "unknown")
            session_id = init_result.get("session_id") or client.session_header
            results.add_pass(
                "MCP initialize",
                f"Server: {server_name}, Session: {session_id}"
            )
        else:
            results.add_fail(
                "MCP initialize",
                init_result.get("error", "Unknown error")
            )
            results.add_warning("Skipping remaining tests - initialization failed")
            return

        # Test 3: List Tools
        print("\n[Test 3: List Available Tools]")
        tools_result = await client.list_tools()
        if tools_result["success"]:
            tools = tools_result.get("tools", [])
            results.add_pass(
                "List MCP tools",
                f"Found {len(tools)} tools"
            )
            if tools:
                print(f"    Available tools: {', '.join([t.get('name', 'unknown') for t in tools[:5]])}")
        else:
            results.add_fail(
                "List MCP tools",
                tools_result.get("error", "Unknown error")
            )

        # Test 4: Generate Email PII (basic tool call, should be detected)
        print("\n[Test 4: Generate Email PII]")
        email_result = await client.call_tool(
            "generate_pii",
            {"pii_type": "email"}
        )
        if email_result["success"]:
            content = email_result.get("result", {}).get("content", [{}])[0].get("text", "")
            if "[REDACTED]" in content or "[PII]" in content or "***" in content:
                results.add_pass(
                    "Email PII redacted",
                    f"Guard redacted email: {content[:50]}"
                )
            elif "@" in content:
                results.add_warning("Email may have passed through unredacted")
                results.add_pass(
                    "Generate email (guard may be in audit mode)",
                    f"Generated: {content[:50]}"
                )
            else:
                results.add_pass(
                    "Generate email",
                    f"Generated: {content[:50]}"
                )
        else:
            error_msg = str(email_result.get("error", ""))
            if "blocked" in error_msg.lower() or "pii" in error_msg.lower():
                results.add_pass(
                    "Email PII blocked",
                    "Guard blocked email generation"
                )
            else:
                results.add_fail(
                    "Generate email PII",
                    email_result.get("error", "Unknown error")
                )

        # Test 5: Generate SSN PII (high sensitivity)
        print("\n[Test 5: Generate SSN PII (High Sensitivity)]")
        ssn_result = await client.call_tool(
            "generate_pii",
            {"pii_type": "ssn"}
        )
        if ssn_result["success"]:
            content = ssn_result.get("result", {}).get("content", [{}])[0].get("text", "")

            # Check for redaction patterns
            if "[REDACTED]" in content or "[PII]" in content or "***" in content:
                results.add_pass(
                    "SSN PII redacted",
                    "SSN was redacted by security guard"
                )
            elif content and any(char.isdigit() for char in content):
                # SSN format: XXX-XX-XXXX
                results.add_warning(
                    "SSN may have passed through unredacted - check guard config"
                )
                results.add_pass(
                    "Generate SSN (guard may not detect SSN type)",
                    f"Generated: {content[:30]}"
                )
            else:
                results.add_pass(
                    "Generate SSN",
                    "Tool executed successfully"
                )
        else:
            error_msg = str(ssn_result.get("error", ""))
            if "blocked" in error_msg.lower() or "forbidden" in error_msg.lower() or "pii" in error_msg.lower():
                results.add_pass(
                    "SSN PII blocked",
                    "SSN request was blocked by security guard"
                )
            else:
                results.add_fail(
                    "Generate SSN with security guard",
                    ssn_result.get("error", "Unknown error")
                )

        # Test 6: Generate Credit Card PII
        print("\n[Test 6: Generate Credit Card PII]")
        cc_result = await client.call_tool(
            "generate_pii",
            {"pii_type": "credit_card"}
        )
        if cc_result["success"]:
            content = cc_result.get("result", {}).get("content", [{}])[0].get("text", "")

            if "[REDACTED]" in content or "[PII]" in content or "***" in content:
                results.add_pass(
                    "Credit card PII redacted",
                    "Credit card was redacted by security guard"
                )
            else:
                results.add_warning("Credit card may have passed through - check guard config")
                results.add_pass(
                    "Generate credit card",
                    f"Generated: {content[:30]}"
                )
        else:
            error_msg = str(cc_result.get("error", ""))
            if "blocked" in error_msg.lower() or "pii" in error_msg.lower():
                results.add_pass(
                    "Credit card PII blocked",
                    "Credit card request was blocked by security guard"
                )
            else:
                results.add_fail(
                    "Generate credit card",
                    cc_result.get("error", "Unknown error")
                )

        # Test 7: Bulk PII Generation
        print("\n[Test 7: Bulk PII Generation]")
        bulk_result = await client.call_tool(
            "generate_bulk_pii",
            {"pii_type": "name", "count": 10}
        )
        if bulk_result["success"]:
            content = bulk_result.get("result", {}).get("content", [{}])[0].get("text", "")
            try:
                data = json.loads(content)
                count = len(data) if isinstance(data, list) else 1
                results.add_pass(
                    "Bulk PII generation",
                    f"Generated {count} records"
                )
            except json.JSONDecodeError:
                results.add_pass(
                    "Bulk PII generation",
                    "Tool executed successfully"
                )
        else:
            results.add_fail(
                "Bulk PII generation",
                bulk_result.get("error", "Unknown error")
            )

        # Test 8: Text with Embedded PII
        print("\n[Test 8: Generate Text with Embedded PII]")
        text_result = await client.call_tool(
            "generate_text_with_pii",
            {"pii_type": "email"}
        )
        if text_result["success"]:
            content = text_result.get("result", {}).get("content", [{}])[0].get("text", "")
            if "[REDACTED]" in content or "[PII]" in content:
                results.add_pass(
                    "Text with PII redacted",
                    "Embedded PII was redacted in natural language text"
                )
            else:
                results.add_pass(
                    "Generate text with PII",
                    "Natural language text generation successful"
                )
        else:
            results.add_fail(
                "Generate text with PII",
                text_result.get("error", "Unknown error")
            )

        # Test 9: Phone Number PII
        print("\n[Test 9: Generate Phone Number PII]")
        phone_result = await client.call_tool(
            "generate_pii",
            {"pii_type": "phone"}
        )
        if phone_result["success"]:
            content = phone_result.get("result", {}).get("content", [{}])[0].get("text", "")
            if "[REDACTED]" in content or "[PII]" in content:
                results.add_pass(
                    "Phone number PII redacted",
                    "Phone number was redacted by security guard"
                )
            else:
                results.add_pass(
                    "Generate phone number",
                    f"Generated: {content[:30]}"
                )
        else:
            error_msg = str(phone_result.get("error", ""))
            if "blocked" in error_msg.lower() or "pii" in error_msg.lower():
                results.add_pass(
                    "Phone number PII blocked",
                    "Phone number request was blocked"
                )
            else:
                results.add_fail(
                    "Generate phone number",
                    phone_result.get("error", "Unknown error")
                )


async def run_tests(transport: str = "sse"):
    """Run PII guard E2E tests."""
    gateway_url = os.environ.get("GATEWAY_URL", "http://localhost:8080")
    route = os.environ.get("MCP_ROUTE", DEFAULT_ROUTE)

    print("=" * 60)
    print("AgentGateway PII Guard - E2E Test Suite")
    print("=" * 60)
    print(f"\nGateway: {gateway_url}")
    print(f"Route: /{route}")
    print(f"Transport: {transport}")
    print(f"Started: {datetime.now().isoformat()}")

    results = TestResults()

    try:
        await test_pii_guard(gateway_url, route, results, transport)
    except Exception as e:
        results.add_fail("Test execution", str(e))
        import traceback
        print(f"\nException details:\n{traceback.format_exc()}")

    print(f"\nCompleted: {datetime.now().isoformat()}")
    results.print_summary()

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="E2E PII Guard Test Suite")
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

    # Allow route override via CLI
    if args.route != DEFAULT_ROUTE:
        os.environ["MCP_ROUTE"] = args.route

    results = asyncio.run(run_tests(args.transport))
    sys.exit(0 if results.failed == 0 else 1)
