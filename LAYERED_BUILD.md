# Layer-Based Build System

## Problem

Traditional ACR builds take 15-25 minutes because they compile all Rust dependencies and application code from scratch on every deployment. This significantly blocks iteration velocity during development.

## Solution

Separate the build process into two layers:
1. **Base Layer**: Contains Rust toolchain + all compiled dependencies (changes infrequently)
2. **Application Layer**: Contains only application code (changes frequently)

## Architecture

### Files Created

- `Dockerfile.base` - Base image with pre-compiled dependencies
- `Dockerfile.app` - Fast application image using base
- `scripts/build-layered.sh` - Automated build & deploy script
- `.dockerignore` - Optimized to exclude unnecessary files

### How It Works

#### First-Time Setup (Slow - 10-15 min)
```bash
# Build base image with all dependencies
./scripts/build-layered.sh dev
```

The script:
1. Checks if base image exists for current `Cargo.lock` hash
2. If not, builds new base image with all dependencies
3. Pushes base image to ACR with hash tag

#### Subsequent Deploys (Fast - 3-5 min)
```bash
# Application code changed? Just rebuild app layer!
./scripts/build-layered.sh dev
```

The script:
1. Detects base image exists (Cargo.lock unchanged)
2. Builds only application layer using cached dependencies
3. Pushes application image to ACR
4. Updates Azure Container App

## Speed Comparison

| Build Type | Time | Use Case |
|------------|------|----------|
| Traditional ACR | 15-25 min | Every deployment |
| Layer-based (first time) | 10-15 min | Only when dependencies change |
| Layer-based (subsequent) | 3-5 min | Most deployments (code changes only) |

**Expected speedup**: **60-70% faster** for typical code-only changes

## Usage

### Local Development
```bash
# Test locally (no push to ACR)
LOCAL_ONLY=true ./scripts/build-layered.sh dev

# Run locally
docker run -p 8080:8080 \
  -v $(pwd)/azure-config.yaml:/etc/agentgateway/config.yaml \
  unitone-agentgateway:latest
```

### Deploy to Dev
```bash
./scripts/build-layered.sh dev
```

### Deploy to Staging
```bash
./scripts/build-layered.sh staging
```

### Deploy to Production
```bash
./scripts/build-layered.sh prod
```

### Force Rebuild Base Image
```bash
# When dependencies change (Cargo.toml updated)
REBUILD_BASE=true ./scripts/build-layered.sh dev
```

## When to Rebuild Base Image

The base image must be rebuilt when:
- `Cargo.toml` changes (dependencies added/removed/updated)
- `Cargo.lock` changes (dependency versions locked)
- Rust version needs updating (Dockerfile.base ARG)
- Build tools need updating (clang, lld versions)

The script automatically detects `Cargo.lock` changes and rebuilds when needed.

## Advantages

1. **Faster iteration**: 60-70% faster builds for code changes
2. **Reduced CI/CD time**: Shorter feedback loops
3. **Cost savings**: Less ACR build time = lower costs
4. **Local testing**: Can test full Docker build locally before pushing
5. **Predictable performance**: Consistent build times based on what changed

## Technical Details

### Base Image Stages

1. **Node.js stage**: Installs UI npm dependencies
2. **Rust toolchain**: Sets up build environment (clang, lld)
3. **Dependency builder**: Compiles all Rust dependencies using dummy source files
4. **Final base**: Ready-to-use image with compiled dependencies

### Application Image Stages

1. **UI builder**: Builds Next.js UI (fast - uses cached npm install)
2. **App builder**: Compiles only application code using base image dependencies
3. **Runtime**: Minimal Debian slim with binary + UI assets

### Smart Caching

The build script uses `Cargo.lock` hash to tag base images:
```bash
BASE_TAG="$REGISTRY/unitone-agentgateway-base:cargo-$CARGO_LOCK_HASH"
```

This ensures:
- Same dependencies = reuse existing base image
- Different dependencies = automatic rebuild
- No manual cache invalidation needed

## Troubleshooting

### Base image not found
```bash
# Manually trigger base rebuild
REBUILD_BASE=true ./scripts/build-layered.sh dev
```

### Local Docker build fails
```bash
# Ensure Docker daemon is running
docker info

# Check platform support
docker buildx ls
```

### ACR authentication errors
```bash
# Refresh Azure CLI token
az account get-access-token --output none
```

## Migration Path

1. ✅ Created `Dockerfile.base` and `Dockerfile.app`
2. ✅ Created `scripts/build-layered.sh` automation
3. ✅ Optimized `.dockerignore` for faster builds
4. 🔄 Testing local builds
5. ⏳ Deploy to dev environment
6. ⏳ Verify speed improvements
7. ⏳ Document actual build times

## Metrics to Track

After implementation, track:
- Base build time (first deployment after dependency change)
- Application build time (typical code change deployment)
- Overall deployment time (build + Azure Container App update)
- Developer feedback on iteration speed

## Future Optimizations

1. **Multi-stage base caching**: Cache Node.js dependencies separately
2. **Parallel builds**: Build UI and Rust in parallel where possible
3. **Incremental compilation**: Enable Rust incremental compilation in Docker
4. **Build matrix**: Pre-build base images for common configurations

---

**Status**: Implementation complete, testing in progress
**Created**: 2026-01-13
**Author**: AI Assistant (Claude Code)
