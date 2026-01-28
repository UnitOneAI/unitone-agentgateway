# Build Options

UnitOne AgentGateway supports three build methods to suit different workflows.

## Quick Comparison

| Method | Local Docker | Best For | Build Location |
|--------|--------------|----------|----------------|
| ACR Cloud Build | No | Quick deploys, no Docker setup | Azure cloud |
| VM-Based Build | Yes | Fast iteration, CI/CD pipelines | Your VM/server |
| ACR Tasks | No | Automatic deploys on git push | Azure cloud |

## Option A: ACR Cloud Build

Build in Azure Container Registry without local Docker. Context is uploaded to Azure.

```bash
ACR_NAME=$(cd terraform && terraform output -raw acr_name)
az acr build --registry $ACR_NAME --image unitone-agentgateway:latest -f Dockerfile.acr .
```

**Pros:**
- No local Docker required
- Works from any machine with Azure CLI
- Simple one-liner

**Cons:**
- Slower (uploads context to Azure each time)
- Requires internet bandwidth for context upload

## Option B: VM-Based Build

Build locally on a VM or build server, then push to ACR.

### Setup Build VM

```bash
# On a fresh Ubuntu/Debian VM
curl -fsSL https://raw.githubusercontent.com/UnitOneAI/unitone-agentgateway/main/scripts/setup-build-vm.sh | bash

# Log out and back in for docker group, then:
az login
```

### Build and Push

```bash
# Basic build
./scripts/build-on-vm.sh --acr-name myacr

# Build with specific tag
./scripts/build-on-vm.sh --acr-name myacr --tag v1.2.3

# Build and deploy in one command
./scripts/build-on-vm.sh --acr-name myacr \
  --deploy \
  --resource-group my-rg \
  --app-name my-app

# Build for ARM64
./scripts/build-on-vm.sh --acr-name myacr --platform linux/arm64

# Build without cache (fresh build)
./scripts/build-on-vm.sh --acr-name myacr --no-cache
```

**Pros:**
- Fastest iteration (Docker layer caching)
- Full control over build environment
- Works in air-gapped environments (once image is cached)
- Good for CI/CD pipelines (GitHub Actions, Azure DevOps)

**Cons:**
- Requires Docker on build machine
- Need to manage build VM

### Recommended VM Specs

| Environment | VM Size | Disk |
|-------------|---------|------|
| Dev/Test | Standard_D2s_v3 (2 vCPU, 8GB) | 64GB |
| Production | Standard_D4s_v3 (4 vCPU, 16GB) | 128GB |

## Option C: ACR Tasks (Automatic)

Automatically build and push when you push to GitHub.

### Configure

In `terraform/terraform.tfvars`:

```hcl
github_repo_url = "https://github.com/YOUR_ORG/unitone-agentgateway.git"
github_pat      = "ghp_xxxxxxxxxxxx"  # GitHub PAT with repo access
```

Or configure during `./setup.sh`.

### How It Works

1. You push to `main` branch
2. ACR Task detects the push via webhook
3. Build runs in Azure
4. New image pushed to ACR with `latest` and commit SHA tags

### Trigger Manual Build

```bash
az acr task run --name agentgateway-build-task --registry $ACR_NAME
```

**Pros:**
- Fully automated
- No manual builds needed
- Consistent builds in Azure environment

**Cons:**
- Requires GitHub PAT
- Build triggered on every push (can be noisy)
- Slightly slower than cached VM builds

## CI/CD Integration

### GitHub Actions

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Build and Push
        run: |
          ./scripts/build-on-vm.sh \
            --acr-name ${{ secrets.ACR_NAME }} \
            --tag ${{ github.sha }}
```

### Azure DevOps

```yaml
steps:
  - checkout: self
    submodules: recursive

  - task: AzureCLI@2
    inputs:
      azureSubscription: 'your-subscription'
      scriptType: 'bash'
      scriptLocation: 'inlineScript'
      inlineScript: |
        ./scripts/build-on-vm.sh \
          --acr-name $(ACR_NAME) \
          --tag $(Build.SourceVersion)
```

## Multiple Deployments

Use deployment stamps to build different versions:

```bash
# Build for production primary
./scripts/build-on-vm.sh --acr-name myacr --tag prod-primary

# Build for production test
./scripts/build-on-vm.sh --acr-name myacr --tag prod-test
```

Each stamp can have its own ACR if configured with `deployment_stamp` in terraform.
