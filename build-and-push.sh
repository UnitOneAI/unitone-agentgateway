#!/bin/bash
set -e

# ==============================================================================
# Local Build and Push Script for UnitOne AgentGateway
# ==============================================================================
#
# This script builds the Docker image locally and pushes to Azure Container Registry.
# Replaces the automated ACR Task build process.
#
# Usage:
#   ./build-and-push.sh [OPTIONS]
#
# Options:
#   --tag TAG          Image tag (default: latest)
#   --registry NAME    ACR registry name (default: unitoneagwdevacr)
#   --platform ARCH    Platform architecture (default: linux/amd64)
#   --no-cache         Build without cache
#   --no-push          Build only, don't push to registry
#   --profile PROFILE  Build profile: release or debug (default: release)
#
# Examples:
#   ./build-and-push.sh
#   ./build-and-push.sh --tag v1.2.3
#   ./build-and-push.sh --tag feature-test --no-push
#   ./build-and-push.sh --platform linux/arm64
#
# ==============================================================================

# Default values
TAG="${TAG:-latest}"
REGISTRY="${REGISTRY:-unitoneagwdevacr}"
PLATFORM="${PLATFORM:-linux/amd64}"
PROFILE="${PROFILE:-release}"
NO_CACHE=""
NO_PUSH=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --tag)
      TAG="$2"
      shift 2
      ;;
    --registry)
      REGISTRY="$2"
      shift 2
      ;;
    --platform)
      PLATFORM="$2"
      shift 2
      ;;
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --no-cache)
      NO_CACHE="--no-cache"
      shift
      ;;
    --no-push)
      NO_PUSH=true
      shift
      ;;
    -h|--help)
      grep "^#" "$0" | grep -v "^#!/" | sed 's/^# //'
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}UnitOne AgentGateway - Local Build${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Registry:  $REGISTRY.azurecr.io"
echo "  Image:     unitone-agentgateway"
echo "  Tag:       $TAG"
echo "  Platform:  $PLATFORM"
echo "  Profile:   $PROFILE"
echo "  Push:      $([ "$NO_PUSH" = true ] && echo "No" || echo "Yes")"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo -e "${RED}Error: Docker is not running${NC}"
  exit 1
fi

# Check if azure-config.yaml exists (required by Dockerfile.acr)
if [ ! -f "azure-config.yaml" ]; then
  echo -e "${YELLOW}Warning: azure-config.yaml not found${NC}"
  echo -e "${YELLOW}Creating placeholder azure-config.yaml...${NC}"
  cat > azure-config.yaml << 'YAML_EOF'
# Placeholder configuration for Docker build
# Real configuration should be mounted or provided at runtime
upstreams: []
YAML_EOF
fi

# Build the image
echo -e "${BLUE}Building Docker image...${NC}"
BUILD_START=$(date +%s)

docker build \
  $NO_CACHE \
  --platform "$PLATFORM" \
  --build-arg PROFILE="$PROFILE" \
  --build-arg VERSION="$(git describe --tags --always --dirty 2>/dev/null || echo 'dev')" \
  --build-arg GIT_REVISION="$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" \
  -f Dockerfile.acr \
  -t "$REGISTRY.azurecr.io/unitone-agentgateway:$TAG" \
  -t "$REGISTRY.azurecr.io/unitone-agentgateway:$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')" \
  .

BUILD_END=$(date +%s)
BUILD_TIME=$((BUILD_END - BUILD_START))

echo -e "${GREEN}Build completed in ${BUILD_TIME}s${NC}"
echo ""

# Push to registry (unless --no-push)
if [ "$NO_PUSH" = false ]; then
  echo -e "${BLUE}Logging in to Azure Container Registry...${NC}"
  az acr login --name "$REGISTRY"
  
  echo -e "${BLUE}Pushing image to registry...${NC}"
  PUSH_START=$(date +%s)
  
  docker push "$REGISTRY.azurecr.io/unitone-agentgateway:$TAG"
  
  # Also push the git commit tag
  if git rev-parse --short HEAD > /dev/null 2>&1; then
    docker push "$REGISTRY.azurecr.io/unitone-agentgateway:$(git rev-parse --short HEAD)"
  fi
  
  PUSH_END=$(date +%s)
  PUSH_TIME=$((PUSH_END - PUSH_START))
  
  echo -e "${GREEN}Push completed in ${PUSH_TIME}s${NC}"
  echo ""
  
  echo -e "${GREEN}Image successfully pushed:${NC}"
  echo "  $REGISTRY.azurecr.io/unitone-agentgateway:$TAG"
  echo "  $REGISTRY.azurecr.io/unitone-agentgateway:$(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
else
  echo -e "${YELLOW}Skipping push (--no-push specified)${NC}"
  echo -e "${GREEN}Image built locally:${NC}"
  echo "  $REGISTRY.azurecr.io/unitone-agentgateway:$TAG"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Build complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
if [ "$NO_PUSH" = false ]; then
  echo "  1. Deploy to Container App:"
  echo "     az containerapp update \\"
  echo "       --name unitone-agw-dev-app \\"
  echo "       --resource-group mcp-gateway-dev-rg \\"
  echo "       --image $REGISTRY.azurecr.io/unitone-agentgateway:$TAG"
  echo ""
  echo "  2. Or wait for auto-deployment (if enabled in Terraform)"
else
  echo "  1. Test the image locally:"
  echo "     docker run -p 8080:8080 $REGISTRY.azurecr.io/unitone-agentgateway:$TAG"
  echo ""
  echo "  2. Push when ready:"
  echo "     ./build-and-push.sh --tag $TAG"
fi
echo ""
