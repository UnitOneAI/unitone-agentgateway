# UnitOne AgentGateway Wrapper - Makefile
# Automates build, deployment, and testing workflows
#
# Directory Structure Requirements:
# - This Makefile is in: unitone-agentgateway/
# - Terraform configs in: ../terraform/environments/{ENV}/agentgateway/
# - Submodule in: agentgateway/
#
# CI/CD Setup Requirements:
# Ensure both repositories are checked out as siblings:
#   - actions/checkout@v4 for unitone-agentgateway
#   - actions/checkout@v4 with path: terraform for terraform repo
#
# Example GitHub Actions step:
#   - uses: actions/checkout@v4
#     with:
#       repository: UnitOneAI/terraform
#       path: terraform
#       token: ${{ secrets.GITHUB_TOKEN }}

.PHONY: help build build-ui deploy-dev deploy-staging deploy-prod test test-e2e clean update-submodule terraform-init terraform-plan terraform-apply logs-dev logs-staging logs-prod check-terraform-dir

# Default environment
ENV ?= dev

# Terraform directory (relative to this Makefile)
# Override with: make deploy-dev TERRAFORM_DIR=/custom/path
TERRAFORM_DIR ?= ../terraform/environments

# Check if terraform directory exists
check-terraform-dir:
	@if [ ! -d "$(TERRAFORM_DIR)" ]; then \
		echo "ERROR: Terraform directory not found at: $(TERRAFORM_DIR)"; \
		echo ""; \
		echo "Expected directory structure:"; \
		echo "  parent/"; \
		echo "  ├── unitone-agentgateway/  (this repo)"; \
		echo "  └── terraform/             (sibling repo)"; \
		echo ""; \
		echo "Solutions:"; \
		echo "  1. Clone terraform repo as sibling: git clone <terraform-repo> ../terraform"; \
		echo "  2. Override path: make deploy-dev TERRAFORM_DIR=/path/to/terraform/environments"; \
		echo "  3. For CI/CD: Ensure both repos are checked out (see Makefile comments)"; \
		exit 1; \
	fi

# Default gateway URL
GATEWAY_URL_dev := https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io
GATEWAY_URL_staging := https://unitone-agentgateway-staging.azurecontainerapps.io
GATEWAY_URL_prod := https://unitone-agentgateway-prod.azurecontainerapps.io

# Resource group names
RG_dev := mcp-gateway-dev-rg
RG_staging := mcp-gateway-staging-rg
RG_prod := mcp-gateway-prod-rg

# Container app names
APP_dev := unitone-agentgateway
APP_staging := unitone-agentgateway
APP_prod := unitone-agentgateway

help: ## Show this help message
	@echo "UnitOne AgentGateway - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Examples:"
	@echo "  make build        - Build with UnitOne branding"
	@echo "  make deploy-dev   - Deploy to development"
	@echo "  make test         - Run E2E tests"

# Build targets
build: ## Build agentgateway with UnitOne branding
	@echo "Building agentgateway with UnitOne branding..."
	@if [ ! -d "agentgateway" ]; then \
		echo "Error: agentgateway submodule not initialized"; \
		echo "Run: git submodule update --init --recursive"; \
		exit 1; \
	fi
	@# Apply UI customizations
	@if [ -d "ui-customizations" ] && [ "$(shell ls -A ui-customizations 2>/dev/null)" ]; then \
		echo "Applying UI customizations..."; \
		cp -r ui-customizations/* agentgateway/ui/ 2>/dev/null || true; \
	fi
	@# Build the project
	cd agentgateway && cargo build --release --features ui
	@echo "Build complete!"

build-ui: ## Build only the UI component
	@echo "Building UI with UnitOne branding..."
	cd agentgateway/ui && npm install && npm run build

# Deployment targets
deploy-dev: check-terraform-dir ## Deploy to development environment
	@echo "Deploying to development environment..."
	cd $(TERRAFORM_DIR)/dev/agentgateway && terraform apply -auto-approve

deploy-staging: check-terraform-dir ## Deploy to staging environment
	@echo "Deploying to staging environment..."
	cd $(TERRAFORM_DIR)/staging/agentgateway && terraform apply -auto-approve

deploy-prod: check-terraform-dir ## Deploy to production environment (requires confirmation)
	@echo "WARNING: Deploying to PRODUCTION"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	cd $(TERRAFORM_DIR)/prod/agentgateway && terraform apply

# Testing targets
test: test-e2e ## Run all tests

test-e2e: ## Run E2E tests against development environment
	@echo "Running E2E tests..."
	cd agentgateway/tests && \
	GATEWAY_URL=$(GATEWAY_URL_dev) \
	./test_venv/bin/python3 e2e_mcp_sse_test.py

test-staging: ## Run E2E tests against staging
	@echo "Running E2E tests against staging..."
	cd agentgateway/tests && \
	GATEWAY_URL=$(GATEWAY_URL_staging) \
	./test_venv/bin/python3 e2e_mcp_sse_test.py

# Terraform targets
terraform-init: ## Initialize Terraform for specified environment
	@cd $(TERRAFORM_DIR)/$(ENV)/agentgateway && terraform init

terraform-plan: ## Plan Terraform changes for specified environment
	@cd $(TERRAFORM_DIR)/$(ENV)/agentgateway && terraform plan

terraform-apply: ## Apply Terraform changes for specified environment
	@cd $(TERRAFORM_DIR)/$(ENV)/agentgateway && terraform apply

# Submodule management
update-submodule: ## Update agentgateway submodule to latest
	@echo "Updating agentgateway submodule..."
	cd agentgateway && git pull origin main
	git add agentgateway
	@echo "Submodule updated. Don't forget to commit the change!"

# Logs and monitoring
logs-dev: ## Stream logs from development environment
	az containerapp logs show \
		--name $(APP_dev) \
		--resource-group $(RG_dev) \
		--follow

logs-staging: ## Stream logs from staging environment
	az containerapp logs show \
		--name $(APP_staging) \
		--resource-group $(RG_staging) \
		--follow

logs-prod: ## Stream logs from production environment
	az containerapp logs show \
		--name $(APP_prod) \
		--resource-group $(RG_prod) \
		--follow

# Cleanup targets
clean: ## Clean build artifacts and reset submodule
	@echo "Cleaning build artifacts..."
	cd agentgateway && cargo clean 2>/dev/null || true
	cd agentgateway && git checkout ui/ 2>/dev/null || true
	@echo "Clean complete!"

# Utility targets
status: ## Check deployment status for all environments
	@echo "=== Development ==="
	@az containerapp show --name $(APP_dev) --resource-group $(RG_dev) \
		--query "{Name:name, Status:properties.provisioningState, URL:properties.configuration.ingress.fqdn}" \
		-o table 2>/dev/null || echo "Not deployed"
	@echo ""
	@echo "=== Staging ==="
	@az containerapp show --name $(APP_staging) --resource-group $(RG_staging) \
		--query "{Name:name, Status:properties.provisioningState, URL:properties.configuration.ingress.fqdn}" \
		-o table 2>/dev/null || echo "Not deployed"
	@echo ""
	@echo "=== Production ==="
	@az containerapp show --name $(APP_prod) --resource-group $(RG_prod) \
		--query "{Name:name, Status:properties.provisioningState, URL:properties.configuration.ingress.fqdn}" \
		-o table 2>/dev/null || echo "Not deployed"

.DEFAULT_GOAL := help
