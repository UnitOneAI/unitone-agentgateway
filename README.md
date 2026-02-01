# UnitOne AgentGateway

Production-ready Azure deployment of [AgentGateway](https://github.com/agentgateway/agentgateway) with MCP Security Guards.

## What is AgentGateway?

AgentGateway is an API gateway for AI agents that provides:

- **MCP Protocol Support** - Route and proxy Model Context Protocol (MCP) requests
- **Security Guards** - Protect against tool poisoning, rug pulls, and PII leakage
- **Multi-tenant Routing** - Single gateway for multiple MCP servers
- **Web UI** - Visual dashboard for monitoring and configuration

## Quick Start

### Prerequisites

- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) with active subscription
- [Terraform](https://www.terraform.io/downloads) >= 1.5.0
- [Docker](https://www.docker.com/get-started) (for local testing)
- **Contributor role** on an Azure resource group (ask your admin if needed)

### 1. Clone and Setup

```bash
git clone --recursive https://github.com/UnitOneAI/unitone-agentgateway.git
cd unitone-agentgateway
./agw setup
```

The setup wizard guides you through Azure configuration, OAuth setup, and deployment.

### 2. Build and Deploy

```bash
./agw build --deploy
```

### 3. Access Your Gateway

```bash
./agw status
```

## CLI Reference

All operations use the unified `./agw` CLI:

```bash
./agw setup              # Interactive first-time setup
./agw scope              # Manage deployment scopes (dev/staging/prod)
./agw auth               # Configure OAuth authentication
./agw build              # Build and push image to ACR
./agw build --deploy     # Build and deploy in one step
./agw deploy             # Deploy latest image
./agw test               # Run E2E tests locally
./agw test-servers       # Deploy test servers to Azure
./agw logs               # View container logs
./agw logs --follow      # Stream logs
./agw status             # Show deployment status
./agw help               # Show all commands
```

### Multi-Scope Support

Manage multiple deployments (dev, staging, prod) with scopes:

```bash
./agw scope list                 # List all scopes
./agw scope import --name dev    # Import from terraform
./agw scope set prod             # Switch to prod
./agw scope add staging          # Add new scope interactively
```

### Authentication

Configure OAuth providers via CLI (no portal needed):

```bash
./agw auth urls      # Get callback URLs for OAuth app setup
./agw auth setup     # Configure Microsoft/Google/GitHub
./agw auth enable    # Require authentication
./agw auth disable   # Allow anonymous access
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Production Setup](docs/PRODUCTION_SETUP.md) | Detailed deployment guide |
| [Security Guards](docs/SECURITY_GUARDS.md) | Configure protection policies |
| [Authentication](docs/AUTHENTICATION.md) | Configure OAuth and mTLS |
| [E2E Test Guide](docs/E2E_TEST_GUIDE.md) | Run security guard tests locally |
| [Config Hot Reload](docs/CONFIG_HOT_RELOAD.md) | Runtime configuration updates |
| [Sticky Sessions](docs/STICKY_SESSIONS.md) | Multi-replica session affinity |

## Local E2E Testing

```bash
./agw test                 # Run full test suite
./agw test --skip-build    # Use existing image
./agw test --stop          # Stop test containers
```

Tests validate:
- **Tool Poisoning Guard** - Blocks malicious tool descriptions
- **Rug Pull Guard** - Detects runtime tool changes
- **PII Guard** - Masks sensitive data in responses

See [docs/E2E_TEST_GUIDE.md](docs/E2E_TEST_GUIDE.md) for details.

## Security Guards

| Guard | Purpose | Default |
|-------|---------|---------|
| `toolPoisoning` | Block malicious tool descriptions | Enabled |
| `rugPull` | Detect runtime tool changes | Enabled |
| `pii` | Block PII in responses | Configurable |

See [docs/SECURITY_GUARDS.md](docs/SECURITY_GUARDS.md) for configuration details.

## Build Options

The CLI supports two build modes:

| Mode | Command | Best For |
|------|---------|----------|
| **ACR Cloud Build** | `./agw build` | Default. No local Docker needed. |
| **Local Build** | `./agw build --local` | Faster iteration on a VM. |

### When to Use Local Builds

Use `./agw build --local` when you have a dedicated Linux build VM:
- Faster iteration (Docker layer caching)
- Lower ACR build costs
- More control over the build process

**Quick Setup on a fresh Ubuntu/Debian VM:**

```bash
# 1. Setup build VM with Docker and Azure CLI
curl -fsSL https://raw.githubusercontent.com/UnitOneAI/unitone-agentgateway/main/scripts/setup-build-vm.sh | bash

# 2. Log out/in for docker group, then login to Azure
az login

# 3. Clone and build
git clone --recursive https://github.com/UnitOneAI/unitone-agentgateway.git
cd unitone-agentgateway
./agw build --local --deploy
```

## Repository Structure

```
unitone-agentgateway/
├── agw                        # Unified CLI (start here)
├── .agw/                      # Local scope config (gitignored)
│   ├── current                # Active scope name
│   └── scopes/*.env           # Scope configurations
├── agentgateway/              # Git submodule (core gateway)
├── terraform/                 # Azure infrastructure
├── tests/                     # E2E test suite
├── testservers/               # Mock MCP servers for testing
├── scripts/
│   ├── setup-build-vm.sh      # Setup a Linux VM for local builds
│   ├── build-on-vm.sh         # Used by ./agw build --local
│   └── deploy-test-servers.sh # Deploy test servers to Azure
└── docs/                      # Documentation
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Azure Container Apps                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 UnitOne AgentGateway                 │    │
│  │  ┌──────────────────────────────────────────────┐   │    │
│  │  │              Security Guards                  │   │    │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────────────┐ │   │    │
│  │  │  │ Tool    │ │ Rug     │ │ PII Detection   │ │   │    │
│  │  │  │Poisoning│ │ Pull    │ │                 │ │   │    │
│  │  │  └────┬────┘ └────┬────┘ └────────┬────────┘ │   │    │
│  │  │       └───────────┼───────────────┘          │   │    │
│  │  └───────────────────┼──────────────────────────┘   │    │
│  │                      ▼                               │    │
│  │  ┌──────────────────────────────────────────────┐   │    │
│  │  │              MCP Route Handlers               │   │    │
│  │  │  /mcp/server-a → Backend A                   │   │    │
│  │  │  /mcp/server-b → Backend B                   │   │    │
│  │  └──────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────┘    │
│                              │                               │
│  ┌───────────────────────────┼───────────────────────────┐  │
│  │         Azure Easy Auth   │   (OAuth)                 │  │
│  │  Microsoft | Google | GitHub                          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
                 ┌──────────────────────────┐
                 │    Your MCP Servers      │
                 └──────────────────────────┘
```

## License

MIT License - see [LICENSE](LICENSE).

## Support

- [GitHub Issues](https://github.com/UnitOneAI/unitone-agentgateway/issues)
- [AgentGateway Documentation](https://github.com/agentgateway/agentgateway)
