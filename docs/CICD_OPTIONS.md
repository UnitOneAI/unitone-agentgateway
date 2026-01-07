# CI/CD Options for UnitOne AgentGateway

This document explains the available CI/CD options for automating builds and deployments.

## Overview

There are **two CI/CD approaches** available for UnitOne AgentGateway:

1. **GitHub Actions** (Primary - ACTIVE)
2. **Azure Container Registry (ACR) Tasks** (Alternative - AVAILABLE)

## Current Setup: GitHub Actions (PRIMARY)

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

| Feature | GitHub Actions | ACR Tasks |
|---------|---------------|-----------|
| **Status** | ✅ Active | ⚠️ Available (not deployed) |
| **Trigger** | Push to main | Push to main (via webhook) |
| **Build Location** | GitHub-hosted runners | Azure ACR |
| **Deployment** | Via workflow steps | Via webhook |
| **Multi-environment** | ✅ Yes (dev/staging/prod) | Limited |
| **Testing/Validation** | ✅ Full support | Limited |
| **Monitoring** | GitHub Actions UI | Azure portal |
| **Cost** | Free/generous limits | $0.0001 per build second |
| **Setup Complexity** | Medium | High |
| **Portability** | ✅ High | ❌ Azure-specific |
| **Base Image Updates** | Manual | ✅ Automatic |

## When to Use Each

### Use GitHub Actions When:
- ✅ You need multi-environment support (dev/staging/prod)
- ✅ You want complex workflows (tests, linting, validation)
- ✅ You prefer centralized CI/CD where code lives
- ✅ You want easy monitoring via GitHub UI
- ✅ You need portability (can migrate to other cloud providers)

**Recommendation:** GitHub Actions is **currently the primary choice** and meets all requirements.

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

- **Current Setup:** GitHub Actions (primary, active)
- **Status:** ✅ Working well, meets all requirements
- **Alternative:** ACR Tasks (available, not deployed)
- **Recommendation:** Continue with GitHub Actions
- **Option:** Enable ACR Tasks as backup if needed

For most use cases, **GitHub Actions is the right choice** and should remain the primary CI/CD solution.
