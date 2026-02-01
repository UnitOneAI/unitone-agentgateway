# Server Spoofing Guard - WASM Component

WASM-compiled version of the Server Spoofing Guard using [componentize-py](https://github.com/bytecodealliance/componentize-py).

This guard protects against:
- Fake/unauthorized MCP servers
- Typosquatting attacks (similar server names)
- Tool mimicry (duplicate tools across servers)

## Prerequisites

- Python 3.10+
- componentize-py 0.16.0+
- wasmtime 27.0.0+ (for testing)

## Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install build tools
pip install componentize-py wasmtime
```

## Building

```bash
chmod +x build.sh
./build.sh
```

This produces `server_spoofing_guard.wasm` - a WebAssembly Component that implements the guard interface.

## WIT Interface

The guard implements the `mcp:security-guard` world with two exported functions:

```wit
evaluate-server-connection: func(context: guard-context) -> result<decision, string>;
evaluate-tools-list: func(tools: list<tool>, context: guard-context) -> result<decision, string>;
```

### Decision Types

| Decision | Description |
|----------|-------------|
| `allow` | Request is permitted |
| `deny(reason)` | Request is blocked with reason |
| `warn(messages)` | Request is permitted with warnings |

## Configuration

The guard reads configuration from the host via `get_config("guard_config")`. Expected JSON structure:

```json
{
  "whitelist_enabled": true,
  "whitelist": [
    {
      "name": "finance-tools",
      "url_pattern": "https://finance\\.company\\.com/.*",
      "tool_fingerprints": {
        "calculate_invoice": "abc123def456"
      }
    }
  ],
  "block_unknown_servers": true,
  "typosquat_detection_enabled": true,
  "typosquat_similarity_threshold": 0.85,
  "tool_mimicry_detection_enabled": true
}
```

## AgentGateway Integration

Add to your AgentGateway configuration:

```yaml
security_guards:
  - id: server-spoofing-guard
    type: wasm
    enabled: true
    priority: 10              # Run early
    failure_mode: fail_closed # Block on failure
    timeout_ms: 100
    runs_on:
      - connection            # Check before connecting
      - response              # Check tools/list responses
    module_path: ./guards/server_spoofing_guard.wasm
    config:
      whitelist:
        - name: finance-tools
          url_pattern: "https://finance\\.company\\.com/.*"
        - name: hr-tools
          url_pattern: "https://hr\\.company\\.com/.*"
      block_unknown_servers: true
      typosquat_similarity_threshold: 0.85
```

## Testing with wasmtime

```python
from wasmtime import Config, Engine, Store, Module, Linker

# Load the component
config = Config()
config.wasm_component_model = True
engine = Engine(config)
store = Store(engine)

with open("server_spoofing_guard.wasm", "rb") as f:
    module = Module(engine, f.read())

# Test evaluation...
```

## Attack Detection Examples

### Typosquatting

```
Approved: "finance-tools"
Attack:   "finance-too1s" (1 instead of l)
Result:   DENY - typosquat_detected
```

### Tool Mimicry

```
Trusted Server: "finance-tools" with tool "calculate_invoice"
Malicious:      "evil-server" with tool "calculate_invoice" (same fingerprint)
Result:         DENY - tool_mimicry_detected
```

### Unknown Server

```
Whitelist: ["finance-tools", "hr-tools"]
Request:   "random-server"
Result:    DENY - server_not_whitelisted
```

## Performance

| Metric | Value |
|--------|-------|
| Module size | ~500KB |
| Cold start | ~10ms |
| Evaluation | ~2-5ms |

## Comparison with Pure Python Version

| Aspect | Pure Python | WASM |
|--------|-------------|------|
| Runtime | Python interpreter | WASM runtime |
| Sandboxing | Process isolation | WASM sandbox |
| Dependencies | Can use pip packages | No external deps |
| Startup | Faster | Slower cold start |
| Integration | HTTP/subprocess | Native WASM loading |

## Limitations

- No external Python packages (Levenshtein implemented manually)
- No file system access (config via host)
- No network access (all data via host interface)
- State resets between invocations (unless host provides persistence)

## Development

The pure Python version at `../server-spoofing-guard/` can be used for:
- Rapid development and testing
- Debugging logic
- Unit tests

Once logic is validated, rebuild the WASM component.

## References

- [componentize-py](https://github.com/bytecodealliance/componentize-py)
- [WebAssembly Component Model](https://component-model.bytecodealliance.org/)
- [WIT Format](https://component-model.bytecodealliance.org/design/wit.html)
