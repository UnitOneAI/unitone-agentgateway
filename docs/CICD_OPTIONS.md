# CI/CD Options for UnitOne AgentGateway

This document explains the available CI/CD options for automating builds and deployments.

## Overview

There are **three build and deployment approaches** available for UnitOne AgentGateway:

1. **Fast Build (VM-based)** (Recommended for development - ACTIVE)
2. **GitHub Actions** (Primary CI/CD - ACTIVE)
3. **Azure Container Registry (ACR) Tasks** (Alternative - AVAILABLE)

## Option 1: Fast Build - VM-Based (RECOMMENDED FOR DEVELOPMENT)

### Status
**✅ ACTIVE** - Currently deployed and actively used for development

### Overview
VM-based fast build system using layered Docker caching for **4-7 minute builds** compared to traditional 15-25 minute builds.

### Location
- Main script: `./scripts/fast-build.sh`
- Layered build: `./scripts/build-layered.sh`
- VM setup: `./scripts/setup-build-machine.sh`
- Documentation: [FAST_BUILD.md](FAST_BUILD.md)

### How It Works
```
Local Machine → Azure VM (Standard_D4s_v3) → Layered Docker Build → ACR → Container Apps
```

1. Starts build VM automatically (1-2 minutes)
2. Syncs code via rsync (excludes .git, target/)
3. Authenticates to ACR using managed identity (automatic)
4. Builds application layer (3-5 minutes) or base layer (8-10 minutes first time)
5. Pushes to ACR and deploys
6. VM auto-shuts down after 30 minutes of inactivity

### Triggers
```bash
# Manual trigger - build and deploy
./scripts/fast-build.sh dev       # Deploy to dev (4-7 min)
./scripts/fast-build.sh staging   # Deploy to staging
./scripts/fast-build.sh prod      # Deploy to prod
```

### Key Features
- ✅ **75% faster** than traditional ACR builds (4-7 min vs 15-25 min)
- ✅ **Layered caching**: Dependencies compiled once (Dockerfile.base), reused for all builds
- ✅ **Automated authentication**: Managed identity, no manual login required
- ✅ **Multi-environment support**: dev, staging, prod
- ✅ **Cost-effective**: VM auto-stops, ~$10-20/month typical usage
- ✅ **Native Linux Docker**: Faster than macOS Docker Desktop

### Advantages
- **Fastest iteration speed** for active development
- Layered build strategy: 3-5 min for code changes, 8-10 min first time
- Native Linux Docker (no macOS virtualization overhead)
- Automatic VM lifecycle management
- Cost-effective with auto-shutdown

### When to Use
- ✅ Active development and rapid iteration
- ✅ Testing configuration changes quickly
- ✅ Multiple builds per day
- ✅ Quick bug fixes and feature development

### Cost
| State | Cost | Usage |
|-------|------|-------|
| **Stopped (deallocated)** | $5/month | Disk storage only |
| **Running** | $0.19/hour | Active building |
| **Typical monthly** | $10-20 | Active development |

For complete documentation, see [FAST_BUILD.md](FAST_BUILD.md).

---

## Option 2: GitHub Actions (PRIMARY CI/CD)

### Status
**✅ ACTIVE** - Currently deployed and operational

### Location
`.github/workflows/azure-deploy.yml` in `unitone-agentgateway` repository

### How It Works
```
Push to main → GitHub Actions → Build Docker image → Push to ACR → Deploy to Azure Container Apps
```

### Triggers
- **Push to `main` branch** → Deploys to **dev**
- **Pull request to `main`** → Build only (no deployment)
- **Manual workflow dispatch** → Deploy to any environment (dev/staging/prod)

### Workflow Details
```yaml
on:
  push:
    branches: [main]      # Auto-deploy to dev
  pull_request:
    branches: [main]      # Build only
  workflow_dispatch:      # Manual trigger
```

### Key Features
- ✅ Full CI/CD automation
- ✅ Multi-environment support (dev/staging/prod)
- ✅ Automatic submodule initialization (`submodules: 'recursive'`)
- ✅ Multi-tag strategy (commit SHA, timestamp, `latest`)
- ✅ Deployment verification and health checks
- ✅ Integrated with GitHub UI (easy monitoring)

### Advantages
- Centralized CI/CD in GitHub (where code lives)
- Easy to monitor via GitHub Actions UI
- Supports complex workflows with multiple steps
- Can run tests, linting, validation before deployment
- Free for public repositories, generous limits for private

## Alternative: ACR Tasks (OPTIONAL)

### Status
**⚠️ AVAILABLE BUT NOT DEPLOYED** - Terraform code exists but not applied

### Location
`terraform/modules/azure/agentgateway/ci_cd.tf` in sibling terraform repository

### How It Would Work
```
Push to main → GitHub webhook → ACR Task → Build Docker image → Auto-deploy to Container App
```

### Terraform Resources
The following resources are defined but **not currently deployed**:

1. **ACR Task** - Automated Docker builds on git push
2. **Source Trigger** - GitHub webhook integration
3. **Base Image Trigger** - Rebuild on base image updates
4. **Container App Webhook** - Auto-deployment after successful build

### Key Features (If Enabled)
- ✅ Azure-native CI/CD (no external dependencies)
- ✅ Automatic builds on git commits to `unitone-agentgateway` main branch
- ✅ Automatic rebuilds on base image updates (security patches)
- ✅ Direct integration with Azure Container Apps
- ✅ No dependency on GitHub Actions

### Advantages
- Pure Azure solution (no GitHub Actions dependency)
- Integrated with Azure monitoring and logging
- Can trigger on base image updates automatically
- Lower latency (builds run in Azure)

### Disadvantages
- More complex setup (requires GitHub PAT)
- Less flexible than GitHub Actions workflows
- Harder to test complex scenarios
- Azure-specific (not portable)

## Comparison Table

| Feature | Fast Build (VM) | GitHub Actions | ACR Tasks |
|---------|-----------------|----------------|-----------|
| **Status** | ✅ Active (dev) | ✅ Active (CI/CD) | ⚠️ Available (not deployed) |
| **Build Time** | **4-7 min** | 15-25 min | 15-20 min |
| **First Build** | 8-10 min | 15-25 min | 15-20 min |
| **Trigger** | Manual command | Push to main | Push to main (via webhook) |
| **Build Location** | Azure VM (Linux) | GitHub runners | Azure ACR |
| **Deployment** | Automatic | Via workflow steps | Via webhook |
| **Multi-environment** | ✅ Yes (dev/staging/prod) | ✅ Yes (dev/staging/prod) | Limited |
| **Testing/Validation** | Basic | ✅ Full support | Limited |
| **Monitoring** | Build output | GitHub Actions UI | Azure portal |
| **Cost** | $10-20/month | Free/generous limits | $0.0001 per build second |
| **Setup Complexity** | Medium (one-time VM) | Medium | High |
| **Portability** | ❌ Azure-specific | ✅ High | ❌ Azure-specific |
| **Cache Strategy** | ✅ Layered (2-stage) | Single layer | Single layer |
| **Best For** | Development | CI/CD automation | Alternative CI/CD |
| **Speed Improvement** | **75% faster** | Baseline | Baseline |

## When to Use Each

### Use Fast Build When:
- ✅ **Active development** - Building and testing multiple times per day
- ✅ **Rapid iteration** - Need fast feedback loops (4-7 minutes)
- ✅ **Testing configuration changes** - Quick deployment to verify changes
- ✅ **Bug fixes** - Fast turnaround for critical fixes
- ✅ **Feature development** - Iterative development workflow

**Recommendation:** Fast Build is **the recommended choice for active development** due to 75% speed improvement.

### Use GitHub Actions When:
- ✅ **CI/CD automation** - Automatic builds on push to main
- ✅ **Complex workflows** - Tests, linting, validation pipelines
- ✅ **Multi-step deployments** - Staging → Production promotion
- ✅ **Team collaboration** - Consistent build process for all developers
- ✅ **Audit trails** - Built-in monitoring and logging

**Recommendation:** GitHub Actions is **the primary CI/CD choice** for automated deployments.

### Use ACR Tasks When:
- You want pure Azure solution
- You need automatic rebuilds on base image updates
- You prefer lower latency (builds in Azure)
- You don't need complex workflow logic
- You want independence from GitHub Actions

**Note:** ACR Tasks can be **used alongside GitHub Actions** as a backup or for specific scenarios (like base image update triggers).

## Current Recommendation

**Continue using GitHub Actions as the primary CI/CD** for the following reasons:

1. ✅ **Already deployed and working** - No migration needed
2. ✅ **Meets all requirements** - Multi-environment, testing, validation
3. ✅ **Better developer experience** - Easy monitoring, flexible workflows
4. ✅ **Lower complexity** - No additional Azure configuration needed

## Enabling ACR Tasks (Optional)

If you want to **enable ACR Tasks as a backup/alternative**, follow these steps:

### Prerequisites
1. GitHub Personal Access Token (PAT) with `repo` scope
2. Terraform configured for dev environment

### Steps

#### 1. Create GitHub PAT
```bash
# Visit: https://github.com/settings/tokens/new
# Scopes: repo (Full control of private repositories)
# Expiration: 90 days (recommended)
```

#### 2. Update Terraform Variables
```bash
cd ~/terraform/environments/dev/agentgateway

# Edit terraform.tfvars
# Set: github_pat = "ghp_YOUR_TOKEN_HERE"
```

#### 3. Apply Terraform
```bash
terraform plan  # Review changes
terraform apply # Deploy ACR Task
```

#### 4. Verify Deployment
```bash
# List ACR Tasks
az acr task list --registry agwimages -o table

# Test trigger
az acr task run --name agentgateway-build-task --registry agwimages
```

### What Gets Deployed
- ✅ ACR Task `agentgateway-build-task`
- ✅ GitHub webhook (triggers on push to main)
- ✅ Base image update trigger
- ✅ Container App auto-deployment (if `enable_auto_deployment = true`)

## Disabling ACR Tasks

If ACR Tasks are enabled and you want to disable them:

```bash
cd ~/terraform/environments/dev/agentgateway

# Option 1: Set github_pat to empty string
# In terraform.tfvars:
# github_pat = ""

# Option 2: Destroy only ACR Task resources
terraform destroy -target=azurerm_container_registry_task.agentgateway_build
```

## Hybrid Approach (Both Enabled)

You can run **both GitHub Actions and ACR Tasks** simultaneously:

- **GitHub Actions** - Primary CI/CD for all environments
- **ACR Tasks** - Backup builds + base image update triggers

**Benefits:**
- Redundancy (if GitHub Actions has issues)
- Automatic security updates (base image triggers)
- Flexibility to choose build method

**Considerations:**
- Double the builds on each push (higher cost)
- Two systems to monitor
- Potential for conflicting deployments

## Monitoring

### GitHub Actions
```bash
# View workflow runs
# https://github.com/UnitOneAI/unitone-agentgateway/actions

# Or via CLI
gh run list
gh run view <run-id>
```

### ACR Tasks (if enabled)
```bash
# List recent builds
az acr task list-runs --registry agwimages -o table

# View build logs
az acr task logs --registry agwimages --run-id <run-id>

# Follow latest build
az acr task logs --name agentgateway-build-task --registry agwimages --follow
```

## Troubleshooting

### GitHub Actions Not Triggering
1. Check workflow file syntax: `.github/workflows/azure-deploy.yml`
2. Verify GitHub Actions are enabled for the repository
3. Check branch protection rules
4. Review workflow run logs in GitHub Actions UI

### ACR Tasks Not Triggering (if enabled)
1. Verify task exists: `az acr task list --registry agwimages`
2. Check webhook status: `az acr task show --name agentgateway-build-task`
3. Verify GitHub PAT is valid
4. Check ACR task logs for errors

## Cost Considerations

### GitHub Actions
- **Free** for public repositories
- **2,000 minutes/month free** for private repositories (UnitOne plan may have more)
- Additional minutes: ~$0.008 per minute

**Estimated cost:** $0/month (within free tier)

### ACR Tasks (if enabled)
- **Build time:** $0.0001 per second
- **Typical build:** ~120 seconds = $0.012 per build
- **Monthly (30 deploys):** ~$0.36/month

**Estimated cost:** <$1/month

## Migration Path

If you decide to switch from GitHub Actions to ACR Tasks:

1. **Enable ACR Tasks** (follow steps above)
2. **Test ACR Task builds** (verify they work)
3. **Run both in parallel** for 1-2 weeks
4. **Disable GitHub Actions workflow** (rename `.github/workflows/azure-deploy.yml`)
5. **Monitor ACR Tasks** for stability

**Recommendation:** This is **not recommended** unless there's a specific requirement for ACR Tasks.

## Summary

### Active Systems
1. **Fast Build (VM-based)** - For active development (4-7 minutes)
2. **GitHub Actions** - For CI/CD automation (15-25 minutes)

### Recommended Workflow
- **Development**: Use Fast Build for rapid iteration
  ```bash
  ./scripts/fast-build.sh dev  # 4-7 minutes
  ```
- **CI/CD**: GitHub Actions handles automated deployments
  ```bash
  git push origin main  # Automatic deployment to dev
  ```
- **Production**: Manual GitHub Actions workflow dispatch
  - Staging deployment via workflow dispatch
  - Production deployment via workflow dispatch (requires approval)

### Cost Analysis
- **Fast Build**: $10-20/month (active development)
- **GitHub Actions**: Free (within generous limits)
- **Total**: ~$10-20/month for optimal development speed

### Speed Comparison
| Workflow | Build Method | Time |
|----------|-------------|------|
| **Active Development** | Fast Build | **4-7 min** ⚡ |
| **Automated CI/CD** | GitHub Actions | 15-25 min |
| **Alternative CI/CD** | ACR Tasks | 15-20 min |

**Recommendation:** Use Fast Build for development (75% faster), GitHub Actions for CI/CD automation.
