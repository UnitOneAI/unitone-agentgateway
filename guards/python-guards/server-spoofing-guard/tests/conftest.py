"""Pytest configuration and fixtures for Server Spoofing Guard tests."""

import pytest
from server_spoofing_guard import (
    ServerSpoofingGuard,
    ServerConfig,
    WhitelistEntry,
    GuardContext,
    Tool,
)


@pytest.fixture
def basic_whitelist() -> list[WhitelistEntry]:
    """Basic whitelist with common test servers."""
    return [
        WhitelistEntry(
            name="finance-tools",
            url_pattern=r"https://finance\.company\.com/.*",
            description="Official finance tools server",
            tool_fingerprints={
                "calculate_invoice": "abc123def456",
                "send_receipt": "789xyz012abc",
            },
        ),
        WhitelistEntry(
            name="hr-tools",
            url_pattern=r"https://hr\.company\.com/.*",
            description="Official HR tools server",
        ),
        WhitelistEntry(
            name="company-tools",
            url_pattern=r"https://tools\.company\.com/.*",
            description="General company tools",
        ),
    ]


@pytest.fixture
def strict_config(basic_whitelist: list[WhitelistEntry]) -> ServerConfig:
    """Strict configuration that blocks unknown servers."""
    return ServerConfig(
        whitelist_enabled=True,
        whitelist=basic_whitelist,
        block_unknown_servers=True,
        typosquat_detection_enabled=True,
        typosquat_similarity_threshold=0.85,
        tool_mimicry_detection_enabled=True,
        health_validation_enabled=False,  # Disable for unit tests
        require_valid_tls=False,
    )


@pytest.fixture
def permissive_config(basic_whitelist: list[WhitelistEntry]) -> ServerConfig:
    """Permissive configuration that allows unknown servers with warnings."""
    return ServerConfig(
        whitelist_enabled=True,
        whitelist=basic_whitelist,
        block_unknown_servers=False,
        typosquat_detection_enabled=True,
        typosquat_similarity_threshold=0.85,
        tool_mimicry_detection_enabled=True,
        health_validation_enabled=False,
        require_valid_tls=False,
        alert_on_warnings=True,
    )


@pytest.fixture
def strict_guard(strict_config: ServerConfig) -> ServerSpoofingGuard:
    """Guard with strict configuration."""
    return ServerSpoofingGuard(config=strict_config)


@pytest.fixture
def permissive_guard(permissive_config: ServerConfig) -> ServerSpoofingGuard:
    """Guard with permissive configuration."""
    return ServerSpoofingGuard(config=permissive_config)


@pytest.fixture
def whitelisted_context() -> GuardContext:
    """Context for a whitelisted server."""
    return GuardContext(
        server_name="finance-tools",
        server_url="https://finance.company.com/mcp",
    )


@pytest.fixture
def unknown_context() -> GuardContext:
    """Context for an unknown server."""
    return GuardContext(
        server_name="unknown-server",
        server_url="https://unknown.example.com/mcp",
    )


@pytest.fixture
def sample_tools() -> list[Tool]:
    """Sample tools for testing."""
    return [
        Tool(
            name="calculate",
            description="Perform calculations",
            input_schema='{"type": "object", "properties": {"expression": {"type": "string"}}}',
        ),
        Tool(
            name="send_email",
            description="Send an email",
            input_schema='{"type": "object", "properties": {"to": {"type": "string"}, "body": {"type": "string"}}}',
        ),
    ]
