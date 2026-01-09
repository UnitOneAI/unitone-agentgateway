# Quick Start Guide - UnitOne AgentGateway

**For new developers**: Get up and running in 5 minutes.

## Prerequisites

- Git with submodules
- Rust & Cargo (for local builds)
- Docker (for production-like testing)
- Azure CLI (for deployments)

## 1. Clone the Repository

```bash
git clone --recursive https://github.com/UnitOneAI/unitone-agentgateway.git
cd unitone-agentgateway

# Verify submodule is initialized
git submodule status
# Should show: agentgateway (heads/feature/mcp-security-guards)
```

## 2. Build Locally

**Option A: Using Makefile (Recommended)**
```bash
# Build with UnitOne branding
make build

# Run locally
cd agentgateway
./target/release/agentgateway --config ../azure-config.yaml

# Access at http://localhost:19000/ui
```

**Option B: Quick iteration**
```bash
cd agentgateway
cargo build --release --features ui
./target/release/agentgateway --config ../azure-config.yaml
```

**Option C: Full Docker build (matches production)**
```bash
docker build -f Dockerfile.acr -t local-test .
docker run -p 19000:19000 local-test

# Access at http://localhost:19000/ui
```

## 3. Make Code Changes

```bash
# Navigate to submodule
cd agentgateway

# Create feature branch
git checkout -b feature/my-feature

# Make changes
vim crates/agentgateway/src/...

# Test locally
cd ..
make build
cd agentgateway && cargo run --features ui
```

## 4. Commit and Deploy

```bash
# Commit to submodule
cd agentgateway
git add .
git commit -m "feat: Add my feature"
git push origin feature/my-feature

# Create PR in agentgateway repo
# Target: feature/mcp-security-guards branch

# After PR is merged, update wrapper repo
cd ..  # Back to wrapper repo root
cd agentgateway
git checkout feature/mcp-security-guards
git pull origin feature/mcp-security-guards

cd ..
git add agentgateway
git commit -m "Update agentgateway with my feature"
git push origin main

# This automatically deploys to dev environment
```

## 5. Verify Deployment

```bash
# Check dev environment
curl https://unitone-agw-dev-app.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/health

# View logs
make logs-dev

# Or manually:
az containerapp logs show \
  --name unitone-agw-dev-app \
  --resource-group mcp-gateway-dev-rg \
  --follow
```

## Common Makefile Commands

```bash
make help           # Show all available commands
make build          # Build with UnitOne branding
make build-ui       # Build just the UI
make logs-dev       # Stream dev logs
make logs-staging   # Stream staging logs
make logs-prod      # Stream production logs
make status         # Check all environments
make clean          # Clean build artifacts
```

## Development Workflow Summary

```
1. Make changes in agentgateway/ submodule
2. Build: make build
3. Test: cargo run --features ui
4. Commit: git add . && git commit
5. Push to PR: git push origin feature-branch
6. Merge PR in agentgateway repo
7. Update wrapper: cd .. && git add agentgateway && git commit && git push
8. Auto-deploy to dev ✅
```

## Key Points

1. **Always work in the submodule** (`agentgateway/` directory) for code changes
2. **UI is embedded at compile time** - rebuild Rust after UI changes
3. **Use `make build`** for UnitOne branding
4. **Dev auto-deploys** from main branch of wrapper repo
5. **Staging/Prod** require manual deployment

## Environments

| Environment | URL | Deploy Method |
|-------------|-----|---------------|
| Dev | https://unitone-agw-dev-app.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/ui | Auto (on push to main) |
| Staging | https://unitone-agw-staging-app.icyisland-535dd8c7.eastus2.azurecontainerapps.io/ui | Manual ACR build |
| Production | https://unitone-agw-prod-app.calmfield-9aeb3d35.eastus2.azurecontainerapps.io/ui | Manual ACR build |

## Need Help?

- **Full workflow**: See [DEVELOPER_WORKFLOW.md](docs/DEVELOPER_WORKFLOW.md)
- **Environment details**: See [ENVIRONMENTS.md](ENVIRONMENTS.md)
- **Issues**: Ask in #agentgateway-dev channel

---

**Last Updated**: January 8, 2026
