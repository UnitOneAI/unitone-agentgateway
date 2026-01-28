# UnitOne AgentGateway

Production-ready Azure deployment of [AgentGateway](https://github.com/agentgateway/agentgateway) with MCP Security Guards.

## What is AgentGateway?

AgentGateway is an API gateway for AI agents that provides:

- **MCP Protocol Support** - Route and proxy Model Context Protocol (MCP) requests
- **Security Guards** - Protect against tool poisoning, rug pulls, and PII leakage
- **Multi-tenant Routing** - Single gateway for multiple MCP servers
- **Web UI** - Visual dashboard for monitoring and configuration

## What This Repo Adds

This wrapper provides one-click Azure deployment:

- **Interactive Setup** - `./setup.sh` guides you through configuration
- **Easy Auth Integration** - OAuth with Microsoft, Google, GitHub
- **Security Guards** - Pre-configured tool poisoning, rug pull, and PII protection
- **Terraform Infrastructure** - Production-ready Azure Container Apps deployment
- **E2E Testing** - Validate security guards locally before deploying

## Quick Start

### Prerequisites

- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) with active subscription
- [Terraform](https://www.terraform.io/downloads) >= 1.5.0
- [Docker](https://www.docker.com/get-started) (for local testing)
- Git

### 1. Clone the Repository

```bash
git clone --recursive https://github.com/UnitOneAI/unitone-agentgateway.git
cd unitone-agentgateway
```

### 2. Run Interactive Setup

```bash
./setup.sh
```

The setup wizard will prompt you for:
- **Azure region and resource group**
- **OAuth credentials** (Microsoft/Google/GitHub) for Easy Auth
- **CI/CD settings** (optional GitHub integration)

Your configuration is saved to `terraform/terraform.tfvars`.

### 3. Deploy to Azure

```bash
cd terraform
terraform init
terraform apply
```

### 4. Build and Push the Image

Choose one of three build methods:

**Option A: ACR Cloud Build** (no local Docker needed)
```bash
ACR_NAME=$(terraform output -raw acr_name)
cd ..
az acr build --registry $ACR_NAME --image unitone-agentgateway:latest -f Dockerfile.acr .
```

**Option B: VM-Based Build** (fastest iteration, requires Docker)
```bash
# On your build VM or local machine with Docker
./scripts/build-on-vm.sh --acr-name $ACR_NAME

# Build and deploy in one command
./scripts/build-on-vm.sh --acr-name $ACR_NAME --deploy --resource-group my-rg --app-name my-app
```

**Option C: ACR Tasks** (automatic builds on git push)
```bash
# Configure during setup.sh or add to terraform.tfvars:
github_repo_url = "https://github.com/YOUR_ORG/unitone-agentgateway.git"
github_pat      = "ghp_xxxxxxxxxxxx"
```

### 5. Access Your Gateway

```bash
cd terraform
terraform output ui_url
# Opens: https://your-app.azurecontainerapps.io/ui
```

## Local E2E Testing

Test security guards locally before deploying:

```bash
# Run full test suite
./deploy.sh

# Or step by step:
./deploy.sh --skip-tests    # Start services only
./deploy.sh --stop          # Stop services
```

This runs tests for:
- **Tool Poisoning Guard** - Blocks malicious tool descriptions
- **Rug Pull Guard** - Detects runtime tool changes
- **PII Guard** - Blocks sensitive data exposure

## Authentication

UnitOne AgentGateway supports multiple authentication methods:

### OAuth (Easy Auth) - For Users

| Provider | Setup Guide |
|----------|-------------|
| Microsoft (Azure AD) | [Azure Portal](https://portal.azure.com) → Azure AD → App registrations |
| Google | [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials |
| GitHub | [GitHub Settings](https://github.com/settings/developers) → OAuth Apps |

### Client Certificates (mTLS) - For Services

For service-to-service authentication:

| Mode | Use Case |
|------|----------|
| `ignore` | Public access, OAuth only |
| `accept` | Accept certs if provided |
| `require` | All requests must have valid cert |

The `./setup.sh` wizard will guide you through both OAuth and mTLS configuration.

See [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md) for detailed setup instructions.

## Security Guards

| Guard | Purpose | Default |
|-------|---------|---------|
| `toolPoisoning` | Block malicious tool descriptions | Enabled |
| `rugPull` | Detect runtime tool changes | Enabled |
| `pii` | Block PII in responses | Configurable |

See [docs/SECURITY_GUARDS.md](docs/SECURITY_GUARDS.md) for configuration details.

## Repository Structure

```
unitone-agentgateway/
├── setup.sh                   # Interactive setup wizard
├── deploy.sh                  # Local E2E testing
├── agentgateway/              # Git submodule (core gateway)
├── terraform/
│   ├── main.tf                # Azure infrastructure
│   ├── variables.tf           # Configuration options
│   └── README.md              # Terraform docs
├── tests/
│   ├── docker/                # Docker-based E2E tests
│   └── e2e_*.py               # Test scripts
├── testservers/               # Mock MCP servers for testing
├── examples/
│   └── config.yaml            # Example gateway config
└── docs/
    ├── AUTHENTICATION.md      # OAuth setup guide
    ├── SECURITY_GUARDS.md     # Security guard docs
    └── CONFIG_HOT_RELOAD.md   # Runtime config updates
```

## Configuration

### Gateway Config (examples/config.yaml)

```yaml
binds:
- port: 8080
  listeners:
  - hostname: "*"
    routes:
    - name: my-mcp-server
      matches:
      - path:
          pathPrefix: /mcp
      backends:
      - mcp:
          targets:
          - name: backend
            mcp:
              host: http://your-mcp-server:3000/mcp
          statefulMode: stateful
      policies:
        securityGuards:
          toolPoisoning:
            enabled: true
          rugPull:
            enabled: true
```

### Terraform Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `environment` | dev / staging / prod | Yes |
| `resource_group_name` | Azure resource group | Yes |
| `location` | Azure region | No (default: eastus2) |
| `configure_auth` | Enable Easy Auth | No (default: false) |
| `microsoft_client_id` | Azure AD OAuth | No |
| `google_client_id` | Google OAuth | No |
| `github_client_id` | GitHub OAuth | No |

See [terraform/README.md](terraform/README.md) for all options.

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

## Development

### Update Submodule

```bash
cd agentgateway
git fetch origin
git checkout origin/main
cd ..
git add agentgateway
git commit -m "Update agentgateway submodule"
```

### Build Locally

```bash
# Using Makefile
make build

# Or directly
docker build -f Dockerfile.acr -t unitone-agentgateway:local .
```

## License

Apache License 2.0 - see [LICENSE](LICENSE).

## Support

- [GitHub Issues](https://github.com/UnitOneAI/unitone-agentgateway/issues)
- [AgentGateway Documentation](https://github.com/agentgateway/agentgateway)
