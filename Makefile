# UnitOne AgentGateway - Makefile
# Automates build, deployment, and testing workflows

.PHONY: help build deploy test test-docker test-docker-up test-docker-down clean update-submodule

# Default environment
ENV ?= dev

# Terraform directory
TERRAFORM_DIR ?= terraform

help: ## Show this help message
	@echo "UnitOne AgentGateway - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Examples:"
	@echo "  make test-docker   - Run E2E tests in Docker"
	@echo "  make deploy        - Deploy with Terraform"

# Build targets
build: ## Build agentgateway Docker image locally
	@echo "Building agentgateway..."
	@if [ ! -d "agentgateway" ]; then \
		echo "Error: agentgateway submodule not initialized"; \
		echo "Run: git submodule update --init --recursive"; \
		exit 1; \
	fi
	docker build -f Dockerfile.acr -t agentgateway:local .
	@echo "Build complete!"

# E2E Testing
test: test-docker ## Run all tests

test-docker: ## Run E2E tests using deploy.sh (recommended)
	./deploy.sh --skip-build

test-docker-up: ## Start E2E test services for local testing
	@echo "Starting E2E test services..."
	docker compose -f tests/docker/docker-compose.yaml up -d --build mcp-test-servers agentgateway
	@echo "Waiting for services to be healthy..."
	@sleep 15
	@docker compose -f tests/docker/docker-compose.yaml ps
	@echo ""
	@echo "Services running. Gateway available at http://localhost:8080"

test-docker-down: ## Stop E2E test services
	docker compose -f tests/docker/docker-compose.yaml down -v

test-docker-logs: ## Show logs from E2E test services
	docker compose -f tests/docker/docker-compose.yaml logs -f

# Terraform deployment
deploy: ## Deploy with Terraform (specify ENV=dev|staging|prod)
	@echo "Deploying to $(ENV) environment..."
	cd $(TERRAFORM_DIR) && terraform init && terraform apply -var="environment=$(ENV)"

deploy-plan: ## Plan Terraform changes
	cd $(TERRAFORM_DIR) && terraform plan -var="environment=$(ENV)"

deploy-destroy: ## Destroy Terraform resources
	cd $(TERRAFORM_DIR) && terraform destroy -var="environment=$(ENV)"

# Submodule management
update-submodule: ## Update agentgateway submodule to latest
	@echo "Updating agentgateway submodule..."
	cd agentgateway && git pull origin main
	git add agentgateway
	@echo "Submodule updated. Don't forget to commit the change!"

# Cleanup
clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	docker compose -f tests/docker/docker-compose.yaml down -v 2>/dev/null || true
	cd agentgateway && cargo clean 2>/dev/null || true
	@echo "Clean complete!"

.DEFAULT_GOAL := help
