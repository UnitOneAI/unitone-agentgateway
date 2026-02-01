# E2E Test Guide

This guide explains how to run end-to-end (E2E) tests for AgentGateway security guards.

## What Gets Tested

The E2E tests validate three security guards that protect AI agents from malicious MCP servers:

| Guard | Purpose | What It Detects |
|-------|---------|-----------------|
| **PII Guard** | Detects/redacts/blocks PII in tool responses | Email, SSN, credit card, phone numbers in responses |
| **Tool Poisoning** | Detects malicious instructions in tool descriptions | Hidden prompts like "ignore previous instructions" |
| **Rug Pull** | Detects tool definition changes mid-session | Server modifying tools after baseline establishment |

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
az acr login --name <your-acr-name>
```

### Step 3: Run E2E Tests

```bash
./deploy.sh
```

This command will:
1. Pull the AgentGateway image from ACR
2. Build the test MCP servers locally
3. Start all containers
4. Run security guard tests (PII, Tool Poisoning, Rug Pull)
5. Show results and keep services running

### Step 4: View Results

You should see output like:
```
============================================================
Test Results: 25 passed, 0 failed
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
az acr login --name <your-acr-name>

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
│  │  Runs E2E tests │      │  :8010 - Tool Poisoning     │  │
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
│  │    /pii-test  → PII Server (:8000)                  │   │
│  │    /poison    → Tool Poisoning Server (:8010)       │   │
│  │    /rug-pull  → Rug Pull Server (:8020)             │   │
│  │                                                     │   │
│  │  Security Guards:                                   │   │
│  │    - PII Guard (detects/redacts/blocks PII)         │   │
│  │    - Tool Poisoning Guard (blocks malicious descs)  │   │
│  │    - Rug Pull Guard (detects tool changes)          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## What Each Test Does

### PII Guard Tests (9 tests)

Tests PII detection, redaction, and blocking in tool responses.

| Test | Description | Expected Result |
|------|-------------|-----------------|
| 1 | MCP Endpoint Connectivity | Connection succeeds |
| 2 | MCP Session Initialization | Session created |
| 3 | List Available Tools | Tools listed (generate_pii, generate_bulk_pii, etc.) |
| 4 | Generate Email PII | Email redacted or blocked |
| 5 | Generate SSN PII | SSN redacted or blocked (high sensitivity) |
| 6 | Generate Credit Card PII | Credit card redacted or blocked |
| 7 | Bulk PII Generation | Bulk records generated |
| 8 | Generate Text with Embedded PII | Embedded PII redacted in text |
| 9 | Generate Phone Number PII | Phone number redacted or blocked |

### Tool Poisoning Tests (3 tests)

Tests detection and blocking of malicious tool descriptions.

| Test | Description | Expected Result |
|------|-------------|-----------------|
| 1 | Connectivity | Connection succeeds |
| 2 | Initialize Session | Session created |
| 3 | List Tools | **BLOCKED** - Guard detects poisoned descriptions |

The tool poisoning server returns tools with malicious descriptions containing patterns like "ignore previous instructions", "bypass", or "override".

### Rug Pull Tests (13 tests)

Tests detection of tool definition changes (rug pull attacks) where an MCP server changes its tool definitions after initial baseline establishment.

**Session Scope Tests:**

| Test | Description | Expected Result |
|------|-------------|-----------------|
| 1 | Connectivity | Connection succeeds |
| 2 | Initialize & Reset State | Session created, global state reset |
| 3 | Baseline Establishment | Tools recorded (get_weather, get_global_weather, etc.) |
| 4 | Unchanged Tools Pass | Second list allowed (no changes) |
| 5 | Trigger Session Rug Pull | Call `get_weather` (triggers session-level tool change) |
| 6 | Detect Session Rug Pull | **BLOCKED** - Guard detects tools changed from baseline |
| 7 | New Session After Session Rug | Fresh baseline established (session rug is isolated) |

**Global Scope Tests:**

| Test | Description | Expected Result |
|------|-------------|-----------------|
| 8 | Reset for Global Rug Test | State cleared |
| 9 | Client A Establishes Baseline | Tools recorded |
| 10 | Client B Triggers Global Rug | Call `get_global_weather` (changes tools for all sessions) |
| 11 | Client A Detects Global Rug | **BLOCKED** - Cross-session detection |
| 12 | New Session After Global Rug | Fresh baseline (guard cannot know "original" state) |
| 13 | Cleanup | Global state reset |

## Troubleshooting

### "Cannot connect to ACR"

```bash
# Re-authenticate
az login
az acr login --name <your-acr-name>
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
| `tests/e2e_security_guards_test.py` | Main test suite (runs all guards) |
| `tests/e2e_pii_guard_test.py` | PII guard test suite |
| `tests/e2e_tool_poisoning_guard_test.py` | Tool poisoning guard test suite |
| `tests/e2e_rug_pull_guard_test.py` | Rug pull guard test suite |
| `tests/mcp_client.py` | Shared MCP client library |

## Running Individual Tests

To run specific test suites:

```bash
cd tests/docker

# Run all tests
docker compose run --rm test-runner

# Run against external gateway
docker compose run --rm -e GATEWAY_URL=https://your-gateway.azurecontainerapps.io test-runner
```

### Running Individual Guard Tests

Each guard has its own standalone test file:

```bash
# PII Guard only
python tests/e2e_pii_guard_test.py

# Tool Poisoning Guard only
python tests/e2e_tool_poisoning_guard_test.py

# Rug Pull Guard only
python tests/e2e_rug_pull_guard_test.py
```

> **Note**: The test framework supports both Streamable HTTP (default) and SSE transports. However, the current MCP test servers only implement Streamable HTTP. To run tests with SSE transport, the MCP servers would need to be updated to support SSE.

## CI/CD Integration

The same tests run automatically in GitHub Actions:

1. On push to `main` - runs E2E tests, then deploys if passing
2. On pull request - runs E2E tests only
3. Manual trigger - choose environment and whether to run tests

See `.github/workflows/azure-deploy.yml` for the workflow definition.
