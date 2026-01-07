# Deployment Automation Guide

This document explains the deployment automation for UnitOne AgentGateway.

## Overview

The deployment process is fully automated using:
- **Bicep** for infrastructure-as-code
- **GitHub Actions** for CI/CD
- **Azure Container Registry (ACR)** for Docker image storage
- **Azure Container Apps** for hosting

---

## Getting Started

### Repository Architecture

The UnitOne AgentGateway uses a **wrapper repository** pattern with git submodules:

```
unitone-agentgateway/          # Wrapper repository (THIS REPO)
├── .github/workflows/         # GitHub Actions workflows
│   └── azure-deploy.yml       # Automated deployment workflow
├── Dockerfile.acr             # Docker build configuration
├── docs/                      # Documentation
├── ui-customizations/         # UnitOne UI branding (optional)
└── agentgateway/              # Git submodule → original agentgateway source
    ├── src/                   # Rust source code
    ├── ui/                    # Next.js UI application
    └── Cargo.toml             # Rust project configuration
```

**Key Points**:
- `unitone-agentgateway` is the wrapper repository that contains customizations and deployment configs
- `agentgateway` is included as a **git submodule** pointing to the upstream source repository
- GitHub Actions workflow triggers on push to `unitone-agentgateway`'s `main` branch
- The workflow automatically initializes the submodule during build

---

### Initial Setup

#### 1. Clone the Repository

```bash
# Clone with submodules
git clone --recursive https://github.com/UnitOneAI/unitone-agentgateway.git
cd unitone-agentgateway

# If you already cloned without --recursive, initialize submodules:
git submodule update --init --recursive
```

#### 2. Verify Submodule Setup

```bash
# Check submodule status
git submodule status

# Should show something like:
# abc123def456... agentgateway (heads/main)

# Verify the submodule directory has content
ls agentgateway/
# Should show: Cargo.toml, src/, ui/, etc.
```

---

### Updating the Agentgateway Submodule

When the upstream `agentgateway` repository releases new features or fixes, you need to update the submodule pointer:

#### Step 1: Update the Submodule

```bash
cd unitone-agentgateway

# Navigate into the submodule
cd agentgateway

# Fetch latest changes from upstream
git fetch origin

# Checkout the desired version (usually main branch or a specific tag)
git checkout origin/main
# OR for a specific version:
# git checkout v1.2.3

# Return to wrapper repo
cd ..
```

#### Step 2: Commit the Submodule Update

```bash
# The submodule pointer change will show as modified
git status
# Shows: modified:   agentgateway (new commits)

# Stage the submodule update
git add agentgateway

# Commit with a descriptive message
git commit -m "Update agentgateway submodule to latest version

- Includes new feature X
- Fixes bug Y
- Version: <commit-sha or tag>"

# Push to trigger deployment
git push origin main
```

#### Step 3: Automated Deployment

Once you push the submodule update to `unitone-agentgateway`'s `main` branch:

1. **GitHub Actions Workflow Triggers** (`.github/workflows/azure-deploy.yml`)
2. **Workflow checks out repository** with `submodules: 'recursive'`
3. **Docker build uses the updated submodule** version
4. **Image is built** using the new agentgateway code
5. **Deployment to Azure** happens automatically

**Example Workflow**:

```bash
# Developer workflow for submodule update
cd ~/unitone-agentgateway
cd agentgateway
git fetch origin
git checkout origin/main  # Use latest agentgateway code
cd ..
git add agentgateway
git commit -m "Update agentgateway to include security fixes"
git push origin main

# Wait 3-5 minutes for GitHub Actions to complete
# Check deployment at: https://github.com/UnitOneAI/unitone-agentgateway/actions
```

---

### Developer Workflow

#### Making Changes to UnitOne Customizations

If you're modifying **wrapper repository files** (not the submodule):

```bash
# Example: Update Dockerfile.acr
vim Dockerfile.acr

# Stage and commit
git add Dockerfile.acr
git commit -m "Update Dockerfile to optimize build cache"
git push origin main

# GitHub Actions will automatically:
# 1. Build new Docker image
# 2. Push to Azure Container Registry
# 3. Deploy to dev environment
```

#### Making Changes to Agentgateway Source Code

If you're modifying the **agentgateway submodule source code**:

```bash
# Navigate to submodule
cd agentgateway

# Create a feature branch
git checkout -b feature/my-new-feature

# Make your changes
vim src/my_file.rs

# Commit to the submodule repository
git add src/my_file.rs
git commit -m "Add new feature"

# Push to agentgateway repository
git push origin feature/my-new-feature

# Create PR in agentgateway repository
# Once merged to agentgateway/main, update the wrapper:

cd ..  # Back to wrapper repo
cd agentgateway
git fetch origin
git checkout origin/main  # Pull the merged changes
cd ..
git add agentgateway
git commit -m "Update agentgateway submodule with new feature"
git push origin main  # Triggers deployment with new feature
```

---

### Understanding Workflow Triggers

The GitHub Actions workflow (`.github/workflows/azure-deploy.yml`) **ONLY** triggers on:

- **Push to `unitone-agentgateway`'s `main` branch** → Deploys to **dev**
- **Published release in `unitone-agentgateway`** → Deploys to **prod**
- **Manual workflow dispatch** → Deploy to any environment

**Important**: Pushing changes to the `agentgateway` submodule repository does **NOT** trigger the workflow. You must update the submodule pointer in `unitone-agentgateway` and push to trigger deployment.

---

### Quick Reference: Common Tasks

| Task | Commands |
|------|----------|
| Clone with submodules | `git clone --recursive <repo-url>` |
| Initialize submodules (if not done) | `git submodule update --init --recursive` |
| Update submodule to latest | `cd agentgateway && git fetch origin && git checkout origin/main && cd .. && git add agentgateway && git commit -m "Update submodule" && git push` |
| Check submodule status | `git submodule status` |
| View submodule current commit | `cd agentgateway && git log -1` |
| Trigger dev deployment | `git push origin main` |
| Trigger prod deployment | Create and publish a release on GitHub |

---

## Deployment Workflows

### 1. CI/CD Pipeline (`.github/workflows/pull_request.yml`)

**Triggers**: Push to `main`, Pull Requests to `main`

**What it does**:
- Builds on multiple platforms (Linux x86/ARM, macOS, Windows)
- Builds UI (`npm run build`)
- Runs all tests (`make test`)
- Runs validation (`make validate`)
- Runs linting

**Does NOT**: Deploy to Azure

---

### 2. Azure Deployment (`.github/workflows/azure-deploy.yml`) ⭐ NEW

**Triggers**:
- **Push to `main`**: Automatically deploys to **dev** environment
- **Release published**: Automatically deploys to **prod** environment
- **Manual dispatch**: Deploy to any environment with custom tag

**What it does**:
1. Determines environment and image tag based on trigger
2. Builds Docker image using `az acr build`
3. Multi-tags images:
   - Main tag (commit SHA for dev, semantic version for prod)
   - Timestamp tag (YYYYMMDD-HHMMSS)
   - `latest` tag
4. Deploys infrastructure using Bicep
5. Verifies deployment health
6. Outputs UI and MCP endpoint URLs

**Image Tagging Strategy**:
- **Dev builds** (push to main): `<short-commit-sha>`, `<timestamp>`, `latest`
- **Prod releases** (published release): `<semantic-version>`, `<timestamp>`, `latest`
- **Manual dispatch**: Custom tag + `<timestamp>`, `latest`

---

### 3. Release Workflow (`.github/workflows/release.yml`)

**Triggers**: Manual dispatch or release creation

**What it does**:
- Creates semantic version tags (v1.0.0, v1.0, v1)
- Builds and pushes to GitHub Container Registry (`ghcr.io`)

**Note**: This workflow is separate from Azure deployment. Azure uses ACR (`agwimages.azurecr.io`).

---

## Infrastructure-as-Code (Bicep)

### Files
- **`deploy/bicep/main.bicep`**: Main infrastructure template
- **`deploy/bicep/parameters-dev.json`**: Dev environment parameters
- **`deploy/bicep/parameters-staging.json`**: Staging environment parameters (if exists)
- **`deploy/bicep/parameters-prod.json`**: Prod environment parameters (if exists)

### Resources Defined
- Azure Container Registry (ACR)
- Log Analytics Workspace
- Application Insights
- Key Vault (for OAuth secrets)
- Container Apps Environment
- Container App with:
  - Managed identity
  - Ingress configuration
  - CORS policy
  - OAuth environment variables
  - Auto-scaling rules

---

## GitHub Secrets Required

To enable automated deployments, configure these secrets in GitHub repository settings:

### `AZURE_CREDENTIALS`
Azure Service Principal credentials in JSON format:

```json
{
  "clientId": "<client-id>",
  "clientSecret": "<client-secret>",
  "subscriptionId": "<subscription-id>",
  "tenantId": "<tenant-id>"
}
```

**How to create**:
```bash
az ad sp create-for-rbac \
  --name "github-actions-agentgateway" \
  --role contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/mcp-gateway-dev-rg \
  --sdk-auth
```

### Environment-Specific Secrets

For each environment (dev, staging, prod), configure:
- OAuth client IDs and secrets (stored in Azure Key Vault)
- Any environment-specific configuration

---

## Environment Configuration

### Dev Environment
- **Resource Group**: `mcp-gateway-dev-rg`
- **ACR**: `unitoneagwdevacr`
- **Container App**: `unitone-agentgateway`
- **Auto-deploy**: On push to `main`
- **Scaling**: 1-3 replicas

### Staging Environment (if configured)
- **Resource Group**: `mcp-gateway-staging-rg`
- **ACR**: `unitoneagwstagingacr`
- **Container App**: `unitone-agentgateway`
- **Auto-deploy**: Manual dispatch
- **Scaling**: 1-5 replicas

### Prod Environment
- **Resource Group**: `mcp-gateway-prod-rg`
- **ACR**: `unitoneagwprodacr`
- **Container App**: `unitone-agentgateway`
- **Auto-deploy**: On release published
- **Scaling**: 2-10 replicas

---

## Manual Deployment

If you need to deploy manually, use the deployment script:

```bash
cd deploy

# Deploy to dev (build + deploy)
./deploy.sh --environment dev --build --tag latest

# Deploy to staging
./deploy.sh --environment staging --build --tag v1.0.0

# Deploy to prod
./deploy.sh --environment prod --build --tag v1.0.0

# Deploy without building (use existing image)
./deploy.sh --environment dev --tag existing-tag
```

**Script Options**:
- `-e, --environment ENV`: Environment to deploy (dev, staging, prod) [default: dev]
- `-b, --build`: Build and push Docker image before deploying
- `-t, --tag TAG`: Docker image tag [default: latest]
- `-s, --subscription ID`: Azure subscription ID
- `-h, --help`: Show help message

---

## Deployment Process Flow

### Automated Dev Deployment (Push to Main)

1. **Trigger**: Developer pushes code to `main` branch
2. **CI Tests**: `pull_request.yml` runs tests, validation, linting
3. **Build**: `azure-deploy.yml` builds Docker image with commit SHA tag
4. **Push to ACR**: Image pushed to `agwimages.azurecr.io`
5. **Deploy**: Bicep template updates Container App with new image
6. **Verify**: Workflow checks Container App health status
7. **Notify**: Workflow outputs deployment URLs in GitHub Actions UI

### Automated Prod Deployment (Release Published)

1. **Trigger**: Maintainer publishes a release (e.g., v1.2.0)
2. **Build**: `azure-deploy.yml` builds Docker image with semantic version tag
3. **Push to ACR**: Image pushed to `agwimages.azurecr.io`
4. **Deploy**: Bicep template updates Container App with new image
5. **Verify**: Workflow checks Container App health status
6. **Notify**: Workflow outputs deployment URLs

### Manual Deployment (Workflow Dispatch)

1. **Trigger**: Navigate to Actions → Azure Deployment → Run workflow
2. **Select**: Choose environment (dev/staging/prod) and optional custom tag
3. **Build**: Builds Docker image with specified or commit SHA tag
4. **Deploy**: Same as above
5. **Verify**: Same as above

---

## Image Tag History

All image tags created during this development session:

### Development Tags (Manual)
- `security-guards-tests-pass` - Security guards implementation with all tests passing
- `config-fixed` - Configuration fixes
- `oauth-v1`, `oauth-v2-fixed` - OAuth integration fixes
- `user-menu` - User menu feature
- `ui-enabled`, `admin-api-fix` - UI and admin API fixes
- `verify-config`, `working`, `fixed-final` - Various development iterations

**Note**: Going forward, these manual tags will be replaced by automated tags based on commit SHA (dev) and semantic versioning (prod).

### Automated Tags (Future)
- **Dev**: `<commit-sha>` (e.g., `a1b2c3d`), `YYYYMMDD-HHMMSS`, `latest`
- **Prod**: `<version>` (e.g., `1.2.0`), `YYYYMMDD-HHMMSS`, `latest`

---

## Rollback Procedure

### Using Azure Portal
1. Navigate to Container App → Revisions
2. Select previous healthy revision
3. Click "Activate" and set traffic to 100%

### Using Azure CLI
```bash
# List all revisions
az containerapp revision list \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --query "[].{Name:name, Active:properties.active, Created:properties.createdTime, Image:properties.template.containers[0].image}" \
  -o table

# Activate specific revision
az containerapp revision activate \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --revision <revision-name>

# Deactivate current revision
az containerapp revision deactivate \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --revision <bad-revision-name>
```

### Using GitHub Actions (Manual Dispatch)
1. Go to Actions → Azure Deployment → Run workflow
2. Select the environment
3. Enter the previous working tag (check ACR for available tags)
4. Run workflow

---

## Monitoring Deployments

### GitHub Actions
- View workflow runs at: https://github.com/<org>/<repo>/actions
- Each run shows:
  - Build logs
  - Deployment logs
  - Health check results
  - Deployment URLs

### Azure Portal
- **Container App**: Monitor revisions, logs, metrics
- **Application Insights**: View telemetry, errors, performance
- **Log Analytics**: Query logs across all components

### Azure CLI
```bash
# Follow logs
az containerapp logs show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --follow

# Get Container App URL
az containerapp show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --query "properties.configuration.ingress.fqdn" \
  -o tsv

# Check health status
az containerapp show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --query "{ProvisioningState:properties.provisioningState, RunningState:properties.runningStatus}" \
  -o table
```

---

## Troubleshooting

### Deployment Fails with "Not Authorized"
- Check `AZURE_CREDENTIALS` secret is properly configured
- Verify Service Principal has Contributor role on resource group
- Ensure subscription ID is correct

### Image Build Fails
- Check Dockerfile.acr exists and is valid
- Verify ACR exists and has sufficient permissions
- Check build logs in GitHub Actions workflow run

### Container App Not Starting
- Check container logs: `az containerapp logs show`
- Verify environment variables are set correctly
- Check if OAuth secrets are properly configured in Key Vault
- Verify image was successfully pushed to ACR

### UI Returns 404
- Verify UI was built during Docker image creation
- Check Dockerfile.acr includes UI build steps
- Ensure ingress is configured correctly in Bicep

### OAuth Not Working
- Verify OAuth client IDs and secrets in Key Vault
- Check redirect URIs are configured in OAuth provider
- Verify environment variables are passed to container

---

## Security Best Practices

1. **Secrets Management**:
   - Never commit secrets to Git
   - Use Azure Key Vault for OAuth secrets
   - Use GitHub Secrets for Azure credentials

2. **Image Security**:
   - Scan images for vulnerabilities before deployment
   - Use minimal base images
   - Keep dependencies up to date

3. **Access Control**:
   - Use Managed Identity for Azure resource access
   - Restrict ACR access with role-based access control
   - Limit Service Principal permissions to specific resource groups

4. **Network Security**:
   - Use HTTPS for all endpoints
   - Configure CORS policies appropriately
   - Enable OAuth authentication for UI

---

## Next Steps

1. **Set up GitHub Secrets**: Configure `AZURE_CREDENTIALS` secret
2. **Test Workflow**: Make a small change and push to `main` to trigger dev deployment
3. **Monitor**: Watch the GitHub Actions workflow run and verify deployment
4. **Create Release**: When ready, create a release to deploy to production
5. **Document**: Update this file with any environment-specific configuration
