#!/bin/bash
# ==============================================================================
# Deploy MCP Test Servers - Idempotent Script
# ==============================================================================
#
# Deploys PII, Tool Poisoning, and Rug Pull test servers to Azure Container Apps.
# This script is idempotent - it skips steps that are already completed.
#
# Usage:
#   ./scripts/deploy-test-servers.sh [OPTIONS]
#
# Options:
#   --resource-group, -g    Resource group name (required)
#   --acr-name, -a          ACR name (required)
#   --environment, -e       Container App Environment name (required)
#   --skip-image-build      Skip building the test server image
#   --update-gateway        Update gateway config with test server URLs
#   --help, -h              Show this help message
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
print_skip() { echo -e "${YELLOW}⊘${NC} $1 (already exists)"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }

# Default values
SKIP_IMAGE_BUILD=false
UPDATE_GATEWAY=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --resource-group|-g)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        --acr-name|-a)
            ACR_NAME="$2"
            shift 2
            ;;
        --environment|-e)
            ENVIRONMENT_NAME="$2"
            shift 2
            ;;
        --skip-image-build)
            SKIP_IMAGE_BUILD=true
            shift
            ;;
        --update-gateway)
            UPDATE_GATEWAY=true
            shift
            ;;
        --help|-h)
            head -30 "$0" | tail -25
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$RESOURCE_GROUP" ]] || [[ -z "$ACR_NAME" ]] || [[ -z "$ENVIRONMENT_NAME" ]]; then
    print_error "Missing required parameters"
    echo "Usage: $0 --resource-group <rg> --acr-name <acr> --environment <env>"
    exit 1
fi

ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"
IMAGE_NAME="mcp-test-server"
IMAGE_TAG="latest"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Deploying MCP Test Servers${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
print_info "Resource Group: $RESOURCE_GROUP"
print_info "ACR: $ACR_LOGIN_SERVER"
print_info "Environment: $ENVIRONMENT_NAME"
echo ""

# ==============================================================================
# Step 1: Build and push test server image (if not exists or not skipped)
# ==============================================================================
print_step "Checking test server image..."

IMAGE_EXISTS=$(az acr repository show --name "$ACR_NAME" --image "$IMAGE_NAME:$IMAGE_TAG" 2>/dev/null && echo "true" || echo "false")

if [[ "$IMAGE_EXISTS" == "true" ]] && [[ "$SKIP_IMAGE_BUILD" == "false" ]]; then
    print_skip "Test server image $IMAGE_NAME:$IMAGE_TAG"
elif [[ "$SKIP_IMAGE_BUILD" == "true" ]]; then
    print_skip "Image build skipped by flag"
else
    print_step "Building test server image..."
    if [[ -d "$ROOT_DIR/testservers" ]]; then
        az acr build \
            --registry "$ACR_NAME" \
            --image "$IMAGE_NAME:$IMAGE_TAG" \
            --file "$ROOT_DIR/testservers/Dockerfile.unified" \
            "$ROOT_DIR/testservers" \
            --only-show-errors
        print_success "Test server image built and pushed"
    else
        print_error "testservers directory not found at $ROOT_DIR/testservers"
        exit 1
    fi
fi

# ==============================================================================
# Step 2: Get ACR credentials
# ==============================================================================
print_step "Getting ACR credentials..."
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)
print_success "ACR credentials retrieved"

# ==============================================================================
# Step 3: Deploy test servers (idempotent)
# ==============================================================================

deploy_test_server() {
    local NAME=$1
    local SERVER_TYPE=$2
    local EXTRA_ENVS=${3:-""}

    # Check if container app already exists
    if az containerapp show --name "$NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
        print_skip "Container app $NAME"
        return 0
    fi

    print_step "Creating container app: $NAME (type: $SERVER_TYPE)..."

    ENV_VARS="SERVER_TYPE=$SERVER_TYPE MCP_PORT=8000 MCP_HOST=0.0.0.0"
    if [[ -n "$EXTRA_ENVS" ]]; then
        ENV_VARS="$ENV_VARS $EXTRA_ENVS"
    fi

    az containerapp create \
        --name "$NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --environment "$ENVIRONMENT_NAME" \
        --image "$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG" \
        --registry-server "$ACR_LOGIN_SERVER" \
        --registry-username "$ACR_USERNAME" \
        --registry-password "$ACR_PASSWORD" \
        --target-port 8000 \
        --ingress external \
        --cpu 0.5 --memory 1Gi \
        --min-replicas 1 --max-replicas 1 \
        --env-vars $ENV_VARS \
        --only-show-errors \
        --output none

    print_success "Container app $NAME created"
}

echo ""
print_step "Deploying test servers..."

# Deploy PII test server
deploy_test_server "pii-test-server" "pii"

# Deploy Tool Poisoning test server
deploy_test_server "tool-poisoning-test" "tool-poison"

# Deploy Rug Pull test server
deploy_test_server "rug-pull-test" "rug-pull" "RUG_PULL_TRIGGER=3 RUG_PULL_MODE=remove"

# ==============================================================================
# Step 4: Get test server URLs
# ==============================================================================
echo ""
print_step "Getting test server URLs..."

PII_URL=$(az containerapp show --name pii-test-server --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
POISON_URL=$(az containerapp show --name tool-poisoning-test --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
RUGPULL_URL=$(az containerapp show --name rug-pull-test --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")

echo ""
echo -e "${GREEN}Test Server URLs:${NC}"
echo -e "  PII Test Server:          ${CYAN}https://$PII_URL/mcp${NC}"
echo -e "  Tool Poisoning Test:      ${CYAN}https://$POISON_URL/mcp${NC}"
echo -e "  Rug Pull Test:            ${CYAN}https://$RUGPULL_URL/mcp${NC}"

# ==============================================================================
# Step 5: Update gateway config (optional)
# ==============================================================================
if [[ "$UPDATE_GATEWAY" == "true" ]]; then
    echo ""
    print_step "Updating gateway configuration..."

    CONFIG_FILE="$ROOT_DIR/azure-config.yaml"
    CONFIG_WITH_TESTS="$ROOT_DIR/azure-config-with-tests.yaml"

    # Generate config with test servers
    cat > "$CONFIG_WITH_TESTS" << EOF
# UnitOne AgentGateway - Configuration with Test Servers
# Auto-generated by deploy-test-servers.sh
#
# Test Server URLs:
#   PII: https://$PII_URL/mcp
#   Tool Poisoning: https://$POISON_URL/mcp
#   Rug Pull: https://$RUGPULL_URL/mcp

binds:
- port: 8080
  listeners:
  - hostname: "*"
    name: default
    protocol: HTTP
    routes:
    # UI Dashboard
    - name: ui-route
      matches:
      - path:
          pathPrefix: /ui
      backends:
      - host: 127.0.0.1:15000

    # Admin API
    - name: admin-api-route
      matches:
      - path:
          pathPrefix: /config
      backends:
      - host: 127.0.0.1:15000

    - name: admin-route
      matches:
      - path:
          pathPrefix: /admin
      backends:
      - host: 127.0.0.1:15000

    # MCP route with test servers and security guards
    - name: mcp-with-guards
      matches:
      - path:
          pathPrefix: /mcp
      backends:
      - mcp:
          targets:
          - name: pii-test-server
            mcp:
              host: https://$PII_URL/mcp
          - name: tool-poisoning-test
            mcp:
              host: https://$POISON_URL/mcp
          - name: rug-pull-test
            mcp:
              host: https://$RUGPULL_URL/mcp
          statefulMode: stateful
          securityGuards:
          - id: tool-poisoning
            type: tool_poisoning
            enabled: true
            runs_on:
            - response
          - id: rug-pull
            type: rug_pull
            enabled: true
            runs_on:
            - response
            risk_threshold: 5
          - id: pii-detection
            type: pii
            enabled: true
            runs_on:
            - response
            action: mask
      policies:
        cors:
          allowCredentials: false
          allowHeaders:
          - '*'
          allowMethods:
          - '*'
          allowOrigins:
          - '*'
          exposeHeaders:
          - mcp-session-id
EOF

    # Backup and replace
    if [[ -f "$CONFIG_FILE" ]]; then
        cp "$CONFIG_FILE" "${CONFIG_FILE}.backup"
    fi
    cp "$CONFIG_WITH_TESTS" "$CONFIG_FILE"

    print_success "Gateway config updated with test servers"
    print_info "Config file: $CONFIG_FILE"
    print_info "Backup: ${CONFIG_FILE}.backup"

    echo ""
    print_info "To apply changes, rebuild and redeploy the gateway:"
    echo -e "  ${CYAN}az acr build --registry $ACR_NAME --image unitone-agentgateway:latest -f Dockerfile.acr .${NC}"
    echo -e "  ${CYAN}az containerapp update --name <gateway-app> --resource-group $RESOURCE_GROUP --image $ACR_LOGIN_SERVER/unitone-agentgateway:latest${NC}"
fi

# ==============================================================================
# Summary
# ==============================================================================
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Test Servers Deployment Complete${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
