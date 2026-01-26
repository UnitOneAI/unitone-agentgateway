#!/bin/bash
# Fast build script using Azure VM with layered Docker cache
#
# Usage: ./scripts/fast-build.sh [dev|staging|prod]
#
# This script:
# 1. Starts the build VM (1-2 min)
# 2. Runs layered build on native Linux (3-5 min)
# 3. Pushes to ACR and deploys
# 4. VM auto-shuts down after 30 min of inactivity
#
# Total time: 4-7 minutes vs 15-25 minutes with ACR

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENV="${1:-dev}"
RESOURCE_GROUP="mcp-gateway-dev-rg"
VM_NAME="agentgateway-builder"
REPO_URL="https://github.com/unitone-ai/unitone-agentgateway.git"  # Update with your repo URL

# Validate environment
case "$ENV" in
  dev|staging|prod)
    ;;
  *)
    echo -e "${RED}Error: Invalid environment '$ENV'${NC}"
    echo "Usage: $0 [dev|staging|prod]"
    exit 1
    ;;
esac

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Fast Build for $ENV${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Step 1: Start VM
echo -e "${YELLOW}Step 1: Starting build VM...${NC}"
START_TIME=$(date +%s)

# Check if VM is already running
VM_STATE=$(az vm get-instance-view --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --query "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus" -o tsv)

if [ "$VM_STATE" = "VM running" ]; then
    echo -e "${GREEN}✓ VM already running${NC}"
else
    echo "  Starting VM (this takes 1-2 minutes)..."
    az vm start --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --no-wait --output none

    # Wait for VM to be ready
    echo "  Waiting for VM to boot..."
    az vm wait --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --custom "instanceView.statuses[?code=='PowerState/running']" --timeout 120 --output none || true

    echo -e "${GREEN}✓ VM started${NC}"
fi

# Get VM IP address
VM_IP=$(az vm show --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --show-details --query publicIps -o tsv)

# Wait for SSH to be ready
echo "  Waiting for SSH to be ready..."
MAX_SSH_WAIT=120
SSH_WAIT_START=$(date +%s)
while true; do
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 azureuser@$VM_IP 'echo "SSH ready"' >/dev/null 2>&1; then
        echo -e "${GREEN}✓ SSH ready${NC}"
        break
    fi

    ELAPSED=$(($(date +%s) - SSH_WAIT_START))
    if [ $ELAPSED -ge $MAX_SSH_WAIT ]; then
        echo -e "${RED}Error: SSH not ready after ${MAX_SSH_WAIT}s${NC}"
        exit 1
    fi

    echo "    Waiting for SSH... (${ELAPSED}s elapsed)"
    sleep 5
done

VM_START_TIME=$(($(date +%s) - START_TIME))
echo ""

# Step 2: Run build on VM
echo -e "${YELLOW}Step 2: Running Docker build on VM...${NC}"
BUILD_START=$(date +%s)

# Get current commit
COMMIT_HASH=$(git rev-parse --short HEAD)

# Ensure git submodules are checked out locally before syncing
echo "  Ensuring git submodules are checked out..."
git submodule update --init --recursive

# Sync code to VM using tar+ssh (fastest and most reliable method)
echo "  Syncing code to VM using tar+ssh..."
ssh -o StrictHostKeyChecking=no azureuser@$VM_IP 'mkdir -p /home/azureuser/workspace/unitone-agentgateway'

# Create tar archive locally and extract on VM in one pipeline
# This preserves all directory structures and is faster than rsync
# COPYFILE_DISABLE=1 suppresses macOS extended attributes warnings on Linux
COPYFILE_DISABLE=1 tar czf - \
  --exclude='target' \
  --exclude='node_modules' \
  --exclude='.git' \
  --exclude='.dockerignore' \
  . | ssh -o StrictHostKeyChecking=no azureuser@$VM_IP \
  "cd /home/azureuser/workspace/unitone-agentgateway && tar xzf -"

echo "✓ Code synced successfully"

# Create the build script with ENV substituted
cat > /tmp/remote-build.sh <<'BUILD_SCRIPT'
#!/bin/bash
set -euo pipefail

echo "=== Setting up workspace ==="
cd /home/azureuser/workspace/unitone-agentgateway

echo "=== Authenticating to ACR using Managed Identity ==="

# First, login using managed identity
echo "Logging in with managed identity..."
az login --identity || {
    echo "Failed to login with managed identity"
    exit 1
}

# Set the correct subscription explicitly
echo "Setting subscription to 398d3082-298e-4633-9a4a-816c025965ee..."
az account set --subscription 398d3082-298e-4633-9a4a-816c025965ee

ACR_NAME="unitoneagw${ENV_VALUE}acr"
REGISTRY="${ACR_NAME}.azurecr.io"

# Now login to ACR using the authenticated managed identity
echo "Logging in to ACR: $ACR_NAME..."
az acr login --name $ACR_NAME || {
    echo "Failed to login to ACR"
    echo "Ensure the VM identity has AcrPush role on $ACR_NAME"
    echo "Also ensure the VM identity has Reader role at subscription level"
    exit 1
}

echo "✓ Successfully authenticated to ACR: $ACR_NAME"

echo "=== Building Docker image using Dockerfile.acr ==="
# Build using Dockerfile.acr (not the layered approach which doesn't work with submodules)
# Use --no-cache to ensure fresh build with latest UI files
COMMIT_HASH="${COMMIT_HASH_VALUE}"
docker build \
  --no-cache \
  -f Dockerfile.acr \
  -t $REGISTRY/unitone-agentgateway:$COMMIT_HASH \
  -t $REGISTRY/unitone-agentgateway:latest \
  --platform linux/amd64 \
  .

echo "=== Pushing images to ACR ==="
docker push $REGISTRY/unitone-agentgateway:$COMMIT_HASH
docker push $REGISTRY/unitone-agentgateway:latest

echo "=== Build and push complete ==="
BUILD_SCRIPT

# Substitute ENV_VALUE and COMMIT_HASH_VALUE in the script (portable for macOS and Linux)
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS requires empty string after -i
  sed -i '' "s/\${ENV_VALUE}/$ENV/g" /tmp/remote-build.sh
  sed -i '' "s/\${COMMIT_HASH_VALUE}/$COMMIT_HASH/g" /tmp/remote-build.sh
else
  # Linux doesn't use empty string
  sed -i "s/\${ENV_VALUE}/$ENV/g" /tmp/remote-build.sh
  sed -i "s/\${COMMIT_HASH_VALUE}/$COMMIT_HASH/g" /tmp/remote-build.sh
fi

# Run build script on VM
echo "  Uploading build script..."

# Upload script
scp -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -o ServerAliveCountMax=120 /tmp/remote-build.sh azureuser@$VM_IP:/tmp/remote-build.sh

echo "  Executing build..."
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -o ServerAliveCountMax=120 azureuser@$VM_IP 'bash /tmp/remote-build.sh' || {
    echo ""
    echo -e "${RED}Build failed!${NC}"
    echo ""
    echo "Check the VM logs for details. To debug:"
    echo ""
    echo "  VM_IP=\$(az vm show --resource-group $RESOURCE_GROUP --name $VM_NAME --show-details --query publicIps -o tsv)"
    echo "  ssh azureuser@\$VM_IP"
    echo ""
    exit 1
}

rm /tmp/remote-build.sh

BUILD_TIME=$(($(date +%s) - BUILD_START))
echo -e "${GREEN}✓ Build completed in ${BUILD_TIME}s${NC}"
echo ""

# Step 3: Force Container App to pull latest image
echo -e "${YELLOW}Step 3: Updating Azure Container App...${NC}"
UPDATE_START=$(date +%s)

# Map environment to resource group and app name
case "$ENV" in
  dev)
    APP_NAME="unitone-agw-dev-app"
    APP_RG="mcp-gateway-dev-rg"
    ;;
  staging)
    APP_NAME="unitone-agw-staging-app"
    APP_RG="mcp-gateway-staging-rg"
    ;;
  prod)
    APP_NAME="unitone-agw-prod-app"
    APP_RG="mcp-gateway-prod-rg"
    ;;
esac

echo "  Triggering container update for $APP_NAME..."
az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$APP_RG" \
  --output none || {
    echo -e "${RED}Warning: Container app update failed${NC}"
    echo "The image was pushed to ACR, but the container app may need manual restart"
}

UPDATE_TIME=$(($(date +%s) - UPDATE_START))
echo -e "${GREEN}✓ Container app updated in ${UPDATE_TIME}s${NC}"
echo ""

# Calculate total time
TOTAL_TIME=$(($(date +%s) - START_TIME))

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✓ Fast Build Complete!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Summary:"
echo "  Environment: $ENV"
echo "  Commit: $COMMIT_HASH"
echo "  VM start time: ${VM_START_TIME}s"
echo "  Build time: ${BUILD_TIME}s"
echo "  Total time: ${TOTAL_TIME}s"
echo ""
echo "Speed comparison:"
echo "  Traditional ACR build: ~15-25 minutes"
echo "  Fast build with VM: ~${TOTAL_TIME}s ($(((1200 - TOTAL_TIME) * 100 / 1200))% faster)"
echo ""
echo "Note: VM will remain running until explicitly stopped"
echo ""
echo "To stop the VM:"
echo "  ${YELLOW}az vm deallocate --resource-group $RESOURCE_GROUP --name $VM_NAME${NC}"
echo ""
