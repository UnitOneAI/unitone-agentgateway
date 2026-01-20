#!/bin/bash
# Pre-deployment configuration validation script
# Validates that all required settings are present in azure-config.yaml

set -euo pipefail

CONFIG_FILE="${1:-azure-config.yaml}"
ERRORS=0

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================"
echo "Pre-Deployment Configuration Validation"
echo "Config file: $CONFIG_FILE"
echo "================================================"
echo ""

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}✗ FATAL: Config file not found: $CONFIG_FILE${NC}"
    exit 1
fi

# Function to check if a field exists in YAML
check_field() {
    local field="$1"
    local description="$2"
    local required="${3:-true}"

    if grep -q "^${field}:" "$CONFIG_FILE"; then
        echo -e "${GREEN}✓${NC} $description"
        return 0
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}✗ MISSING REQUIRED: $description${NC}"
            ((ERRORS++))
        else
            echo -e "${YELLOW}⚠ OPTIONAL (missing): $description${NC}"
        fi
        return 1
    fi
}

# Function to check nested field
check_nested_field() {
    local pattern="$1"
    local description="$2"
    local required="${3:-true}"

    if grep -E "$pattern" "$CONFIG_FILE" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $description"
        return 0
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}✗ MISSING REQUIRED: $description${NC}"
            ((ERRORS++))
        else
            echo -e "${YELLOW}⚠ OPTIONAL (missing): $description${NC}"
        fi
        return 1
    fi
}

echo "Checking REQUIRED configuration fields:"
echo "----------------------------------------"

# Core settings
check_field "adminAddr" "Admin server address (required for UI)"

# Check binds section
check_field "binds" "Bind configuration"
check_nested_field "port:" "Port configuration in binds"
check_nested_field "listeners:" "Listeners configuration"

# Check routes
check_nested_field "routes:" "Routes configuration"
check_nested_field "name: ui-route" "UI route configuration"
check_nested_field "name: admin-api-route" "Admin API route configuration"
check_nested_field "name: mcp-route" "MCP route configuration"

# Check MCP backend configuration
check_nested_field "backends:" "Backend configuration"
check_nested_field "mcp:" "MCP backend type"

echo ""
echo "Checking SECURITY configuration:"
echo "----------------------------------------"

# Security guards
if check_nested_field "securityGuards:" "Security guards configuration"; then
    # Check specific guards
    check_nested_field "id: tool-poisoning-detector" "Tool poisoning detector guard" "false"
    check_nested_field "type: tool_poisoning" "Tool poisoning guard type" "false"

    # Check guard settings
    if grep -q "securityGuards:" "$CONFIG_FILE"; then
        check_nested_field "enabled: true" "At least one guard is enabled" "false"
        check_nested_field "runs_on:" "Guard execution trigger (runs_on)" "false"
    fi
fi

# CORS configuration
check_nested_field "cors:" "CORS configuration"
check_nested_field "allowOrigins:" "CORS allow origins" "false"
check_nested_field "allowMethods:" "CORS allow methods" "false"

echo ""
echo "Checking MCP BACKEND configuration:"
echo "----------------------------------------"

# MCP targets
check_nested_field "targets:" "MCP backend targets"
if check_nested_field "- name:" "At least one MCP target defined" "false"; then
    # Check target types
    if ! grep -E "(stdio:|mcp:)" "$CONFIG_FILE" > /dev/null 2>&1; then
        echo -e "${RED}✗ MISSING: No target type (stdio/mcp) defined${NC}"
        ((ERRORS++))
    else
        echo -e "${GREEN}✓${NC} MCP target type defined"
    fi
fi

echo ""
echo "Checking UI configuration:"
echo "----------------------------------------"

# UI route check
if check_nested_field "pathPrefix: /ui" "UI path prefix"; then
    # Check UI backend points to admin server
    if grep -A 5 "name: ui-route" "$CONFIG_FILE" | grep -q "host: 127.0.0.1"; then
        echo -e "${GREEN}✓${NC} UI route points to admin server (localhost)"
    else
        echo -e "${YELLOW}⚠ WARNING: UI route may not point to admin server${NC}"
    fi
fi

# Admin API route check
check_nested_field "pathPrefix: /config" "Admin API path prefix" "false"

echo ""
echo "Validating configuration integrity:"
echo "----------------------------------------"

# Check YAML syntax
if command -v yamllint > /dev/null 2>&1; then
    if yamllint -d relaxed "$CONFIG_FILE" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} YAML syntax is valid"
    else
        echo -e "${YELLOW}⚠ YAML syntax warnings (non-fatal)${NC}"
        yamllint -d relaxed "$CONFIG_FILE" || true
    fi
else
    echo -e "${YELLOW}⚠ yamllint not installed, skipping YAML validation${NC}"
fi

# Check for common mistakes
echo ""
echo "Checking for common configuration mistakes:"
echo "----------------------------------------"

# Check if adminAddr is set to 0.0.0.0 (should be 127.0.0.1)
if grep -q "adminAddr:.*0\.0\.0\.0" "$CONFIG_FILE"; then
    echo -e "${YELLOW}⚠ WARNING: adminAddr set to 0.0.0.0 - should typically be 127.0.0.1${NC}"
fi

# Check if UI is enabled in build (requires Rust feature flag)
echo -e "${YELLOW}ℹ NOTE: Remember to build with '--features ui' flag in Dockerfile${NC}"

# Final summary
echo ""
echo "================================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ Validation PASSED - All required configurations present${NC}"
    echo "================================================"
    exit 0
else
    echo -e "${RED}✗ Validation FAILED - $ERRORS required configurations missing${NC}"
    echo "================================================"
    echo ""
    echo "Fix the missing configurations before deploying."
    echo "See azure-config.yaml for the configuration file."
    exit 1
fi
