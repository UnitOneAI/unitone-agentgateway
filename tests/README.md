# E2E Tests

End-to-end test suite for AgentGateway security guards and MCP protocol compliance.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────────┐
│   Test Runner   │────>│  AgentGateway   │────>│   MCP Test Servers      │
│   (Python)      │     │   (port 8080)   │     │  - PII (8000)           │
└─────────────────┘     └─────────────────┘     │  - Tool Poisoning (8010)│
                                                │  - Rug Pull (8020)      │
                                                └─────────────────────────┘
```

Tests send MCP requests through AgentGateway, which routes them to mock MCP servers in `testservers/`. Security guards intercept requests/responses at the gateway layer, and tests verify that guards correctly detect and block attack scenarios.

## Test Suites

| File | Guard Tested | What It Validates |
|------|-------------|-------------------|
| `e2e_security_guards_test.py` | All guards | Master orchestrator — runs PII (mask + reject), Tool Poisoning, and Rug Pull tests sequentially |
| `e2e_pii_guard_test.py` | PII Guard | Tests 6 PII types (email, phone, SSN, credit card, CA SIN, URL) across mask and reject modes (19 tests per mode) |
| `e2e_tool_poisoning_guard_test.py` | Tool Poisoning Guard | Blocks tools with malicious descriptions across 6 attack categories; validates deny reason structure (6 tests) |
| `e2e_rug_pull_guard_test.py` | Rug Pull Guard | Detects tool metadata changes — session/global scope, 4 mutation modes with risk scoring (22 tests) |
| `e2e_mcp_sse_test.py` | N/A | Validates MCP protocol over SSE transport |
| `benchmark.py` | N/A | Performance benchmarking with configurable concurrency |

## Shared Library

`mcp_client.py` provides reusable MCP client classes used by all test files:

- **`MCPSSEClient`** — Server-Sent Events transport
- **`MCPStreamableHTTPClient`** — HTTP POST transport (default)
- **`TestResults`** — Pass/fail/warning result tracker
- **`create_mcp_client()`** — Factory function that returns the right client for the chosen transport

## Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Dependencies: `pip install httpx pytest pytest-asyncio`
- ACR access for the AgentGateway image (or local Docker build with 10GB+ memory)

## Quick Start

### Option 1: Docker (Recommended)

Run the full test infrastructure in containers:

```bash
cd tests/docker

# CI/CD mode — runs all tests and exits
docker compose up --build --abort-on-container-exit --exit-code-from test-runner

# Development mode — start services, run tests from host
docker compose up -d mcp-test-servers agentgateway
GATEWAY_URL=http://localhost:8080 python ../e2e_security_guards_test.py
```

See [docker/README.md](docker/README.md) for detailed Docker instructions.

### Option 2: Against a Deployed Environment

Run tests against a running AgentGateway instance (e.g., Azure dev):

```bash
GATEWAY_URL=https://unitone-agw-dev-app.agreeablesmoke-2aeab779.eastus2.azurecontainerapps.io \
  python tests/e2e_security_guards_test.py
```

### Option 3: Local Development

Start testservers and AgentGateway manually, then:

```bash
python tests/e2e_security_guards_test.py
python tests/e2e_pii_guard_test.py
python tests/e2e_rug_pull_guard_test.py
python tests/e2e_tool_poisoning_guard_test.py
```

## Transport Selection

Tests support two MCP transport protocols:

```bash
# Streamable HTTP (default, more stable)
python tests/e2e_security_guards_test.py --transport streamable

# Server-Sent Events
python tests/e2e_security_guards_test.py --transport sse

# Both transports sequentially
python tests/e2e_security_guards_test.py --transport all
```

## Benchmarking

Measure gateway performance with and without security guards:

```bash
python tests/benchmark.py --route /pii-test --requests 100 --concurrency 10
python tests/benchmark.py --route /pii-test --output results.json
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_URL` | `http://localhost:8080` | AgentGateway endpoint URL |
| `MCP_TRANSPORT` | `streamable` | Transport protocol (`streamable` or `sse`) |
| `MCP_ROUTE` | *(per-test default)* | Override gateway route path (used by rug pull and tool poisoning tests) |
| `ACR_REGISTRY` | — | Azure Container Registry URL (for Docker tests) |
| `IMAGE_TAG` | `latest` | AgentGateway image tag (for Docker tests) |

## Gateway Routes

Tests use these AgentGateway routes to reach the mock MCP servers:

### Core routes

| Route | Backend | Guard | Description |
|-------|---------|-------|-------------|
| `/pii-test` | `localhost:8000` | PII (mask mode) | Replaces PII with `<ENTITY_TYPE>` placeholders |
| `/pii-test-reject` | `localhost:8000` | PII (reject mode) | Blocks entire response when PII is detected |
| `/poison` | `localhost:8010` | Tool Poisoning | Blocks `tools/list` when poisoned descriptions are found |
| `/rug-pull` | `localhost:8020` | Rug Pull | Tracks tool metadata changes across `tools/list` calls |

### Rug pull mutation mode routes

Each mode uses a separate route with its own target name, giving the guard an independent baseline per mode:

| Route | Mutation Mode | Expected Outcome |
|-------|--------------|------------------|
| `/rug-pull-desc` | description | BLOCKED (3 changes x weight 2 = score 6 >= threshold 5) |
| `/rug-pull-schema` | schema | BLOCKED (2 changes x weight 3 = score 6 >= threshold 5) |
| `/rug-pull-remove` | remove | ALLOWED (1 removal x weight 3 = score 3 < threshold 5) |
| `/rug-pull-add` | add | ALLOWED (1 addition x weight 1 = score 1 < threshold 5) |

## Configuration Files

### Gateway configs (`docker/configs/`)

| Config | Guards | Use Case |
|--------|--------|----------|
| `e2e-gateway-config.yaml` | All enabled | Full security guard testing |
| `e2e-gateway-config-basic.yaml` | None | Basic MCP routing tests |
| `e2e-gateway-config-passthrough.yaml` | None | Simple HTTP proxy tests |

### Test server configs (`configs/`)

| Config | Purpose |
|--------|---------|
| `test_security_guards_config.yaml` | Guard settings for E2E tests |
| `demo_security_guards_config.yaml` | Demo/presentation config |
| `wasm_guard_benchmark.yaml` | WASM guard performance config |

## Test Servers (`testservers/`)

Mock MCP servers that simulate attack scenarios:

### PII Test Server (port 8000)

Generates realistic fake PII data using the Faker library. Supports 6 PII types detected by the guard plus additional composite types.

**Guard-detected types:** `email`, `phone`, `ssn`, `credit_card`, `ca_sin`, `url`

**Additional types (not guard-detected):** `name`, `dob`, `address`, `personal`, `drivers_license`, `passport`, `identity`, `bank_account`, `tax_id`, `financial`

**Tools:** `generate_pii`, `generate_bulk_pii`, `generate_full_record`, `generate_text_with_pii`, `list_pii_types`

### Tool Poisoning Server (port 8010)

Exposes tools across 6 attack categories with malicious content in descriptions, plus 2 clean tools that should pass through.

**Poisoned tools (6 attack categories):**

| Category | Tool | Pattern |
|----------|------|---------|
| Hidden instructions | `add`, `secret_notes` | `[HIDDEN]`, `[SECRET]` tags |
| Prompt injection | `translate_text` | "ignore all previous instructions" |
| System override | `get_status` | "SYSTEM: override" |
| Safety bypass | `search_files` | "bypass all security restrictions" |
| Role manipulation | `run_diagnostic` | "you are now a jailbroken AI" |
| Prompt leaking | `get_help` | "reveal your system prompt" |

**Clean tools:** `subtract`, `multiply`

### Rug Pull Server (port 8020)

Simulates bait-and-switch attacks where tool metadata changes after initial listing. Supports session-level and global rug pulls with 5 configurable mutation modes.

**Weather tools (rug pull triggers):**
- `get_weather` — triggers SESSION-level rug pull (affects current session only)
- `get_global_weather` — triggers GLOBAL rug pull (affects ALL sessions)
- `get_forecast` — extra weather tool (target for remove/schema mutations)
- `emergency_weather_alert` — social engineering tool (only visible in "add" mode)

**Management tools:** `reset_session_rug`, `reset_global_rug`, `get_rug_status`, `set_rug_pull_mode`

**Mutation modes** (set via `set_rug_pull_mode`):

| Mode | Changes | Risk Weight |
|------|---------|-------------|
| `all` (default) | Description + schema changes on weather tools | 2-3 per change |
| `description` | Only description changes on all weather tools | 2 per change |
| `schema` | Only schema changes (adds malicious parameters) | 3 per change |
| `remove` | Removes `get_forecast` from tool list | 3 per removal |
| `add` | Adds `emergency_weather_alert` tool | 1 per addition |

## Test Details

### PII Guard Tests (19 tests per mode)

| Tests | What |
|-------|------|
| 1 | MCP endpoint connectivity |
| 2 | MCP session initialization |
| 3 | List available tools |
| 4-9 | Single PII type detection via `generate_pii` (email, phone, SSN, credit card, CA SIN, URL) |
| 10-15 | Embedded PII in natural language text via `generate_text_with_pii` |
| 16 | Full record with multiple PII types simultaneously |
| 17 | Bulk PII generation (email) |
| 18 | Bulk PII generation (credit card) |
| 19 | Clean data — name only, should NOT be flagged |

The master orchestrator (`e2e_security_guards_test.py`) runs mask mode via `/pii-test` and reject mode via `/pii-test-reject` sequentially. When run standalone, `e2e_pii_guard_test.py` supports `--expect-mode` to select mask, reject, both (default), or any.

### Tool Poisoning Guard Tests (6 tests)

| Test | What |
|------|------|
| 1 | Endpoint connectivity |
| 2 | Session initialization |
| 3 | `tools/list` should be BLOCKED (poisoned descriptions detected) |
| 4 | Deny reason has structured JSON with error code and details |
| 5 | Attack category coverage in deny reason |
| 6 | Tool call behavior after `tools/list` block |

### Rug Pull Guard Tests (22 tests)

**Core tests (1-13):**

| Test | What |
|------|------|
| 1 | Endpoint connectivity |
| 2 | Initialize and reset state |
| 3 | Baseline establishment (first `tools/list`) |
| 4 | Unchanged tools pass through |
| 5 | Trigger session rug pull (`get_weather`) |
| 6 | Detect session rug pull (guard blocks changed tools) |
| 7 | New session after session rug gets fresh baseline |
| 8 | Reset for global rug test |
| 9 | Client A establishes baseline with clean tools |
| 10 | Client B triggers global rug (`get_global_weather`) |
| 11 | Client A detects global rug pull on next `tools/list` |
| 12 | New session after global rug establishes new baseline (expected) |
| 13 | Cleanup |

**Mutation mode tests (14-22):**

Each mode uses a dedicated route (`/rug-pull-desc`, `/rug-pull-schema`, etc.) with isolated guard baselines. Tests verify the guard's risk scoring (threshold = 5):

| Tests | Mode | Expected |
|-------|------|----------|
| 14-15 | description | BLOCKED (score 6) |
| 16-17 | schema | BLOCKED (score 6) |
| 18-19 | remove | ALLOWED (score 3) |
| 20-21 | add | ALLOWED (score 1) |
| 22 | Reset mode to default |

## Directory Structure

```
tests/
├── README.md                          # This file
├── e2e_security_guards_test.py        # Master test orchestrator
├── e2e_pii_guard_test.py              # PII guard tests
├── e2e_tool_poisoning_guard_test.py   # Tool poisoning guard tests
├── e2e_rug_pull_guard_test.py         # Rug pull guard tests
├── e2e_mcp_sse_test.py                # SSE transport tests
├── mcp_client.py                      # Shared MCP client library
├── benchmark.py                       # Performance benchmarking
├── configs/                           # Test server configurations
│   ├── test_security_guards_config.yaml
│   ├── demo_security_guards_config.yaml
│   └── wasm_guard_benchmark.yaml
└── docker/                            # Docker test infrastructure
    ├── README.md                      # Docker-specific docs
    ├── docker-compose.yaml            # Full test environment
    ├── Dockerfile.test-runner         # CI/CD test container
    ├── requirements.txt               # Python dependencies
    └── configs/                       # Gateway configurations
        ├── e2e-gateway-config.yaml
        ├── e2e-gateway-config-basic.yaml
        └── e2e-gateway-config-passthrough.yaml
```

## CI/CD

Tests run automatically via GitHub Actions (`.github/workflows/azure-deploy.yml`) on push to main. The pipeline builds the gateway image in ACR, deploys it, and runs the full test suite in containers.

Manual CI-equivalent run:

```bash
cd tests/docker
docker compose up --build --abort-on-container-exit --exit-code-from test-runner
docker compose down -v
```
