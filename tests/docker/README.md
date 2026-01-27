# Docker-Based E2E Tests

This directory contains Docker infrastructure for running E2E tests against AgentGateway with MCP test servers.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────────┐
│   Test Runner   │────▶│  AgentGateway   │────▶│   MCP Test Servers      │
│   (Python)      │     │   (port 8080)   │     │  - PII (8000)           │
└─────────────────┘     └─────────────────┘     │  - Tool Poisoning (8010)│
                                                │  - Rug Pull (8020)      │
                                                └─────────────────────────┘
```

## Prerequisites

1. **Docker** and **Docker Compose** installed

That's it! All images are built from source - no ACR access required.

## Usage

### CI/CD Mode (Fully Containerized)

Run all tests in containers - ideal for CI/CD pipelines:

```bash
# From project root
make test-docker

# Or directly with docker-compose
cd tests/docker
docker-compose up --build --abort-on-container-exit --exit-code-from test-runner
docker-compose down -v
```

### Development Mode (Services in Docker, Tests from Host)

Start services and run tests from your host machine - ideal for development:

```bash
# Start services
make test-docker-up

# Run specific tests (streamable transport is default)
GATEWAY_URL=http://localhost:8080 python tests/e2e_pii_guard_test.py
GATEWAY_URL=http://localhost:8080 python tests/e2e_security_guards_test.py

# Stop services
make test-docker-down
```

### Transport Protocols

The MCP test servers use **Streamable HTTP** transport (FastMCP default), which returns plain JSON responses.

| Transport | Format | Supported |
|-----------|--------|-----------|
| `streamable` | Plain JSON `{...}` | ✅ Yes (recommended) |
| `sse` | SSE format `data: {...}` | ❌ No (servers don't support SSE) |

Streamable HTTP is the default transport, so no `--transport` flag is needed.

### View Logs

```bash
make test-docker-logs

# Or specific service
docker-compose -f tests/docker/docker-compose.yaml logs -f agentgateway
```

## Services

| Service | Source | Ports | Description |
|---------|--------|-------|-------------|
| mcp-test-servers | Built from `testservers/` | 8000, 8010, 8020 | PII, Tool Poisoning, Rug Pull test servers |
| agentgateway | Built from `Dockerfile.acr` | 8080 | AgentGateway with security guards |
| test-runner | Built from `Dockerfile.test-runner` | - | Python test container (CI/CD only) |

All images are built from source during `docker-compose up --build`.

## Configuration

The gateway is configured via `configs/e2e-gateway-config.yaml`:

| Route | Target | Security Guards |
|-------|--------|-----------------|
| `/pii-test` | mcp-test-servers:8000 | PII detection, Tool poisoning |
| `/poison` | mcp-test-servers:8010 | Tool poisoning |
| `/rug-pull` | mcp-test-servers:8020 | Rug pull detection |

## Troubleshooting

### Service Not Starting

```bash
# Check service logs
docker-compose -f tests/docker/docker-compose.yaml logs mcp-test-servers
docker-compose -f tests/docker/docker-compose.yaml logs agentgateway

# Check health status
docker-compose -f tests/docker/docker-compose.yaml ps
```

### Tests Failing to Connect

1. Ensure gateway is healthy: `curl http://localhost:8080/ui/`
2. Check MCP servers: `curl http://localhost:8000/mcp` (if ports exposed)
3. Verify network: `docker network ls` and `docker network inspect docker_test-network`

## Test Server Source

The MCP test servers are located in `testservers/` directory at the project root. They include:
- **PII Test Server** - Generates fake PII data for testing detection
- **Tool Poisoning Test Server** - Contains malicious patterns in tool metadata
- **Rug Pull Test Server** - Changes tool metadata after initial listing
