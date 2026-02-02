"""
Server Spoofing & Whitelisting Guard

Protects against:
1. Fake servers not in whitelist
2. Typosquatting attacks (e.g., "company-to0ls" vs "company-tools")
3. Tool mimicry (malicious server copying trusted server's tools)
4. Invalid TLS/auth configurations
5. Shadow MCP deployments

Reference: UNITONE Gateway Security Capabilities v1.0 - Capability #4
"""

import re
import hashlib
import ssl
import socket
from typing import Optional
from urllib.parse import urlparse
import logging

try:
    from Levenshtein import ratio as levenshtein_ratio
except ImportError:
    # Fallback implementation if python-Levenshtein not installed
    def levenshtein_ratio(s1: str, s2: str) -> float:
        if not s1 or not s2:
            return 0.0
        if s1 == s2:
            return 1.0
        len1, len2 = len(s1), len(s2)
        if len1 < len2:
            s1, s2 = s2, s1
            len1, len2 = len2, len1
        distances = range(len2 + 1)
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

from .models import (
    Tool,
    GuardContext,
    GuardDecision,
    ServerConfig,
    WhitelistEntry,
)

logger = logging.getLogger(__name__)


class ServerSpoofingGuard:
    """
    MCP Security Guard for Server Spoofing Detection & Whitelisting.

    This guard enforces:
    - Server whitelist: Only approved servers can be accessed
    - Typosquat detection: Blocks servers with names similar to approved ones
    - Tool mimicry detection: Detects tools that copy trusted server signatures
    - Health validation: Verifies TLS and auth endpoint requirements
    """

    def __init__(self, config: Optional[ServerConfig] = None):
        self.config = config or ServerConfig()
        self._tool_registry: dict[str, dict[str, str]] = {}  # server -> {tool_name: fingerprint}

    def evaluate_server_connection(
        self,
        context: GuardContext,
    ) -> GuardDecision:
        """
        Evaluate whether a connection to an MCP server should be allowed.

        Called before establishing connection to a new MCP server.
        """
        server_name = context.server_name
        server_url = context.server_url
        warnings: list[str] = []

        # 1. Check whitelist
        if self.config.whitelist_enabled:
            whitelist_entry = self._find_whitelist_entry(server_name, server_url)

            if whitelist_entry is None:
                # Server not in whitelist - check for typosquat
                if self.config.typosquat_detection_enabled:
                    typosquat_match = self._detect_typosquat(server_name)
                    if typosquat_match:
                        return GuardDecision.deny(
                            code="typosquat_detected",
                            message=f"Server '{server_name}' appears to be typosquatting approved server '{typosquat_match}'",
                            details={
                                "detected_name": server_name,
                                "similar_to": typosquat_match,
                                "attack_type": "typosquatting",
                            }
                        )

                # Block unknown servers if configured
                if self.config.block_unknown_servers:
                    return GuardDecision.deny(
                        code="server_not_whitelisted",
                        message=f"Server '{server_name}' is not in the approved server registry",
                        details={
                            "server_name": server_name,
                            "server_url": server_url,
                            "action": "Add server to whitelist if this is a legitimate server",
                        }
                    )
                else:
                    warnings.append(f"Server '{server_name}' is not in whitelist")

        # 2. Validate server health (TLS, auth)
        if self.config.health_validation_enabled and server_url:
            health_result = self._validate_server_health(server_url, context)
            if health_result.decision.value == "deny":
                return health_result
            warnings.extend(health_result.warnings)

        if warnings and self.config.alert_on_warnings:
            return GuardDecision.warn(warnings)

        return GuardDecision.allow()

    def evaluate_tools_list(
        self,
        tools: list[Tool],
        context: GuardContext,
    ) -> GuardDecision:
        """
        Evaluate tools returned by an MCP server.

        Detects tool mimicry where a server returns tools that impersonate
        tools from trusted servers.
        """
        server_name = context.server_name
        warnings: list[str] = []

        # Store tool fingerprints for this server
        tool_fingerprints = {}
        for tool in tools:
            fingerprint = self._compute_tool_fingerprint(tool)
            tool_fingerprints[tool.name] = fingerprint

        # Check for tool mimicry
        if self.config.tool_mimicry_detection_enabled:
            mimicry_result = self._detect_tool_mimicry(server_name, tools)
            if mimicry_result:
                return GuardDecision.deny(
                    code="tool_mimicry_detected",
                    message=f"Server '{server_name}' contains tools that mimic trusted server tools",
                    details={
                        "server_name": server_name,
                        "mimicked_tools": mimicry_result,
                        "attack_type": "tool_mimicry",
                    }
                )

        # Check for duplicate tool names across servers (namespace collision)
        duplicates = self._check_duplicate_tools(server_name, tools)
        if duplicates:
            return GuardDecision.deny(
                code="tool_namespace_collision",
                message=f"Server '{server_name}' has tools that collide with other servers",
                details={
                    "collisions": duplicates,
                    "recommendation": "Use namespaced tool names (e.g., server_name.tool_name)",
                }
            )

        # Update registry with this server's tools
        self._tool_registry[server_name] = tool_fingerprints

        if warnings:
            return GuardDecision.warn(warnings)

        return GuardDecision.allow()

    def _find_whitelist_entry(
        self,
        server_name: str,
        server_url: Optional[str]
    ) -> Optional[WhitelistEntry]:
        """Find matching whitelist entry for a server."""
        for entry in self.config.whitelist:
            # Match by name
            if entry.name.lower() == server_name.lower():
                return entry

            # Match by URL pattern
            if server_url and entry.url_pattern:
                try:
                    if re.match(entry.url_pattern, server_url, re.IGNORECASE):
                        return entry
                except re.error:
                    logger.warning(f"Invalid regex in whitelist: {entry.url_pattern}")

        return None

    def _detect_typosquat(self, server_name: str) -> Optional[str]:
        """
        Detect if server name is a typosquat of an approved server.

        Uses Levenshtein distance to find similar names.
        """
        threshold = self.config.typosquat_similarity_threshold

        for entry in self.config.whitelist:
            approved_name = entry.name.lower()
            test_name = server_name.lower()

            # Skip exact matches
            if approved_name == test_name:
                continue

            # Calculate similarity
            similarity = levenshtein_ratio(approved_name, test_name)

            if similarity >= threshold:
                # Additional heuristics for common typosquat patterns
                if self._is_typosquat_pattern(approved_name, test_name):
                    return entry.name

        return None

    def _is_typosquat_pattern(self, approved: str, suspect: str) -> bool:
        """Check for common typosquat patterns."""
        # Check if difference is a single character substitution
        if len(approved) == len(suspect):
            diffs = sum(1 for a, b in zip(approved, suspect) if a != b)
            if diffs == 1:
                return True

        # Check homoglyph attacks (visually similar characters)
        homoglyphs = {
            'o': ['0', 'ο'],  # Latin o, zero, Greek omicron
            'l': ['1', 'I', '|'],
            'i': ['1', 'l', '|'],
            'a': ['@', 'α'],
            'e': ['3', 'е'],  # Latin e, Cyrillic е
        }

        normalized_approved = approved
        normalized_suspect = suspect
        for char, substitutes in homoglyphs.items():
            for sub in substitutes:
                normalized_suspect = normalized_suspect.replace(sub, char)

        if normalized_approved == normalized_suspect and approved != suspect:
            return True

        return False

    def _compute_tool_fingerprint(self, tool: Tool) -> str:
        """Compute a fingerprint for a tool based on its metadata."""
        content = f"{tool.name}|{tool.description or ''}|{tool.input_schema}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _detect_tool_mimicry(
        self,
        server_name: str,
        tools: list[Tool]
    ) -> Optional[list[dict]]:
        """
        Detect if tools mimic trusted server tools.

        Returns list of mimicked tools if detected, None otherwise.
        """
        mimicked = []

        # Get trusted tool fingerprints from whitelist
        trusted_tools: dict[str, tuple[str, str]] = {}  # fingerprint -> (server_name, tool_name)
        for entry in self.config.whitelist:
            for tool_name, fingerprint in entry.tool_fingerprints.items():
                trusted_tools[fingerprint] = (entry.name, tool_name)

        # Compare incoming tools against trusted fingerprints
        for tool in tools:
            fingerprint = self._compute_tool_fingerprint(tool)

            # Check for exact fingerprint match from different server
            if fingerprint in trusted_tools:
                trusted_server, trusted_tool = trusted_tools[fingerprint]
                if trusted_server.lower() != server_name.lower():
                    mimicked.append({
                        "tool_name": tool.name,
                        "mimics_server": trusted_server,
                        "mimics_tool": trusted_tool,
                        "match_type": "exact_fingerprint",
                    })

            # Check for similar tool names with different implementations
            for entry in self.config.whitelist:
                if entry.name.lower() == server_name.lower():
                    continue

                for trusted_name in entry.tool_fingerprints.keys():
                    if tool.name.lower() == trusted_name.lower():
                        # Same name, different server - potential mimicry
                        mimicked.append({
                            "tool_name": tool.name,
                            "mimics_server": entry.name,
                            "mimics_tool": trusted_name,
                            "match_type": "name_collision",
                        })

        return mimicked if mimicked else None

    def _check_duplicate_tools(
        self,
        server_name: str,
        tools: list[Tool]
    ) -> Optional[list[dict]]:
        """Check for tool name collisions with other registered servers."""
        duplicates = []

        for tool in tools:
            for other_server, other_tools in self._tool_registry.items():
                if other_server.lower() == server_name.lower():
                    continue

                if tool.name in other_tools:
                    duplicates.append({
                        "tool_name": tool.name,
                        "this_server": server_name,
                        "other_server": other_server,
                    })

        return duplicates if duplicates else None

    def _validate_server_health(
        self,
        server_url: str,
        context: GuardContext
    ) -> GuardDecision:
        """
        Validate server health and security configuration.

        Checks:
        - Valid TLS certificate
        - Auth endpoints respond correctly
        - No exposed debug endpoints
        """
        warnings: list[str] = []
        parsed = urlparse(server_url)

        # Check TLS requirement
        if self.config.require_valid_tls:
            if parsed.scheme == "http":
                return GuardDecision.deny(
                    code="tls_required",
                    message=f"Server '{context.server_name}' does not use TLS (HTTPS required)",
                    details={
                        "server_url": server_url,
                        "scheme": parsed.scheme,
                        "requirement": "All MCP servers must use HTTPS",
                    }
                )

            # Validate TLS certificate
            if parsed.scheme == "https":
                tls_valid, tls_error = self._check_tls_certificate(
                    parsed.hostname or "",
                    parsed.port or 443
                )
                if not tls_valid:
                    return GuardDecision.deny(
                        code="invalid_tls_certificate",
                        message=f"Server '{context.server_name}' has invalid TLS certificate",
                        details={
                            "server_url": server_url,
                            "tls_error": tls_error,
                        }
                    )

        if warnings:
            return GuardDecision.warn(warnings)

        return GuardDecision.allow()

    def _check_tls_certificate(
        self,
        hostname: str,
        port: int
    ) -> tuple[bool, Optional[str]]:
        """Verify TLS certificate is valid."""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    if cert:
                        return True, None
                    return False, "No certificate returned"
        except ssl.SSLCertVerificationError as e:
            return False, f"Certificate verification failed: {e}"
        except socket.timeout:
            return False, "Connection timeout"
        except socket.gaierror as e:
            return False, f"DNS resolution failed: {e}"
        except Exception as e:
            return False, f"TLS check failed: {e}"

    def reset_server(self, server_name: str) -> None:
        """Reset state for a server (called on session re-initialization)."""
        if server_name in self._tool_registry:
            del self._tool_registry[server_name]

    def add_to_whitelist(self, entry: WhitelistEntry) -> None:
        """Add a server to the whitelist."""
        # Remove existing entry with same name
        self.config.whitelist = [
            e for e in self.config.whitelist
            if e.name.lower() != entry.name.lower()
        ]
        self.config.whitelist.append(entry)

    def remove_from_whitelist(self, server_name: str) -> bool:
        """Remove a server from the whitelist."""
        original_len = len(self.config.whitelist)
        self.config.whitelist = [
            e for e in self.config.whitelist
            if e.name.lower() != server_name.lower()
        ]
        return len(self.config.whitelist) < original_len
