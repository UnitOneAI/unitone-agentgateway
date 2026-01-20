#!/bin/bash
set -e

# Build and Deploy Script for Unitone AgentGateway
# Usage: ./scripts/build-and-deploy.sh [dev|staging|prod]

# Default to dev if no environment specified
ENV=${1:-dev}

# Validate environment
if [[ ! "$ENV" =~ ^(dev|staging|prod)$ ]]; then
    echo "Error: Invalid environment '$ENV'. Must be dev, staging, or prod."
    exit 1
fi

# Get git commit hash for tagging
GIT_HASH=$(cd agentgateway && git rev-parse --short HEAD)

# Environment-specific configuration
case $ENV in
    dev)
        ACR_NAME="unitoneagwdevacr"
        APP_NAME="unitone-agw-dev-app"
        RESOURCE_GROUP="mcp-gateway-dev-rg"
        ;;
    staging)
        ACR_NAME="unitoneagwstagingacr"
        APP_NAME="unitone-agw-staging-app"
        RESOURCE_GROUP="mcp-gateway-staging-rg"
        ;;
    prod)
        ACR_NAME="unitoneagwprodacr"
        APP_NAME="unitone-agw-prod-app"
        RESOURCE_GROUP="mcp-gateway-prod-rg"
        ;;
esac

echo "================================"
echo "Building for environment: $ENV"
echo "Registry: $ACR_NAME"
echo "Image tag: $GIT_HASH"
echo "================================"
echo ""

# Build image in ACR
echo "Starting ACR build..."
az acr build \
  --registry "$ACR_NAME" \
  --image unitone-agentgateway:latest \
  --image "unitone-agentgateway:$ENV-$GIT_HASH" \
  --file Dockerfile.acr \
  --platform linux/amd64 \
  .

if [ $? -ne 0 ]; then
    echo "Error: ACR build failed"
    exit 1
fi

echo ""
echo "================================"
echo "Build complete!"
echo "Images created:"
echo "  - $ACR_NAME.azurecr.io/unitone-agentgateway:latest"
echo "  - $ACR_NAME.azurecr.io/unitone-agentgateway:$ENV-$GIT_HASH"
echo "================================"
echo ""

# Ask if user wants to deploy
read -p "Deploy to Container App $APP_NAME? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Updating Container App..."
    az containerapp update \
      --name "$APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --image "$ACR_NAME.azurecr.io/unitone-agentgateway:latest"

    echo ""
    echo "Deployment complete!"
else
    echo "Skipping deployment."
    echo "To deploy manually, run:"
    echo "  az containerapp update --name $APP_NAME --resource-group $RESOURCE_GROUP --image $ACR_NAME.azurecr.io/unitone-agentgateway:latest"
fi
