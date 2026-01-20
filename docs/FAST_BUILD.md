# Fast Build System

The Fast Build system uses an Azure VM with layered Docker caching to achieve **4-7 minute builds** compared to traditional 15-25 minute ACR builds - a **75% speed improvement**.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [First-Time Setup](#first-time-setup)
- [Daily Usage](#daily-usage)
- [Architecture](#architecture)
- [Cost Breakdown](#cost-breakdown)
- [Troubleshooting](#troubleshooting)
- [Comparison](#comparison)

## Overview

The Fast Build system consists of:
- **Azure VM**: Standard_D4s_v3 (4 vCPU, 16GB RAM) running native Linux Docker
- **Layered Builds**: Dependencies compiled once and cached (Dockerfile.base)
- **Automated Authentication**: Managed identity for ACR access (no manual login needed)
- **Auto-Shutdown**: VM stops after 30 minutes of inactivity to minimize costs

### Speed Comparison

| Build Type | First Build | Subsequent Builds | Use Case |
|------------|-------------|-------------------|----------|
| **Fast Build (VM)** | 8-10 min | **3-5 min** | Active development |
| ACR Tasks | 15-20 min | 15-20 min | CI/CD pipelines |
| GitHub Actions | 20-25 min | 20-25 min | Automated deployments |

## Quick Start

For developers who just want to build quickly:

```bash
# Build and deploy to dev environment (4-7 minutes)
./scripts/fast-build.sh dev

# Build and deploy to staging
./scripts/fast-build.sh staging

# Build and deploy to prod
./scripts/fast-build.sh prod
```

That's it! The script handles everything:
- Starting the VM
- Authenticating to ACR
- Building with layered caching
- Pushing to registry
- Deploying to Container Apps

## How It Works

### Layered Build Strategy

Traditional builds recompile everything every time. The Fast Build system uses a two-layer approach:

#### Layer 1: Base Image (Dockerfile.base)
Contains compiled Rust dependencies and build tools:
- Rust 1.91.1 toolchain
- LLVM 17 and 19
- Clang 17 and 19
- All Cargo dependencies pre-compiled

**Build time**: 8-10 minutes (first time only)
**Rebuild trigger**: Only when Cargo.lock changes

#### Layer 2: Application Layer (Dockerfile.app)
Contains only your application code:
- Source files (src/, crates/)
- UI assets
- Configuration

**Build time**: 3-5 minutes (every build)
**Rebuild trigger**: Any code change

### Automated Authentication

The system uses Azure Managed Identity for seamless authentication:

```bash
# Happens automatically inside fast-build.sh
az login --identity                                  # Login with VM identity
az account set --subscription <subscription-id>      # Set subscription
az acr login --name <registry>                       # Login to ACR
```

No manual authentication steps required!

## Prerequisites

Before using the Fast Build system, you need:

1. **Azure CLI** installed and configured on your local machine
2. **SSH access** to Azure VMs (uses your default SSH key)
3. **Access to Azure subscription** `398d3082-298e-4633-9a4a-816c025965ee`
4. **Build VM** already created and configured (one-time setup)

## First-Time Setup

The build VM has already been set up for this project. If you need to create a new one:

### 1. Create and Configure VM

```bash
# Run the setup script (takes 5-10 minutes)
./scripts/setup-build-machine.sh
```

This script:
- Creates Standard_D4s_v3 VM in eastus2
- Installs Docker, Azure CLI, Git
- Configures auto-shutdown (30 min inactivity)
- Sets up managed identity authentication
- Configures ACR access for all environments

### 2. Verify VM Setup

```bash
# Check VM status
az vm show --resource-group mcp-gateway-dev-rg --name agentgateway-builder --query provisioningState

# Check managed identity
az vm identity show --resource-group mcp-gateway-dev-rg --name agentgateway-builder
```

### 3. Grant ACR Access

The VM's managed identity needs AcrPush role on all registries:

```bash
# Get the VM's principal ID
VM_PRINCIPAL_ID=$(az vm identity show \
  --resource-group mcp-gateway-dev-rg \
  --name agentgateway-builder \
  --query principalId -o tsv)

# Grant AcrPush role for each environment
for registry in unitoneagwdevacr unitoneagwstagingacr unitoneagwprodacr; do
  az role assignment create \
    --assignee $VM_PRINCIPAL_ID \
    --role AcrPush \
    --scope /subscriptions/398d3082-298e-4633-9a4a-816c025965ee/resourceGroups/mcp-gateway-dev-rg/providers/Microsoft.ContainerRegistry/registries/$registry
done
```

## Daily Usage

### Building and Deploying

```bash
# Build for development
./scripts/fast-build.sh dev

# Build for staging
./scripts/fast-build.sh staging

# Build for production
./scripts/fast-build.sh prod
```

### What Happens During a Build

```
Step 1: Starting build VM (1-2 minutes)
  ✓ VM started
  ✓ SSH ready

Step 2: Running layered build on VM (3-5 minutes)
  ✓ Code synced to VM
  ✓ Authenticated to ACR (automatic)
  ✓ Checking base image...
  ✓ Base image exists (using cache)
  ✓ Building application (3-5 min)
  ✓ Application image pushed

Step 3: Updating Azure Container App
  ✓ Container App updated
  ✓ New revision deploying...
  ✓ New revision is healthy!

✓ Fast Build Complete!
  Environment: dev
  Build time: 245s
  Total time: 327s
```

### Manual VM Management

If you need to manually control the VM:

```bash
# Start VM
az vm start --resource-group mcp-gateway-dev-rg --name agentgateway-builder

# Stop VM (to save costs)
az vm deallocate --resource-group mcp-gateway-dev-rg --name agentgateway-builder

# Check VM status
az vm get-instance-view \
  --resource-group mcp-gateway-dev-rg \
  --name agentgateway-builder \
  --query instanceView.statuses[1].displayStatus

# SSH into VM for debugging
VM_IP=$(az vm show \
  --resource-group mcp-gateway-dev-rg \
  --name agentgateway-builder \
  --show-details \
  --query publicIps -o tsv)
ssh azureuser@$VM_IP
```

## Architecture

### Directory Structure

```
unitone-agentgateway/
├── scripts/
│   ├── fast-build.sh           # Main orchestration script
│   ├── build-layered.sh        # Layered Docker build
│   ├── setup-build-machine.sh  # VM setup (one-time)
│   └── build-and-deploy.sh     # Traditional ACR build
├── Dockerfile.base             # Base image with dependencies
├── Dockerfile.app              # Application layer
├── Dockerfile.acr              # Full build for ACR Tasks
└── Dockerfile.fast             # Quick test builds
```

### Build Flow

```
Local Machine                    Build VM                         Azure
─────────────                    ────────                         ─────

./scripts/fast-build.sh
    │
    ├─► Start VM ────────────► VM boots (1-2 min)
    │                              │
    ├─► Sync code via rsync ──────►│
    │   (excludes .git, target/)   │
    │                              │
    │                         Authenticate
    │                         az login --identity
    │                         az acr login
    │                              │
    │                         Check base image
    │                         ├─► Exists? Use cache ────► Fast build (3-5 min)
    │                         └─► Missing? Build base ───► Slow build (8-10 min)
    │                              │
    │                         Build application
    │                         docker build -f Dockerfile.app
    │                              │
    │                         Push to ACR ────────────────► unitoneagwdevacr
    │                              │
    ◄─── Build complete ───────────┘
    │
    └─► Deploy to Container Apps ─────────────────────────► Update revision
```

### Cache Strategy

The base image is tagged with a hash of Cargo.lock:

```bash
BASE_TAG="unitoneagwdevacr.azurecr.io/unitone-agentgateway-base:cargo-a1b2c3d4"
```

**When base rebuilds:**
- `Cargo.lock` changes (dependencies added/updated/removed)
- `REBUILD_BASE=true` environment variable set
- Base image doesn't exist in registry

**When base is reused:**
- `Cargo.lock` unchanged
- Base image exists with matching hash
- Build time: 3-5 minutes instead of 8-10 minutes

## Cost Breakdown

### VM Costs

| State | Cost | Usage |
|-------|------|-------|
| **Stopped (deallocated)** | $5/month | Disk storage only |
| **Running** | $0.19/hour | Active building |
| **Typical monthly cost** | $10-20/month | Active development |

### Cost Comparison

Assuming 20 builds per week:

| Build Method | Time per Build | Monthly Time | Monthly Cost |
|--------------|---------------|--------------|--------------|
| **Fast Build** | 4 min | 5.3 hours | $1 VM runtime + $5 storage = **$6** |
| ACR Tasks | 20 min | 26.7 hours | $0 (included in ACR) |

**Fast Build is cheaper and 5x faster!**

### Auto-Shutdown

The VM automatically deallocates after 30 minutes of inactivity:
- No SSH sessions
- No running Docker containers
- Saves costs when not actively building

## Troubleshooting

### Build Fails with "unauthorized" Error

**Symptom**: ACR login fails with authentication error

**Solution**: Verify the VM's managed identity has AcrPush role:

```bash
# Check role assignments
az role assignment list \
  --assignee $(az vm identity show --resource-group mcp-gateway-dev-rg --name agentgateway-builder --query principalId -o tsv) \
  --scope /subscriptions/398d3082-298e-4633-9a4a-816c025965ee
```

### VM Not Starting

**Symptom**: fast-build.sh hangs at "Starting VM"

**Solutions**:

```bash
# Check VM status
az vm get-instance-view \
  --resource-group mcp-gateway-dev-rg \
  --name agentgateway-builder

# If VM is in failed state, restart it
az vm restart --resource-group mcp-gateway-dev-rg --name agentgateway-builder
```

### SSH Connection Timeout

There are two types of SSH timeout issues:

#### Timeout During Initial Connection

**Symptom**: "Waiting for SSH..." timeout after 120 seconds during VM startup

**Causes**:
- Network security group blocking SSH
- VM not fully booted
- SSH key mismatch

**Solutions**:

```bash
# Check NSG rules
az network nsg show \
  --resource-group mcp-gateway-dev-rg \
  --name agentgateway-builder-nsg

# Verify SSH key
ssh-add -l

# Manually test SSH
VM_IP=$(az vm show --resource-group mcp-gateway-dev-rg --name agentgateway-builder --show-details --query publicIps -o tsv)
ssh -v azureuser@$VM_IP
```

#### Timeout During Long Builds

**Symptom**: "Read from remote host ... Operation timed out" or "Broken pipe" during base image build

**Cause**: SSH connection times out during long-running operations (8-10 minute base image compilation)

**Solution**: The fast-build.sh script now includes SSH keepalive options:
- `ServerAliveInterval=60` - Send keepalive every 60 seconds
- `ServerAliveCountMax=120` - Allow up to 120 failed keepalives (2 hours)

This fix is already applied in fast-build.sh:161. If you encounter this issue with an older version:

```bash
# Update fast-build.sh to include keepalive options
git pull origin main
```

### Base Image Build Fails

**Symptom**: Error during base image build (LLVM installation)

**Solution**: This is usually a transient network issue. Retry:

```bash
# Rebuild base image
REBUILD_BASE=true ./scripts/fast-build.sh dev
```

### Git Commit Hash Missing

**Symptom**: Warning about timestamp-based commit hash

**Cause**: The VM doesn't have a .git directory (excluded by rsync)

**This is normal**: The commit hash is captured locally and passed to the VM via environment variable.

### Deployment Hangs at "Waiting for new revision"

**Symptom**: Build succeeds but deployment waits for health check

**Solutions**:

```bash
# Check container logs
az containerapp logs show \
  --name unitone-agw-dev-app \
  --resource-group mcp-gateway-dev-rg \
  --tail 50

# Check revision status
az containerapp revision list \
  --name unitone-agw-dev-app \
  --resource-group mcp-gateway-dev-rg \
  --query "[?properties.active==\`true\`]"
```

## Comparison

### When to Use Fast Build

**Use Fast Build for:**
- Active development and iteration
- Testing configuration changes
- Quick bug fixes
- Multiple builds per day

**Use Traditional ACR Build for:**
- CI/CD pipeline integration
- GitHub Actions workflows
- Automated deployments
- When VM is not available

### Build Method Comparison

| Feature | Fast Build | ACR Tasks | GitHub Actions |
|---------|------------|-----------|----------------|
| **Build Time** | 3-5 min | 15-20 min | 20-25 min |
| **First Build** | 8-10 min | 15-20 min | 20-25 min |
| **Requires VM** | Yes | No | No |
| **Monthly Cost** | $10-20 | Free | Free |
| **Setup Complexity** | Medium | Low | Low |
| **Cache Strategy** | Layered | Single layer | Single layer |
| **Best For** | Development | CI/CD | Automation |

## Advanced Usage

### Local-Only Builds (No Deployment)

For testing Docker builds without pushing to ACR:

```bash
# Build locally, skip push and deployment
LOCAL_ONLY=true ./scripts/build-layered.sh dev
```

### Force Rebuild Base Image

When you need to rebuild the base image (e.g., after upgrading Rust):

```bash
# Force base image rebuild
REBUILD_BASE=true ./scripts/fast-build.sh dev
```

### Skip Container App Deployment

Build and push to ACR, but skip the deployment step:

```bash
SKIP_PUSH=false ./scripts/build-layered.sh dev
# Then manually deploy when ready
az containerapp update \
  --name unitone-agw-dev-app \
  --resource-group mcp-gateway-dev-rg \
  --image unitoneagwdevacr.azurecr.io/unitone-agentgateway:latest
```

### Build with Custom Commit Hash

Override the auto-detected commit hash:

```bash
COMMIT_HASH="custom-tag" ./scripts/build-layered.sh dev
```

## Dockerfile Guide

### When to Use Each Dockerfile

| Dockerfile | Purpose | Build Time | Use Case |
|------------|---------|------------|----------|
| `Dockerfile.base` | Dependency layer | 8-10 min | First time or when Cargo.lock changes |
| `Dockerfile.app` | Application layer | 3-5 min | Every build (uses base image) |
| `Dockerfile.acr` | Full build | 15-20 min | ACR Tasks, GitHub Actions |
| `Dockerfile.fast` | Pre-built binary | <1 min | Quick local testing |

### Dockerfile.base

Contains all dependencies that change infrequently:

```dockerfile
FROM rust:1.91.1-trixie AS base-builder
RUN apt-get update && apt-get install -y clang-17 lld-17
COPY Cargo.toml Cargo.lock ./
RUN cargo build --release --features ui
```

Rebuild only when:
- Rust version changes
- Dependencies added/removed/updated in Cargo.toml
- Build tools need updating

### Dockerfile.app

Uses the base image and adds application code:

```dockerfile
ARG BASE_IMAGE=unitone-agentgateway-base:latest
FROM ${BASE_IMAGE} AS app-builder
COPY src/ ./src/
COPY crates/ ./crates/
RUN cargo build --release --features ui
```

Rebuilds on every code change (3-5 minutes).

## Next Steps

- Review [DEVELOPER_WORKFLOW.md](./DEVELOPER_WORKFLOW.md) for full development workflow
- See [CICD_OPTIONS.md](./CICD_OPTIONS.md) for CI/CD integration options
- Check [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment automation

## Support

For issues or questions:
- Check the troubleshooting section above
- Review VM logs: `ssh azureuser@<VM_IP>` and check `/home/azureuser/workspace/`
- Contact the DevOps team
