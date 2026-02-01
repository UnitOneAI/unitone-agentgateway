# Production Setup Guide

This guide walks you through deploying AgentGateway to Azure for production use.

## Overview

The production deployment consists of:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Azure                                    │
│                                                                  │
│  ┌──────────────┐    ┌──────────────────────────────────────┐   │
│  │     ACR      │    │         Azure Container App          │   │
│  │              │    │                                      │   │
│  │  unitone-    │───▶│  AgentGateway                        │   │
│  │  agentgateway│    │    - Routes MCP requests             │   │
│  │              │    │    - Security guards enabled         │   │
│  └──────────────┘    │    - UI dashboard                    │   │
│                      │                                      │   │
│                      └──────────────┬───────────────────────┘   │
│                                     │                            │
│                                     ▼                            │
│                      ┌──────────────────────────────────────┐   │
│                      │      Your MCP Servers                │   │
│                      │  (internal or external)              │   │
│                      └──────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

| Requirement | Purpose |
|-------------|---------|
| Azure subscription | Host the infrastructure |
| Azure CLI | Deploy and manage resources |
| Terraform (v1.0+) | Provision infrastructure |
| Git | Clone repository |

### Verify Prerequisites

```bash
# Azure CLI
az --version
az login
az account show  # Verify correct subscription

# Terraform
terraform --version

# Git
git --version
```

## Quick Start with CLI (Recommended)

The `./agw` CLI guides you through the entire process.

### Step 1: Clone and Setup

```bash
git clone --recursive https://github.com/UnitOneAI/unitone-agentgateway.git
cd unitone-agentgateway
./agw setup
```

The wizard will:
1. Check prerequisites (Azure CLI, Terraform)
2. Ask for deployment configuration
3. Create Terraform variable files
4. Provision Azure infrastructure

### Step 2: Build and Deploy

```bash
./agw build --deploy
```

### Step 3: Configure Authentication (Optional)

```bash
# Get callback URLs for OAuth app registration
./agw auth urls

# Configure OAuth providers
./agw auth setup
```

### Step 4: Verify Deployment

```bash
./agw status
```

### Step 5: Save Scope for Future Use

```bash
# Import terraform config as a named scope
./agw scope import --name prod

# Later, switch between scopes
./agw scope set dev
./agw scope set prod
```

## Manual Setup (Step by Step)

If you prefer manual control, follow these steps:

### Step 1: Clone Repository

```bash
git clone --recursive https://github.com/UnitOneAI/unitone-agentgateway.git
cd unitone-agentgateway
```

### Step 2: Configure Terraform Variables

```bash
cd terraform

# Create your variables file
cat > terraform.tfvars << 'EOF'
# Required
resource_group_name = "agentgateway-prod-rg"
location            = "eastus"
environment         = "prod"

# Optional: Custom naming
container_app_name  = "agentgateway"
acr_name            = "mycompanyagwacr"  # Must be globally unique

# Optional: Scaling
min_replicas = 1
max_replicas = 10

# Optional: GitHub integration for auto-deploy
# github_repo_url = "https://github.com/YOUR_ORG/unitone-agentgateway.git"
# github_pat      = "ghp_xxxxxxxxxxxx"
EOF
```

### Step 3: Provision Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Apply (creates Azure resources)
terraform apply
```

This creates:
- Resource Group
- Azure Container Registry (ACR)
- Azure Container App Environment
- Azure Container App
- Managed Identity (for ACR access)

### Step 4: Build and Push Container Image

```bash
# Get ACR name from Terraform output
ACR_NAME=$(terraform output -raw acr_name)

# Login to ACR
az acr login --name $ACR_NAME

# Build and push (from repo root)
cd ..
az acr build \
  --registry $ACR_NAME \
  --image unitone-agentgateway:latest \
  --file Dockerfile.acr \
  .
```

### Step 5: Deploy to Container App

```bash
# Get values from Terraform
ACR_NAME=$(cd terraform && terraform output -raw acr_name)
APP_NAME=$(cd terraform && terraform output -raw container_app_name)
RG_NAME=$(cd terraform && terraform output -raw resource_group_name)

# Update container app with new image
az containerapp update \
  --name $APP_NAME \
  --resource-group $RG_NAME \
  --image ${ACR_NAME}.azurecr.io/unitone-agentgateway:latest
```

### Step 6: Get Your Gateway URL

```bash
az containerapp show \
  --name $APP_NAME \
  --resource-group $RG_NAME \
  --query properties.configuration.ingress.fqdn \
  --output tsv
```

## Configuration

### Default Configuration

The container ships with a default configuration at `/app/config.yaml`:

```yaml
binds:
- port: 8080
  listeners:
  - hostname: "*"
    name: default
    protocol: http
    routes:
    # UI Dashboard
    - name: ui-route
      matches:
      - path:
          pathPrefix: /ui
      backends:
      - host: 127.0.0.1:15000

    # Your MCP routes go here
    - name: my-mcp-server
      matches:
      - path:
          pathPrefix: /mcp
      backends:
      - mcp:
          targets:
          - name: my-server
            mcp:
              host: https://your-mcp-server.com/mcp
          statefulMode: stateful
      policies:
        securityGuards:
          toolPoisoning:
            enabled: true
          rugPull:
            enabled: true
            scope: session
```

### Custom Configuration

To use a custom configuration:

#### Option A: Mount Config File (Recommended)

1. Create your config file locally
2. Mount it when deploying:

```bash
# Store config in Azure Files or Blob Storage
# Then mount to /app/mounted-config/config.yaml

az containerapp update \
  --name $APP_NAME \
  --resource-group $RG_NAME \
  --set-env-vars "CONFIG_PATH=/app/mounted-config/config.yaml"
```

#### Option B: Build Custom Image

1. Create your config file:
```bash
cp examples/config.yaml my-config.yaml
# Edit my-config.yaml with your settings
```

2. Build with custom config:
```bash
# The Dockerfile.acr copies azure-config.yaml as the default
# Edit azure-config.yaml before building
az acr build \
  --registry $ACR_NAME \
  --image unitone-agentgateway:custom \
  --file Dockerfile.acr \
  .
```

### Security Guards Configuration

Enable security guards on any MCP route:

```yaml
policies:
  securityGuards:
    # Detects malicious instructions in tool descriptions
    toolPoisoning:
      enabled: true

    # Detects tool changes after initial connection
    rugPull:
      enabled: true
      scope: session  # or "global" for cross-session detection
```

## Authentication (Optional)

### Using the CLI (Recommended)

The easiest way to configure authentication:

```bash
# Get callback URLs for registering OAuth apps
./agw auth urls

# Interactive setup for Microsoft/Google/GitHub
./agw auth setup

# Require authentication (block anonymous access)
./agw auth enable

# Check current auth status
./agw auth
```

### Manual Azure Easy Auth

If you prefer manual configuration:

```bash
# Enable Easy Auth with Azure AD
az containerapp auth microsoft update \
  --name $APP_NAME \
  --resource-group $RG_NAME \
  --client-id YOUR_APP_CLIENT_ID \
  --client-secret YOUR_APP_CLIENT_SECRET \
  --issuer https://login.microsoftonline.com/YOUR_TENANT_ID/v2.0 \
  --yes
```

See [AUTHENTICATION.md](AUTHENTICATION.md) for detailed auth setup.

## CI/CD Setup

### GitHub Actions (Automatic)

The repository includes a GitHub Actions workflow that:
- Runs E2E tests on every push/PR
- Builds and deploys to Azure on push to `main`

Required GitHub Secrets:

| Secret | Description |
|--------|-------------|
| `AZURE_CREDENTIALS` | Service principal credentials (JSON) |
| `ACR_NAME` | Your ACR name (e.g., `mycompanyagwacr`) |
| `RESOURCE_GROUP` | Resource group name |
| `CONTAINER_APP_NAME` | Container app name |

#### Create Service Principal

```bash
# Create service principal with Contributor role
az ad sp create-for-rbac \
  --name "github-agentgateway-deploy" \
  --role contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RG \
  --sdk-auth

# Copy the JSON output to GitHub secret AZURE_CREDENTIALS
```

### Manual Deployment

For manual deployments, use the VM build script:

```bash
./scripts/build-on-vm.sh \
  --acr-name $ACR_NAME \
  --deploy \
  --resource-group $RG_NAME \
  --app-name $APP_NAME
```

## Monitoring

### View Logs

```bash
# Using the CLI (recommended)
./agw logs              # View recent logs
./agw logs --follow     # Stream live logs

# Or using Azure CLI directly
az containerapp logs show \
  --name $APP_NAME \
  --resource-group $RG_NAME \
  --tail 100
```

### Check Health

```bash
# Using the CLI
./agw status

# Or using curl directly
curl https://YOUR_URL/health
curl https://YOUR_URL/ready
```

### Metrics

View metrics in Azure Portal:
1. Navigate to your Container App
2. Click "Metrics" in the left menu
3. Select metrics like "Requests", "CPU Usage", "Memory Usage"

## Scaling

### Important: Enable Sticky Sessions First

When running multiple replicas, you **must** enable sticky sessions for MCP session affinity. MCP sessions are stored in-memory, so requests must be routed to the same replica.

```bash
# Enable sticky sessions (required for multi-replica)
az containerapp ingress sticky-sessions set \
  --name $APP_NAME \
  --resource-group $RG_NAME \
  --affinity sticky
```

If using Terraform, sticky sessions are enabled by default (`enable_sticky_sessions = true`).

See [STICKY_SESSIONS.md](STICKY_SESSIONS.md) for details.

### Configure Auto-scaling

```bash
az containerapp update \
  --name $APP_NAME \
  --resource-group $RG_NAME \
  --min-replicas 2 \
  --max-replicas 10 \
  --scale-rule-name http-scaling \
  --scale-rule-type http \
  --scale-rule-http-concurrency 100
```

### Manual Scaling

```bash
# Scale to specific replica count
az containerapp revision copy \
  --name $APP_NAME \
  --resource-group $RG_NAME \
  --min-replicas 5 \
  --max-replicas 5
```

## Updating

### Update to Latest Version

```bash
# Pull latest code
git pull origin main
git submodule update --init --recursive

# Rebuild and deploy using CLI
./agw build --deploy

# Or using Azure CLI directly
az acr build \
  --registry $ACR_NAME \
  --image unitone-agentgateway:latest \
  --file Dockerfile.acr \
  .
```

### Rollback

```bash
# List revisions
az containerapp revision list \
  --name $APP_NAME \
  --resource-group $RG_NAME \
  --output table

# Activate previous revision
az containerapp revision activate \
  --name $APP_NAME \
  --resource-group $RG_NAME \
  --revision REVISION_NAME
```

## Troubleshooting

### Container Won't Start

```bash
# Check container logs
az containerapp logs show \
  --name $APP_NAME \
  --resource-group $RG_NAME \
  --tail 200

# Check revision status
az containerapp revision show \
  --name $APP_NAME \
  --resource-group $RG_NAME \
  --revision LATEST \
  --query properties.runningState
```

### ACR Pull Errors

```bash
# Verify managed identity has ACR pull access
az role assignment list \
  --scope /subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.ContainerRegistry/registries/ACR_NAME \
  --output table

# If missing, add AcrPull role
az role assignment create \
  --assignee MANAGED_IDENTITY_ID \
  --role AcrPull \
  --scope /subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.ContainerRegistry/registries/ACR_NAME
```

### Configuration Issues

```bash
# Verify config is mounted correctly
az containerapp exec \
  --name $APP_NAME \
  --resource-group $RG_NAME \
  --command "cat /app/config.yaml"
```

## Cost Optimization

| Resource | Estimated Monthly Cost |
|----------|----------------------|
| Container App (1 vCPU, 2GB) | ~$50 |
| ACR (Basic tier) | ~$5 |
| Container App Environment | ~$0 (shared) |

Tips:
- Use `--min-replicas 0` for dev/test environments
- Scale down during off-hours with scheduled scaling
- Use Basic ACR tier unless you need geo-replication

## Security Checklist

- [ ] Enable Azure AD authentication (Easy Auth)
- [ ] Configure HTTPS only (default)
- [ ] Enable security guards (toolPoisoning, rugPull)
- [ ] Use managed identity for ACR access (no passwords)
- [ ] Configure network restrictions if needed
- [ ] Enable Azure Monitor for logging
- [ ] Set up alerts for errors/failures
- [ ] Enable sticky sessions if running multiple replicas

## Next Steps

1. **Configure your MCP servers** - Edit the gateway config to route to your actual MCP servers
2. **Enable authentication** - See [AUTHENTICATION.md](AUTHENTICATION.md)
3. **Set up CI/CD** - Configure GitHub Actions for automated deployments
4. **Monitor** - Set up Azure Monitor alerts for production visibility
