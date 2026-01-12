# Local Build and Deployment Guide

This guide explains how to build and deploy UnitOne AgentGateway using **local Docker builds** instead of automated ACR Task builds.

## Why Local Builds?

- **Full control** over build process and timing
- **Faster iteration** for development and testing
- **No GitHub PAT required** - no need to expose GitHub credentials to Azure
- **Build once, deploy anywhere** - test locally before pushing to registry
- **Cost savings** - ACR build minutes are free, but this gives more control

## Prerequisites

1. **Docker Desktop** installed and running
2. **Azure CLI** installed and authenticated:
   ```bash
   az login
   az account set --subscription <YOUR_SUBSCRIPTION_ID>
   ```
3. **Git** for version tagging

## Quick Start

### 1. Build and Push Latest

```bash
./build-and-push.sh
```

This will:
- Build the Docker image locally
- Tag it as `latest` and with the current git commit hash
- Log in to Azure Container Registry
- Push the image to ACR

### 2. Build with Custom Tag

```bash
./build-and-push.sh --tag v1.2.3
```

### 3. Build Without Pushing (Local Testing)

```bash
./build-and-push.sh --no-push
```

Then test locally:
```bash
docker run -p 8080:8080 unitoneagwdevacr.azurecr.io/unitone-agentgateway:latest
```

### 4. Deploy to Azure Container App

After building and pushing:

```bash
az containerapp update \
  --name unitone-agw-dev-app \
  --resource-group mcp-gateway-dev-rg \
  --image unitoneagwdevacr.azurecr.io/unitone-agentgateway:latest
```

## Build Script Options

```bash
./build-and-push.sh [OPTIONS]

Options:
  --tag TAG          Image tag (default: latest)
  --registry NAME    ACR registry name (default: unitoneagwdevacr)
  --platform ARCH    Platform (default: linux/amd64, also: linux/arm64)
  --profile PROFILE  Build profile: release or debug (default: release)
  --no-cache         Build without Docker cache
  --no-push          Build only, don't push to registry
  -h, --help         Show help message
```

## Examples

### Development Workflow

```bash
# 1. Make code changes
vim agentgateway/src/...

# 2. Build and test locally
./build-and-push.sh --tag dev-test --no-push
docker run -p 8080:8080 unitoneagwdevacr.azurecr.io/unitone-agentgateway:dev-test

# 3. When ready, push to ACR
./build-and-push.sh --tag dev-test

# 4. Deploy to dev environment
az containerapp update \
  --name unitone-agw-dev-app \
  --resource-group mcp-gateway-dev-rg \
  --image unitoneagwdevacr.azurecr.io/unitone-agentgateway:dev-test
```

### Production Release

```bash
# 1. Tag the release
git tag v1.2.3
git push origin v1.2.3

# 2. Build production image
./build-and-push.sh --tag v1.2.3 --profile release

# 3. Also tag as latest
docker tag \
  unitoneagwdevacr.azurecr.io/unitone-agentgateway:v1.2.3 \
  unitoneagwdevacr.azurecr.io/unitone-agentgateway:latest
docker push unitoneagwdevacr.azurecr.io/unitone-agentgateway:latest

# 4. Deploy to production
az containerapp update \
  --name unitone-agw-prod-app \
  --resource-group mcp-gateway-prod-rg \
  --image unitoneagwdevacr.azurecr.io/unitone-agentgateway:v1.2.3
```

### Multi-Platform Builds

```bash
# Build for ARM64 (Apple Silicon, ARM servers)
./build-and-push.sh --platform linux/arm64 --tag latest-arm64

# Build for AMD64 (Intel/AMD servers, Azure)
./build-and-push.sh --platform linux/amd64 --tag latest-amd64
```

## Build Process Details

The build script uses `Dockerfile.acr` which:

1. **Builds UI** (Node.js)
   - Installs npm dependencies
   - Runs `npm run build` to create production bundle

2. **Builds Rust Binary**
   - Uses Rust 1.91.1
   - Compiles with `--features ui` to embed the UI
   - Creates optimized release binary

3. **Creates Final Image**
   - Based on `gcr.io/distroless/cc-debian13` (minimal, secure base)
   - Includes only the binary and config placeholder
   - Total image size: ~50MB

4. **Tags and Pushes**
   - Tags with specified tag (default: `latest`)
   - Tags with git commit hash (e.g., `abc1234`)
   - Pushes both tags to ACR

## Configuration Management

The build includes a placeholder `azure-config.yaml`. The actual configuration should be:

- **Mounted at runtime** via Azure File Share (recommended for Terraform-managed deployments)
- **Provided via environment variables** for dynamic configuration
- **Baked into the image** by editing `azure-config.yaml` before building (not recommended)

## Troubleshooting

### Build Fails: "azure-config.yaml not found"

The script auto-creates a placeholder. If you need a real config:

```bash
cp azure-config.example.yaml azure-config.yaml
# Edit as needed
./build-and-push.sh
```

### Push Fails: "unauthorized: authentication required"

Log in to ACR:

```bash
az acr login --name unitoneagwdevacr
```

### Docker Build is Slow

Use `--no-cache` sparingly. Docker layer caching significantly speeds up builds.

For faster builds:
- Ensure Docker Desktop has sufficient resources (CPUs, memory)
- Use `--profile debug` for faster compilation (no optimizations)

### Container App Doesn't Update

Check if the image was actually pulled:

```bash
# Check current image
az containerapp show \
  --name unitone-agw-dev-app \
  --resource-group mcp-gateway-dev-rg \
  --query "properties.template.containers[0].image"

# Check revision status
az containerapp revision list \
  --name unitone-agw-dev-app \
  --resource-group mcp-gateway-dev-rg \
  --query "[].{Name:name, Active:properties.active, Image:properties.template.containers[0].image}"
```

Force a new revision:

```bash
az containerapp update \
  --name unitone-agw-dev-app \
  --resource-group mcp-gateway-dev-rg \
  --image unitoneagwdevacr.azurecr.io/unitone-agentgateway:latest \
  --revision-suffix "$(date +%s)"
```

## Comparison: Local Builds vs ACR Tasks

| Feature | Local Builds | ACR Tasks |
|---------|-------------|-----------|
| **Control** | Full control over timing | Automatic on git push |
| **Speed** | Fast (local Docker cache) | Slower (no local cache) |
| **Cost** | Free (uses local CPU) | $0.0001/second build time |
| **Testing** | Test before pushing | Pushes immediately |
| **GitHub PAT** | Not required | Required |
| **Automation** | Manual (run script) | Fully automated |
| **Best For** | Development, testing | Production CI/CD |

## Terraform Integration

The Terraform configuration in the separate `terraform` repository has been updated to disable ACR Task automation:

```hcl
# terraform/environments/dev/agentgateway/terraform.tfvars
enable_auto_deployment = false
github_pat = ""
```

To apply the Terraform changes:

```bash
cd /path/to/terraform/repo/environments/dev/agentgateway
terraform plan
terraform apply
```

This will:
- **Destroy** the existing ACR Task resource
- **Disable** automatic builds on git push
- **Keep** all other infrastructure (ACR, Container App, Key Vault, etc.)

## Re-enabling ACR Tasks (If Needed)

If you want to switch back to automated builds:

1. Update Terraform variables:
   ```hcl
   enable_auto_deployment = true
   github_pat = "ghp_your_token_here"
   ```

2. Apply Terraform:
   ```bash
   terraform apply
   ```

3. ACR Task will automatically build on next git push to `main`

## Next Steps

1. **Update deployment documentation** in the `terraform` repository
2. **Test the local build process** with a real deployment
3. **Update CI/CD documentation** to reflect the local build workflow
4. **Consider GitHub Actions** for automated testing (separate from builds)

## See Also

- `build-and-push.sh` - The build script
- `Dockerfile.acr` - The Dockerfile used for building
- `../terraform/modules/azure/agentgateway/ci_cd.tf` - Terraform CI/CD configuration
