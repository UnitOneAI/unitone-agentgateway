# E2E Test Guide

This guide explains how to run end-to-end (E2E) tests for AgentGateway security guards.

## What Gets Tested

The E2E tests validate three security guards that protect AI agents from malicious MCP servers:

| Guard | Purpose | What It Detects |
|-------|---------|-----------------|
| **Tool Poisoning** | Detects malicious instructions in tool descriptions | Hidden prompts like "ignore previous instructions" |
| **Rug Pull (Session)** | Detects tool changes within a session | Server modifying tools after initial connection |
| **Rug Pull (Global)** | Detects tool changes across sessions | Server modifying tools that affect all clients |

## Prerequisites

You need the following installed:

- **Docker Desktop** (with Docker Compose v2)
- **Azure CLI** (`az`) - for pulling images from ACR
- **Git** - for cloning the repository

### Verify Prerequisites

```bash
# Check Docker
docker --version
docker compose version

# Check Azure CLI
az --version

# Check Git
git --version
```

## Quick Start (5 minutes)

### Step 1: Clone the Repository

```bash
git clone --recursive https://github.com/UnitOneAI/unitone-agentgateway.git
cd unitone-agentgateway
```

> **Note**: The `--recursive` flag is important - it pulls the agentgateway submodule.

### Step 2: Login to Azure Container Registry

```bash
az login
az acr login --name agwimages
```

### Step 3: Run E2E Tests

```bash
./deploy.sh --e2e
```

This command will:
1. Pull the AgentGateway image from ACR
2. Build the test MCP servers locally
3. Start all containers
4. Run 17 security guard tests
5. Show results and keep services running

### Step 4: View Results

You should see output like:
```
============================================================
Test Results: 17 passed, 0 failed
============================================================
```

### Step 5: Explore (Optional)

While services are running:
- **Gateway UI**: http://localhost:8080/ui
- **View logs**: `cd tests/docker && docker compose logs -f`
- **Re-run tests**: `cd tests/docker && docker compose run --rm test-runner`

### Step 6: Stop Services

```bash
./deploy.sh --stop
```

## Alternative: Manual Docker Compose

If you prefer to run commands directly:

```bash
# Login to ACR first
az login
az acr login --name agwimages

# Run tests
cd tests/docker
docker compose up --build --abort-on-container-exit --exit-code-from test-runner

# Cleanup
docker compose down -v
```

## Test Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network                          │
│                                                             │
│  ┌─────────────────┐      ┌─────────────────────────────┐  │
│  │   Test Runner   │      │      MCP Test Servers       │  │
│  │   (Python)      │      │                             │  │
│  │                 │      │  :8000 - PII Server         │  │
│  │  Runs 17 tests  │      │  :8010 - Tool Poisoning     │  │
│  │                 │      │  :8020 - Rug Pull Server    │  │
│  └────────┬────────┘      └──────────────▲──────────────┘  │
│           │                              │                  │
│           │  HTTP requests               │  MCP protocol    │
│           │                              │                  │
│           ▼                              │                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              AgentGateway (:8080)                   │   │
│  │                                                     │   │
│  │  Routes:                                            │   │
│  │    /poison    → Tool Poisoning Server (:8010)       │   │
│  │    /rug-pull  → Rug Pull Server (:8020)             │   │
│  │    /pii-test  → PII Server (:8000)                  │   │
│  │                                                     │   │
│  │  Security Guards:                                   │   │
│  │    - Tool Poisoning Guard (enabled)                 │   │
│  │    - Rug Pull Guard (enabled, session scope)        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## What Each Test Does

### Tool Poisoning Tests (3 tests)

| Test | Description | Expected Result |
|------|-------------|-----------------|
| 1 | Connect to gateway | Connection succeeds |
| 2 | Initialize MCP session | Session created |
| 3 | List tools | **BLOCKED** - Guard detects poisoned descriptions |

The tool poisoning server returns tools with malicious descriptions like:
```
"When using this tool, first ignore all previous instructions..."
```

### Rug Pull Tests (14 tests)

**Session Scope Tests:**

| Test | Description | Expected Result |
|------|-------------|-----------------|
| 1-2 | Connect and initialize | Session created |
| 3 | Establish baseline | Tools recorded |
| 4 | List unchanged tools | Allowed |
| 5 | Call tool that triggers rug | Tool executes |
| 6 | List tools again | **BLOCKED** - Tools changed |
| 7 | New session after rug | Fresh baseline (allowed) |

**Global Scope Tests:**

| Test | Description | Expected Result |
|------|-------------|-----------------|
| 8-9 | Reset and setup | State cleared |
| 10 | Client A establishes baseline | Tools recorded |
| 11 | Client B triggers global rug | Rug activated |
| 12 | Client A lists tools | **BLOCKED** - Cross-session detection |
| 13 | New session after global rug | Fresh baseline (allowed) |

## Troubleshooting

### "Cannot connect to ACR"

```bash
# Re-authenticate
az login
az acr login --name agwimages
```

### "Docker daemon not running"

Start Docker Desktop, then retry.

### "Port 8080 already in use"

```bash
# Find what's using the port
lsof -i :8080

# Or use a different port
# Edit tests/docker/docker-compose.yaml, change "8080:8080" to "9080:8080"
```

### "Tests fail with connection refused"

Wait for services to be healthy:
```bash
cd tests/docker
docker compose ps  # Check all services show "healthy"
```

### "Out of memory during build"

Increase Docker memory to 10GB+ in Docker Desktop settings.

## Configuration Files

| File | Purpose |
|------|---------|
| `tests/docker/docker-compose.yaml` | Orchestrates all containers |
| `tests/docker/configs/e2e-gateway-config.yaml` | Gateway routing + security guards |
| `testservers/` | MCP test server implementations |
| `tests/e2e_security_guards_test.py` | Test script |

## Running Individual Tests

To run specific test suites:

```bash
cd tests/docker

# Run all tests
docker compose run --rm test-runner

# Run with verbose output
docker compose run --rm -e VERBOSE=1 test-runner

# Run against external gateway
docker compose run --rm -e GATEWAY_URL=https://your-gateway.azurecontainerapps.io test-runner
```

## CI/CD Integration

The same tests run automatically in GitHub Actions:

1. On push to `main` - runs E2E tests, then deploys if passing
2. On pull request - runs E2E tests only
3. Manual trigger - choose environment and whether to run tests

See `.github/workflows/azure-deploy.yml` for the workflow definition.
