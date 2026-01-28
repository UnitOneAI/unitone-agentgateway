#!/bin/bash
# ==============================================================================
# UnitOne AgentGateway - Interactive Setup
# ==============================================================================
#
# This script guides you through setting up UnitOne AgentGateway on Azure.
# It will prompt for required configuration and generate terraform.tfvars.
#
# Usage:
#   ./setup.sh
#
# ==============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_step() { echo -e "${CYAN}▶${NC} $1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }

prompt() {
    local var_name=$1
    local prompt_text=$2
    local default_value=$3
    local is_secret=${4:-false}

    if [ -n "$default_value" ]; then
        prompt_text="$prompt_text [$default_value]"
    fi

    if [ "$is_secret" = true ]; then
        read -sp "$prompt_text: " value
        echo ""
    else
        read -p "$prompt_text: " value
    fi

    if [ -z "$value" ] && [ -n "$default_value" ]; then
        value="$default_value"
    fi

    eval "$var_name='$value'"
}

prompt_yes_no() {
    local prompt_text=$1
    local default=${2:-n}

    if [ "$default" = "y" ]; then
        read -p "$prompt_text [Y/n]: " response
        response=${response:-y}
    else
        read -p "$prompt_text [y/N]: " response
        response=${response:-n}
    fi

    [[ "$response" =~ ^[Yy] ]]
}

# ==============================================================================
# Main Setup
# ==============================================================================

echo ""
echo -e "${BOLD}${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║${NC}   ${BOLD}${CYAN}UnitOne AgentGateway - Interactive Setup${NC}              ${BOLD}${BLUE}║${NC}"
echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

print_info "This wizard will help you configure UnitOne AgentGateway for Azure."
print_info "Your settings will be saved to terraform/terraform.tfvars"
echo ""

# Check prerequisites
print_header "Checking Prerequisites"

if ! command -v az &> /dev/null; then
    print_error "Azure CLI not found. Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi
print_success "Azure CLI installed"

if ! az account show &> /dev/null; then
    print_warning "Not logged in to Azure. Running 'az login'..."
    az login
fi
SUBSCRIPTION=$(az account show --query name -o tsv)
print_success "Logged in to Azure: $SUBSCRIPTION"

if ! command -v terraform &> /dev/null; then
    print_error "Terraform not found. Install from: https://www.terraform.io/downloads"
    exit 1
fi
print_success "Terraform installed"

# ==============================================================================
# Basic Configuration
# ==============================================================================

print_header "Basic Configuration"

prompt ENVIRONMENT "Environment (dev/staging/prod)" "dev"
prompt LOCATION "Azure region" "eastus2"
prompt BASE_NAME "Resource name prefix (lowercase, no spaces)" "unitone-agw"
prompt RESOURCE_GROUP "Resource group name" "agentgateway-${ENVIRONMENT}-rg"

echo ""
print_info "Optional: Use a deployment stamp for multiple deployments in the same environment"
print_info "  Examples: '01', 'primary', 'test' → creates resources like ${BASE_NAME}-${ENVIRONMENT}-01"
prompt DEPLOYMENT_STAMP "Deployment stamp (leave empty for single deployment)" ""

echo ""
if [ -n "$DEPLOYMENT_STAMP" ]; then
    print_info "Resources will be created in: $RESOURCE_GROUP ($LOCATION) with stamp '$DEPLOYMENT_STAMP'"
else
    print_info "Resources will be created in: $RESOURCE_GROUP ($LOCATION)"
fi

# Check if resource group exists
if az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    print_success "Resource group exists: $RESOURCE_GROUP"
else
    if prompt_yes_no "Resource group doesn't exist. Create it?"; then
        az group create --name "$RESOURCE_GROUP" --location "$LOCATION" > /dev/null
        print_success "Created resource group: $RESOURCE_GROUP"
    else
        print_warning "You'll need to create the resource group before running terraform"
    fi
fi

# ==============================================================================
# Authentication Configuration
# ==============================================================================

print_header "Authentication Configuration"

print_info "UnitOne AgentGateway supports OAuth authentication via Azure Easy Auth."
print_info "You can configure Microsoft (Azure AD), Google, and/or GitHub."
echo ""

if prompt_yes_no "Enable authentication (Easy Auth)?"; then
    CONFIGURE_AUTH=true
    ALLOW_ANONYMOUS=false

    echo ""
    print_info "For each OAuth provider, you'll need:"
    print_info "  - Client ID (from OAuth app registration)"
    print_info "  - Client Secret (from OAuth app registration)"
    echo ""

    # Microsoft (Azure AD)
    if prompt_yes_no "Configure Microsoft (Azure AD) authentication?" "y"; then
        echo ""
        print_info "Create an app registration at:"
        print_info "  ${CYAN}https://portal.azure.com → Azure Active Directory → App registrations → New${NC}"
        echo ""
        print_info "Settings to use:"
        print_info "  Name: UnitOne AgentGateway (or your choice)"
        print_info "  Supported account types: Choose based on your needs"
        print_info "  Redirect URI: Web → https://<app-name>.azurecontainerapps.io/.auth/login/aad/callback"
        print_info "  (You'll get the exact URL after deployment - you can update it then)"
        echo ""
        print_info "After creating, go to 'Certificates & secrets' → 'New client secret'"
        echo ""
        prompt MICROSOFT_CLIENT_ID "Microsoft Client ID (Application ID)"
        prompt MICROSOFT_CLIENT_SECRET "Microsoft Client Secret" "" true
    fi

    # Google
    echo ""
    if prompt_yes_no "Configure Google authentication?"; then
        echo ""
        print_info "Create OAuth credentials at:"
        print_info "  ${CYAN}https://console.cloud.google.com → APIs & Services → Credentials${NC}"
        echo ""
        print_info "Settings to use:"
        print_info "  Application type: Web application"
        print_info "  Authorized redirect URIs: https://<app-name>.azurecontainerapps.io/.auth/login/google/callback"
        print_info "  (You'll get the exact URL after deployment)"
        echo ""
        prompt GOOGLE_CLIENT_ID "Google Client ID"
        prompt GOOGLE_CLIENT_SECRET "Google Client Secret" "" true
    fi

    # GitHub
    echo ""
    if prompt_yes_no "Configure GitHub authentication?"; then
        echo ""
        print_info "Create OAuth app at:"
        print_info "  ${CYAN}https://github.com/settings/developers → OAuth Apps → New${NC}"
        echo ""
        print_info "Settings to use:"
        print_info "  Application name: UnitOne AgentGateway"
        print_info "  Homepage URL: https://<app-name>.azurecontainerapps.io"
        print_info "  Authorization callback URL: https://<app-name>.azurecontainerapps.io/.auth/login/github/callback"
        print_info "  (You'll get the exact URL after deployment)"
        echo ""
        prompt GITHUB_CLIENT_ID "GitHub Client ID"
        prompt GITHUB_CLIENT_SECRET "GitHub Client Secret" "" true
    fi
else
    CONFIGURE_AUTH=false
    ALLOW_ANONYMOUS=true
    print_warning "Authentication disabled - anyone can access the gateway"
fi

# ==============================================================================
# Client Certificate (mTLS) Configuration
# ==============================================================================

print_header "Client Certificate Configuration (mTLS)"

print_info "Client certificates provide mutual TLS authentication for service-to-service communication."
echo ""
echo "  ignore  - Don't request client certificates (default)"
echo "  accept  - Accept client certificates if provided, but don't require them"
echo "  require - Require valid client certificates for all requests"
echo ""

if prompt_yes_no "Configure client certificate authentication (mTLS)?"; then
    echo ""
    PS3="Select client certificate mode: "
    select mode in "ignore" "accept" "require"; do
        case $mode in
            ignore|accept|require)
                CLIENT_CERT_MODE=$mode
                print_success "Client certificate mode: $CLIENT_CERT_MODE"
                break
                ;;
            *)
                print_error "Invalid selection"
                ;;
        esac
    done
else
    CLIENT_CERT_MODE="ignore"
fi

# ==============================================================================
# CI/CD Configuration
# ==============================================================================

print_header "CI/CD Configuration (Optional)"

print_info "You can enable automatic builds when you push to GitHub."
print_info "This requires a GitHub Personal Access Token with repo access."
echo ""

if prompt_yes_no "Enable CI/CD automation (ACR Tasks)?"; then
    prompt GITHUB_REPO_URL "GitHub repository URL" "https://github.com/YOUR_ORG/unitone-agentgateway.git"
    echo ""
    print_info "Create a GitHub PAT at: https://github.com/settings/tokens"
    print_info "Required scopes: repo (full control)"
    prompt GITHUB_PAT "GitHub Personal Access Token" "" true
else
    GITHUB_REPO_URL=""
    GITHUB_PAT=""
fi

# ==============================================================================
# Generate terraform.tfvars
# ==============================================================================

print_header "Generating Configuration"

TFVARS_FILE="terraform/terraform.tfvars"

cat > "$TFVARS_FILE" << EOF
# UnitOne AgentGateway - Terraform Configuration
# Generated by setup.sh on $(date)
#
# IMPORTANT: This file contains secrets. Do not commit to git!

# Basic Configuration
environment         = "$ENVIRONMENT"
location            = "$LOCATION"
base_name           = "$BASE_NAME"
resource_group_name = "$RESOURCE_GROUP"
deployment_stamp    = "$DEPLOYMENT_STAMP"

# Authentication
configure_auth         = $CONFIGURE_AUTH
allow_anonymous_access = $ALLOW_ANONYMOUS
EOF

if [ -n "$MICROSOFT_CLIENT_ID" ]; then
    cat >> "$TFVARS_FILE" << EOF

# Microsoft (Azure AD) OAuth
microsoft_client_id     = "$MICROSOFT_CLIENT_ID"
microsoft_client_secret = "$MICROSOFT_CLIENT_SECRET"
EOF
fi

if [ -n "$GOOGLE_CLIENT_ID" ]; then
    cat >> "$TFVARS_FILE" << EOF

# Google OAuth
google_client_id     = "$GOOGLE_CLIENT_ID"
google_client_secret = "$GOOGLE_CLIENT_SECRET"
EOF
fi

if [ -n "$GITHUB_CLIENT_ID" ]; then
    cat >> "$TFVARS_FILE" << EOF

# GitHub OAuth
github_client_id     = "$GITHUB_CLIENT_ID"
github_client_secret = "$GITHUB_CLIENT_SECRET"
EOF
fi

if [ -n "$GITHUB_PAT" ]; then
    cat >> "$TFVARS_FILE" << EOF

# CI/CD Automation
github_repo_url = "$GITHUB_REPO_URL"
github_pat      = "$GITHUB_PAT"
EOF
fi

if [ "$CLIENT_CERT_MODE" != "ignore" ]; then
    cat >> "$TFVARS_FILE" << EOF

# Client Certificate (mTLS)
client_certificate_mode = "$CLIENT_CERT_MODE"
EOF
fi

print_success "Configuration saved to: $TFVARS_FILE"

# Ensure tfvars is gitignored
if ! grep -q "terraform.tfvars" .gitignore 2>/dev/null; then
    echo "terraform/terraform.tfvars" >> .gitignore
    print_success "Added terraform.tfvars to .gitignore"
fi

# ==============================================================================
# Next Steps
# ==============================================================================

print_header "Setup Complete!"

echo -e "${GREEN}Your configuration has been saved.${NC}"
echo ""
echo -e "${BOLD}Next Steps:${NC}"
echo ""
echo "  1. Review your configuration:"
echo -e "     ${CYAN}cat terraform/terraform.tfvars${NC}"
echo ""
echo "  2. Deploy to Azure:"
echo -e "     ${CYAN}cd terraform${NC}"
echo -e "     ${CYAN}terraform init${NC}"
echo -e "     ${CYAN}terraform plan${NC}"
echo -e "     ${CYAN}terraform apply${NC}"
echo ""
echo "  3. Build and push the container image (choose one method):"
echo ""
if [ -n "$GITHUB_PAT" ]; then
    echo -e "     ${GREEN}Option A: ACR Tasks (Automatic - configured!)${NC}"
    echo "     Push to main branch → builds automatically"
    echo ""
fi
echo -e "     ${CYAN}Option B: ACR Cloud Build (no local Docker needed)${NC}"
echo -e "     ACR_NAME=\$(cd terraform && terraform output -raw acr_name)"
echo -e "     az acr build --registry \$ACR_NAME --image unitone-agentgateway:latest -f Dockerfile.acr ."
echo ""
echo -e "     ${CYAN}Option C: VM-Based Build (fastest for iteration)${NC}"
echo -e "     ./scripts/build-on-vm.sh --acr-name \$ACR_NAME"
echo -e "     # Add --deploy --resource-group RG --app-name APP to also deploy"
echo ""
echo "  4. Access your gateway:"
echo -e "     ${CYAN}cd terraform && terraform output ui_url${NC}"
echo ""

if [ "$CONFIGURE_AUTH" = true ]; then
    echo -e "${YELLOW}⚠ After deployment, update your OAuth apps with the correct callback URLs:${NC}"
    echo ""
    echo "  Run this command to get your callback URLs:"
    echo -e "     ${CYAN}cd terraform && terraform output | grep callback${NC}"
    echo ""
    echo "  Then update your OAuth app registrations:"
    if [ -n "$MICROSOFT_CLIENT_ID" ]; then
        echo "  - Microsoft: Azure Portal → App registrations → Your app → Authentication → Redirect URIs"
    fi
    if [ -n "$GOOGLE_CLIENT_ID" ]; then
        echo "  - Google: Cloud Console → Credentials → Your OAuth client → Authorized redirect URIs"
    fi
    if [ -n "$GITHUB_CLIENT_ID" ]; then
        echo "  - GitHub: Settings → Developer settings → OAuth Apps → Your app → Authorization callback URL"
    fi
    echo ""
    echo "  Easy Auth is configured automatically by Terraform - no manual Azure Portal setup needed!"
    echo ""
fi

echo -e "${BOLD}Run E2E tests locally:${NC}"
echo -e "     ${CYAN}./deploy.sh${NC}"
echo ""
