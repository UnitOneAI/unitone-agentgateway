# Server Spoofing & Whitelisting Guard

MCP Security Guard that protects against fake servers, typosquatting attacks, and unauthorized MCP deployments.

## Overview

This guard implements **Capability #4** from the UNITONE Gateway Security Capabilities:

> **Server Spoofing & Whitelisting** (Tier 1: MCP-Specific, Priority P1)
> Block fake servers, enforce registry, validate health

### Attack Patterns Prevented

1. **Server Spoofing**: Attackers create malicious MCP servers that impersonate legitimate servers
2. **Typosquatting**: Attackers register servers with names similar to trusted ones (e.g., `company-to0ls` vs `company-tools`)
3. **Shadow MCP**: Unauthorized MCP servers operating within an organization without security visibility
4. **Tool Mimicry**: Malicious servers copying tool definitions from trusted servers

## Features

### 1. Server Whitelisting
Only approved servers in the registry can be accessed.

```python
config = ServerConfig(
    whitelist_enabled=True,
    block_unknown_servers=True,
    whitelist=[
        WhitelistEntry(
            name="finance-tools",
            url_pattern=r"https://finance\.company\.com/.*",
            description="Official finance tools server",
        ),
    ],
)
```

### 2. Typosquat Detection
Identifies servers with names similar to approved servers using Levenshtein distance and homoglyph detection.

**Detection Examples:**
| Attack | Legitimate | Detection Method |
|--------|-----------|------------------|
| `c0mpany-tools` | `company-tools` | Homoglyph (0→o) |
| `finance-too1s` | `finance-tools` | Homoglyph (1→l) |
| `finance-tool` | `finance-tools` | Missing character |
| `financee-tools` | `finance-tools` | Extra character |

### 3. Tool Mimicry Detection
Detects when a malicious server returns tools that copy trusted server signatures.

```python
# Trusted server fingerprints stored in whitelist
WhitelistEntry(
    name="finance-tools",
    tool_fingerprints={
        "calculate_invoice": "abc123",
        "send_receipt": "def456",
    },
)
```

### 4. TLS/Health Validation
Validates server security configuration:
- Valid TLS certificate required
- Auth endpoints respond correctly
- No exposed debug endpoints

## Installation

```bash
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Usage

### Basic Usage

```python
from server_spoofing_guard import (
    ServerSpoofingGuard,
    GuardContext,
    ServerConfig,
    WhitelistEntry,
)

# Create guard with whitelist
config = ServerConfig(
    whitelist=[
        WhitelistEntry(
            name="trusted-server",
            url_pattern=r"https://trusted\.example\.com/.*",
        ),
    ],
)
guard = ServerSpoofingGuard(config=config)

# Evaluate server connection
context = GuardContext(
    server_name="some-server",
    server_url="https://some-server.example.com/mcp",
)
result = guard.evaluate_server_connection(context)

if result.decision.value == "deny":
    print(f"Blocked: {result.reason.message}")
```

### Evaluating Tools

```python
from server_spoofing_guard import Tool

tools = [
    Tool(name="calculate", description="Perform calculations"),
    Tool(name="send_email", description="Send emails"),
]

result = guard.evaluate_tools_list(tools, context)
```

### Dynamic Whitelist Management

```python
# Add server to whitelist
guard.add_to_whitelist(WhitelistEntry(
    name="new-trusted-server",
    url_pattern=r"https://new\.trusted\.com/.*",
))

# Remove server from whitelist
guard.remove_from_whitelist("old-server")
```

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `whitelist_enabled` | bool | `True` | Enable whitelist enforcement |
| `whitelist` | list | `[]` | List of approved servers |
| `block_unknown_servers` | bool | `True` | Block servers not in whitelist |
| `typosquat_detection_enabled` | bool | `True` | Enable typosquat detection |
| `typosquat_similarity_threshold` | float | `0.85` | Similarity threshold (0-1) |
| `tool_mimicry_detection_enabled` | bool | `True` | Enable tool mimicry detection |
| `health_validation_enabled` | bool | `True` | Enable server health checks |
| `require_valid_tls` | bool | `True` | Require valid TLS certificate |

## Integration with AgentGateway

This guard is designed to integrate with AgentGateway's security guard framework. Example configuration:

```yaml
securityGuards:
  - id: server-spoofing-guard
    type: python
    enabled: true
    priority: 10  # Run early, before other guards
    failure_mode: fail_closed
    timeout_ms: 100
    runs_on:
      - connection  # Evaluate on server connection
      - response    # Evaluate tools/list responses
    module: server_spoofing_guard
    config:
      whitelist:
        - name: finance-tools
          url_pattern: "https://finance\\.company\\.com/.*"
        - name: hr-tools
          url_pattern: "https://hr\\.company\\.com/.*"
      block_unknown_servers: true
      typosquat_similarity_threshold: 0.85
```

## Testing

```bash
pytest tests/ -v
```

## Security Considerations

1. **Whitelist Maintenance**: Regularly review and update the whitelist
2. **Fingerprint Updates**: Update tool fingerprints when trusted servers update their tools
3. **Threshold Tuning**: Adjust similarity thresholds based on your naming conventions
4. **TLS Validation**: Always enable TLS validation in production

## References

- [MCP Manager Security Threat List](https://github.com/MCP-Manager/MCP-Checklists) - Server spoofing definition
- [OWASP MCP Top 10](https://owasp.org) - Shadow MCP deployments
- UNITONE Gateway Security Capabilities v1.0 - Capability #4
