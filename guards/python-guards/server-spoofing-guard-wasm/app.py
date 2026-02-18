"""
Server Spoofing Guard - WASM Component

This module implements the WIT guard interface for compilation to WASM
using componentize-py.

Protects against:
1. Fake servers not in whitelist
2. Typosquatting attacks (e.g., "company-to0ls" vs "company-tools")
3. Tool mimicry (malicious server copying trusted server's tools)
"""

import json
import hashlib
from typing import Optional

# Import the generated bindings (created by componentize-py from WIT)
from wit_world.exports.guard import (
    Tool,
    GuardContext,
    DenyReason,
    Decision,
    Decision_Allow,
    Decision_Deny,
    Decision_Warn,
)
from wit_world.imports import host


# Global state (persists within WASM instance)
_tool_registry: dict[str, dict[str, str]] = {}  # server -> {tool_name: fingerprint}
_config_cache: Optional[dict] = None


def levenshtein_ratio(s1: str, s2: str) -> float:
    """Calculate Levenshtein similarity ratio between two strings."""
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 < len2:
        s1, s2 = s2, s1
        len1, len2 = len2, len1
    distances = list(range(len2 + 1))
    for i1, c1 in enumerate(s1):
        new_distances = [i1 + 1]
        for i2, c2 in enumerate(s2):
            if c1 == c2:
                new_distances.append(distances[i2])
            else:
                new_distances.append(1 + min((distances[i2], distances[i2 + 1], new_distances[-1])))
        distances = new_distances
    distance = distances[-1]
    return 1.0 - (distance / max(len1, len2))


def _get_config() -> dict:
    """Load configuration from host."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    config_json = host.get_config("guard_config")
    if config_json:
        try:
            _config_cache = json.loads(config_json)
        except json.JSONDecodeError:
            host.log(4, "Failed to parse guard config JSON")
            _config_cache = {}
    else:
        _config_cache = {}

    return _config_cache


def _get_whitelist() -> list[dict]:
    """Get whitelist from config."""
    config = _get_config()
    return config.get("whitelist", [])


def _get_threshold() -> float:
    """Get typosquat similarity threshold."""
    config = _get_config()
    return config.get("typosquat_similarity_threshold", 0.85)


def _is_whitelisted(server_name: str) -> bool:
    """Check if server is in whitelist."""
    whitelist = _get_whitelist()
    server_lower = server_name.lower()

    for entry in whitelist:
        if entry.get("name", "").lower() == server_lower:
            return True

    return False


def _detect_typosquat(server_name: str) -> Optional[str]:
    """
    Detect if server name is a typosquat of an approved server.
    Returns the name of the similar approved server if detected.
    """
    threshold = _get_threshold()
    whitelist = _get_whitelist()
    test_name = server_name.lower()

    for entry in whitelist:
        approved_name = entry.get("name", "").lower()

        # Skip exact matches
        if approved_name == test_name:
            continue

        # Calculate similarity
        similarity = levenshtein_ratio(approved_name, test_name)

        if similarity >= threshold:
            # Check for common typosquat patterns
            if _is_typosquat_pattern(approved_name, test_name):
                return entry.get("name")

    return None


def _is_typosquat_pattern(approved: str, suspect: str) -> bool:
    """Check for common typosquat patterns."""
    # Check if difference is a single character substitution
    if len(approved) == len(suspect):
        diffs = sum(1 for a, b in zip(approved, suspect) if a != b)
        if diffs == 1:
            return True

    # Check homoglyph attacks (visually similar characters)
    homoglyphs = {
        'o': ['0'],
        'l': ['1', 'I', '|'],
        'i': ['1', 'l', '|'],
        'a': ['@'],
        'e': ['3'],
    }

    normalized_suspect = suspect
    for char, substitutes in homoglyphs.items():
        for sub in substitutes:
            normalized_suspect = normalized_suspect.replace(sub, char)

    if approved == normalized_suspect and approved != suspect:
        return True

    return False


def _compute_tool_fingerprint(tool: Tool) -> str:
    """Compute a fingerprint for a tool based on its metadata."""
    desc = tool.description if tool.description else ""
    content = f"{tool.name}|{desc}|{tool.input_schema}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _check_tool_mimicry(server_name: str, tools: list[Tool]) -> Optional[dict]:
    """Check if tools mimic trusted server tools."""
    whitelist = _get_whitelist()
    server_lower = server_name.lower()

    for tool in tools:
        for entry in whitelist:
            entry_name = entry.get("name", "").lower()
            if entry_name == server_lower:
                continue

            # Check tool fingerprints
            tool_fingerprints = entry.get("tool_fingerprints", {})
            fingerprint = _compute_tool_fingerprint(tool)

            for trusted_name, trusted_fp in tool_fingerprints.items():
                if fingerprint == trusted_fp:
                    return {
                        "tool_name": tool.name,
                        "mimics_server": entry.get("name"),
                        "mimics_tool": trusted_name,
                        "match_type": "exact_fingerprint",
                    }

                if tool.name.lower() == trusted_name.lower():
                    return {
                        "tool_name": tool.name,
                        "mimics_server": entry.get("name"),
                        "mimics_tool": trusted_name,
                        "match_type": "name_collision",
                    }

    return None


def _check_namespace_collision(server_name: str, tools: list[Tool]) -> Optional[dict]:
    """Check for tool name collisions with other registered servers."""
    global _tool_registry
    server_lower = server_name.lower()

    for tool in tools:
        for other_server, other_tools in _tool_registry.items():
            if other_server.lower() == server_lower:
                continue

            if tool.name in other_tools:
                return {
                    "tool_name": tool.name,
                    "this_server": server_name,
                    "other_server": other_server,
                }

    return None


class Guard:
    """
    Server Spoofing Guard - WASM implementation.

    Implements the Guard protocol for componentize-py.
    """

    def evaluate_server_connection(self, context: GuardContext) -> Decision:
        """
        Evaluate whether a connection to an MCP server should be allowed.
        """
        server_name = context.server_name
        config = _get_config()

        host.log(1, f"Evaluating server connection: {server_name}")

        # Check if whitelisting is enabled
        if not config.get("whitelist_enabled", True):
            return Decision_Allow()

        # Check whitelist
        if _is_whitelisted(server_name):
            host.log(1, f"Server '{server_name}' is whitelisted")
            return Decision_Allow()

        # Check for typosquat
        if config.get("typosquat_detection_enabled", True):
            typosquat_match = _detect_typosquat(server_name)
            if typosquat_match:
                host.log(3, f"Typosquat detected: '{server_name}' similar to '{typosquat_match}'")
                return Decision_Deny(DenyReason(
                    code="typosquat_detected",
                    message=f"Server '{server_name}' appears to be typosquatting approved server '{typosquat_match}'",
                    details=json.dumps({
                        "detected_name": server_name,
                        "similar_to": typosquat_match,
                        "attack_type": "typosquatting",
                    }),
                ))

        # Block unknown servers if configured
        if config.get("block_unknown_servers", True):
            host.log(3, f"Blocking unknown server: {server_name}")
            return Decision_Deny(DenyReason(
                code="server_not_whitelisted",
                message=f"Server '{server_name}' is not in the approved server registry",
                details=json.dumps({
                    "server_name": server_name,
                    "action": "Add server to whitelist if this is a legitimate server",
                }),
            ))

        # Warn but allow
        host.log(2, f"Warning: Server '{server_name}' is not in whitelist")
        return Decision_Warn([f"Server '{server_name}' is not in whitelist"])

    def evaluate_tools_list(self, tools: list[Tool], context: GuardContext) -> Decision:
        """
        Evaluate tools returned by an MCP server.
        """
        global _tool_registry
        server_name = context.server_name
        config = _get_config()

        host.log(1, f"Evaluating {len(tools)} tools from server: {server_name}")

        # Check for tool mimicry
        if config.get("tool_mimicry_detection_enabled", True):
            mimicry = _check_tool_mimicry(server_name, tools)
            if mimicry:
                host.log(3, f"Tool mimicry detected: {mimicry}")
                return Decision_Deny(DenyReason(
                    code="tool_mimicry_detected",
                    message=f"Server '{server_name}' contains tools that mimic trusted server tools",
                    details=json.dumps({
                        "server_name": server_name,
                        "mimicked_tools": [mimicry],
                        "attack_type": "tool_mimicry",
                    }),
                ))

        # Check for namespace collisions
        collision = _check_namespace_collision(server_name, tools)
        if collision:
            host.log(3, f"Tool namespace collision: {collision}")
            return Decision_Deny(DenyReason(
                code="tool_namespace_collision",
                message=f"Server '{server_name}' has tools that collide with other servers",
                details=json.dumps({
                    "collisions": [collision],
                    "recommendation": "Use namespaced tool names (e.g., server_name.tool_name)",
                }),
            ))

        # Register tools for this server
        tool_fingerprints = {}
        for tool in tools:
            fingerprint = _compute_tool_fingerprint(tool)
            tool_fingerprints[tool.name] = fingerprint
        _tool_registry[server_name] = tool_fingerprints

        host.log(1, f"Registered {len(tools)} tools for server: {server_name}")
        return Decision_Allow()

    def get_settings_schema(self) -> str:
        """Return JSON Schema describing guard's configurable parameters."""
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "agentgateway://guards/server-spoofing/v1",
            "title": "Server Spoofing Guard",
            "description": "Detects and blocks server spoofing attacks including fake servers, typosquatting, and tool mimicry",
            "type": "object",
            "properties": {
                "whitelist_enabled": {
                    "type": "boolean",
                    "title": "Enable Whitelist",
                    "description": "Enable server whitelist checking. When disabled, all servers are allowed.",
                    "default": True,
                    "x-ui": {
                        "component": "checkbox",
                        "order": 1,
                        "group": "whitelist",
                    },
                },
                "whitelist": {
                    "type": "array",
                    "title": "Approved Servers",
                    "description": "List of approved MCP servers with optional URL patterns and tool fingerprints",
                    "default": [],
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "title": "Server Name",
                                "description": "Exact server name to whitelist",
                            },
                            "url_pattern": {
                                "type": "string",
                                "title": "URL Pattern",
                                "description": "Regex pattern to match server URL (optional)",
                                "format": "regex",
                            },
                            "tool_fingerprints": {
                                "type": "object",
                                "title": "Tool Fingerprints",
                                "description": "Map of tool name to expected fingerprint hash for mimicry detection",
                                "additionalProperties": {"type": "string"},
                            },
                        },
                        "required": ["name"],
                    },
                    "x-ui": {
                        "component": "object-array",
                        "placeholder": "Add approved server",
                        "helpText": "Each entry defines an approved server. Tool fingerprints are used for mimicry detection.",
                        "order": 2,
                        "group": "whitelist",
                    },
                },
                "block_unknown_servers": {
                    "type": "boolean",
                    "title": "Block Unknown Servers",
                    "description": "Deny connections from servers not in the whitelist. When disabled, unknown servers generate warnings instead.",
                    "default": True,
                    "x-ui": {
                        "component": "checkbox",
                        "helpText": "If disabled, unrecognized servers will be allowed with a warning",
                        "order": 3,
                        "group": "whitelist",
                    },
                },
                "typosquat_detection_enabled": {
                    "type": "boolean",
                    "title": "Enable Typosquat Detection",
                    "description": "Detect server names that are suspiciously similar to approved servers (e.g., 'finance-too1s' vs 'finance-tools')",
                    "default": True,
                    "x-ui": {
                        "component": "checkbox",
                        "order": 4,
                        "group": "typosquat",
                    },
                },
                "typosquat_similarity_threshold": {
                    "type": "number",
                    "title": "Similarity Threshold",
                    "description": "Levenshtein similarity ratio (0.0-1.0) above which a server name is flagged as a potential typosquat. Higher values are stricter.",
                    "default": 0.85,
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "x-ui": {
                        "component": "slider",
                        "helpText": "0.85 means names must be 85% similar to trigger detection. Lower values catch more but may produce false positives.",
                        "order": 5,
                        "group": "typosquat",
                    },
                },
                "tool_mimicry_detection_enabled": {
                    "type": "boolean",
                    "title": "Enable Tool Mimicry Detection",
                    "description": "Detect when an untrusted server provides tools that match fingerprints or names of tools from trusted servers",
                    "default": True,
                    "x-ui": {
                        "component": "checkbox",
                        "helpText": "Compares tool fingerprints (SHA-256 of name+description+schema) and tool names across servers",
                        "order": 6,
                        "group": "mimicry",
                    },
                },
            },
            "x-ui-groups": {
                "whitelist": {
                    "title": "Server Whitelist",
                    "order": 1,
                    "description": "Control which MCP servers are allowed to connect",
                },
                "typosquat": {
                    "title": "Typosquat Detection",
                    "order": 2,
                    "description": "Detect servers with names similar to approved servers",
                },
                "mimicry": {
                    "title": "Tool Mimicry Detection",
                    "order": 3,
                    "description": "Detect tools that impersonate tools from trusted servers",
                },
            },
            "x-guard-meta": {
                "guardType": "server_spoofing",
                "version": "1.0.0",
                "category": "detection",
                "defaultRunsOn": ["connection", "tools_list"],
                "icon": "shield-alert",
            },
        }
        return json.dumps(schema)

    def get_default_config(self) -> str:
        """Return default configuration as JSON."""
        config = {
            "whitelist_enabled": True,
            "whitelist": [],
            "block_unknown_servers": True,
            "typosquat_detection_enabled": True,
            "typosquat_similarity_threshold": 0.85,
            "tool_mimicry_detection_enabled": True,
        }
        return json.dumps(config)
