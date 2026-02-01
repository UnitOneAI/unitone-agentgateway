# Sticky Sessions for MCP Session Affinity

## Overview

AgentGateway stores MCP sessions in-memory. When running multiple replicas, requests from the same client must be routed to the same replica to maintain session state.

**Sticky sessions** (also called session affinity) use HTTP cookies to ensure all requests from a client are routed to the same replica.

## How It Works

1. When a client makes their first request, Azure Container Apps routes it to any available replica
2. The response includes an `ARRAffinity` cookie that identifies the replica
3. Subsequent requests include this cookie, ensuring they go to the same replica
4. If a replica becomes unavailable, the client is routed to a new replica (session will be lost)

## Configuration

### Terraform (Recommended)

Sticky sessions are enabled by default in the Terraform module (`terraform/`):

```hcl
# In terraform/terraform.tfvars
environment         = "prod"
resource_group_name = "agentgateway-prod-rg"

# Enable sticky sessions for MCP session affinity (default: true)
enable_sticky_sessions = true
```

The module automatically runs `az containerapp ingress sticky-sessions set` after creating the Container App.

### Azure CLI

Enable manually with:

```bash
az containerapp ingress sticky-sessions set \
  --name <container-app-name> \
  --resource-group <resource-group> \
  --affinity sticky
```

Verify configuration:

```bash
az containerapp show \
  --name <container-app-name> \
  --resource-group <resource-group> \
  --query "properties.configuration.ingress.stickySessions"
```

## Requirements

- **Single Revision Mode**: Sticky sessions only work when the Container App is in single revision mode
- **HTTP Ingress**: The container app must use HTTP ingress (not TCP)
- **Cookie Support**: Clients must accept and send cookies

## Limitations

1. **Session Loss on Replica Failure**: If a replica goes down, all sessions on that replica are lost
2. **Uneven Load Distribution**: Some replicas may handle more traffic than others
3. **No Cross-Replica Session Sharing**: Sessions exist only on the replica that created them

## Testing

Verify sticky sessions work with multiple replicas:

```bash
# Scale to multiple replicas
az containerapp update \
  --name unitone-agw-prod-app \
  --resource-group mcp-gateway-prod-rg \
  --min-replicas 2 \
  --max-replicas 10

# Run E2E tests
source .venv/bin/activate
GATEWAY_URL="https://your-gateway.azurecontainerapps.io" \
  python3 tests/e2e_mcp_sse_test.py
```

If tests pass with multiple replicas, sticky sessions are working correctly.

## When to Use

**Enable sticky sessions when:**
- Running multiple replicas for high availability
- Using stateful MCP mode (the default)
- Clients need to make multiple requests within a session

**Consider disabling when:**
- Running a single replica
- Using stateless MCP mode
- Session persistence is not required

## Alternative: Redis Session Storage

For production deployments requiring:
- Cross-replica session sharing
- Session persistence across restarts
- High availability without session loss

Consider implementing Redis session storage. This requires modifying the agentgateway core code (currently not supported).

## Troubleshooting

### "Session not found" errors with multiple replicas

1. Verify sticky sessions are enabled:
   ```bash
   az containerapp show --name <app-name> -g <rg> \
     --query "properties.configuration.ingress.stickySessions"
   ```

2. Check that clients are sending the `ARRAffinity` cookie

3. Verify the app is in single revision mode:
   ```bash
   az containerapp show --name <app-name> -g <rg> \
     --query "properties.configuration.activeRevisionsMode"
   ```

### Tests pass with 1 replica but fail with 2+

This indicates sticky sessions are not properly configured. Follow the configuration steps above.
