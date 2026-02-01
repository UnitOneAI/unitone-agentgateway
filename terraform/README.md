# UnitOne AgentGateway - Terraform Module

> ⚠️ **Development & Testing Only** - This terraform is for quick dev/testing.
> For production, copy to your infrastructure repo with proper access controls.
> See [Production Deployment](#production-deployment) section below.

Deploy AgentGateway to Azure Container Apps with this Terraform module.

## Resources Created

- **Azure Container Registry (ACR)** - Stores Docker images
- **Azure Container Apps** - Runs the gateway
- **Container App Environment** - Isolated compute environment
- **Key Vault** - Stores OAuth secrets
- **Log Analytics Workspace** - Centralized logging
- **Application Insights** - APM and monitoring
- **Storage Account** (optional) - Config file mounting

## Quick Start

### 1. Create Resource Group

```bash
az group create --name agentgateway-rg --location eastus2
```

### 2. Initialize Terraform

```bash
cd terraform
terraform init
```

### 3. Create terraform.tfvars

```hcl
environment         = "dev"
resource_group_name = "agentgateway-rg"
location            = "eastus2"
base_name           = "myagw"

# Optional: Enable anonymous access for testing
allow_anonymous_access = true

# Optional: OAuth configuration
# microsoft_client_id     = "your-client-id"
# microsoft_client_secret = "your-client-secret"
```

### 4. Deploy

```bash
terraform plan
terraform apply
```

### 5. Build and Push Image

After Terraform creates the ACR, build and push using one of these methods:

```bash
# Get ACR name from Terraform output
ACR_NAME=$(terraform output -raw acr_name)
cd ..

# Option A: ACR Cloud Build (no local Docker needed)
az acr build \
  --registry $ACR_NAME \
  --image agentgateway:latest \
  --file Dockerfile.acr \
  --platform linux/amd64 \
  .

# Option B: VM-Based Build (faster iteration, requires Docker)
./scripts/build-on-vm.sh --acr-name $ACR_NAME

# Option C: ACR Tasks (automatic on git push - configure in terraform.tfvars)
```

### 6. Access the Gateway

```bash
# Get URLs from Terraform output
terraform output ui_url
terraform output mcp_endpoint
```

## Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `environment` | Environment name (dev/staging/prod) | - | Yes |
| `resource_group_name` | Azure resource group name | - | Yes |
| `location` | Azure region | `eastus2` | No |
| `base_name` | Resource name prefix | `agw` | No |
| `deployment_stamp` | Unique identifier for multiple deployments | `""` | No |
| `image_tag` | Docker image tag | `latest` | No |
| `allow_anonymous_access` | Allow unauthenticated access | `false` | No |
| `enable_config_mount` | Mount config from Azure Files | `false` | No |
| `github_repo_url` | GitHub repo for CI/CD | `""` | No |
| `github_pat` | GitHub PAT for CI/CD | `""` | No |
| `client_certificate_mode` | mTLS mode: ignore/accept/require | `ignore` | No |
| `enable_sticky_sessions` | Enable sticky sessions for MCP session affinity | `true` | No |

## Outputs

| Output | Description |
|--------|-------------|
| `container_app_url` | Gateway URL |
| `ui_url` | Admin UI URL |
| `mcp_endpoint` | MCP API endpoint |
| `acr_login_server` | ACR login server |
| `acr_name` | ACR name |
| `build_command` | Command to build image |
| `deploy_command` | Command to deploy new image |
| `logs_command` | Command to view logs |
| `sticky_sessions_enabled` | Whether sticky sessions are enabled |
| `sticky_sessions_verify_command` | Command to verify sticky sessions |

## Sticky Sessions (Multi-Replica)

When running multiple replicas, sticky sessions ensure MCP clients always connect to the same replica. This is critical because MCP sessions are stored in-memory.

Sticky sessions are **enabled by default**. To disable:

```hcl
enable_sticky_sessions = false
```

See [docs/STICKY_SESSIONS.md](../docs/STICKY_SESSIONS.md) for details.

## CI/CD Automation

Enable automated builds on git push:

```hcl
github_repo_url = "https://github.com/YOUR_ORG/agentgateway-azure.git"
github_pat      = "ghp_xxxxxxxxxxxx"  # GitHub PAT with repo access
```

This creates an ACR Task that:
1. Triggers on commits to `main` branch
2. Builds the Docker image
3. Pushes to ACR with `latest` and unique tags

## Config Hot-Reload

Mount config from Azure Files for hot-reload without container restart:

```hcl
enable_config_mount = true
config_file_path    = "../examples/config.yaml"
```

Update config at runtime:
```bash
az storage file upload \
  --account-name $(terraform output -raw config_storage_account) \
  --share-name agentgateway-config \
  --source ./config.yaml \
  --path config.yaml
```

## OAuth Authentication

Configure Azure Easy Auth with OAuth providers:

```hcl
configure_auth          = true
allow_anonymous_access  = false

microsoft_client_id     = "your-azure-ad-client-id"
microsoft_client_secret = "your-azure-ad-client-secret"

google_client_id        = "your-google-client-id"
google_client_secret    = "your-google-client-secret"
```

## Multiple Environments

Deploy to multiple environments:

```bash
# Dev
terraform workspace new dev
terraform apply -var="environment=dev"

# Staging
terraform workspace new staging
terraform apply -var="environment=staging"

# Production
terraform workspace new prod
terraform apply -var="environment=prod"
```

## Multiple Deployments (Same Environment)

Use `deployment_stamp` to run multiple instances in the same environment:

```bash
# Primary production deployment
terraform workspace new prod-primary
terraform apply -var="environment=prod" -var="deployment_stamp=primary"

# Secondary production deployment (for testing)
terraform workspace new prod-test
terraform apply -var="environment=prod" -var="deployment_stamp=test"
```

This creates isolated resources:
- `agw-prod-primary-app` and `agw-prod-test-app` (Container Apps)
- `agwprodprimaryacr` and `agwprodtestacr` (Container Registries)
- Each with its own Key Vault, Log Analytics, etc.

## Cleanup

```bash
terraform destroy
```

## Scopes

Scopes allow switching between environments without reconfiguring credentials:

```bash
./agw setup                    # Guided setup wizard
./agw scope list               # List available scopes
./agw scope set dev            # Switch to dev
./agw scope set prod           # Switch to prod
```

Scopes are stored in `terraform/scopes/`:
- `global/` - Team-shared scopes (checked into git)
- `users/<username>/` - Personal overrides

See [scopes/README.md](./scopes/README.md) for details.

## Production Deployment

For production deployments, we recommend:

1. **Copy terraform to your infrastructure repo** with proper access controls:
   ```
   your-infra-repo/
   ├── environments/
   │   ├── dev/agentgateway/
   │   ├── staging/agentgateway/
   │   └── prod/agentgateway/    # Restricted access
   ```

2. **Apply with CI/CD** using your organization's pipeline

3. **Import scopes** back to the agentgateway repo:
   ```bash
   ./agw scope import --name prod --global --from /path/to/infra/prod/agentgateway
   git add terraform/scopes/global/prod.env
   git commit -m "Add prod scope"
   ```

This separation ensures:
- Production credentials stay in a separate, access-controlled repo
- The agentgateway repo stays safe for open collaboration
- Team members can switch scopes easily with `./agw scope set prod`
