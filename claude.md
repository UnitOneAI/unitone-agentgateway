# UnitOne AgentGateway - Initial Intent

## Purpose
UnitOne-branded deployment wrapper for the open source agentgateway project. Provides UnitOne-specific configurations, branding, deployment automation, and Azure-optimized infrastructure while maintaining clear separation from the upstream agentgateway codebase.

## Project Vision & Strategic Direction

### Long-term Goals (2026)
**Vision**: Production-grade UnitOne-branded deployment of AgentGateway with enterprise features while maintaining clean upstream synchronization.

**Key Objectives**:
- Zero-friction deployment: Push to main = production deployment in <10 minutes
- Developer-friendly: Local builds for rapid iteration and testing
- Enterprise ready: UnitOne branding, Azure AD authentication, compliance features
- Upstream compatibility: Clean git submodule, easy to sync with open source updates

### Current Phase: **Deployment Automation** (Q1 2026)
**Goal**: Dual-mode build system supporting both production automation and development flexibility
**Success Criteria**:
- ACR Task automation enabled and stable
- Local build path documented and tested
- Team can deploy to Azure without manual `az` commands

## Recent Significant Changes

### Architecture: Dual-Mode Build System (Jan 2026)
**What Changed**: Implemented parallel build paths for different use cases
- **Production Path**: ACR Task auto-builds on `main` branch push → Container App auto-deployment
- **Development Path**: Local `build-and-push.sh` script for feature branches and testing

**Why This Matters**:
- **Before**: Single manual build path via `az acr build` - slow iteration, blocked on infrastructure team
- **After**: Developers iterate locally; production deploys automatically; no manual steps

**Technical Implementation**:
- `build-and-push.sh`: 471-line script supporting multi-platform builds, custom tags, git versioning
- `LOCAL_BUILD_DEPLOYMENT.md`: Complete guide on when to use each build mode
- ACR Task configured in terraform repository (`modules/azure/agentgateway/ci_cd.tf`)
- GitHub PAT stored in terraform.tfvars (not committed) for ACR Task authentication

**Trade-offs**:
- ACR Task workflow runs continuously (minimal cost, ~$0.10/build)
- Local builds require Azure CLI authentication and ACR access
- Must sync both paths when Dockerfile.acr changes

### Submodule Strategy: Clean Upstream Separation (Jan 2026)
**Maintained Invariant**: `agentgateway/` directory remains a clean git submodule
- Points to UnitOne fork: `git@github.com:UnitOneAI/agentgateway.git`
- Tracks `feature/mcp-security-guards` branch for security enhancements
- Zero modifications to core agentgateway code in this wrapper repository

**Why This Matters**:
- Easy to pull upstream updates (both from official agentgateway and UnitOne fork)
- Clear separation between deployment/branding (this repo) and core features (submodule)
- Can switch between branches or forks by updating `.gitmodules`

## Current Focus Areas (Jan 12-19, 2026)

### Theme 1: Build System Stability
**Goal**: Validate dual-mode builds work reliably for entire team
**Why Now**: Recently enabled ACR Task automation; need to ensure it doesn't break workflows
**Impact**:
- Developers can use either path based on their needs
- No confusion about which build mode to use when
- Documentation prevents common mistakes

**Success Metrics**:
- Both Alexey and Surinder can build/deploy independently
- No failed ACR Task builds on main branch
- Local builds work on both arm64 (Mac) and amd64 (Linux)

### Theme 2: Upstream Security Feature Integration
**Goal**: Support security guard features as they land in agentgateway submodule
**Why Now**: Alexey developing MCP security guards in fork; this wrapper must deploy them
**Impact**:
- Security features automatically available in Azure deployment
- No lag between feature development and production availability
- Runtime guard configuration (when ready) flows through this deployment

**Technical Coordination**:
- Submodule updates pull latest security guard code
- Dockerfile.acr includes guard dependencies
- Azure deployment config will support runtime guard configuration API

### Theme 3: Enterprise Polish
**Goal**: UnitOne branding and Azure AD integration fully functional
**Why Now**: Moving from MVP to customer-facing deployment
**Impact**:
- Professional appearance for demos and pilot customers
- Secure authentication via Azure AD (no API key management)
- Compliance with UnitOne security standards

**Known Issues**:
- Google OAuth not showing in Easy Auth login screen (infrastructure team investigating)
- Microsoft OAuth working correctly

## Evolution Notes

### Deployment Evolution (2025-2026)
**Phase 1 (Late 2025)**: Manual deployment
- `az acr build` manually run for each deployment
- Manual `az containerapp update` to deploy new images
- 15-20 minute manual process per deployment

**Phase 2 (Early Jan 2026)**: Local build script
- Created `build-and-push.sh` for developer self-service
- Still required manual steps but more streamlined
- Development velocity improved but production still manual

**Phase 3 (Mid Jan 2026)**: Dual-mode automation
- ACR Task enabled for production automation
- Local builds preserved for development
- Push to main = automatic production deployment
- Team can choose appropriate path for their context

### Wrapper Pattern Success
**Validation**: Clean separation between generic (submodule) and company-specific (wrapper) code
- UnitOne customizations: Branding, deployment scripts, Azure configuration
- Core features: Developed in submodule, automatically inherited
- Pattern scales: Could apply same wrapper approach to other open source tools

## Core Functionality
- **Git Submodule Pattern**: Clean separation between generic and company-specific code
- **Azure Deployment**: Automated CI/CD to Azure Container Apps
- **UnitOne Branding**: Custom UI styling and branding
- **OAuth Integration**: Azure Easy Auth configuration
- **Enterprise Features**: UnitOne-specific customizations and integrations

## Key Components Protected

### Deployment Wrapper
- **Submodule**: `agentgateway/` pointing to core open source repo
- **CI/CD**: `.github/workflows/azure-deploy.yml` for automated deployment
- **Dockerfile**: `Dockerfile.acr` for Azure Container Registry builds
- **Makefile**: Build and deployment automation commands

### UnitOne Customizations
- **Branding**: Custom logos, colors, and styling
- **User Menu**: Enhanced authentication and profile features
- **Configuration**: Environment-specific Azure settings
- **Documentation**: UnitOne-specific deployment guides

### Infrastructure Integration
- **Azure Container Apps**: Serverless container hosting
- **Azure Container Registry**: Private container image storage
- **Easy Auth**: OAuth 2.0 / Azure AD integration
- **App Service Plan**: Compute and scaling configuration

## Critical Workflows

1. **Upstream Sync**
   ```
   agentgateway (upstream) → Pull Updates → Test Compatibility
   → Merge to Submodule → Deploy to Azure
   ```

2. **Deployment Pipeline**
   ```
   Code Push → GitHub Actions → Build Container → Push to ACR
   → Deploy to Container App → Health Check → DNS Update
   ```

3. **Branding Application**
   ```
   Base UI → Apply UnitOne Theme → Add Custom Components
   → Build Production Bundle → Deploy
   ```

4. **Environment Promotion**
   ```
   Dev Deployment → Testing → Staging → Prod → Rollback Capability
   ```

## Security Boundaries

### Access Control
- **Easy Auth**: Azure AD integration for authentication
- **RBAC**: Role-based access via Azure AD groups
- **API Keys**: Managed via Azure Key Vault
- **Network**: VNet integration for private endpoints

### Secrets Management
- **Azure Key Vault**: Centralized secret storage
- **Managed Identity**: Credential-free Azure resource access
- **Environment Variables**: Injected at runtime
- **No Hardcoded Secrets**: All secrets via secure channels

### Container Security
- **Base Image**: Official Rust slim images
- **Vulnerability Scanning**: Automated CVE checks
- **Least Privilege**: Non-root container execution
- **Image Signing**: ACR content trust

## Invariants to Protect

1. **Submodule Relationship**: `agentgateway/` remains a clean submodule
2. **No Upstream Modifications**: Core agentgateway code not modified in wrapper
3. **Branding Layer**: Customizations in separate files/directories
4. **Deployment Targets**: Azure-specific infrastructure
5. **Configuration Hierarchy**: UnitOne configs override defaults, not replace

## Dependencies
- **Upstream**: agentgateway (git submodule)
- **Azure CLI**: Deployment automation
- **Docker**: Container builds
- **GitHub Actions**: CI/CD automation
- **Terraform**: Infrastructure (sibling repository)

## What Should Not Change Without Review

### Submodule Management
- Submodule remote URL (points to UnitOneAI/agentgateway)
- Submodule update strategy
- No direct commits to submodule directory

### Azure Infrastructure
- Container App name and resource group
- ACR registry name and login server
- Easy Auth configuration
- App Service Plan SKU (affects cost)
- Environment variables required by agentgateway

### CI/CD Pipeline
- GitHub Actions workflow triggers
- Build steps and container tags
- Deployment approval requirements
- Rollback procedures

## Approved Extension Points
- New UnitOne-specific UI features (in wrapper, not submodule)
- Enhanced Azure integrations (monitoring, alerts, etc.)
- Additional deployment environments (dev, staging, prod)
- Custom authentication flows
- UnitOne-specific API endpoints (as separate service)
- Performance monitoring and optimization

## Branding Guidelines

### Visual Elements
- UnitOne logo and icon
- Color palette customization
- Typography and fonts
- Custom UI components

### Feature Additions
- User profile menu
- Company-specific dashboards
- Enhanced security features
- Enterprise reporting

### Location of Customizations
- UI branding: `agentgateway/ui/` overlays (not modifications)
- Configuration: Root-level config files
- Documentation: `docs/` directory in wrapper

## Relationship with Sibling Repositories

### Terraform (Infrastructure)
- Defines Azure infrastructure for agentgateway
- Container App, ACR, VNet, Easy Auth resources
- Located at: `terraform/environments/{env}/agentgateway/`

### Integration Points
- Container image name from ACR
- Environment variables from Key Vault
- DNS and networking configuration
- Scaling and resource limits

## Sync Strategy with Upstream

### Current Branch
**Active Branch**: `feature/mcp-security-guards`
- Contains MCP security enhancements
- Includes UnitOne branding already applied
- Tracked in `.gitmodules` for automatic updates

### Regular Updates
1. Check upstream for new releases
2. Update submodule to latest from feature branch
3. Test compatibility with UnitOne customizations
4. Deploy to dev environment
5. Validate functionality
6. Promote to staging and prod

### Conflict Resolution
- Upstream changes take precedence for core functionality
- UnitOne customizations maintained as additive layers
- Breaking changes trigger compatibility review
- Document any temporary workarounds

---
**Document Version**: 1.0
**Created**: 2026-01-08
**Last Updated**: 2026-01-08
**Architecture**: Wrapper pattern with clean upstream separation
