# UnitOne AgentGateway Deployment

This repository contains UnitOne-specific configurations and customizations for deploying [agentgateway](https://github.com/UnitOneAI/agentgateway).

## Overview

This wrapper repository separates UnitOne-specific infrastructure, branding, and deployment configurations from the core agentgateway project, making it easier to:

- Maintain clear separation between generic and company-specific code
- Sync with upstream agentgateway updates without conflicts
- Prepare the main agentgateway repo for future open source contribution
- Provide clear deployment workflows for UnitOne infrastructure

## Repository Structure

```
unitone-agentgateway/
├── agentgateway/              # Git submodule - core agentgateway code
├── terraform/                 # UnitOne-specific Terraform infrastructure
│   ├── environments/
│   │   ├── dev/              # Development environment
│   │   ├── staging/          # Staging environment
│   │   └── prod/             # Production environment
│   └── modules/              # Terraform modules
│       └── azure/
│           └── agentgateway/
├── ui-customizations/         # UnitOne branding overlay
│   ├── theme.config.ts
│   └── images/
│       └── unitone-logo.png
├── deploy/                    # Deployment scripts and configs
│   ├── build-and-deploy.sh
│   ├── rollback.sh
│   └── configs/
│       └── azure-config.yaml
├── tests/                     # E2E tests for UnitOne infrastructure
│   ├── e2e_mcp_sse_test.py
│   ├── .env.unitone
│   └── wait_for_build_and_deploy.sh
├── docs/                      # UnitOne-specific documentation
│   ├── UNITONE_BRANDING_CHANGES.md
│   ├── UNITONE_DEPLOYMENT.md
│   ├── TERRAFORM_CICD_SETUP.md
│   └── RUNBOOKS.md
├── Makefile                   # Build/deploy/test automation
└── README.md                  # This file
```

## Quick Start

### Prerequisites

- Git with submodules support
- Azure CLI (`az`) configured with UnitOne subscription
- Terraform >= 1.0
- Rust toolchain (for building agentgateway)
- Node.js (for UI customizations)

### Clone the Repository

```bash
# Clone with submodules
git clone --recursive git@github.com:UnitOneAI/unitone-agentgateway.git
cd unitone-agentgateway

# Or if already cloned, initialize submodules
git submodule update --init --recursive
```

### Build with UnitOne Branding

```bash
# Apply UnitOne UI branding and build
make build
```

### Deploy to Development

```bash
# Deploy to UnitOne dev environment
make deploy-dev
```

### Run E2E Tests

```bash
# Run E2E tests against UnitOne infrastructure
make test
```

## Available Make Targets

| Target | Description |
|--------|-------------|
| `make build` | Build agentgateway with UnitOne branding |
| `make deploy-dev` | Deploy to development environment |
| `make deploy-staging` | Deploy to staging environment |
| `make deploy-prod` | Deploy to production environment |
| `make test` | Run E2E tests |
| `make clean` | Clean build artifacts and reset submodule |
| `make update-submodule` | Update agentgateway submodule to latest |
| `make terraform-init` | Initialize Terraform |
| `make terraform-plan` | Plan Terraform changes |
| `make terraform-apply` | Apply Terraform changes |

## What's UnitOne-Specific

This repository contains:

### Infrastructure (terraform/)
- Azure Container Registry configuration
- Azure Container Apps deployment
- Azure Key Vault secrets management
- Environment-specific configurations (dev/staging/prod)
- Resource group and naming conventions

### UI Customizations (ui-customizations/)
- UnitOne brand colors and theme
- Logo and imagery
- Custom styling overrides
- Font configurations

### Deployment Scripts (deploy/)
- Azure-specific build and deploy scripts
- Rollback procedures
- Environment configuration files
- CI/CD automation helpers

### Tests (tests/)
- E2E tests with UnitOne infrastructure URLs
- Integration tests for Azure deployment
- Performance and load tests

### Documentation (docs/)
- UnitOne deployment procedures
- Runbooks for common operations
- Branding change documentation
- Terraform CI/CD setup guide

## Syncing with Upstream

To update the core agentgateway code from upstream:

```bash
# Update submodule to latest commit
cd agentgateway
git pull origin main
cd ..

# Commit the submodule update
git add agentgateway
git commit -m "Update agentgateway submodule to latest"
git push
```

## Deployment Workflows

### Development

1. Make changes to agentgateway core (in `agentgateway/` submodule)
2. Test locally
3. Push changes to agentgateway repo
4. Update submodule reference in wrapper repo
5. Deploy to dev: `make deploy-dev`
6. Run tests: `make test`

### Staging

1. Verify dev deployment is stable
2. Deploy to staging: `make deploy-staging`
3. Run full test suite
4. Perform manual QA

### Production

1. Verify staging deployment is stable
2. Create release tag
3. Deploy to production: `make deploy-prod`
4. Monitor deployment
5. Verify with smoke tests

## Environment Variables

The following environment variables can be set for deployments:

```bash
# Azure Configuration
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AZURE_TENANT_ID="your-tenant-id"

# Environment Selection
export ENVIRONMENT="dev"  # or "staging" or "prod"

# Feature Flags
export ENABLE_UI="true"
export ENABLE_OAUTH="true"
export ENABLE_SECURITY_GUARDS="true"
```

## Terraform State

Terraform state is stored in Azure Storage for team collaboration:

- Backend: Azure Storage Account
- Container: `tfstate`
- Key: `agentgateway-{environment}.tfstate`

## CI/CD Integration

This wrapper repository integrates with:

- **Azure ACR Tasks**: Automated builds on git push
- **GitHub Actions**: Automated testing and deployment
- **Terraform Cloud/Enterprise**: Infrastructure as Code management

See `docs/TERRAFORM_CICD_SETUP.md` for detailed CI/CD configuration.

## Troubleshooting

### Common Issues

**Issue**: Submodule not initialized
```bash
git submodule update --init --recursive
```

**Issue**: Build fails with branding errors
```bash
# Reset UI customizations
make clean
make build
```

**Issue**: Terraform state locked
```bash
# Force unlock (use with caution)
cd terraform/environments/{env}/agentgateway
terraform force-unlock <lock-id>
```

**Issue**: Deployment fails
```bash
# Check logs
az containerapp logs show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --tail 100
```

### Getting Help

- Internal Documentation: See `docs/` directory
- Runbooks: See `docs/RUNBOOKS.md`
- Team Channel: #unitone-agentgateway
- On-call: PagerDuty escalation

## Contributing

Since this is a wrapper repository for UnitOne-specific configurations:

1. **Core agentgateway changes**: Contribute to the main agentgateway repository
2. **UnitOne-specific changes**: Make PRs to this repository
3. **Infrastructure changes**: Update Terraform configs in `terraform/`
4. **Branding changes**: Update files in `ui-customizations/`

### PR Guidelines

1. Test changes in dev environment first
2. Update documentation if needed
3. Include deployment notes in PR description
4. Get approval from DevOps team for infrastructure changes
5. Tag PRs appropriately (infrastructure, branding, deployment)

## Monitoring and Observability

### Application Insights

- Workspace: `unitone-agentgateway-insights`
- Logs: Available in Azure Portal
- Dashboards: See Application Insights dashboards

### Health Checks

```bash
# Check application health
curl https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/health

# Check MCP endpoint
curl https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp/github
```

### Logs

```bash
# Stream logs
make logs-dev

# Or directly with Azure CLI
az containerapp logs show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --follow
```

## Security

### Secrets Management

All secrets are stored in Azure Key Vault:

- OAuth credentials
- API keys
- Database connection strings
- Service principal credentials

Never commit secrets to this repository.

### Access Control

- Azure RBAC for resource access
- GitHub team permissions for repo access
- Terraform Cloud workspace access controls

## License

The core agentgateway is licensed under Apache 2.0.

This wrapper repository is proprietary to UnitOne and contains confidential business logic and infrastructure configurations.

## Support

For issues or questions:

1. Check `docs/` directory for documentation
2. Search existing issues in GitHub
3. Contact the DevOps team
4. Escalate to on-call if production issue

---

**Last Updated**: January 2026
**Maintained By**: UnitOne DevOps Team
