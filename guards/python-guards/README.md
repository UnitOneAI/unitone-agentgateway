# Python Security Guards

This directory contains Python-based MCP security guards for AgentGateway.

## Status

| Version | Status | Can Run in AgentGateway? |
|---------|--------|--------------------------|
| Pure Python | ✅ Tests pass | ❌ No - Standalone only |
| WASM | ✅ Builds, tests pass | ✅ Yes - With `--features wasm-guards` |
| Native Rust | N/A | ✅ Yes - PII, Poisoning, Rug Pull guards work today |

### What Works Today

- **Native Rust Guards**: PII detection, Tool Poisoning, Rug Pull detection
- **WASM Guards**: Load `.wasm` components via wasmtime runtime
- **Pure Python**: Standalone library for development, testing, and prototyping

## Available Guards

| Guard | Capability | Description |
|-------|------------|-------------|
| [server-spoofing-guard](./server-spoofing-guard/) | Server Spoofing & Whitelisting | Block fake servers, enforce registry, detect typosquatting |
| [server-spoofing-guard-wasm](./server-spoofing-guard-wasm/) | (WASM build) | Same guard compiled to WebAssembly component |

## Quick Start

### Pure Python Version (Standalone Testing)

```bash
cd server-spoofing-guard
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v  # 14 tests
```

### WASM Version (Build & Run in AgentGateway)

```bash
cd server-spoofing-guard-wasm
python3 -m venv .venv
source .venv/bin/activate
pip install componentize-py wasmtime pytest

# Build WASM component
./build.sh  # Creates server_spoofing_guard.wasm (~39MB)

# Run structural tests
pytest tests/ -v  # 18 tests
```

Then configure in AgentGateway:

```yaml
security_guards:
  - id: server-spoofing-guard
    type: wasm
    enabled: true
    priority: 10
    failure_mode: fail_closed
    timeout_ms: 100
    runs_on: [response]
    module_path: ./guards/server_spoofing_guard.wasm
    config:
      whitelist:
        - name: finance-tools
          url_pattern: "https://finance\\.company\\.com/.*"
      block_unknown_servers: true
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      AgentGateway (Rust)                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                Security Guard Framework                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │  │
│  │  │ Native Rust │  │    WASM     │  │     Python      │   │  │
│  │  │   Guards    │  │   Guards    │  │     Guards      │   │  │
│  │  │             │  │             │  │                 │   │  │
│  │  │ • PII    ✅ │  │ • Server ✅ │  │ (not supported) │   │  │
│  │  │ • Poison ✅ │  │   Spoofing  │  │                 │   │  │
│  │  │ • Rug    ✅ │  │ • Custom ✅ │  │                 │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

✅ = Works today (requires --features wasm-guards for WASM)
```

### Guard Types Comparison

| Aspect | Native Rust | WASM (Python-in-WASM) | Pure Python |
|--------|-------------|----------------------|-------------|
| **Runtime** | Native code | Python interpreter in WASM sandbox | Python interpreter |
| **Runs in Gateway?** | ✅ Yes | ✅ Yes | ❌ No |
| **Latency** | ~1ms | ~5-10ms | N/A |
| **Sandboxing** | Process | WASM sandbox | N/A |
| **Component Size** | In binary | ~39MB (includes Python) | N/A |
| **Use case** | Production | Production | Dev/Testing |

> **Note**: The WASM version uses [componentize-py](https://github.com/bytecodealliance/componentize-py) which embeds a Python interpreter into the WASM component. This is Python running inside WASM, not native WASM code.

## Server Spoofing Guard

Protects against:

1. **Fake Servers** - Only whitelisted servers allowed
2. **Typosquatting** - Detects `finance-too1s` vs `finance-tools` (Levenshtein + homoglyphs)
3. **Tool Mimicry** - Blocks tools copying trusted server signatures (SHA256 fingerprinting)
4. **Namespace Collision** - Prevents duplicate tool names across servers

### Example Usage (Standalone Python)

```python
from server_spoofing_guard import (
    ServerSpoofingGuard,
    GuardContext,
    ServerConfig,
    WhitelistEntry,
)

config = ServerConfig(
    whitelist=[
        WhitelistEntry(
            name="finance-tools",
            url_pattern=r"https://finance\.company\.com/.*",
        ),
    ],
    block_unknown_servers=True,
    typosquat_similarity_threshold=0.85,
)

guard = ServerSpoofingGuard(config=config)

# Evaluate a connection
context = GuardContext(
    server_name="finance-tools",
    server_url="https://finance.company.com/mcp",
)
result = guard.evaluate_server_connection(context)

if result.decision.value == "deny":
    print(f"Blocked: {result.reason.message}")
```

## Guard Interface

All guards implement the WIT-defined interface:

```python
class Guard:
    def evaluate_server_connection(
        self, context: GuardContext
    ) -> GuardResult:
        """Evaluate before connecting to MCP server."""
        ...

    def evaluate_tools_list(
        self, tools: list[Tool], context: GuardContext
    ) -> GuardResult:
        """Evaluate tools/list response."""
        ...
```

### Decision Types

```python
class Decision:
    ALLOW = "allow"   # Proceed with request
    DENY = "deny"     # Block request with reason
    WARN = "warn"     # Allow but log warning
```

## Creating a New Guard

1. Create directory structure:
   ```
   python-guards/
   └── my-guard/
       ├── pyproject.toml
       ├── README.md
       ├── src/my_guard/
       │   ├── __init__.py
       │   ├── guard.py
       │   └── models.py
       └── tests/
           └── test_guard.py
   ```

2. Implement the guard interface

3. Add tests

4. (Optional) Create WASM version:
   ```
   my-guard-wasm/
   ├── wit/guard.wit      # Copy from crates/agentgateway/src/mcp/security/wit/
   ├── app.py             # Guard implementation with Guard class
   ├── build.sh           # componentize-py build script
   └── tests/
       └── test_wasm.py   # WASM structural tests
   ```

## Test Summary

| Guard | Tests | What's Tested |
|-------|-------|---------------|
| server-spoofing-guard | 14 | Guard logic: whitelist, typosquat, mimicry, TLS |
| server-spoofing-guard-wasm | 18 | WASM structure, component loading, WIT compliance |
| **Total** | **32** | |

Run all tests:
```bash
# Pure Python - tests guard logic
cd server-spoofing-guard && pytest tests/ -v

# WASM - tests component structure
cd server-spoofing-guard-wasm && pytest tests/ -v
```

## Security Capabilities

| # | Capability | Status | Implementation |
|---|------------|--------|----------------|
| 1 | Tool Poisoning Detection | ✅ Production | Native Rust |
| 2 | Rug Pull Detection | ✅ Production | Native Rust |
| 3 | Tool Shadowing Prevention | 📋 Planned | - |
| 4 | Server Spoofing & Whitelisting | ✅ Ready | WASM (Python) |
| 5 | Tool-Level Access Control | 📋 Planned | - |
| 10 | Sensitive Data Protection (DLP) | ✅ Production | Native Rust (PII) |

## References

- [componentize-py](https://github.com/bytecodealliance/componentize-py) - Python to WASM compiler
- [WebAssembly Component Model](https://component-model.bytecodealliance.org/)
- [WIT Format](https://component-model.bytecodealliance.org/design/wit.html)
