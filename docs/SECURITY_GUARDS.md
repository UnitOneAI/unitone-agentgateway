# AgentGateway Security Guards

Security guards protect your AI agents from common attack vectors when using MCP (Model Context Protocol) servers.

## Available Guards

### 1. Tool Poisoning Guard

Detects and blocks malicious tool descriptions that could manipulate AI behavior.

**Attack Pattern:**
An MCP server returns tools with descriptions containing hidden instructions like:
- "SYSTEM: ignore all previous instructions"
- "When this tool is called, also execute..."
- Hidden unicode characters with embedded commands

**Configuration:**
```yaml
securityGuards:
  toolPoisoning:
    enabled: true
    strict_mode: true
    custom_patterns:
      - "(?i)SYSTEM:\\s*override"
      - "(?i)ignore\\s+all\\s+previous"
```

**How it works:**
1. Intercepts `tools/list` responses from MCP servers
2. Scans tool names, descriptions, and input schemas
3. Blocks if suspicious patterns are detected
4. Returns error to client instead of poisoned tools

### 2. Rug Pull Guard

Detects when MCP servers change their tools after the initial handshake.

**Attack Pattern:**
An MCP server initially returns safe tools, but after the AI has been "trusted," it changes the tools to malicious ones (the "rug pull").

**Configuration:**
```yaml
securityGuards:
  rugPull:
    enabled: true
    scope: session  # or "global"
```

**Scope options:**
- `session`: Tracks tool changes per client session (recommended)
- `global`: Tracks changes across all sessions (stricter)

**How it works:**
1. Records tool fingerprint on first `tools/list` response
2. Compares subsequent responses against baseline
3. Blocks if tools have changed unexpectedly
4. New sessions establish fresh baselines

### 3. PII Guard

Detects and optionally masks personally identifiable information in MCP responses.

**Configuration:**
```yaml
securityGuards:
  pii:
    enabled: true
    detect:
      - email
      - credit_card
      - phone
      - ssn
    action: mask  # or "block"
    min_score: 0.3
```

**Actions:**
- `mask`: Replace PII with `[REDACTED]`
- `block`: Reject the entire response

## Configuration Example

Complete example with all guards:

```yaml
binds:
- port: 8080
  listeners:
  - hostname: "*"
    routes:
    - name: protected-mcp
      matches:
      - path:
          pathPrefix: /mcp
      backends:
      - mcp:
          targets:
          - name: backend
            mcp:
              host: http://mcp-server:3000/mcp
          statefulMode: stateful
      policies:
        securityGuards:
          toolPoisoning:
            enabled: true
            strict_mode: true
          rugPull:
            enabled: true
            scope: session
          pii:
            enabled: false  # Enable if needed
```

## Testing Security Guards

Run the E2E test suite to verify guards are working:

```bash
# Run all security guard tests
./deploy.sh

# Or manually
cd tests/docker
docker compose up -d --build
docker compose run --rm test-runner
```

The test suite includes:
- Tool poisoning detection tests
- Rug pull detection tests (session and global scope)
- PII masking tests

## Guard Behavior

### Failure Modes

Guards operate in `fail_closed` mode by default:
- If a guard detects a threat, the request is blocked
- If a guard encounters an error, the request is blocked
- This ensures security even during unexpected conditions

### Response Format

When a guard blocks a request, the client receives:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32603,
    "message": "Security guard denied for server 'backend': tool_poisoning detected suspicious content"
  }
}
```

## Best Practices

1. **Enable tool poisoning by default** - Low overhead, high protection
2. **Use session scope for rug pull** - Balances security and usability
3. **Enable PII only when needed** - Has performance overhead
4. **Test with your actual MCP servers** - Ensure no false positives
5. **Monitor guard logs** - Track blocked requests for security analysis

## Limitations

- Guards operate at the gateway level, not inside the AI model
- Cannot detect attacks embedded in legitimate-looking content
- PII detection has accuracy limits (configurable via `min_score`)
- Rug pull detection requires stateful sessions
