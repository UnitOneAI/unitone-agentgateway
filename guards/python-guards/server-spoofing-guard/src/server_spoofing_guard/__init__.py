"""
Server Spoofing & Whitelisting Guard

MCP Security Guard that protects against:
- Fake/unauthorized MCP servers
- Typosquatting attacks (similar server names)
- Tool mimicry (duplicate tools across servers)
- Invalid TLS/auth configurations
"""

from .guard import ServerSpoofingGuard
from .models import (
    GuardContext,
    GuardDecision,
    DenyReason,
    Tool,
    ServerConfig,
    WhitelistEntry,
)

__version__ = "0.1.0"
__all__ = [
    "ServerSpoofingGuard",
    "GuardContext",
    "GuardDecision",
    "DenyReason",
    "Tool",
    "ServerConfig",
    "WhitelistEntry",
]
