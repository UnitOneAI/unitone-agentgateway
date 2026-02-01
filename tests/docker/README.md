# Docker-Based E2E Tests

This directory contains Docker infrastructure for running E2E tests against AgentGateway with MCP test servers.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐      ┌─────────────────────────┐
│   Test Runner   │────▶│  AgentGateway   │────▶│   MCP Test Servers      │
│   (Python)      │     │   (port 8080)   │      │  - PII (8000)           │
└─────────────────┘     └─────────────────┘      │  - Tool Poisoning (8010)│
                                                 │  - Rug Pull (8020)      │
                                                 └─────────────────────────┘
```

## Prerequisites

1. **Docker** and **Docker Compose** installed
2. **For security guards testing**: Either ACR access OR 10GB+ Docker memory for local builds

## Current Status

**MCP Test Servers**: Built from source (`testservers/` directory) - no external dependencies.

**AgentGateway**: Uses pre-built ACR image by default (`your-acr.azurecr.io/unitone-agentgateway:latest`).

⚠️ **Important**: The default ACR image may not have security guards support. For full security guard testing:
- Push a security-guards-enabled image to ACR, or
- Build locally with increased Docker memory (10GB+), or
- Run tests in GitHub Actions CI

## Configuration Options

Three configuration files are available in `configs/`:

| Config | Security Guards | Use Case |
|--------|-----------------|----------|
| `e2e-gateway-config.yaml` | ✅ Full | Production-like testing (requires security-guards image) |
| `e2e-gateway-config-basic.yaml` | ❌ None | Basic MCP routing tests |
| `e2e-gateway-config-passthrough.yaml` | ❌ None | Simple HTTP proxy tests |

To change configs, edit `docker-compose.yaml`:
```yaml
volumes:
  - ./configs/e2e-gateway-config.yaml:/app/config.yaml:ro
```

## Usage

### CI/CD Mode (Fully Containerized)

Run all tests in containers - ideal for CI/CD pipelines:

```bash
# From project root
make test-docker

# Or directly with docker-compose
cd tests/docker
docker compose up --build --abort-on-container-exit --exit-code-from test-runner
docker compose down -v
```

### Development Mode (Services in Docker, Tests from Host)

Start services and run tests from your host machine - ideal for development:

```bash
# Start services (MCP test servers + gateway)
cd tests/docker
docker compose up -d mcp-test-servers agentgateway

# Run specific tests
GATEWAY_URL=http://localhost:8080 python ../e2e_pii_guard_test.py
GATEWAY_URL=http://localhost:8080 python ../e2e_security_guards_test.py

# Stop services
docker compose down
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f agentgateway
docker compose logs -f mcp-test-servers
```

## Services

| Service | Image Source | Ports | Description |
|---------|--------------|-------|-------------|
| mcp-test-servers | Built from `testservers/` | 8000, 8010, 8020 | PII, Tool Poisoning, Rug Pull test servers |
| agentgateway | ACR image (or local build) | 8080 | AgentGateway |
| test-runner | Built from `Dockerfile.test-runner` | - | Python test container (CI/CD only) |

## Building AgentGateway Locally

**Note**: Local builds require 10GB+ memory due to Rust LTO compilation.

To increase Docker memory on Mac (Colima):
```bash
colima stop
colima start --memory 12
```

To build locally instead of using ACR image, edit `docker-compose.yaml`:
```yaml
agentgateway:
  # Replace:
  # image: your-acr.azurecr.io/unitone-agentgateway:latest
  # With:
  build:
    context: ../..
    dockerfile: Dockerfile.acr
```

## Troubleshooting

### Memory Exhaustion During Build

If the agentgateway build fails with "cannot allocate memory":
- Increase Docker memory to 10GB+ (see above)
- Or use the pre-built ACR image

### Service Not Starting

```bash
# Check service logs
docker compose logs mcp-test-servers
docker compose logs agentgateway

# Check health status
docker compose ps
```

### Config Error: "unknown field securityGuards"

The ACR image doesn't have security guards support. Use `e2e-gateway-config-basic.yaml` or `e2e-gateway-config-passthrough.yaml` instead.

### Tests Failing to Connect

1. Ensure gateway is healthy: `curl http://localhost:8080/ui/`
2. Check MCP servers inside container: `docker exec docker-mcp-test-servers-1 python -c "import socket; s=socket.socket(); s.connect(('localhost',8000)); print('OK')"`

## Test Server Source

The MCP test servers are located in `testservers/` directory at the project root. They include:
- **PII Test Server** (8000) - Generates fake PII data for testing detection
- **Tool Poisoning Test Server** (8010) - Contains malicious patterns in tool metadata
- **Rug Pull Test Server** (8020) - Changes tool metadata after initial listing
