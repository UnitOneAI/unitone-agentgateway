"""
Data models for Server Spoofing Guard.

These models match the WIT interface used by WASM guards for compatibility.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json


@dataclass
class Tool:
    """MCP Tool definition."""
    name: str
    description: Optional[str] = None
    input_schema: str = "{}"  # JSON-serialized schema

    def schema_dict(self) -> dict:
        """Parse input_schema as dict."""
        try:
            return json.loads(self.input_schema)
        except json.JSONDecodeError:
            return {}


@dataclass
class GuardContext:
    """Context provided to guard during evaluation."""
    server_name: str
    server_url: Optional[str] = None
    identity: Optional[str] = None
    metadata: str = "{}"  # JSON-serialized metadata

    def metadata_dict(self) -> dict:
        """Parse metadata as dict."""
        try:
            return json.loads(self.metadata)
        except json.JSONDecodeError:
            return {}


@dataclass
class DenyReason:
    """Reason for denying a request."""
    code: str
    message: str
    details: Optional[dict] = None

    def to_dict(self) -> dict:
        result = {"code": self.code, "message": self.message}
        if self.details:
            result["details"] = self.details
        return result


class DecisionType(Enum):
    """Guard decision types."""
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"  # Allow but log warning


@dataclass
class GuardDecision:
    """Decision returned by guard evaluation."""
    decision: DecisionType
    reason: Optional[DenyReason] = None
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def allow(cls) -> "GuardDecision":
        return cls(decision=DecisionType.ALLOW)

    @classmethod
    def deny(cls, code: str, message: str, details: Optional[dict] = None) -> "GuardDecision":
        return cls(
            decision=DecisionType.DENY,
            reason=DenyReason(code=code, message=message, details=details)
        )

    @classmethod
    def warn(cls, warnings: list[str]) -> "GuardDecision":
        return cls(decision=DecisionType.WARN, warnings=warnings)


@dataclass
class WhitelistEntry:
    """Approved server whitelist entry."""
    name: str
    url_pattern: str  # Regex pattern for allowed URLs
    description: Optional[str] = None
    required_tls: bool = True
    required_auth: bool = True
    allowed_tools: Optional[list[str]] = None  # None = all tools allowed

    # Fingerprint for detecting tool mimicry
    tool_fingerprints: dict[str, str] = field(default_factory=dict)  # tool_name -> description_hash


@dataclass
class ServerConfig:
    """Guard configuration."""
    # Whitelist mode
    whitelist_enabled: bool = True
    whitelist: list[WhitelistEntry] = field(default_factory=list)

    # Typosquat detection
    typosquat_detection_enabled: bool = True
    typosquat_similarity_threshold: float = 0.85  # Levenshtein similarity

    # Tool mimicry detection
    tool_mimicry_detection_enabled: bool = True
    tool_similarity_threshold: float = 0.90

    # Health validation
    health_validation_enabled: bool = True
    require_valid_tls: bool = True
    require_auth_endpoints: bool = True

    # Behavior
    block_unknown_servers: bool = True
    alert_on_warnings: bool = True
