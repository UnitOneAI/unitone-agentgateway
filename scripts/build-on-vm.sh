#!/bin/bash
# ==============================================================================
# UnitOne AgentGateway - VM-Based Build Script
# ==============================================================================
#
# Build Docker image locally on a VM and push to Azure Container Registry.
# Use this when you have a dedicated build VM/server instead of ACR Tasks.
#
# Prerequisites:
#   - Docker installed and running
#   - Azure CLI installed and logged in
#   - Access to the target ACR
#
# Usage:
#   ./scripts/build-on-vm.sh [OPTIONS]
#
# Options:
#   --acr-name NAME       ACR name (required, or set ACR_NAME env var)
#   --tag TAG             Image tag (default: latest)
#   --platform PLATFORM   Target platform (default: linux/amd64)
#   --deploy              Also deploy to Container App after build
#   --resource-group RG   Resource group for deployment
#   --app-name NAME       Container App name for deployment
#   --no-cache            Build without Docker cache
#   --help                Show this help
#
# Examples:
#   # Build and push to ACR
#   ./scripts/build-on-vm.sh --acr-name myacr
#
#   # Build with specific tag
#   ./scripts/build-on-vm.sh --acr-name myacr --tag v1.2.3
#
#   # Build and deploy to Container App
#   ./scripts/build-on-vm.sh --acr-name myacr --deploy --resource-group my-rg --app-name my-app
#
#   # Build for ARM64 (e.g., for ARM-based Container Apps)
#   ./scripts/build-on-vm.sh --acr-name myacr --platform linux/arm64
#
# ==============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_step() { echo -e "${CYAN}▶${NC} $1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }

show_help() {
    cat << 'HELP'
UnitOne AgentGateway - VM-Based Build Script

Build Docker image locally and push to Azure Container Registry.

Usage:
  ./scripts/build-on-vm.sh [OPTIONS]

Options:
  --acr-name NAME       ACR name (required, or set ACR_NAME env var)
  --tag TAG             Image tag (default: latest)
  --platform PLATFORM   Target platform (default: linux/amd64)
  --deploy              Also deploy to Container App after build
  --resource-group RG   Resource group for deployment
  --app-name NAME       Container App name for deployment
  --no-cache            Build without Docker cache
  --help                Show this help

Examples:
  # Build and push to ACR
  ./scripts/build-on-vm.sh --acr-name myacr

  # Build with specific tag
  ./scripts/build-on-vm.sh --acr-name myacr --tag v1.2.3

  # Build and deploy to Container App
  ./scripts/build-on-vm.sh --acr-name myacr --deploy --resource-group my-rg --app-name my-app

  # Build for ARM64
  ./scripts/build-on-vm.sh --acr-name myacr --platform linux/arm64
HELP
    exit 0
}

# Default values
ACR_NAME="${ACR_NAME:-}"
IMAGE_TAG="latest"
PLATFORM="linux/amd64"
DEPLOY=false
RESOURCE_GROUP=""
APP_NAME=""
NO_CACHE=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --acr-name)
            ACR_NAME="$2"
            shift 2
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        --deploy)
            DEPLOY=true
            shift
            ;;
        --resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        --app-name)
            APP_NAME="$2"
            shift 2
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate required parameters
if [ -z "$ACR_NAME" ]; then
    print_error "ACR name required. Use --acr-name or set ACR_NAME env var"
    echo ""
    echo "Get ACR name from terraform:"
    echo "  cd terraform && terraform output -raw acr_name"
    exit 1
fi

if [ "$DEPLOY" = true ]; then
    if [ -z "$RESOURCE_GROUP" ] || [ -z "$APP_NAME" ]; then
        print_error "--deploy requires --resource-group and --app-name"
        exit 1
    fi
fi

# ==============================================================================
# Pre-flight checks
# ==============================================================================

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  UnitOne AgentGateway - VM Build${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

print_step "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker not found. Install Docker first."
    exit 1
fi

if ! docker info &> /dev/null; then
    print_error "Docker daemon not running. Start Docker first."
    exit 1
fi
print_success "Docker is running"

# Check Azure CLI
if ! command -v az &> /dev/null; then
    print_error "Azure CLI not found. Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

if ! az account show &> /dev/null; then
    print_error "Not logged in to Azure. Run: az login"
    exit 1
fi
print_success "Azure CLI logged in"

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv 2>/dev/null)
if [ -z "$ACR_LOGIN_SERVER" ]; then
    print_error "Could not find ACR: $ACR_NAME"
    exit 1
fi
print_success "Found ACR: $ACR_LOGIN_SERVER"

# ==============================================================================
# Build
# ==============================================================================

cd "$REPO_ROOT"

IMAGE_FULL="${ACR_LOGIN_SERVER}/unitone-agentgateway:${IMAGE_TAG}"
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
IMAGE_SHA="${ACR_LOGIN_SERVER}/unitone-agentgateway:${GIT_SHA}"

echo ""
print_step "Building image: $IMAGE_FULL"
print_step "Platform: $PLATFORM"
print_step "Git SHA: $GIT_SHA"
echo ""

# Login to ACR
print_step "Logging in to ACR..."
az acr login --name "$ACR_NAME"
print_success "Logged in to ACR"

# Build the image
print_step "Building Docker image (this may take several minutes)..."
BUILD_START=$(date +%s)

docker build \
    --platform "$PLATFORM" \
    --file Dockerfile.acr \
    --tag "$IMAGE_FULL" \
    --tag "$IMAGE_SHA" \
    --build-arg GIT_REVISION="$GIT_SHA" \
    --build-arg VERSION="$IMAGE_TAG" \
    $NO_CACHE \
    .

BUILD_END=$(date +%s)
BUILD_DURATION=$((BUILD_END - BUILD_START))
print_success "Build completed in ${BUILD_DURATION}s"

# ==============================================================================
# Push
# ==============================================================================

echo ""
print_step "Pushing to ACR..."
PUSH_START=$(date +%s)

docker push "$IMAGE_FULL"
docker push "$IMAGE_SHA"

PUSH_END=$(date +%s)
PUSH_DURATION=$((PUSH_END - PUSH_START))
print_success "Push completed in ${PUSH_DURATION}s"

# ==============================================================================
# Deploy (optional)
# ==============================================================================

if [ "$DEPLOY" = true ]; then
    echo ""
    print_step "Deploying to Container App: $APP_NAME"

    az containerapp update \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --image "$IMAGE_FULL"

    print_success "Deployment triggered"

    # Get app URL
    APP_URL=$(az containerapp show \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.configuration.ingress.fqdn" -o tsv)

    if [ -n "$APP_URL" ]; then
        echo ""
        print_success "App URL: https://$APP_URL"
        print_success "UI URL: https://$APP_URL/ui"
    fi
fi

# ==============================================================================
# Summary
# ==============================================================================

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Build Complete${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Image:    $IMAGE_FULL"
echo "  SHA Tag:  $IMAGE_SHA"
echo "  Platform: $PLATFORM"
echo ""

if [ "$DEPLOY" = false ]; then
    echo "To deploy manually:"
    echo "  az containerapp update \\"
    echo "    --name <APP_NAME> \\"
    echo "    --resource-group <RESOURCE_GROUP> \\"
    echo "    --image $IMAGE_FULL"
    echo ""
fi
