# UnitOne AgentGateway - Documentation Index

Complete documentation index across all three repositories: `unitone-agentgateway`, `terraform`, and `agentgateway` (submodule).

## Quick Navigation

| I want to... | Go to... |
|--------------|----------|
| Get started with deployment | [Quick Start](#getting-started) |
| Understand the architecture | [Architecture Overview](#architecture-overview) |
| Deploy to Azure | [Deployment Guides](#deployment-guides) |
| Configure CI/CD | [CI/CD Documentation](#cicd-and-automation) |
| Manage infrastructure | [Terraform Documentation](#infrastructure-terraform) |
| Customize UI/branding | [UnitOne Customizations](#unitone-customizations) |
| Understand core gateway | [Core AgentGateway Docs](#core-agentgateway-submodule) |

---

## Getting Started

### For New Engineers

**Start here:**
1. **[UnitOne AgentGateway README](../README.md)** - Main entry point, repository overview
2. **[Terraform README](../../terraform/README.md)** - Infrastructure overview and quick start
3. **[Deployment Guide (DEPLOYMENT.md)](DEPLOYMENT.md)** - Complete deployment walkthrough

**Quick deployment:**
```bash
# Clone with submodules
git clone --recursive https://github.com/UnitOneAI/unitone-agentgateway.git

# Push to main triggers deployment to dev
git push origin main
```

### For DevOps Engineers

**Infrastructure setup:**
1. **[Terraform Project Structure](../../terraform/docs/terraform-project-structure.md)** - How terraform is organized
2. **[Terraform README](../../terraform/README.md)** - Quick start and common operations
3. **[CI/CD Options (CICD_OPTIONS.md)](CICD_OPTIONS.md)** - Compare GitHub Actions vs ACR Tasks

---

## Architecture Overview

### Three-Repository Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Repository Ecosystem                                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. agentgateway (submodule)                                │
│     └─ Core open-source gateway functionality               │
│                                                              │
│  2. unitone-agentgateway (wrapper) - THIS REPO              │
│     ├─ UnitOne-specific deployment configs                  │
│     ├─ GitHub Actions CI/CD                                 │
│     ├─ Docker build configurations                          │
│     └─ UI customizations and branding                       │
│                                                              │
│  3. terraform (sibling repo)                                │
│     ├─ Infrastructure provisioning                          │
│     ├─ Multi-environment setup (dev/staging/prod)           │
│     └─ Cloud resources (ACR, Container Apps, etc.)          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Documentation:**
- **[UnitOne AgentGateway README](../README.md)** - Wrapper repository overview
- **[Terraform README](../../terraform/README.md)** - Infrastructure repository overview
- **[Terraform Project Structure](../../terraform/docs/terraform-project-structure.md)** - Detailed terraform organization

---

## Deployment Guides

### Primary Deployment Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | Complete deployment automation guide with submodule workflow | Developers, DevOps |
| **[Terraform README](../../terraform/README.md)** | Infrastructure deployment and management | DevOps, Platform Engineers |
| **[CICD_OPTIONS.md](CICD_OPTIONS.md)** | Compare GitHub Actions vs ACR Tasks | DevOps, Architects |

### Deployment Methods

#### 1. Automated Deployment (Primary)
**Via GitHub Actions:**
- **Documentation:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **Workflow File:** `../.github/workflows/azure-deploy.yml`
- **Trigger:** Push to `main` branch → deploys to dev
- **Manual:** GitHub Actions UI → select environment

#### 2. Manual Deployment
**Via Azure CLI:**
```bash
# Build
az acr build --registry agwimages --image unitone-agentgateway:latest --file Dockerfile.acr .

# Deploy
az containerapp update --name unitone-agentgateway --resource-group mcp-gateway-dev-rg --image agwimages.azurecr.io/unitone-agentgateway:latest
```

**Documentation:** [UnitOne AgentGateway README](../README.md)

#### 3. Infrastructure Provisioning
**Via Terraform:**
```bash
cd /path/to/terraform/environments/dev/agentgateway
terraform plan
terraform apply
```

**Documentation:**
- [Terraform README](../../terraform/README.md)
- [Terraform Project Structure](../../terraform/docs/terraform-project-structure.md)

---

## CI/CD and Automation

### Overview

| Approach | Status | Documentation |
|----------|--------|---------------|
| **GitHub Actions** | ✅ ACTIVE (Primary) | [CICD_OPTIONS.md](CICD_OPTIONS.md) |
| **ACR Tasks** | ⚠️ AVAILABLE (Optional) | [CICD_OPTIONS.md](CICD_OPTIONS.md), [ci_cd.tf](../../terraform/modules/azure/agentgateway/ci_cd.tf) |

### Key Documents

1. **[CICD_OPTIONS.md](CICD_OPTIONS.md)** - Comprehensive comparison
   - GitHub Actions vs ACR Tasks
   - When to use each approach
   - Cost considerations
   - Monitoring and troubleshooting

2. **[DEPLOYMENT.md](DEPLOYMENT.md)** - GitHub Actions workflow
   - Automated deployment process
   - Submodule handling
   - Multi-environment deployment
   - Deployment verification

3. **[ci_cd.tf](../../terraform/modules/azure/agentgateway/ci_cd.tf)** - ACR Tasks definition
   - Terraform configuration for ACR Tasks
   - Optional automation setup
   - Webhook configuration

### GitHub Actions Workflow

**Location:** `../.github/workflows/azure-deploy.yml`

**Triggers:**
- Push to `main` → Deploy to dev
- Manual dispatch → Deploy to selected environment

**Documentation:** [CICD_OPTIONS.md](CICD_OPTIONS.md) section "Current Setup: GitHub Actions"

---

## Infrastructure (Terraform)

### Main Documentation

1. **[Terraform README](../../terraform/README.md)**
   - Quick start guide
   - Common operations (deploy, destroy, view state)
   - Environment configuration
   - Security and secrets management

2. **[Terraform Project Structure](../../terraform/docs/terraform-project-structure.md)**
   - Repository organization principles
   - Module development guidelines
   - Environment isolation strategy
   - State management patterns
   - Best practices

### Key Concepts

**Environment Separation:**
```
terraform/environments/
├── dev/agentgateway/          # Development
├── staging/agentgateway/      # Staging
└── prod/agentgateway/         # Production
```

**Reusable Modules:**
```
terraform/modules/
├── aws/agentgateway/          # AWS-specific
└── azure/agentgateway/        # Azure-specific
    ├── main.tf                # Core resources
    ├── ci_cd.tf              # Optional ACR Tasks
    ├── variables.tf
    └── outputs.tf
```

**Documentation:**
- Module organization: [Terraform Project Structure](../../terraform/docs/terraform-project-structure.md) section "Module Organization"
- CI/CD infrastructure: [ci_cd.tf](../../terraform/modules/azure/agentgateway/ci_cd.tf)

### Azure Resources

| Resource | Purpose | Documentation |
|----------|---------|---------------|
| Container Registry (ACR) | Docker image storage | [Terraform README](../../terraform/README.md) |
| Container Apps | Application hosting | [Terraform README](../../terraform/README.md) |
| Log Analytics | Centralized logging | [Terraform README](../../terraform/README.md) |
| Application Insights | Monitoring | [Terraform README](../../terraform/README.md) |
| Key Vault | Secrets management | [EASY_AUTH_DEPLOYMENT.md](EASY_AUTH_DEPLOYMENT.md) |

---

## UnitOne Customizations

### Branding and UI

1. **[UNITONE_BRANDING_CHANGES.md](UNITONE_BRANDING_CHANGES.md)**
   - Logo and color scheme changes
   - Theme configuration
   - Font customization (Inter vs Geist)
   - Build-time customization approach

2. **[UNITONE_USER_MENU_FEATURE.md](UNITONE_USER_MENU_FEATURE.md)**
   - User menu implementation
   - OAuth integration details
   - Azure AD and Google authentication
   - Branch: `unitone/user-menu-feature`

### OAuth and Authentication

**[EASY_AUTH_DEPLOYMENT.md](EASY_AUTH_DEPLOYMENT.md)**
- Azure Container Apps Easy Auth setup
- Microsoft (Azure AD) configuration
- Google OAuth configuration
- Testing and verification
- Troubleshooting auth issues

**Key Features:**
- Platform-level authentication (no app code needed)
- Multiple OAuth providers (Microsoft, Google)
- User menu with avatar and profile
- Sign out functionality

### Customization Strategy

**Separation of Concerns:**
- Core functionality → `agentgateway` submodule
- UnitOne customizations → `unitone-agentgateway` wrapper
- Infrastructure → `terraform` sibling repo

**Documentation:** [UnitOne AgentGateway README](../README.md) section "What's UnitOne-Specific"

---

## Core AgentGateway (Submodule)

### Upstream Documentation

The `agentgateway` submodule contains the core gateway functionality. Key documentation:

**Location:** `../agentgateway/`

**Main Docs:**
- `agentgateway/README.md` - Core project overview
- `agentgateway/docs/` - Feature documentation
- `agentgateway/ui/README.md` - UI application details

### Updating the Submodule

**Documentation:** [DEPLOYMENT.md](DEPLOYMENT.md) section "Submodule Update Workflow"

**Process:**
```bash
cd unitone-agentgateway/agentgateway
git fetch origin
git checkout origin/main
cd ..
git add agentgateway
git commit -m "Update agentgateway submodule"
git push origin main  # Triggers deployment
```

### Contributing to Core

**For core agentgateway improvements:**
1. Contribute to upstream [agentgateway repository](https://github.com/UnitOneAI/agentgateway)
2. Update submodule in unitone-agentgateway
3. Test in dev environment
4. Deploy to staging/prod

**Documentation:** [UnitOne AgentGateway README](../README.md) section "Contributing"

---

## Development Workflows

### Local Development

**Prerequisites:**
- Git with submodules support
- Docker
- Rust toolchain (optional)
- Node.js (optional, for UI)
- Azure CLI

**Documentation:** [UnitOne AgentGateway README](../README.md) section "Prerequisites"

### Common Tasks

| Task | Documentation | Commands |
|------|---------------|----------|
| Clone repository | [README](../README.md) | `git clone --recursive` |
| Update submodule | [DEPLOYMENT.md](DEPLOYMENT.md) | `git submodule update --init --recursive` |
| Build Docker image | [README](../README.md) | `az acr build ...` |
| Deploy to dev | [DEPLOYMENT.md](DEPLOYMENT.md) | `git push origin main` |
| Deploy to prod | [DEPLOYMENT.md](DEPLOYMENT.md) | Manual via GitHub Actions |
| View logs | [README](../README.md) | `az containerapp logs show ...` |
| Manage infrastructure | [Terraform README](../../terraform/README.md) | `terraform plan/apply` |

---

## Monitoring and Troubleshooting

### Health Checks

**Documentation:** [UnitOne AgentGateway README](../README.md) section "Monitoring"

**Endpoints:**
- Application health: `https://unitone-agentgateway.../health`
- MCP endpoint: `https://unitone-agentgateway.../mcp/github`
- OAuth user info: `https://unitone-agentgateway.../.auth/me`

### Logs and Debugging

**Container App Logs:**
```bash
az containerapp logs show --name unitone-agentgateway --resource-group mcp-gateway-dev-rg --follow
```

**ACR Build Logs:**
```bash
az acr task logs --registry agwimages --follow
```

**Documentation:**
- [UnitOne AgentGateway README](../README.md) section "Monitoring"
- [DEPLOYMENT.md](DEPLOYMENT.md) section "Troubleshooting"
- [Terraform README](../../terraform/README.md) section "Troubleshooting"

### Common Issues

| Issue | Documentation |
|-------|---------------|
| Submodule not initialized | [README](../README.md) section "Troubleshooting" |
| Build fails | [README](../README.md) section "Troubleshooting" |
| Deployment fails | [README](../README.md) section "Troubleshooting" |
| OAuth issues | [EASY_AUTH_DEPLOYMENT.md](EASY_AUTH_DEPLOYMENT.md) section "Troubleshooting" |
| Terraform state lock | [Terraform README](../../terraform/README.md) section "Troubleshooting" |

---

## Security

### Secrets Management

**Documentation:**
- [Terraform README](../../terraform/README.md) section "Security"
- [EASY_AUTH_DEPLOYMENT.md](EASY_AUTH_DEPLOYMENT.md)

**Key Principles:**
- OAuth credentials → Azure Key Vault
- API keys → Cloud-native secret stores
- Terraform variables → Environment variables or `.tfvars` files (never committed)
- Service principal credentials → GitHub Secrets

### Access Control

**Documentation:** [Terraform README](../../terraform/README.md) section "Security"

- Cloud provider RBAC for resource access
- Separate service principals per environment
- Least-privilege permissions
- OAuth authentication required for UI

---

## Reference

### All Documentation Files

#### UnitOne AgentGateway (This Repository)
- [README.md](../README.md) - Main entry point
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment automation guide
- [CICD_OPTIONS.md](CICD_OPTIONS.md) - CI/CD comparison
- [EASY_AUTH_DEPLOYMENT.md](EASY_AUTH_DEPLOYMENT.md) - OAuth configuration
- [UNITONE_BRANDING_CHANGES.md](UNITONE_BRANDING_CHANGES.md) - UI customizations
- [UNITONE_USER_MENU_FEATURE.md](UNITONE_USER_MENU_FEATURE.md) - User menu feature
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - This file

#### Terraform (Sibling Repository)
- [README.md](../../terraform/README.md) - Infrastructure overview
- [docs/terraform-project-structure.md](../../terraform/docs/terraform-project-structure.md) - Organization guide
- [modules/azure/agentgateway/ci_cd.tf](../../terraform/modules/azure/agentgateway/ci_cd.tf) - ACR Tasks definition

#### AgentGateway (Submodule)
- `../agentgateway/README.md` - Core project documentation
- `../agentgateway/docs/` - Feature documentation
- `../agentgateway/ui/README.md` - UI documentation

### External Resources

- [Terraform Documentation](https://www.terraform.io/docs)
- [Azure Container Apps Documentation](https://docs.microsoft.com/en-us/azure/container-apps/)
- [Azure Container Registry Documentation](https://docs.microsoft.com/en-us/azure/container-registry/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

## Document Maintenance

### Keeping Documentation Updated

When making changes:
1. Update relevant documentation in the same PR
2. Run through this index to identify related docs
3. Update cross-references between documents
4. Keep examples and commands current

### Documentation Principles

From [Terraform Project Structure](../../terraform/docs/terraform-project-structure.md):
- README files at every level
- Self-documenting code with comments
- Examples in documentation
- Clear cross-references between docs

---

**Last Updated:** January 2026
**Maintained By:** UnitOne DevOps Team

For questions or improvements to this documentation, contact the DevOps team or create an issue in the respective repository.
