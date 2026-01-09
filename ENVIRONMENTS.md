# UnitOne AgentGateway - Deployment Environments

All three environments have been successfully deployed via Terraform with health probes and monitoring.

## Environment Overview

| Environment | Status | URL | Use Case |
|-------------|--------|-----|----------|
| **Dev** | ✅ Active | https://unitone-agw-dev-app.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/ui | Development, testing, allows anonymous access |
| **Staging** | ✅ Active | https://unitone-agw-staging-app.icyisland-535dd8c7.eastus2.azurecontainerapps.io/ui | Pre-production validation, authentication required |
| **Production** | ✅ Active | https://unitone-agw-prod-app.calmfield-9aeb3d35.eastus2.azurecontainerapps.io/ui | Production workloads, authentication required |

## Resources Deployed Per Environment

Each environment includes:
- **Azure Container Registry (ACR)**: Stores Docker images
- **Container App**: Runs the agentgateway with health probes
- **Container App Environment**: Isolated environment for apps
- **Log Analytics Workspace**: Centralized logging
- **Application Insights**: APM and monitoring
- **Key Vault**: Stores OAuth secrets (Microsoft, Google, GitHub)
- **PII MCP Test Server**: Internal testing server for PII detection

## Health Probes Configuration

All environments now have:
- **Readiness Probe**: HTTP check on port 15021, path `/healthz/ready`
  - Interval: 10 seconds
  - Timeout: 3 seconds
  - Failure threshold: 3
  - Success threshold: 1
- **Liveness Probe**: HTTP check on port 15021, path `/healthz/ready`
  - Initial delay: 30 seconds
  - Interval: 30 seconds
  - Timeout: 5 seconds
  - Failure threshold: 3

## Dev Environment

**Resource Group**: `mcp-gateway-dev-rg`

**Endpoints**:
- UI: https://unitone-agw-dev-app.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/ui
- MCP: https://unitone-agw-dev-app.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp
- ACR: unitoneagwdevacr.azurecr.io

**Configuration**:
- Min replicas: 1
- Max replicas: 3
- Anonymous access: **Enabled** (for E2E testing)
- Authentication: Optional

## Staging Environment

**Resource Group**: `mcp-gateway-staging-rg`

**Endpoints**:
- UI: https://unitone-agw-staging-app.icyisland-535dd8c7.eastus2.azurecontainerapps.io/ui
- MCP: https://unitone-agw-staging-app.icyisland-535dd8c7.eastus2.azurecontainerapps.io/mcp
- ACR: unitoneagwstagingacr.azurecr.io

**Configuration**:
- Min replicas: 1
- Max replicas: 3
- Anonymous access: **Disabled**
- Authentication: Required (Microsoft, Google, GitHub)

## Production Environment

**Resource Group**: `mcp-gateway-prod-rg`

**Endpoints**:
- UI: https://unitone-agw-prod-app.calmfield-9aeb3d35.eastus2.azurecontainerapps.io/ui
- MCP: https://unitone-agw-prod-app.calmfield-9aeb3d35.eastus2.azurecontainerapps.io/mcp
- ACR: unitoneagwprodacr.azurecr.io

**Configuration**:
- Min replicas: 2 (high availability)
- Max replicas: 10
- Anonymous access: **Disabled**
- Authentication: Required (Microsoft, Google, GitHub)

## Deployment Commands

### View Environment Status

```bash
# Dev
az containerapp show --name unitone-agw-dev-app --resource-group mcp-gateway-dev-rg

# Staging
az containerapp show --name unitone-agw-staging-app --resource-group mcp-gateway-staging-rg

# Production
az containerapp show --name unitone-agw-prod-app --resource-group mcp-gateway-prod-rg
```

### View Logs

```bash
# Dev
az containerapp logs show --name unitone-agw-dev-app --resource-group mcp-gateway-dev-rg --follow

# Staging
az containerapp logs show --name unitone-agw-staging-app --resource-group mcp-gateway-staging-rg --follow

# Production
az containerapp logs show --name unitone-agw-prod-app --resource-group mcp-gateway-prod-rg --follow
```

### Deploy New Image

```bash
# Build for specific environment
cd /Users/surindersingh/source_code/unitone-agentgateway

# Dev
az acr build --registry unitoneagwdevacr --image unitone-agentgateway:latest --file Dockerfile.acr .

# Staging
az acr build --registry unitoneagwstagingacr --image unitone-agentgateway:latest --file Dockerfile.acr .

# Production
az acr build --registry unitoneagwprodacr --image unitone-agentgateway:latest --file Dockerfile.acr .
```

### Update Infrastructure

```bash
# Navigate to environment directory
cd /Users/surindersingh/source_code/terraform/environments/{dev|staging|prod}/agentgateway

# Plan changes
terraform plan

# Apply changes
terraform apply
```

## Issues Fixed (January 8, 2026)

1. **Dev Environment Down**: Fixed by adding health probes and correcting MCP route configuration
2. **Health Probe Configuration**: Added liveness and readiness probes to all container apps
3. **MCP Route Parse Error**: Fixed missing `name:` field in azure-config.yaml
4. **Staging Environment**: Created complete staging environment via Terraform
5. **Production Environment**: Created complete production environment via Terraform

## Next Steps

1. Configure OAuth applications (Microsoft, Google, GitHub) for staging and production
2. Update Key Vault secrets with OAuth credentials
3. Set up CI/CD pipelines for automated deployments
4. Configure custom domains (optional)
5. Set up monitoring alerts in Application Insights

## Terraform State

All environments are managed via Terraform:
- Dev: `/terraform/environments/dev/agentgateway/`
- Staging: `/terraform/environments/staging/agentgateway/`
- Production: `/terraform/environments/prod/agentgateway/`

---

**Last Updated**: January 8, 2026
**Managed By**: Terraform
**Documentation**: See [DEVELOPER_WORKFLOW.md](docs/DEVELOPER_WORKFLOW.md) for detailed development guide
