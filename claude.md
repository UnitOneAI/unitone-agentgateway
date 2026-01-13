# UnitOne AgentGateway - Initial Intent

## Purpose
UnitOne-branded deployment wrapper for the open source agentgateway project. Provides UnitOne-specific configurations, branding, deployment automation, and Azure-optimized infrastructure while maintaining clear separation from the upstream agentgateway codebase.

## Current Sprint (Jan 12-19, 2026)

### Active Work Items
- **Dual-Mode Build System** (Surinder)
  - ACR Task automation for production deployments (ENABLED)
  - Local build script for development (build-and-push.sh)
  - Documentation updates for when to use each approach

- **Security Guard Configuration** (Alexey via upstream)
  - Move guard config from baked-in image to runtime dashboard configuration
  - Enable/disable guards per MCP target dynamically

### Completed This Sprint
- ✅ Local build infrastructure (build-and-push.sh, LOCAL_BUILD_DEPLOYMENT.md)
- ✅ Re-enabled ACR Task automation for auto-deploy on main branch push
- ✅ Dual-mode documentation (both automated and manual builds)

### Sprint Goals
- Maintain both deployment paths: automated (ACR Task) and manual (local builds)
- Support AgentGateway security features as they're developed in upstream fork
- Keep wrapper clean and focused on deployment/branding

### Build Strategy
- **Production**: Push to main → ACR Task auto-build → Auto-deploy to Container App
- **Development**: Local build → Test → Push when ready
- **Configuration**: GitHub PAT enabled for ACR Task, terraform.tfvars controls automation

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
