#!/usr/bin/env python3
"""
E2E Test Suite for AgentGateway PII Security Guard

Tests all 6 PII types detected by the guard:
  - email       -> <EMAIL_ADDRESS>
  - phone       -> <PHONE_NUMBER>
  - ssn         -> <SSN>
  - credit_card -> <CREDIT_CARD>
  - ca_sin      -> <CA_SIN>
  - url         -> <URL>

Tests both guard action modes via separate gateway routes:
  - /pii-test        : mask mode  (PII replaced with <ENTITY_TYPE> placeholder)
  - /pii-test-reject : reject mode (entire response blocked with pii_detected error)

Usage:
    # Run both modes sequentially (default)
    python tests/e2e_pii_guard_test.py

    # Run mask mode tests only
    python tests/e2e_pii_guard_test.py --expect-mode mask

    # Run reject mode tests only
    python tests/e2e_pii_guard_test.py --expect-mode reject

    # Run without mode enforcement (accept either outcome)
    python tests/e2e_pii_guard_test.py --expect-mode any

    # Override route explicitly
    python tests/e2e_pii_guard_test.py --expect-mode mask --route my-custom-pii-route
"""

import asyncio
import os
import re
import sys
from datetime import datetime

from mcp_client import create_mcp_client, TestResults

# Route defaults per mode
ROUTE_MASK = "pii-test"
ROUTE_REJECT = "pii-test-reject"

# Guard mask placeholders per PII type (from Rust recognizer entity_type strings).
# The guard replaces detected PII with <{ENTITY_TYPE}> via mask_text().
MASK_PLACEHOLDERS = {
    "email": "<EMAIL_ADDRESS>",
    "phone": "<PHONE_NUMBER>",
    "ssn": "<SSN>",
    "credit_card": "<CREDIT_CARD>",
    "ca_sin": "<CA_SIN>",
    "url": "<URL>",
}

# Patterns indicating raw (unredacted) PII still present in response
RAW_PII_PATTERNS = {
    "email": re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'),
    "phone": re.compile(r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'),
    "ssn": re.compile(r'\d{3}-\d{2}-\d{4}'),
    "credit_card": re.compile(r'\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3,4}'),
    "ca_sin": re.compile(r'\d{3}[-\s]\d{3}[-\s]\d{3}'),
    "url": re.compile(r'https?://[^\s"]+'),
}

# Keywords in error messages that indicate guard rejection
REJECT_KEYWORDS = ["pii_detected", "rejected", "blocked", "forbidden"]

# All 6 PII types the guard supports, with human-readable labels
PII_TYPES_UNDER_TEST = {
    "email": "Email address",
    "phone": "Phone number",
    "ssn": "US Social Security Number",
    "credit_card": "Credit card number",
    "ca_sin": "Canadian SIN",
    "url": "URL",
}


def _has_mask_placeholder(content: str, pii_type: str) -> bool:
    """Check if content contains the expected mask placeholder for a PII type."""
    return MASK_PLACEHOLDERS[pii_type] in content


def _has_raw_pii(content: str, pii_type: str) -> bool:
    """Check if content contains raw (unredacted) PII of the given type."""
    pattern = RAW_PII_PATTERNS.get(pii_type)
    return bool(pattern.search(content)) if pattern else False


def _is_guard_rejection(error: str) -> bool:
    """Check if an error message indicates guard rejection (reject mode)."""
    error_lower = str(error).lower()
    return any(kw in error_lower for kw in REJECT_KEYWORDS)


def assess_pii_response(
    result: dict,
    pii_type: str,
    results: TestResults,
    label: str,
    expect_mode: str = "any",
) -> str:
    """Assess a tool call result for PII guard behavior.

    Args:
        result: The MCP tool call result dict.
        pii_type: Which PII type was tested (e.g. "email").
        results: TestResults accumulator.
        label: Human-readable test label.
        expect_mode: "mask", "reject", or "any".

    Returns:
        Detected mode: "masked", "rejected", "unredacted", "error", or "unknown".
    """
    placeholder = MASK_PLACEHOLDERS[pii_type]

    if result["success"]:
        content = result.get("result", {}).get("content", [{}])[0].get("text", "")

        # Detect tool execution errors returned as content (e.g. pydantic validation errors)
        if content.startswith("Error executing tool"):
            results.add_fail(
                f"{label} - tool error",
                f"Tool returned error (server may not support this type): {content[:100]}"
            )
            return "error"

        if _has_mask_placeholder(content, pii_type):
            if expect_mode == "reject":
                results.add_fail(
                    f"{label} - wrong mode",
                    f"Expected reject but got mask ({placeholder} found in response)"
                )
            else:
                results.add_pass(
                    f"{label} - masked",
                    f"Guard replaced {pii_type} with {placeholder}: {content[:80]}"
                )
            return "masked"

        if _has_raw_pii(content, pii_type):
            results.add_fail(
                f"{label} - unredacted",
                f"Raw {pii_type} PII passed through unredacted: {content[:80]}"
            )
            return "unredacted"

        # Check for cross-type masking: PII was caught but by a different recognizer
        # (e.g. SSN masked as <PHONE_NUMBER> due to recognizer overlap)
        other_placeholders = {
            pt: ph for pt, ph in MASK_PLACEHOLDERS.items()
            if pt != pii_type and ph in content
        }
        if other_placeholders:
            actual = ", ".join(f"{ph} ({pt})" for pt, ph in other_placeholders.items())
            if expect_mode == "reject":
                results.add_fail(
                    f"{label} - wrong mode",
                    f"Expected reject but got cross-type mask: {actual}"
                )
            else:
                results.add_pass(
                    f"{label} - cross-type mask",
                    f"PII detected but masked as different type: {actual} (recognizer overlap)"
                )
            return "masked"

        results.add_warning(
            f"{label}: response has no mask placeholder or raw PII pattern: {content[:80]}"
        )
        return "unknown"

    # Tool call failed - check if it was a guard rejection
    error_msg = str(result.get("error", ""))
    if _is_guard_rejection(error_msg):
        if expect_mode == "mask":
            results.add_fail(
                f"{label} - wrong mode",
                f"Expected mask but got reject: {error_msg[:80]}"
            )
        else:
            results.add_pass(
                f"{label} - rejected",
                f"Guard rejected {pii_type}: {error_msg[:80]}"
            )
        return "rejected"

    results.add_fail(
        label,
        f"Tool call failed (not a guard rejection): {error_msg[:80]}"
    )
    return "error"


async def test_pii_guard(
    gateway_url: str,
    route: str,
    results: TestResults,
    transport: str = "streamable",
    expect_mode: str = "any",
):
    """Test PII security guard functionality across all 6 PII types.

    Args:
        expect_mode: "mask" (assert masking), "reject" (assert rejection), "any" (accept either).
    """
    mode_label = {"mask": "MASK", "reject": "REJECT", "any": "ANY"}.get(expect_mode, "ANY")

    print("\n" + "=" * 60)
    print(f"PII SECURITY GUARD TESTS [{mode_label} MODE]")
    print("=" * 60)
    print(f"Route: /{route}")
    print(f"Transport: {transport}")
    print(f"Expected mode: {expect_mode}\n")

    async with create_mcp_client(gateway_url, route=route, transport=transport) as client:

        # -- Test 1: Basic Connectivity --
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

        # -- Test 2: MCP Initialize --
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

        # -- Test 3: List Tools --
        print("\n[Test 3: List Available Tools]")
        tools_result = await client.list_tools()
        if tools_result["success"]:
            tools = tools_result.get("tools", [])
            tool_names = [t.get("name", "unknown") for t in tools]
            results.add_pass(
                "List MCP tools",
                f"Found {len(tools)} tools: {', '.join(tool_names)}"
            )
        else:
            results.add_fail(
                "List MCP tools",
                tools_result.get("error", "Unknown error")
            )

        # -- Tests 4-9: Single PII type detection via generate_pii --
        detected_mode = None

        for i, (pii_type, label) in enumerate(PII_TYPES_UNDER_TEST.items(), start=4):
            print(f"\n[Test {i}: Generate {label} PII]")
            result = await client.call_tool(
                "generate_pii",
                {"pii_type": pii_type}
            )
            mode = assess_pii_response(
                result, pii_type, results,
                f"{label} PII detection", expect_mode,
            )
            if mode in ("masked", "rejected") and detected_mode is None:
                detected_mode = mode

        if detected_mode:
            print(f"\n    Detected guard mode: {detected_mode}")

        # -- Tests 10-15: Embedded PII in natural language text --
        all_embedded_types = ["email", "ssn", "credit_card", "phone", "ca_sin", "url"]

        for i, pii_type in enumerate(all_embedded_types, start=10):
            label = PII_TYPES_UNDER_TEST[pii_type]
            print(f"\n[Test {i}: Embedded {label} in Text]")
            result = await client.call_tool(
                "generate_text_with_pii",
                {"pii_type": pii_type}
            )
            assess_pii_response(
                result, pii_type, results,
                f"Embedded {label} detection", expect_mode,
            )

        # -- Test 16: Full record (multiple PII types simultaneously) --
        print("\n[Test 16: Full Record with Multiple PII Types]")
        full_result = await client.call_tool("generate_full_record", {})
        if full_result["success"]:
            content = full_result.get("result", {}).get("content", [{}])[0].get("text", "")
            masked_types = [pt for pt, ph in MASK_PLACEHOLDERS.items() if ph in content]
            raw_types = [
                pt for pt in ["email", "phone", "ssn", "credit_card"]
                if _has_raw_pii(content, pt)
            ]
            if masked_types:
                if expect_mode == "reject":
                    results.add_fail(
                        "Full record - wrong mode",
                        f"Expected reject but got mask (masked: {', '.join(masked_types)})"
                    )
                else:
                    results.add_pass(
                        "Full record PII masking",
                        f"Masked types: {', '.join(masked_types)}"
                    )
            elif raw_types:
                results.add_fail(
                    "Full record PII detection",
                    f"Raw PII found for types: {', '.join(raw_types)}"
                )
            else:
                results.add_pass(
                    "Full record - no raw PII detected",
                    "Content appears clean (guard may have masked or data format differs)"
                )
        else:
            error_msg = str(full_result.get("error", ""))
            if _is_guard_rejection(error_msg):
                if expect_mode == "mask":
                    results.add_fail(
                        "Full record - wrong mode",
                        f"Expected mask but got reject: {error_msg[:80]}"
                    )
                else:
                    results.add_pass(
                        "Full record PII rejected",
                        "Guard blocked full record with multiple PII types"
                    )
            else:
                results.add_fail(
                    "Full record generation",
                    full_result.get("error", "Unknown error")
                )

        # -- Test 17: Bulk PII generation (email) --
        print("\n[Test 17: Bulk PII Generation (email)]")
        bulk_result = await client.call_tool(
            "generate_bulk_pii",
            {"pii_type": "email", "count": 5}
        )
        if bulk_result["success"]:
            content = bulk_result.get("result", {}).get("content", [{}])[0].get("text", "")
            placeholder = MASK_PLACEHOLDERS["email"]
            if placeholder in content:
                if expect_mode == "reject":
                    results.add_fail(
                        "Bulk email - wrong mode",
                        "Expected reject but got mask"
                    )
                else:
                    results.add_pass(
                        "Bulk email PII masked",
                        f"Emails masked ({content.count(placeholder)} occurrences)"
                    )
            elif _has_raw_pii(content, "email"):
                results.add_fail(
                    "Bulk email PII unredacted",
                    "Raw emails found in bulk response"
                )
            else:
                results.add_pass(
                    "Bulk email PII generation",
                    "Bulk response returned (format may differ)"
                )
        else:
            error_msg = str(bulk_result.get("error", ""))
            if _is_guard_rejection(error_msg):
                if expect_mode == "mask":
                    results.add_fail(
                        "Bulk email - wrong mode",
                        "Expected mask but got reject"
                    )
                else:
                    results.add_pass(
                        "Bulk email PII rejected",
                        "Guard blocked bulk email generation"
                    )
            else:
                results.add_fail(
                    "Bulk PII generation",
                    bulk_result.get("error", "Unknown error")
                )

        # -- Test 18: Bulk PII generation (credit_card) --
        print("\n[Test 18: Bulk PII Generation (credit_card)]")
        bulk_cc_result = await client.call_tool(
            "generate_bulk_pii",
            {"pii_type": "credit_card", "count": 3}
        )
        if bulk_cc_result["success"]:
            content = bulk_cc_result.get("result", {}).get("content", [{}])[0].get("text", "")
            placeholder = MASK_PLACEHOLDERS["credit_card"]
            if placeholder in content:
                if expect_mode == "reject":
                    results.add_fail(
                        "Bulk credit card - wrong mode",
                        "Expected reject but got mask"
                    )
                else:
                    results.add_pass(
                        "Bulk credit card PII masked",
                        f"Cards masked ({content.count(placeholder)} occurrences)"
                    )
            elif _has_raw_pii(content, "credit_card"):
                results.add_fail(
                    "Bulk credit card PII unredacted",
                    "Raw credit cards found in bulk response"
                )
            else:
                results.add_pass(
                    "Bulk credit card PII generation",
                    "Bulk response returned (format may differ)"
                )
        else:
            error_msg = str(bulk_cc_result.get("error", ""))
            if _is_guard_rejection(error_msg):
                if expect_mode == "mask":
                    results.add_fail(
                        "Bulk credit card - wrong mode",
                        "Expected mask but got reject"
                    )
                else:
                    results.add_pass(
                        "Bulk credit card PII rejected",
                        "Guard blocked bulk credit card generation"
                    )
            else:
                results.add_fail(
                    "Bulk credit card PII generation",
                    bulk_cc_result.get("error", "Unknown error")
                )

        # -- Test 19: Clean data (no PII - name only) --
        print("\n[Test 19: Clean Data - No PII Expected]")
        clean_result = await client.call_tool(
            "generate_pii",
            {"pii_type": "name"}
        )
        if clean_result["success"]:
            content = clean_result.get("result", {}).get("content", [{}])[0].get("text", "")
            any_mask = any(ph in content for ph in MASK_PLACEHOLDERS.values())
            if any_mask:
                results.add_warning(
                    "Name data triggered PII detection (may be false positive)"
                )
            else:
                results.add_pass(
                    "Clean data passes through",
                    "Name-only data not flagged as PII"
                )
        else:
            error_msg = str(clean_result.get("error", ""))
            if _is_guard_rejection(error_msg):
                results.add_warning(
                    "Name data was rejected - guard may be overly aggressive"
                )
            else:
                results.add_fail(
                    "Clean data test",
                    clean_result.get("error", "Unknown error")
                )


async def run_tests(
    transport: str = "streamable",
    expect_mode: str = "both",
    route: str | None = None,
):
    """Run PII guard E2E tests.

    Args:
        transport: MCP transport type.
        expect_mode: "mask", "reject", "both", or "any".
        route: Explicit route override. Ignored when expect_mode is "both".
    """
    gateway_url = os.environ.get("GATEWAY_URL", "http://localhost:8080")

    print("=" * 60)
    print("AgentGateway PII Guard - E2E Test Suite")
    print("=" * 60)
    print(f"\nGateway: {gateway_url}")
    print(f"Transport: {transport}")
    print(f"Mode: {expect_mode}")
    print(f"Started: {datetime.now().isoformat()}")

    results = TestResults()

    if expect_mode == "both":
        # Run mask tests then reject tests sequentially
        for mode, default_route in [("mask", ROUTE_MASK), ("reject", ROUTE_REJECT)]:
            try:
                await test_pii_guard(
                    gateway_url, default_route, results,
                    transport=transport, expect_mode=mode,
                )
            except Exception as e:
                results.add_fail(f"Test execution ({mode} mode)", str(e))
                import traceback
                print(f"\nException details:\n{traceback.format_exc()}")
    else:
        # Single mode run
        if route is None:
            if expect_mode == "reject":
                route = ROUTE_REJECT
            else:
                route = ROUTE_MASK
        try:
            await test_pii_guard(
                gateway_url, route, results,
                transport=transport, expect_mode=expect_mode,
            )
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
        default="streamable",
        help="MCP transport type (default: streamable)"
    )
    parser.add_argument(
        "--route", "-r",
        default=None,
        help="MCP route path override (default: auto-selected per mode)"
    )
    parser.add_argument(
        "--expect-mode", "-m",
        choices=["mask", "reject", "both", "any"],
        default="both",
        help=(
            "Expected guard mode. "
            "'mask': assert PII is masked via /pii-test. "
            "'reject': assert PII is rejected via /pii-test-reject. "
            "'both': run mask then reject sequentially (default). "
            "'any': accept either outcome."
        )
    )
    args = parser.parse_args()

    results = asyncio.run(run_tests(
        transport=args.transport,
        expect_mode=args.expect_mode,
        route=args.route,
    ))
    sys.exit(0 if results.failed == 0 else 1)
