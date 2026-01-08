# Developer Workflow Guide - UnitOne AgentGateway

**For:** New Engineers (like Alexey)
**Goal:** Understand the complete development, testing, and deployment workflow

---

## Table of Contents
1. [Quick Start - Your First Day](#quick-start---your-first-day)
2. [Local Development](#local-development)
3. [Making Changes](#making-changes)
4. [Testing Locally](#testing-locally)
5. [Deploying to Dev](#deploying-to-dev)
6. [Deploying to Staging](#deploying-to-staging)
7. [Deploying to Production](#deploying-to-production)
8. [Common Workflows](#common-workflows)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start - Your First Day

### 1. Clone the Repository

```bash
# Clone with submodules (required!)
git clone --recursive https://github.com/UnitOneAI/unitone-agentgateway.git
cd unitone-agentgateway

# Verify submodule is initialized
git submodule status
# Should show: 7df6fc7... agentgateway (heads/feature/mcp-security-guards)
```

### 2. Check Prerequisites

```bash
# You need:
- Git with submodules support
- Docker (for containerized builds)
- Azure CLI (for deployments)
- Rust + Cargo (optional, for local builds)
- Node.js + npm (optional, for UI development)

# Verify installations
docker --version
az --version
cargo --version  # optional
node --version   # optional
```

### 3. Understand the Structure

```
unitone-agentgateway/          ← You work here (wrapper repo)
├── agentgateway/              ← Git submodule (core code, feature/mcp-security-guards)
│   ├── ui/                    ← UI source code
│   ├── crates/                ← Rust source code
│   └── ...
├── ui-customizations/         ← UnitOne branding (logo, colors)
├── Dockerfile.acr             ← How we build the Docker image
├── Makefile                   ← Build automation commands
└── docs/                      ← Documentation
```

---

## Local Development

### Option 1: Docker Build (Recommended - Matches Production)

```bash
# Build Docker image locally (this takes 10-15 minutes first time)
docker build -f Dockerfile.acr -t unitone-agentgateway:local .

# Run the container
docker run -p 19000:19000 \
  -v $(pwd)/azure-config.yaml:/app/config.yaml \
  unitone-agentgateway:local

# Access the UI
open http://localhost:19000/ui
```

**What this does:**
- Builds UI with UnitOne branding
- Compiles Rust binary with embedded UI
- Creates production-like container
- Perfect for testing before deployment

### Option 2: Local Rust Build (Faster for Development)

```bash
# 1. Build the UI first
make build-ui
# This applies UnitOne customizations and builds UI

# 2. Build Rust binary with embedded UI
cd agentgateway
cargo build --release --features ui

# 3. Run locally
./target/release/agentgateway --config ../azure-config.yaml

# Access the UI
open http://localhost:19000/ui
```

**What this does:**
- Faster incremental builds (after first time)
- Good for rapid development/testing
- UI changes require rebuild

### Option 3: UI Development Only (Limited - No Backend)

```bash
# For UI-only visual/styling changes (hot reload)
cd agentgateway/ui
npm install
npm run dev

# Access development UI (standalone, no backend APIs)
open http://localhost:3000
```

**What this does:**
- Instant hot reload on UI changes
- Good for visual/styling work ONLY
- ⚠️ **No backend functionality** - API calls won't work
- ⚠️ **Must rebuild Rust binary** to see changes in production mode

**Important:** The UI is **embedded in the Rust binary at compile time**. The `npm run dev` server is ONLY for quick visual iteration. To test with actual backend functionality, you MUST rebuild the Rust binary (Option 2) after UI changes.

---

## Making Changes

### Scenario 1: UI Branding Changes (UnitOne-Specific)

**What:** Change logo, colors, theme
**Where:** `ui-customizations/`

```bash
# 1. Make changes to UnitOne branding
vim ui-customizations/theme.config.ts
# Or replace: ui-customizations/public/images/unitone-logo.png

# 2. Test locally
make build-ui
cd agentgateway
cargo run --features ui -- --config ../azure-config.yaml

# 3. Verify in browser
open http://localhost:19000/ui

# 4. Commit changes
git add ui-customizations/
git commit -m "Update UnitOne branding: new logo and colors"
git push origin main  # Deploys to dev automatically
```

### Scenario 2: Wrapper Configuration Changes

**What:** Dockerfile, Makefile, deployment configs
**Where:** Root of `unitone-agentgateway`

```bash
# 1. Make changes
vim Dockerfile.acr
# or
vim Makefile

# 2. Test locally (build Docker image)
docker build -f Dockerfile.acr -t test:local .
docker run -p 19000:19000 test:local

# 3. Commit and deploy
git add Dockerfile.acr Makefile
git commit -m "Fix: Update Docker build steps"
git push origin main  # Deploys to dev
```

### Scenario 3: Core Feature Changes (agentgateway submodule)

**What:** New routes, security features, core logic
**Where:** Inside `agentgateway/` submodule

```bash
# 1. Navigate to submodule
cd agentgateway

# 2. Create feature branch in submodule
git checkout -b feature/alexey-new-security-hook

# 3. Make changes
vim crates/agentgateway/src/security/hooks.rs

# 4. Test locally
cd ..
make build-ui
cd agentgateway
cargo build --features ui
cargo test
./target/release/agentgateway --config ../azure-config.yaml

# 5. Commit to submodule
git add .
git commit -m "feat: Add new security hook for PII detection"
git push origin feature/alexey-new-security-hook

# 6. Create PR in agentgateway repo
# Go to https://github.com/UnitOneAI/agentgateway
# Create PR: feature/alexey-new-security-hook → feature/mcp-security-guards

# 7. After PR is merged, update wrapper repo
cd ..  # Back to unitone-agentgateway
cd agentgateway
git fetch origin
git checkout origin/feature/mcp-security-guards
cd ..
git add agentgateway
git commit -m "Update agentgateway submodule with PII detection hook"
git push origin main  # Deploys to dev
```

---

## Testing Locally

### Test UI Branding

```bash
# Build with UnitOne branding
make build-ui

# Run locally
cd agentgateway
cargo run --features ui -- --config ../azure-config.yaml

# Check in browser:
# 1. Open http://localhost:19000/ui
# 2. Verify UnitOne logo appears (not agentgateway logo)
# 3. Verify blue theme (#3b82f6, not purple)
# 4. Verify dark sidebar
```

### Test Core Functionality

```bash
# Health check
curl http://localhost:19000/health

# MCP endpoint
curl http://localhost:19000/mcp/github

# Test with real MCP client (if you have one)
# See agentgateway/examples/ for test clients
```

### Test Docker Build

```bash
# Build exactly as production does
docker build -f Dockerfile.acr -t test:local .

# Run and test
docker run -p 19000:19000 test:local

# Should see UnitOne branding at http://localhost:19000/ui
```

---

## Deploying to Dev

**Dev Environment**: Automatic deployment on push to `main`

```bash
# 1. Make sure your changes are committed
git status

# 2. Push to main branch
git push origin main

# 3. Monitor deployment
# Go to: https://github.com/UnitOneAI/unitone-agentgateway/actions
# Watch: "Azure Deployment" workflow

# 4. Verify deployment (after ~5-10 minutes)
# Check logs
az containerapp logs show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --follow

# 5. Test the deployed app
open https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/ui

# 6. Health check
curl https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/health
```

**What Happens Automatically:**
1. GitHub Actions triggers on push to `main`
2. Checks out code with submodules
3. Builds Docker image in Azure Container Registry
4. Pushes image with tags: `<commit-sha>`, `latest`
5. Updates dev Container App with new image
6. Health check runs after 30 seconds
7. Deployment completes or rolls back

**Rollback Dev:**
```bash
# If deployment fails, previous version stays active
# To manually rollback:
az containerapp revision list \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg

# Activate previous revision
az containerapp revision activate \
  --revision <previous-revision-name> \
  --resource-group mcp-gateway-dev-rg
```

---

## Deploying to Staging

**Staging Environment**: Manual deployment via GitHub Actions

### Steps

```bash
# 1. Ensure changes are merged to main and tested in dev
git checkout main
git pull origin main

# 2. Go to GitHub Actions
open https://github.com/UnitOneAI/unitone-agentgateway/actions

# 3. Click "Azure Deployment" workflow

# 4. Click "Run workflow" button (top right)

# 5. Select:
   Branch: main
   Environment: staging
   Image tag: (leave empty to use latest commit SHA)

# 6. Click "Run workflow"

# 7. Monitor deployment
# Watch the workflow run in GitHub Actions

# 8. Verify staging deployment
open https://unitone-agentgateway-staging.azurecontainerapps.io/ui

# 9. Run staging tests
curl https://unitone-agentgateway-staging.azurecontainerapps.io/health

# 10. Check logs
az containerapp logs show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-staging-rg \
  --follow
```

### Staging Verification Checklist

```bash
# 1. UI loads with UnitOne branding
# 2. OAuth login works (Microsoft + Google)
# 3. MCP endpoints respond
# 4. Security hooks are active
# 5. Logs show no errors
# 6. Response times are acceptable

# Run E2E tests (if available)
cd tests
./run_e2e_tests.sh --env staging
```

---

## Deploying to Production

**Production Environment**: Manual deployment with confirmation

### Prerequisites

- [ ] Changes tested in dev
- [ ] Changes tested in staging
- [ ] All tests passing
- [ ] No critical bugs in staging
- [ ] Approved by team lead
- [ ] Deployment window scheduled (if needed)

### Steps

```bash
# 1. Final verification on staging
curl https://unitone-agentgateway-staging.azurecontainerapps.io/health

# 2. Go to GitHub Actions
open https://github.com/UnitOneAI/unitone-agentgateway/actions

# 3. Click "Azure Deployment" workflow

# 4. Click "Run workflow"

# 5. Select:
   Branch: main
   Environment: prod
   Image tag: <staging-commit-sha>  # Use the SAME sha as staging!

# 6. Click "Run workflow"

# 7. CONFIRM: GitHub will ask for approval (prod deploys require approval)

# 8. Monitor deployment closely
# Watch GitHub Actions workflow

# 9. Verify production
open https://unitone-agentgateway-prod.azurecontainerapps.io/ui

# 10. Health checks
curl https://unitone-agentgateway-prod.azurecontainerapps.io/health
curl https://unitone-agentgateway-prod.azurecontainerapps.io/mcp/github

# 11. Monitor logs for 15 minutes
az containerapp logs show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-prod-rg \
  --follow
```

### Production Rollback (Emergency)

```bash
# If production has issues:

# Option 1: Activate previous revision
az containerapp revision list \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-prod-rg \
  -o table

az containerapp revision activate \
  --revision <previous-good-revision> \
  --resource-group mcp-gateway-prod-rg

# Option 2: Re-deploy previous commit
# Go to GitHub Actions → Run workflow
# Use previous commit SHA that was working
```

---

## Common Workflows

### Daily Development Workflow

```bash
# Morning: Get latest changes
git checkout main
git pull origin main
git submodule update --remote

# Make changes
# ... work on feature ...

# Test locally
make build-ui
cd agentgateway && cargo test && cargo run --features ui

# Deploy to dev (automatic)
git add .
git commit -m "feat: Add new feature"
git push origin main

# Verify in dev
open https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/ui
```

### Release Workflow

```bash
# 1. Dev → Staging (once per day or as needed)
# GitHub Actions: main → staging

# 2. Staging testing (1-2 days)
# QA team tests in staging

# 3. Staging → Production (weekly or as needed)
# GitHub Actions: main (staging SHA) → prod
# Requires approval

# 4. Tag release
git tag v1.2.3
git push origin v1.2.3
```

### Hotfix Workflow

```bash
# 1. Create hotfix branch
git checkout main
git pull origin main
git checkout -b hotfix/critical-security-fix

# 2. Make fix
vim agentgateway/crates/agentgateway/src/security/auth.rs

# 3. Test locally
make build-ui && cd agentgateway && cargo test

# 4. Push hotfix
git add .
git commit -m "hotfix: Fix critical auth vulnerability"
git push origin hotfix/critical-security-fix

# 5. Fast-track to main
# Create PR → get quick review → merge

# 6. Deploy to staging immediately
# GitHub Actions: main → staging

# 7. After verification, deploy to prod
# GitHub Actions: main → prod (with approval)
```

---

## Troubleshooting

### Build Fails Locally

```bash
# Problem: Docker build fails
# Solution: Check Dockerfile.acr paths

# Problem: Cargo build fails
cd agentgateway
cargo clean
cargo build --features ui

# Problem: UI build fails
cd agentgateway/ui
rm -rf node_modules package-lock.json
npm install
npm run build

# Problem: UnitOne branding not showing
make build-ui  # Re-applies customizations
```

### Submodule Issues

```bash
# Problem: Submodule not initialized
git submodule update --init --recursive

# Problem: Submodule on wrong branch
cd agentgateway
git branch
# Should show: feature/mcp-security-guards
# If not:
git checkout origin/feature/mcp-security-guards

# Problem: Submodule has uncommitted changes
cd agentgateway
git status
git stash  # Save changes
# or
git checkout .  # Discard changes
```

### Deployment Fails

```bash
# Check GitHub Actions logs
open https://github.com/UnitOneAI/unitone-agentgateway/actions

# Check Container App status
az containerapp show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --query "{Status:properties.provisioningState, RunningStatus:properties.runningStatus}"

# Check Container App logs
az containerapp logs show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --tail 100

# Check ACR build logs
az acr task logs --registry agwimages --follow
```

---

## Quick Reference

### Key URLs

| Environment | URL |
|-------------|-----|
| Dev | https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/ui |
| Staging | https://unitone-agentgateway-staging.azurecontainerapps.io/ui |
| Production | https://unitone-agentgateway-prod.azurecontainerapps.io/ui |
| GitHub Actions | https://github.com/UnitOneAI/unitone-agentgateway/actions |
| Submodule Repo | https://github.com/UnitOneAI/agentgateway |

### Key Commands

```bash
# Clone
git clone --recursive https://github.com/UnitOneAI/unitone-agentgateway.git

# Build UI locally
make build-ui

# Build Docker image
docker build -f Dockerfile.acr -t test:local .

# Deploy to dev
git push origin main

# Deploy to staging/prod
# Use GitHub Actions UI → Run workflow

# View logs
az containerapp logs show --name unitone-agentgateway --resource-group mcp-gateway-{ENV}-rg --follow

# Health check
curl https://unitone-agentgateway.../health
```

### Resource Groups

| Environment | Resource Group |
|-------------|----------------|
| Dev | `mcp-gateway-dev-rg` |
| Staging | `mcp-gateway-staging-rg` |
| Production | `mcp-gateway-prod-rg` |

---

## Getting Help

1. **Documentation**: Start with [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)
2. **Team Chat**: Ask in #agentgateway-dev channel
3. **Issues**: Create issue in GitHub with `question` label
4. **Escalate**: Contact DevOps team for infrastructure issues

---

**Last Updated:** January 2026
**Maintained By:** UnitOne DevOps Team
