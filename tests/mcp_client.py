#!/usr/bin/env python3
"""
Shared MCP Client Library for E2E Tests

Provides MCP clients with different transport protocols:
- MCPSSEClient: Server-Sent Events transport
- MCPStreamableHTTPClient: Streamable HTTP transport

Usage:
    from mcp_client import create_mcp_client, TestResults

    async with create_mcp_client(base_url, route, transport="streamable") as client:
        await client.initialize()
        tools = await client.list_tools()
"""

import json
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    raise ImportError("Required package not installed. Install with: pip install httpx")


class MCPClientBase(ABC):
    """Base class for MCP clients with different transport protocols."""

    def __init__(self, base_url: str, route: str):
        """
        Args:
            base_url: Gateway base URL (e.g., http://localhost:8080)
            route: Route path (e.g., "poison", "rug-pull", "pii-test")
        """
        self.base_url = base_url.rstrip('/')
        self.route = route.lstrip('/')
        self.session_id = str(uuid.uuid4())
        self.session_header = None
        self.client = httpx.AsyncClient(timeout=60.0)
        self.message_id = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        await self.client.aclose()

    def _next_message_id(self) -> int:
        self.message_id += 1
        return self.message_id

    def _get_mcp_url(self) -> str:
        """Get the MCP endpoint URL."""
        return f"{self.base_url}/{self.route}"

    @abstractmethod
    def _get_accept_header(self) -> str:
        """Get the Accept header for this transport."""
        pass

    @abstractmethod
    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse the response and extract JSON-RPC message."""
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Test basic connectivity to MCP endpoint."""
        pass

    async def initialize(self, client_name: str = "mcp-e2e-test") -> Dict[str, Any]:
        """Initialize MCP session."""
        url = f"{self._get_mcp_url()}?sessionId={self.session_id}"

        initialize_message = {
            "jsonrpc": "2.0",
            "id": self._next_message_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": client_name,
                    "version": "1.0.0"
                }
            }
        }

        try:
            response = await self.client.post(
                url,
                json=initialize_message,
                headers={
                    "Content-Type": "application/json",
                    "Accept": self._get_accept_header()
                }
            )

            if response.status_code == 200:
                # httpx Headers are case-insensitive, but use lowercase for consistency
                self.session_header = response.headers.get("mcp-session-id")
                data = self._parse_response(response.text)
                if data and "result" in data:
                    return {
                        "success": True,
                        "server_info": data["result"],
                        "session_id": self.session_header
                    }
                elif data and "error" in data:
                    return {"success": False, "error": data["error"]}

            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:500]}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_tools(self) -> Dict[str, Any]:
        """List available tools via MCP."""
        url = self._get_mcp_url()

        list_message = {
            "jsonrpc": "2.0",
            "id": self._next_message_id(),
            "method": "tools/list",
            "params": {}
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": self._get_accept_header()
        }
        if self.session_header:
            headers["mcp-session-id"] = self.session_header

        try:
            response = await self.client.post(url, json=list_message, headers=headers)

            if response.status_code == 200:
                data = self._parse_response(response.text)
                if data and "result" in data:
                    return {"success": True, "tools": data["result"].get("tools", [])}
                elif data and "error" in data:
                    return {"success": False, "error": data["error"], "blocked": True}

            # Check if blocked by security guard
            if response.status_code in [403, 400]:
                return {
                    "success": False,
                    "error": response.text[:500],
                    "blocked": True,
                    "status_code": response.status_code
                }

            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:500]}",
                "raw_response": response.text
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool."""
        url = self._get_mcp_url()

        tool_call_message = {
            "jsonrpc": "2.0",
            "id": self._next_message_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": self._get_accept_header()
        }
        if self.session_header:
            headers["mcp-session-id"] = self.session_header

        try:
            response = await self.client.post(url, json=tool_call_message, headers=headers)

            if response.status_code == 200:
                data = self._parse_response(response.text)
                if data and "result" in data:
                    return {"success": True, "result": data["result"]}
                elif data and "error" in data:
                    return {"success": False, "error": data["error"]}

            if response.status_code in [403, 400]:
                return {
                    "success": False,
                    "error": response.text[:500],
                    "blocked": True,
                    "status_code": response.status_code
                }

            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:500]}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class MCPSSEClient(MCPClientBase):
    """MCP client that uses Server-Sent Events (SSE) transport protocol."""

    def _get_accept_header(self) -> str:
        return "application/json, text/event-stream"

    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse SSE response and extract JSON-RPC message."""
        for line in response_text.split('\n'):
            if line.startswith('data: '):
                data_str = line[6:]
                try:
                    return json.loads(data_str)
                except json.JSONDecodeError:
                    continue
        return None

    async def test_connection(self) -> Dict[str, Any]:
        """Test basic connectivity to MCP endpoint via SSE."""
        url = self._get_mcp_url()
        try:
            response = await self.client.get(
                url,
                headers={"Accept": "text/event-stream"}
            )
            return {
                "success": response.status_code in [200, 422],
                "status_code": response.status_code,
                "response": response.text[:500] if response.text else None,
                "url": url,
                "transport": "sse"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "url": url, "transport": "sse"}


class MCPStreamableHTTPClient(MCPClientBase):
    """MCP client that uses Streamable HTTP transport protocol.

    This transport uses standard HTTP POST with JSON request/response bodies.
    Unlike SSE, responses are direct JSON (not wrapped in 'data:' lines).

    Key differences from SSE:
    - Accept header: application/json (not text/event-stream)
    - Response: Direct JSON body (not SSE data: lines)
    - Session: Same mcp-session-id header mechanism
    """

    def _get_accept_header(self) -> str:
        # Gateway requires both content types in Accept header
        return "application/json, text/event-stream"

    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response directly."""
        if not response_text or not response_text.strip():
            return None

        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try SSE format as fallback (some servers may return SSE even for JSON accept)
            for line in response_text.split('\n'):
                if line.startswith('data: '):
                    try:
                        return json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
            return None

    async def test_connection(self) -> Dict[str, Any]:
        """Test basic connectivity to MCP endpoint via Streamable HTTP."""
        url = self._get_mcp_url()
        try:
            # For streamable HTTP, send an empty/invalid JSON-RPC request
            # The server should respond (even with error) if reachable
            response = await self.client.post(
                url,
                json={"jsonrpc": "2.0", "method": "ping", "id": 0},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            )
            # Any response indicates the endpoint is reachable
            # 200 = success, 400/422 = invalid request but server responding
            is_success = response.status_code in [200, 400, 422, 404, 405]
            result = {
                "success": is_success,
                "status_code": response.status_code,
                "response": response.text[:500] if response.text else None,
                "url": url,
                "transport": "streamable-http"
            }
            if not is_success:
                result["error"] = f"HTTP {response.status_code}: {response.text[:200] if response.text else 'No response body'}"
            return result
        except httpx.ConnectError as e:
            return {"success": False, "error": f"Connection failed: {e}", "url": url, "transport": "streamable-http"}
        except Exception as e:
            return {"success": False, "error": f"{type(e).__name__}: {e}", "url": url, "transport": "streamable-http"}

    async def initialize(self, client_name: str = "mcp-e2e-test") -> Dict[str, Any]:
        """Initialize MCP session for Streamable HTTP.

        Override to not include sessionId in query params (streamable HTTP uses headers).
        """
        url = self._get_mcp_url()

        initialize_message = {
            "jsonrpc": "2.0",
            "id": self._next_message_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": client_name,
                    "version": "1.0.0"
                }
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }

        try:
            response = await self.client.post(
                url,
                json=initialize_message,
                headers=headers
            )

            if response.status_code == 200:
                # httpx Headers are case-insensitive
                self.session_header = response.headers.get("mcp-session-id")
                data = self._parse_response(response.text)
                if data and "result" in data:
                    return {
                        "success": True,
                        "server_info": data["result"],
                        "session_id": self.session_header
                    }
                elif data and "error" in data:
                    return {"success": False, "error": data["error"]}

            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:500]}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


def create_mcp_client(base_url: str, route: str, transport: str = "streamable") -> MCPClientBase:
    """Factory function to create MCP client with specified transport.

    Args:
        base_url: Gateway base URL (e.g., http://localhost:8080)
        route: Route path (e.g., "pii-test", "poison", "rug-pull")
        transport: Transport type - "streamable" (default) or "sse"

    Returns:
        MCPClientBase: Appropriate client instance
    """
    if transport.lower() in ["streamable", "streamable-http", "http"]:
        return MCPStreamableHTTPClient(base_url, route)
    else:
        return MCPSSEClient(base_url, route)


class TestResults:
    """Track test results with pass/fail/warning counts."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_pass(self, test_name: str, details: str = ""):
        self.passed += 1
        print(f"  ✓ {test_name}")
        if details:
            print(f"    {details}")

    def add_fail(self, test_name: str, error: str):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        print(f"  ✗ {test_name}")
        print(f"    Error: {error}")

    def add_warning(self, message: str):
        self.warnings.append(message)
        print(f"  ⚠ {message}")

    def print_summary(self):
        print("\n" + "=" * 60)
        print(f"Test Results: {self.passed} passed, {self.failed} failed")

        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")

        if self.errors:
            print(f"\nFailed Tests ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")

        print("=" * 60)
        return self.failed == 0
