# UnitOne AgentGateway

UnitOne-branded deployment wrapper for [agentgateway](https://github.com/UnitOneAI/agentgateway).

## Overview

This wrapper repository contains UnitOne-specific configurations, branding, and deployment automation for agentgateway. It uses a git submodule pattern to separate UnitOne customizations from the core agentgateway project.

**Key Benefits:**
- Clear separation between generic and company-specific code
- Easy syncing with upstream agentgateway updates
- Simplified deployment workflows for UnitOne infrastructure
- Prepares main agentgateway repo for future open source contribution

## Repository Structure

```
unitone-agentgateway/          # This repository (wrapper)
├── agentgateway/              # Git submodule → core agentgateway
│   ├── src/                   # Rust source code
│   ├── ui/                    # Next.js UI application
│   └── Cargo.toml             # Rust project
├── .github/workflows/         # GitHub Actions CI/CD
│   └── azure-deploy.yml       # Automated Azure deployment
├── Dockerfile.acr             # Azure Container Registry build
├── Makefile                   # Build/deploy automation
├── docs/                      # UnitOne-specific documentation
│   ├── DEPLOYMENT.md          # Deployment automation guide
│   ├── EASY_AUTH_DEPLOYMENT.md # OAuth configuration
│   ├── UNITONE_BRANDING_CHANGES.md # UI branding changes
│   └── UNITONE_USER_MENU_FEATURE.md # User menu feature
└── README.md                  # This file
```

**Sibling Repository** (separate repo):
```
terraform/                     # Infrastructure as Code (sibling repo)
├── environments/
│   ├── dev/agentgateway/
│   ├── staging/agentgateway/
│   └── prod/agentgateway/
└── modules/
    └── azure/agentgateway/
```

## Quick Start

### Prerequisites

- **Git** with submodules support
- **Azure CLI** (`az`) configured with UnitOne subscription
- **Docker** (for building images)
- **Rust toolchain** (optional, for local builds)
- **Node.js** (optional, for UI development)

### 1. Clone with Submodules

```bash
# Clone the wrapper repository with agentgateway submodule
git clone --recursive https://github.com/UnitOneAI/unitone-agentgateway.git
cd unitone-agentgateway

# If already cloned, initialize submodules
git submodule update --init --recursive
```

### 2. Deploy to Development

**Fastest Method: Fast Build (4-7 minutes)**

For active development, use the VM-based fast build system:

```bash
# Build and deploy to dev (4-7 minutes vs 15-25 minutes traditional)
./scripts/fast-build.sh dev

# Or to staging/prod
./scripts/fast-build.sh staging
./scripts/fast-build.sh prod
```

See [FAST_BUILD.md](docs/FAST_BUILD.md) for complete documentation on the fast build system.

**Alternative: GitHub Actions (Automatic)**

Push to main branch triggers automatic deployment to dev:

```bash
# Push to main branch triggers automatic deployment to dev
git push origin main
```

**Alternative: Manual ACR Build (15-20 minutes)**

```bash
# Build Docker image in Azure Container Registry
az acr build \
  --registry unitoneagwdevacr \
  --image unitone-agentgateway:latest \
  --file Dockerfile.acr \
  --platform linux/amd64 \
  .

# Deploy to Azure Container Apps
az containerapp update \
  --name unitone-agw-dev-app \
  --resource-group mcp-gateway-dev-rg \
  --image unitoneagwdevacr.azurecr.io/unitone-agentgateway:latest
```

### 3. Verify Deployment

```bash
# Check deployment status
az containerapp show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --query "{Status:properties.provisioningState, URL:properties.configuration.ingress.fqdn}"

# Access the UI
open https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/ui
```

## Development Workflow

### Updating the Agentgateway Submodule

When upstream agentgateway releases new features:

```bash
cd unitone-agentgateway

# Navigate to submodule
cd agentgateway

# Fetch latest changes
git fetch origin
git checkout origin/feature/mcp-security-guards  # Using feature branch with MCP security

# Return to wrapper repo and commit update
cd ..
git add agentgateway
git commit -m "Update agentgateway submodule to latest version"
git push origin main  # Triggers automatic deployment
```

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed submodule workflow documentation.

### Making UI Customizations

UnitOne branding customizations are applied at build time. See [UNITONE_BRANDING_CHANGES.md](docs/UNITONE_BRANDING_CHANGES.md) for details on:
- Logo and color scheme
- Theme configuration
- Font customization

## CI/CD and Deployment

### Primary CI/CD: GitHub Actions (ACTIVE)

The automated deployment workflow (`.github/workflows/azure-deploy.yml`) triggers on:

| Event | Environment | Action |
|-------|-------------|--------|
| Push to `main` | Development | Build + Deploy to dev |
| Manual dispatch | Any (dev/staging/prod) | Build + Deploy to selected environment |

**Key Features:**
- Automatic submodule initialization (`submodules: 'recursive'`)
- Docker build using `az acr build`
- Multi-tag strategy (commit SHA, timestamp, `latest`)
- Deployment verification and health checks

### Alternative CI/CD: ACR Tasks (OPTIONAL)

An Azure-native CI/CD alternative is available but not currently deployed. ACR Tasks can provide:
- Automated builds on git push to `main` branch
- Automatic rebuilds on base image updates (security patches)
- Azure-native CI/CD without GitHub Actions dependency

**Current Status:** GitHub Actions is the primary and recommended CI/CD approach.

For a detailed comparison of both approaches and when to use each, see [CICD_OPTIONS.md](docs/CICD_OPTIONS.md)

## Available Commands

### Using Makefile (if sibling terraform repo is checked out)

```bash
make build              # Build agentgateway with UnitOne branding
make deploy-dev         # Deploy to dev environment (requires terraform)
make test               # Run E2E tests
make clean              # Clean build artifacts
make update-submodule   # Update agentgateway to latest
```

### Using Azure CLI Directly

```bash
# Build image
az acr build --registry agwimages --image unitone-agentgateway:latest --file Dockerfile.acr --platform linux/amd64 .

# Deploy
az containerapp update --name unitone-agentgateway --resource-group mcp-gateway-dev-rg --image agwimages.azurecr.io/unitone-agentgateway:latest

# View logs
az containerapp logs show --name unitone-agentgateway --resource-group mcp-gateway-dev-rg --follow

# Check revisions
az containerapp revision list --name unitone-agentgateway --resource-group mcp-gateway-dev-rg
```

## What's UnitOne-Specific

This wrapper repository contains:

### Deployment Configuration
- `.github/workflows/azure-deploy.yml` - Automated CI/CD to Azure
- `Dockerfile.acr` - Azure Container Registry optimized build
- `Makefile` - Build and deployment automation

### UI Customizations (Applied to Submodule)
- UnitOne brand colors (blue #3b82f6 vs purple)
- Dark sidebar theme (#0f172a)
- UnitOne logo and branding assets
- Inter font instead of Geist
- User menu with OAuth integration

### Documentation
- Deployment automation guides
- Azure Easy Auth OAuth setup
- Branding change documentation
- Developer workflows

## Infrastructure

Azure Container Apps deployment in **East US 2**:

| Resource | Name | Purpose |
|----------|------|---------|
| Resource Group | `mcp-gateway-dev-rg` | Development environment |
| Container Registry | `agwimages` | Docker image storage |
| Container App | `unitone-agentgateway` | Running application |
| URL | `unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io` | Public endpoint |

**OAuth Providers:**
- Microsoft (Azure AD) - Client ID: `4b497d98-cb3a-400e-9374-0e23d57dd480`
- Google OAuth 2.0 - Client ID: `919355621898-us1vie0rv5mqaff752hhqb9espne87ug.apps.googleusercontent.com`

See [EASY_AUTH_DEPLOYMENT.md](docs/EASY_AUTH_DEPLOYMENT.md) for OAuth configuration details.

## Monitoring

### Health Checks

```bash
# Application health
curl https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/health

# MCP endpoint
curl https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp/github

# OAuth user info
curl https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/.auth/me
```

### Logs

```bash
# Stream logs
az containerapp logs show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --follow

# Check specific revision
az containerapp revision list \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --query "[].{Name:name, Active:properties.active, Created:properties.createdTime, Image:properties.template.containers[0].image}"
```

## Troubleshooting

### Submodule Not Initialized

```bash
git submodule update --init --recursive
```

### Build Fails

```bash
# Check for errors in the build logs
az acr task logs --registry agwimages --follow

# Verify Dockerfile.acr exists
ls -la Dockerfile.acr
```

### Deployment Fails

```bash
# Check Container App logs
az containerapp logs show --name unitone-agentgateway --resource-group mcp-gateway-dev-rg --tail 100

# Check Container App status
az containerapp show --name unitone-agentgateway --resource-group mcp-gateway-dev-rg \
  --query "{Provisioning:properties.provisioningState, Running:properties.runningStatus}"
```

### OAuth Issues

See [EASY_AUTH_DEPLOYMENT.md](docs/EASY_AUTH_DEPLOYMENT.md) for OAuth troubleshooting.

## Security

### Secrets Management
- OAuth credentials: Azure Container Apps secrets
- API keys: Azure Key Vault
- Never commit secrets to git

### Access Control
- Azure RBAC for resource access
- GitHub team permissions for repository access
- OAuth authentication required for UI

## Contributing

### Core Agentgateway Changes
Contribute to the main [agentgateway repository](https://github.com/UnitOneAI/agentgateway), then update the submodule here.

### UnitOne-Specific Changes
1. Create a branch in this repository
2. Make changes to wrapper files (not submodule)
3. Test in dev environment
4. Create PR for review
5. Merge triggers automatic deployment

## Documentation

- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Complete deployment automation guide with submodule workflow
- **[EASY_AUTH_DEPLOYMENT.md](docs/EASY_AUTH_DEPLOYMENT.md)** - OAuth configuration for Microsoft and Google
- **[UNITONE_BRANDING_CHANGES.md](docs/UNITONE_BRANDING_CHANGES.md)** - UI customization details
- **[UNITONE_USER_MENU_FEATURE.md](docs/UNITONE_USER_MENU_FEATURE.md)** - User menu implementation

## License

The core agentgateway is licensed under Apache 2.0.

This wrapper repository contains UnitOne proprietary configurations and customizations.

## Support

For issues or questions:
1. Check documentation in `docs/` directory
2. Review [GitHub Actions workflow runs](https://github.com/UnitOneAI/unitone-agentgateway/actions)
3. Contact DevOps team
4. Escalate to on-call if production issue

---

**Last Updated:** January 2026
**Maintained By:** UnitOne DevOps Team
