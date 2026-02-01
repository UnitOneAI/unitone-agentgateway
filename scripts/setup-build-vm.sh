#!/bin/bash
# ==============================================================================
# UnitOne AgentGateway - Build VM Setup Script
# ==============================================================================
#
# Sets up a fresh Linux VM with all dependencies needed to build and deploy
# UnitOne AgentGateway. Run this on a new Azure VM or any Linux build server.
#
# Supported distributions:
#   - Ubuntu 20.04, 22.04, 24.04
#   - Debian 11, 12
#
# What gets installed:
#   - Docker Engine
#   - Azure CLI
#   - Git
#   - jq (for JSON parsing)
#
# Usage:
#   # Download and run (new VM)
#   curl -fsSL https://raw.githubusercontent.com/UnitOneAI/unitone-agentgateway/main/scripts/setup-build-vm.sh | bash
#
#   # Or if you have the repo cloned
#   ./scripts/setup-build-vm.sh
#
# After setup:
#   1. Log out and back in (for docker group)
#   2. az login
#   3. Clone the repo: git clone --recursive https://github.com/UnitOneAI/unitone-agentgateway.git
#   4. Build: ./scripts/build-on-vm.sh --acr-name <YOUR_ACR>
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

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  UnitOne AgentGateway - Build VM Setup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    if ! command -v sudo &> /dev/null; then
        print_error "This script requires root or sudo access"
        exit 1
    fi
    SUDO="sudo"
else
    SUDO=""
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    print_error "Cannot detect OS. This script supports Ubuntu/Debian."
    exit 1
fi

print_step "Detected OS: $OS $VERSION"

if [[ "$OS" != "ubuntu" && "$OS" != "debian" ]]; then
    print_error "Unsupported OS: $OS. This script supports Ubuntu and Debian."
    exit 1
fi

# ==============================================================================
# Update system
# ==============================================================================

print_step "Updating package lists..."
$SUDO apt-get update -qq
print_success "Package lists updated"

# ==============================================================================
# Install basic tools
# ==============================================================================

print_step "Installing basic tools..."
$SUDO apt-get install -y -qq \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    jq \
    unzip
print_success "Basic tools installed"

# ==============================================================================
# Install Docker
# ==============================================================================

if command -v docker &> /dev/null; then
    print_success "Docker already installed: $(docker --version)"
else
    print_step "Installing Docker..."

    # Add Docker's official GPG key
    $SUDO install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$OS/gpg | $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    $SUDO chmod a+r /etc/apt/keyrings/docker.gpg

    # Add Docker repository
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
        $(lsb_release -cs) stable" | $SUDO tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add current user to docker group
    if [ -n "$SUDO_USER" ]; then
        $SUDO usermod -aG docker "$SUDO_USER"
        print_warning "Added $SUDO_USER to docker group. Log out and back in for this to take effect."
    elif [ "$EUID" -ne 0 ]; then
        $SUDO usermod -aG docker "$USER"
        print_warning "Added $USER to docker group. Log out and back in for this to take effect."
    fi

    # Start Docker
    $SUDO systemctl enable docker
    $SUDO systemctl start docker

    print_success "Docker installed: $(docker --version)"
fi

# ==============================================================================
# Install Azure CLI
# ==============================================================================

if command -v az &> /dev/null; then
    print_success "Azure CLI already installed: $(az --version | head -1)"
else
    print_step "Installing Azure CLI..."

    # Install Azure CLI
    curl -sL https://aka.ms/InstallAzureCLIDeb | $SUDO bash

    print_success "Azure CLI installed: $(az --version | head -1)"
fi

# ==============================================================================
# Verify installations
# ==============================================================================

echo ""
print_step "Verifying installations..."
echo ""

echo "  Docker:    $(docker --version 2>/dev/null || echo 'Not available')"
echo "  Azure CLI: $(az --version 2>/dev/null | head -1 || echo 'Not available')"
echo "  Git:       $(git --version 2>/dev/null || echo 'Not available')"
echo "  jq:        $(jq --version 2>/dev/null || echo 'Not available')"

# ==============================================================================
# Summary
# ==============================================================================

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Setup Complete${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Next steps:"
echo ""
echo "  1. Log out and back in (for docker group permissions)"
echo ""
echo "  2. Login to Azure:"
echo "     az login"
echo ""
echo "  3. Clone the repository:"
echo "     git clone --recursive https://github.com/UnitOneAI/unitone-agentgateway.git"
echo "     cd unitone-agentgateway"
echo ""
echo "  4. Build and push to ACR:"
echo "     ./scripts/build-on-vm.sh --acr-name <YOUR_ACR_NAME>"
echo ""
echo "  To get your ACR name from Terraform:"
echo "     cd terraform && terraform output -raw acr_name"
echo ""
