#!/bin/bash
# ==============================================================================
# Update AgentGateway Config (Hot Reload)
# ==============================================================================
# Uploads config to Azure Files, triggering automatic hot-reload.
# No container restart needed - file watcher picks up changes within 250ms.
#
# Usage:
#   ./scripts/update-config.sh [dev|staging|prod] [config-file]
#
# Examples:
#   ./scripts/update-config.sh dev                    # Upload azure-config.yaml to dev
#   ./scripts/update-config.sh dev ./custom.yaml      # Upload custom file to dev
#   ./scripts/update-config.sh prod ./prod-config.yaml
# ==============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="${1:-dev}"
CONFIG_FILE="${2:-azure-config.yaml}"
SHARE_NAME="agentgateway-config"

# Storage account naming convention (must match terraform)
case "$ENVIRONMENT" in
  dev)
    STORAGE_ACCOUNT="unitoneagwdevcfg"
    ;;
  staging)
    STORAGE_ACCOUNT="unitoneagwstagingcfg"
    ;;
  prod)
    STORAGE_ACCOUNT="unitoneagwprodcfg"
    ;;
  *)
    echo -e "${RED}Error: Invalid environment '$ENVIRONMENT'${NC}"
    echo "Usage: $0 [dev|staging|prod] [config-file]"
    exit 1
    ;;
esac

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}AgentGateway Config Update (Hot Reload)${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "Environment:     ${GREEN}$ENVIRONMENT${NC}"
echo -e "Config file:     ${GREEN}$CONFIG_FILE${NC}"
echo -e "Storage account: ${GREEN}$STORAGE_ACCOUNT${NC}"
echo -e "File share:      ${GREEN}$SHARE_NAME${NC}"
echo ""

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Config file not found: $CONFIG_FILE${NC}"
    exit 1
fi

# Validate YAML syntax
echo -e "${YELLOW}Validating YAML syntax...${NC}"
if command -v python3 &> /dev/null; then
    python3 -c "import yaml; yaml.safe_load(open('$CONFIG_FILE'))" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Invalid YAML syntax in $CONFIG_FILE${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ YAML syntax valid${NC}"
elif command -v yq &> /dev/null; then
    yq eval '.' "$CONFIG_FILE" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Invalid YAML syntax in $CONFIG_FILE${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ YAML syntax valid${NC}"
else
    echo -e "${YELLOW}⚠ Skipping YAML validation (python3/yq not found)${NC}"
fi

# Check Azure CLI login
echo -e "${YELLOW}Checking Azure CLI authentication...${NC}"
if ! az account show &> /dev/null; then
    echo -e "${RED}Error: Not logged in to Azure CLI${NC}"
    echo "Run: az login"
    exit 1
fi
echo -e "${GREEN}✓ Azure CLI authenticated${NC}"

# Get storage account key
echo -e "${YELLOW}Getting storage account key...${NC}"
STORAGE_KEY=$(az storage account keys list \
    --account-name "$STORAGE_ACCOUNT" \
    --query '[0].value' \
    --output tsv 2>/dev/null)

if [ -z "$STORAGE_KEY" ]; then
    echo -e "${RED}Error: Could not get storage account key${NC}"
    echo "Make sure the storage account '$STORAGE_ACCOUNT' exists and you have access."
    echo ""
    echo "If config mount is not enabled yet, run:"
    echo "  cd terraform/environments/$ENVIRONMENT/agentgateway"
    echo "  terraform apply"
    exit 1
fi
echo -e "${GREEN}✓ Storage key retrieved${NC}"

# Upload config file
echo -e "${YELLOW}Uploading config to Azure Files...${NC}"
az storage file upload \
    --account-name "$STORAGE_ACCOUNT" \
    --account-key "$STORAGE_KEY" \
    --share-name "$SHARE_NAME" \
    --source "$CONFIG_FILE" \
    --path "config.yaml" \
    --output none

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Config uploaded successfully${NC}"
else
    echo -e "${RED}Error: Failed to upload config${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✓ Config Update Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "AgentGateway will auto-reload within ${YELLOW}250ms${NC}."
echo -e "No container restart needed."
echo ""
echo -e "To verify, check the logs:"
echo -e "  ${BLUE}az containerapp logs show --name unitone-agw-$ENVIRONMENT-app --resource-group mcp-gateway-$ENVIRONMENT-rg --follow${NC}"
echo ""
echo -e "Look for: ${GREEN}\"Config file changed, reloading...\"${NC}"
echo -e "Followed by: ${GREEN}\"Config reloaded successfully\"${NC}"
