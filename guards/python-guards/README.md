# Python Security Guards

This directory contains Python-based MCP security guards for AgentGateway.

## Available Guards

| Guard | Capability | Priority | Description |
|-------|------------|----------|-------------|
| [server-spoofing-guard](./server-spoofing-guard/) | #4 Server Spoofing & Whitelisting | P1 | Block fake servers, enforce registry, validate health |

## Architecture

Python guards complement the native Rust guards and WASM guards:

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentGateway                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Security Guard Framework                │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │    │
│  │  │ Native Rust  │ │    WASM      │ │   Python     │ │    │
│  │  │   Guards     │ │   Guards     │ │   Guards     │ │    │
│  │  │              │ │              │ │              │ │    │
│  │  │ - PII        │ │ - Custom     │ │ - Server     │ │    │
│  │  │ - Poisoning  │ │   patterns   │ │   Spoofing   │ │    │
│  │  │ - Rug Pull   │ │              │ │              │ │    │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Guard Interface

All Python guards implement the same interface as WASM guards:

```python
class Guard:
    def evaluate_server_connection(
        self,
        context: GuardContext,
    ) -> GuardDecision:
        """Evaluate before connecting to MCP server."""
        ...

    def evaluate_tools_list(
        self,
        tools: list[Tool],
        context: GuardContext,
    ) -> GuardDecision:
        """Evaluate tools/list response."""
        ...

    def evaluate_tool_invoke(
        self,
        tool_name: str,
        arguments: dict,
        context: GuardContext,
    ) -> GuardDecision:
        """Evaluate tool invocation."""
        ...

    def reset_server(self, server_name: str) -> None:
        """Reset state for server (called on session re-init)."""
        ...
```

## Decision Types

```python
from enum import Enum

class DecisionType(Enum):
    ALLOW = "allow"   # Proceed with request
    DENY = "deny"     # Block request with reason
    WARN = "warn"     # Allow but log warning
```

## Creating a New Guard

1. Create a new directory under `python-guards/`:
   ```
   python-guards/
   └── my-new-guard/
       ├── pyproject.toml
       ├── README.md
       ├── src/
       │   └── my_guard/
       │       ├── __init__.py
       │       ├── guard.py
       │       └── models.py
       └── tests/
           └── test_guard.py
   ```

2. Implement the guard interface in `guard.py`

3. Add tests in `tests/`

4. Document in `README.md`

## UNITONE Security Capabilities

These guards implement capabilities from the UNITONE Gateway Security Capabilities v1.0:

### Tier 1: MCP-Specific Differentiators (P0-P1)
- #1 Tool Poisoning Detection ✓ (Native Rust)
- #2 Rug Pull Detection ✓ (Native Rust)
- #3 Tool Shadowing Prevention (Planned)
- **#4 Server Spoofing & Whitelisting ✓ (Python)**

### Tier 2: MCP-Enhanced Security (P1-P2)
- #5 Tool-Level Access Control (Planned)
- #6 Content Filtering & Protocol Validation (Planned)
- #7 Token & Session Security (Planned)
- #8 Context Integrity Validation (Planned)

### Tier 3: Operational Foundation (P2-P3)
- #9 Audit Logging with MCP Correlation (Planned)
- #10 Sensitive Data Protection (DLP) ✓ (Native Rust - PII Guard)
- #11 Rate Limiting & Abuse Protection (Planned)
- #12 Anomaly Detection & Behavior Analytics (Planned)

## Running Tests

```bash
# Run all Python guard tests
cd guards/python-guards/server-spoofing-guard
pip install -e ".[dev]"
pytest tests/ -v
```
