# Claude Code Project Memory

## Project Overview

UnitOne AgentGateway - Production-ready Azure deployment of AgentGateway with MCP Security Guards.

## Key Tool: `./agw` CLI

**All operations use the unified `./agw` CLI.** This is the single entry point for setup, build, deploy, and management.

### Essential Commands

```bash
./agw setup              # Interactive first-time setup
./agw scope              # Show current scope
./agw scope list         # List all scopes (dev/staging/prod)
./agw scope set dev      # Switch to dev scope
./agw build              # Build in ACR Cloud Build (~20-30 min)
./agw build --local      # Build locally with Docker
./agw build --deploy     # Build AND deploy in one step
./agw deploy             # Deploy latest image
./agw status             # Show deployment status and URL
./agw logs --follow      # Stream container logs
./agw auth               # Show/configure OAuth authentication
```

### Build Locations

1. **ACR Cloud Build** (default): `./agw build` - builds in Azure Container Registry, no local Docker needed
2. **Local Build**: `./agw build --local` - builds on local machine/VM with Docker

### Scopes

Scopes define which Azure environment to target:
- **Global scopes**: `terraform/scopes/global/*.env` - shared, committed to repo
- **Personal scopes**: `terraform/scopes/users/<username>/*.env` - per-developer
- **Current scope**: stored in `.agw/current` (gitignored)

### DEV Environment (Pre-configured)

The dev scope is already configured in `terraform/scopes/global/dev.env`:
```
AGW_RESOURCE_GROUP=unitone-agw-dev-rg
AGW_CONTAINER_APP=unitone-agw-dev-app
AGW_ACR_NAME=unitoneagwdevacr
AGW_URL=https://unitone-agw-dev-app.agreeablesmoke-2aeab779.eastus2.azurecontainerapps.io
```

## Repository Structure

```
unitone-agentgateway/
├── agw                           # Unified CLI (START HERE)
├── .agw/                         # Local config (gitignored)
│   └── current                   # Active scope name
├── terraform/scopes/             # Scope configurations
│   ├── global/*.env              # Team-shared scopes
│   └── users/<username>/*.env    # Personal scopes
├── agentgateway/                 # Git submodule (core gateway code)
├── terraform/                    # Azure infrastructure (Terraform)
├── tests/                        # E2E test suite
├── testservers/                  # Mock MCP servers for testing
└── docs/                         # Documentation
```

## Security Guards

Guards protect MCP tool calls at different phases (scopes):

| Scope | When it runs |
|-------|--------------|
| `tools_list` | When tools are listed (filters/modifies tool list) |
| `tool_invoke` | Before a tool is called (can block/modify) |
| `request` | On any MCP request |
| `response` | On any MCP response |

Guards can run on multiple scopes simultaneously using `runs_on: [tools_list, tool_invoke]`.

### Built-in Guards
- `toolPoisoning` - Blocks malicious tool descriptions
- `rugPull` - Detects runtime tool changes
- `pii` - Masks sensitive data in responses

## CI/CD

- **GitHub Actions**: `.github/workflows/azure-deploy.yml` - auto-deploys on push to main (requires secrets)
- **Manual**: Use `./agw build --deploy`

## Common Workflows

### Deploy to Dev
```bash
./agw scope set dev
./agw build --deploy
```

### Check Status
```bash
./agw status
./agw logs --follow
```

### Configure OAuth
```bash
./agw auth urls      # Get callback URLs
./agw auth setup     # Configure providers
```
