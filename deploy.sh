#!/bin/bash
# ==============================================================================
# UnitOne AgentGateway - Local E2E Test Script
# ==============================================================================
#
# Runs E2E tests locally using Docker. For production deployments, use Terraform.
#
# Usage:
#   ./deploy.sh [OPTIONS]
#
# Options:
#   --skip-build       Skip ACR build, use existing image
#   --skip-tests       Start services but skip running tests
#   --clean            Clean up containers before starting
#   --registry NAME    ACR registry name (default from ACR_REGISTRY env var)
#   --tag TAG          Image tag (default: latest)
#   --stop             Stop running services and exit
#   -h, --help         Show this help message
#
# Examples:
#   ./deploy.sh                    # Full: build + deploy + test
#   ./deploy.sh --skip-build       # Use existing ACR image
#   ./deploy.sh --skip-tests       # Start services only
#   ./deploy.sh --stop             # Stop services
#
# Production Deployment:
#   For production, use Terraform:
#   cd terraform && terraform apply
#
# ==============================================================================

set -e

# Configuration
REGISTRY="${REGISTRY:-${ACR_REGISTRY:-agwimages}}"
TAG="${TAG:-latest}"
SKIP_BUILD=false
SKIP_TESTS=false
CLEAN=false
STOP_ONLY=false

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ==============================================================================
# Helper Functions
# ==============================================================================

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

show_help() {
    cat << 'HELP'
AgentGateway - Local E2E Test Script

Runs E2E tests locally using Docker. For production deployments, use Terraform.

Usage:
  ./deploy.sh [OPTIONS]

Options:
  --skip-build       Skip ACR build, use existing image
  --skip-tests       Start services but skip running tests
  --clean            Clean up containers before starting
  --registry NAME    ACR registry name (default: ACR_REGISTRY env or agwimages)
  --tag TAG          Image tag (default: latest)
  --stop             Stop running services and exit
  -h, --help         Show this help message

Examples:
  ./deploy.sh                    # Full: build + deploy + test
  ./deploy.sh --skip-build       # Use existing ACR image
  ./deploy.sh --skip-tests       # Start services only
  ./deploy.sh --stop             # Stop services

Production Deployment:
  For production, use Terraform:
  cd ../terraform/environments/dev/agentgateway && terraform apply
HELP
    exit 0
}

check_command() {
    command -v "$1" &> /dev/null
}

# ==============================================================================
# Parse Arguments
# ==============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --registry) REGISTRY="$2"; shift 2 ;;
        --tag) TAG="$2"; shift 2 ;;
        --skip-build) SKIP_BUILD=true; shift ;;
        --skip-tests) SKIP_TESTS=true; shift ;;
        --clean) CLEAN=true; shift ;;
        --stop) STOP_ONLY=true; shift ;;
        -h|--help) show_help ;;
        *) print_error "Unknown option: $1"; exit 1 ;;
    esac
done

# ==============================================================================
# Stop Services
# ==============================================================================

stop_services() {
    print_header "Stopping Services"
    cd tests/docker
    docker compose down -v 2>/dev/null || true
    print_success "Services stopped"
    exit 0
}

[ "$STOP_ONLY" = true ] && stop_services

# ==============================================================================
# Prerequisites Check
# ==============================================================================

check_prerequisites() {
    print_header "Checking Prerequisites"
    local failed=0

    print_step "Checking Azure CLI..."
    if check_command "az"; then
        print_success "Azure CLI installed"
        if az account show &> /dev/null; then
            print_success "Logged in: $(az account show --query name -o tsv)"
        else
            print_warning "Not logged in (run: az login)"
            failed=1
        fi
    else
        print_error "Azure CLI not installed"
        failed=1
    fi

    print_step "Checking Docker..."
    if check_command "docker" && docker info &> /dev/null; then
        print_success "Docker running"
    else
        print_error "Docker not running"
        failed=1
    fi

    print_step "Checking Docker Compose..."
    if docker compose version &> /dev/null; then
        print_success "Docker Compose available"
    else
        print_error "Docker Compose not available"
        failed=1
    fi

    print_step "Checking submodule..."
    if [ -f "agentgateway/Cargo.toml" ]; then
        print_success "Submodule: $(cd agentgateway && git rev-parse --short HEAD)"
    else
        print_error "Submodule not initialized (run: git submodule update --init)"
        failed=1
    fi

    print_step "Checking test servers..."
    if [ -f "testservers/Dockerfile" ]; then
        print_success "Test servers found"
    else
        print_error "Test servers not found"
        failed=1
    fi

    [ $failed -eq 1 ] && { print_error "Prerequisites failed"; exit 1; }
    print_success "All prerequisites met"
}

# ==============================================================================
# ACR Build
# ==============================================================================

build_in_acr() {
    print_header "Building in ACR"

    print_info "Registry: ${REGISTRY}.azurecr.io"
    print_info "Image: unitone-agentgateway:${TAG}"
    echo ""

    print_step "Logging in to ACR..."
    az acr login --name "$REGISTRY" || { print_error "ACR login failed"; exit 1; }
    print_success "Logged in"

    # Clean large target directory
    if [ -d "agentgateway/target" ]; then
        local size=$(du -sm agentgateway/target 2>/dev/null | cut -f1)
        if [ "$size" -gt 1000 ]; then
            print_warning "Cleaning ${size}MB target directory..."
            rm -rf agentgateway/target
        fi
    fi

    print_step "Starting build (20-30 min)..."
    local start=$(date +%s)

    az acr build \
        --registry "$REGISTRY" \
        --image "unitone-agentgateway:${TAG}" \
        --image "unitone-agentgateway:$(date +%Y%m%d-%H%M%S)" \
        --platform linux/amd64 \
        --file Dockerfile.acr .

    local elapsed=$(( $(date +%s) - start ))
    print_success "Build complete in $((elapsed/60))m $((elapsed%60))s"
}

# ==============================================================================
# Run E2E Tests
# ==============================================================================

run_e2e_tests() {
    print_header "E2E Test Mode"

    print_info "Steps:"
    echo "  1. Build in ACR (unless --skip-build)"
    echo "  2. Start test servers + gateway locally"
    echo "  3. Run security guard tests"
    echo ""

    # Clean if requested
    if [ "$CLEAN" = true ]; then
        print_step "Cleaning containers..."
        cd tests/docker && docker compose down -v 2>/dev/null || true
        cd "$SCRIPT_DIR"
        print_success "Cleaned"
    fi

    # Build
    if [ "$SKIP_BUILD" = false ]; then
        build_in_acr
    else
        print_info "Using existing image: ${REGISTRY}.azurecr.io/unitone-agentgateway:${TAG}"
    fi

    # Start services
    print_header "Starting Services"
    cd tests/docker

    print_step "Logging in to ACR..."
    az acr login --name "$REGISTRY" &>/dev/null && print_success "ACR login" || print_warning "ACR login failed"

    print_step "Pulling image..."
    docker compose pull agentgateway 2>&1 && print_success "Pulled" || print_warning "Using cached"

    print_step "Starting containers..."
    docker compose up -d --build mcp-test-servers agentgateway

    print_step "Waiting for healthy..."
    for i in {1..30}; do
        health=$(docker compose ps agentgateway --format json 2>/dev/null | jq -r '.Health // "starting"' 2>/dev/null || echo "starting")
        [ "$health" = "healthy" ] && break
        echo -n "."
        sleep 2
    done
    echo ""

    if [ "$health" = "healthy" ]; then
        print_success "Services healthy"
    else
        print_error "Services unhealthy"
        docker compose logs --tail=20
        exit 1
    fi

    echo ""
    docker compose ps
    echo ""

    # Run tests
    if [ "$SKIP_TESTS" = false ]; then
        print_header "Running Tests"
        docker compose run --rm test-runner
        local code=$?
        echo ""
        [ $code -eq 0 ] && print_success "All tests passed!" || print_error "Tests failed"
    else
        print_info "Skipping tests (--skip-tests)"
    fi

    cd "$SCRIPT_DIR"

    # Summary
    print_header "Summary"
    echo -e "${GREEN}Services running:${NC}"
    echo "  Gateway:  http://localhost:8080"
    echo "  UI:       http://localhost:8080/ui"
    echo ""
    echo -e "${CYAN}Routes with security guards:${NC}"
    echo "  /pii-test   - PII detection + tool poisoning"
    echo "  /poison     - Tool poisoning guard"
    echo "  /rug-pull   - Rug pull guard"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo "  Logs:    cd tests/docker && docker compose logs -f"
    echo "  Retest:  cd tests/docker && docker compose run --rm test-runner"
    echo "  Stop:    ./deploy.sh --stop"
    echo ""
    echo -e "${BLUE}Production deployment:${NC}"
    echo "  Use Terraform: cd ../terraform/environments/dev/agentgateway"
    echo "                 terraform apply"
    echo ""
}

# ==============================================================================
# Main
# ==============================================================================

echo ""
echo -e "${BOLD}${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║${NC}   ${BOLD}${CYAN}UnitOne AgentGateway - Local E2E Testing${NC}            ${BOLD}${BLUE}║${NC}"
echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

print_info "Registry: ${REGISTRY}.azurecr.io"
print_info "Tag: ${TAG}"

check_prerequisites
run_e2e_tests

print_success "Done!"
echo ""
