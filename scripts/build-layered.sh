#!/bin/bash
# Fast layered build script for rapid iteration
# Separates dependency layer from application layer

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Default values
ENV="${1:-dev}"
REBUILD_BASE="${REBUILD_BASE:-false}"
SKIP_PUSH="${SKIP_PUSH:-false}"
LOCAL_ONLY="${LOCAL_ONLY:-false}"

# Registry configuration
case "$ENV" in
  dev)
    REGISTRY="unitoneagwdevacr.azurecr.io"
    ;;
  staging)
    REGISTRY="unitoneagwstagingacr.azurecr.io"
    ;;
  prod)
    REGISTRY="unitoneagwprodacr.azurecr.io"
    ;;
  *)
    echo -e "${RED}Unknown environment: $ENV${NC}"
    echo "Usage: $0 [dev|staging|prod]"
    exit 1
    ;;
esac

# Get commit hash from env var or git (if available)
if [ -z "${COMMIT_HASH:-}" ]; then
  if git rev-parse --short HEAD 2>/dev/null; then
    COMMIT_HASH=$(git rev-parse --short HEAD)
  else
    # Fallback to timestamp if git is not available
    COMMIT_HASH="$(date +%s | tail -c 8)"
    echo "Warning: Git not available, using timestamp-based commit hash: $COMMIT_HASH"
  fi
fi
BASE_IMAGE="$REGISTRY/unitone-agentgateway-base:latest"
APP_IMAGE="$REGISTRY/unitone-agentgateway:$COMMIT_HASH"
APP_LATEST="$REGISTRY/unitone-agentgateway:latest"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Layer-based Build for $ENV${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# ============================================================================
# Step 1: Check if base image needs rebuilding
# ============================================================================
echo -e "${YELLOW}Step 1: Checking base image...${NC}"

CARGO_LOCK_HASH=$(md5sum agentgateway/Cargo.lock | cut -d' ' -f1)
BASE_TAG="$REGISTRY/unitone-agentgateway-base:cargo-$CARGO_LOCK_HASH"

# Check if base image exists
if docker manifest inspect "$BASE_TAG" > /dev/null 2>&1 && [ "$REBUILD_BASE" != "true" ]; then
  echo -e "${GREEN}✓ Base image exists with current dependencies${NC}"
  echo "  Using: $BASE_TAG"
  USE_BASE_IMAGE="$BASE_TAG"
else
  echo -e "${YELLOW}⚠ Base image not found or rebuild requested${NC}"
  echo "  Building new base image..."

  # Build base image
  echo ""
  echo -e "${BLUE}Building base image with dependencies...${NC}"
  docker build \
    -f Dockerfile.base \
    -t "$BASE_TAG" \
    -t "$BASE_IMAGE" \
    --platform linux/amd64 \
    .

  if [ "$LOCAL_ONLY" != "true" ]; then
    echo ""
    echo -e "${BLUE}Pushing base image to registry...${NC}"
    docker push "$BASE_TAG"
    docker push "$BASE_IMAGE"
    echo -e "${GREEN}✓ Base image pushed${NC}"
  fi

  USE_BASE_IMAGE="$BASE_TAG"
fi

echo ""

# ============================================================================
# Step 2: Build application using base image
# ============================================================================
echo -e "${YELLOW}Step 2: Building application...${NC}"

BUILD_START=$(date +%s)

docker build \
  -f Dockerfile.app \
  --build-arg BASE_IMAGE="$USE_BASE_IMAGE" \
  -t "$APP_IMAGE" \
  -t "$APP_LATEST" \
  --platform linux/amd64 \
  .

BUILD_END=$(date +%s)
BUILD_TIME=$((BUILD_END - BUILD_START))

echo -e "${GREEN}✓ Application built in ${BUILD_TIME}s${NC}"
echo ""

# ============================================================================
# Step 3: Push application image
# ============================================================================
if [ "$LOCAL_ONLY" != "true" ] && [ "$SKIP_PUSH" != "true" ]; then
  echo -e "${YELLOW}Step 3: Pushing application image...${NC}"

  docker push "$APP_IMAGE"
  docker push "$APP_LATEST"

  echo -e "${GREEN}✓ Application image pushed${NC}"
  echo "  Tags:"
  echo "    - $APP_IMAGE"
  echo "    - $APP_LATEST"
else
  echo -e "${YELLOW}Step 3: Skipping push (LOCAL_ONLY=$LOCAL_ONLY, SKIP_PUSH=$SKIP_PUSH)${NC}"
fi

echo ""

# ============================================================================
# Step 4: Update Container App (if not local-only)
# ============================================================================
if [ "$LOCAL_ONLY" != "true" ]; then
  echo -e "${YELLOW}Step 4: Updating Azure Container App...${NC}"

  case "$ENV" in
    dev)
      RESOURCE_GROUP="mcp-gateway-dev-rg"
      APP_NAME="unitone-agw-dev-app"
      ;;
    staging)
      RESOURCE_GROUP="mcp-gateway-staging-rg"
      APP_NAME="unitone-agw-staging-app"
      ;;
    prod)
      RESOURCE_GROUP="mcp-gateway-prod-rg"
      APP_NAME="unitone-agw-prod-app"
      ;;
  esac

  # Trigger new revision deployment
  az containerapp update \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --image "$APP_IMAGE" \
    --output none

  echo -e "${GREEN}✓ Container App updated${NC}"
  echo "  New revision deploying..."

  # Wait for deployment
  echo ""
  echo -e "${BLUE}Waiting for new revision to become healthy...${NC}"
  for i in {1..30}; do
    HEALTH=$(az containerapp revision list \
      --name "$APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --query "[?properties.active==\`true\`] | [0].properties.healthState" \
      -o tsv 2>/dev/null || echo "Unknown")

    if [ "$HEALTH" = "Healthy" ]; then
      echo -e "${GREEN}✓ New revision is healthy!${NC}"
      break
    fi

    echo "  Status: $HEALTH (attempt $i/30)"
    sleep 10
  done
else
  echo -e "${YELLOW}Step 4: Skipping deployment (LOCAL_ONLY=true)${NC}"
fi

echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✓ Build Complete!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Summary:"
echo "  Environment: $ENV"
echo "  Build time: ${BUILD_TIME}s"
echo "  Image: $APP_IMAGE"
echo ""
echo "Speed comparison:"
echo "  Traditional ACR build: ~15-25 minutes"
echo "  Layer-based build: ~${BUILD_TIME}s ($(((1500 - BUILD_TIME) * 100 / 1500))% faster)"
echo ""

if [ "$LOCAL_ONLY" = "true" ]; then
  echo "To test locally:"
  echo "  docker run -p 8080:8080 -v \$(pwd)/azure-config.yaml:/etc/agentgateway/config.yaml $APP_IMAGE"
fi
