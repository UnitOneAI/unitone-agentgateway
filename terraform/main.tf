# ==============================================================================
# UnitOne AgentGateway - Terraform Module
# ==============================================================================
#
# Deploys AgentGateway to Azure Container Apps with:
# - Azure Container Registry (ACR)
# - Container App with health probes
# - Key Vault for secrets
# - Log Analytics and Application Insights
# - Optional: CI/CD automation via ACR Tasks
# - Optional: Config file mounting via Azure Files
#
# Usage:
#   terraform init
#   terraform apply -var="environment=dev" -var="resource_group_name=my-rg"
#
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

provider "azurerm" {
  features {}
}

# Data sources
data "azurerm_subscription" "current" {}
data "azurerm_client_config" "current" {}

# Resource naming
locals {
  # Include stamp in prefix if provided (e.g., "agw-dev-01" or "agw-dev" if no stamp)
  stamp_suffix       = var.deployment_stamp != "" ? "-${var.deployment_stamp}" : ""
  resource_prefix    = "${var.base_name}-${var.environment}${local.stamp_suffix}"
  acr_name           = replace("${var.base_name}${var.environment}${var.deployment_stamp}acr", "-", "")
  key_vault_name     = "${local.resource_prefix}-kv"
  log_analytics_name = "${local.resource_prefix}-logs"
  app_insights_name  = "${local.resource_prefix}-insights"
  container_app_env_name = var.container_app_env_name != "" ? var.container_app_env_name : "${local.resource_prefix}-env"
  container_app_name = "${local.resource_prefix}-app"

  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Project     = "UnitOne AgentGateway"
      ManagedBy   = "Terraform"
    }
  )
}

# ==============================================================================
# 1. Container Registry (ACR)
# ==============================================================================
resource "azurerm_container_registry" "acr" {
  name                = local.acr_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = true

  tags = local.tags
}

# ==============================================================================
# 2. Log Analytics Workspace
# ==============================================================================
resource "azurerm_log_analytics_workspace" "logs" {
  name                = local.log_analytics_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = local.tags
}

# ==============================================================================
# 3. Application Insights
# ==============================================================================
resource "azurerm_application_insights" "insights" {
  name                = local.app_insights_name
  resource_group_name = var.resource_group_name
  location            = var.location
  workspace_id        = azurerm_log_analytics_workspace.logs.id
  application_type    = "web"

  tags = local.tags
}

# ==============================================================================
# 4. Key Vault for Secrets
# ==============================================================================
resource "azurerm_key_vault" "kv" {
  name                       = local.key_vault_name
  resource_group_name        = var.resource_group_name
  location                   = var.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  enable_rbac_authorization  = false
  enabled_for_deployment     = true
  enabled_for_template_deployment = true
  purge_protection_enabled   = false

  tags = local.tags
}

# Store OAuth secrets in Key Vault (optional)
resource "azurerm_key_vault_secret" "microsoft_client_id" {
  count        = var.microsoft_client_id != "" ? 1 : 0
  name         = "microsoft-client-id"
  value        = var.microsoft_client_id
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "microsoft_client_secret" {
  count        = var.microsoft_client_secret != "" ? 1 : 0
  name         = "microsoft-client-secret"
  value        = var.microsoft_client_secret
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "google_client_id" {
  count        = var.google_client_id != "" ? 1 : 0
  name         = "google-client-id"
  value        = var.google_client_id
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "google_client_secret" {
  count        = var.google_client_secret != "" ? 1 : 0
  name         = "google-client-secret"
  value        = var.google_client_secret
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "github_client_id" {
  count        = var.github_client_id != "" ? 1 : 0
  name         = "github-client-id"
  value        = var.github_client_id
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "github_client_secret" {
  count        = var.github_client_secret != "" ? 1 : 0
  name         = "github-client-secret"
  value        = var.github_client_secret
  key_vault_id = azurerm_key_vault.kv.id
}

# ==============================================================================
# 5. Container Apps Environment
# ==============================================================================
resource "azurerm_container_app_environment" "env" {
  count = var.container_app_env_name == "" ? 1 : 0

  name                       = local.container_app_env_name
  resource_group_name        = var.resource_group_name
  location                   = var.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id

  tags = local.tags
}

# Use existing environment if provided
data "azurerm_container_app_environment" "existing" {
  count               = var.container_app_env_name != "" ? 1 : 0
  name                = var.container_app_env_name
  resource_group_name = var.resource_group_name
}

locals {
  container_app_env_id = var.container_app_env_name != "" ? data.azurerm_container_app_environment.existing[0].id : azurerm_container_app_environment.env[0].id
}

# ==============================================================================
# 6. Config Storage (Optional - for hot-reload)
# ==============================================================================
resource "azurerm_storage_account" "config_mount" {
  count = var.enable_config_mount ? 1 : 0

  name                     = replace("${var.base_name}${var.environment}${var.deployment_stamp}cfg", "-", "")
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  tags = local.tags
}

resource "azurerm_storage_share" "config_mount" {
  count = var.enable_config_mount ? 1 : 0

  name                 = "agentgateway-config"
  storage_account_name = azurerm_storage_account.config_mount[0].name
  quota                = 1
}

resource "azurerm_storage_share_file" "config_mount" {
  count = var.enable_config_mount && var.config_file_path != "" ? 1 : 0

  name             = "config.yaml"
  storage_share_id = azurerm_storage_share.config_mount[0].id
  source           = var.config_file_path
}

resource "azurerm_container_app_environment_storage" "config_mount" {
  count = var.enable_config_mount ? 1 : 0

  name                         = "config-storage"
  container_app_environment_id = local.container_app_env_id
  account_name                 = azurerm_storage_account.config_mount[0].name
  share_name                   = azurerm_storage_share.config_mount[0].name
  access_key                   = azurerm_storage_account.config_mount[0].primary_access_key
  access_mode                  = "ReadWrite"
}

# ==============================================================================
# 7. Container App
# ==============================================================================
resource "azurerm_container_app" "app" {
  name                         = local.container_app_name
  resource_group_name          = var.resource_group_name
  container_app_environment_id = local.container_app_env_id
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }

  ingress {
    external_enabled           = true
    target_port                = 8080
    transport                  = "auto"
    client_certificate_mode    = var.client_certificate_mode

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = var.environment == "prod" ? 2 : 1
    max_replicas = var.environment == "prod" ? 10 : 3

    dynamic "volume" {
      for_each = var.enable_config_mount ? [1] : []
      content {
        name         = "config-volume"
        storage_name = azurerm_container_app_environment_storage.config_mount[0].name
        storage_type = "AzureFile"
      }
    }

    container {
      name   = "agentgateway"
      image  = "${azurerm_container_registry.acr.login_server}/unitone-agentgateway:${var.image_tag}"
      cpu    = 1.0
      memory = "2Gi"

      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = azurerm_application_insights.insights.connection_string
      }

      dynamic "volume_mounts" {
        for_each = var.enable_config_mount ? [1] : []
        content {
          name = "config-volume"
          path = "/app/mounted-config"
        }
      }

      readiness_probe {
        transport = "HTTP"
        port      = 15021
        path      = "/healthz/ready"

        interval_seconds        = 10
        timeout                 = 3
        failure_count_threshold = 3
        success_count_threshold = 1
      }

      liveness_probe {
        transport = "HTTP"
        port      = 15021
        path      = "/healthz/ready"

        initial_delay           = 30
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }
    }

    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = "100"
    }
  }

  tags = local.tags
}

# ==============================================================================
# 8. Key Vault Access Policy for Container App
# ==============================================================================
resource "azurerm_key_vault_access_policy" "container_app" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_container_app.app.identity[0].principal_id

  secret_permissions = [
    "Get",
    "List",
  ]
}

# ==============================================================================
# 9. Authentication Configuration (Easy Auth)
# ==============================================================================

# Enable Easy Auth and set unauthenticated action
resource "null_resource" "configure_auth" {
  count = var.configure_auth ? 1 : 0

  triggers = {
    container_app_id = azurerm_container_app.app.id
    allow_anonymous  = var.allow_anonymous_access
    environment      = var.environment
  }

  provisioner "local-exec" {
    command = <<-EOT
      az containerapp auth update \
        --name ${local.container_app_name} \
        --resource-group ${var.resource_group_name} \
        --unauthenticated-client-action ${var.allow_anonymous_access ? "AllowAnonymous" : "RedirectToLoginPage"} \
        --enabled true
    EOT
  }

  depends_on = [azurerm_container_app.app]
}

# Configure Microsoft (Azure AD) identity provider
resource "null_resource" "configure_microsoft_auth" {
  count = var.configure_auth && var.microsoft_client_id != "" ? 1 : 0

  triggers = {
    container_app_id = azurerm_container_app.app.id
    client_id        = var.microsoft_client_id
  }

  provisioner "local-exec" {
    command = <<-EOT
      az containerapp auth microsoft update \
        --name ${local.container_app_name} \
        --resource-group ${var.resource_group_name} \
        --client-id "${var.microsoft_client_id}" \
        --client-secret "${var.microsoft_client_secret}" \
        --yes
    EOT
  }

  depends_on = [null_resource.configure_auth]
}

# Configure Google identity provider
resource "null_resource" "configure_google_auth" {
  count = var.configure_auth && var.google_client_id != "" ? 1 : 0

  triggers = {
    container_app_id = azurerm_container_app.app.id
    client_id        = var.google_client_id
  }

  provisioner "local-exec" {
    command = <<-EOT
      az containerapp auth google update \
        --name ${local.container_app_name} \
        --resource-group ${var.resource_group_name} \
        --client-id "${var.google_client_id}" \
        --client-secret "${var.google_client_secret}" \
        --yes
    EOT
  }

  depends_on = [null_resource.configure_auth]
}

# Configure GitHub identity provider
resource "null_resource" "configure_github_auth" {
  count = var.configure_auth && var.github_client_id != "" ? 1 : 0

  triggers = {
    container_app_id = azurerm_container_app.app.id
    client_id        = var.github_client_id
  }

  provisioner "local-exec" {
    command = <<-EOT
      az containerapp auth github update \
        --name ${local.container_app_name} \
        --resource-group ${var.resource_group_name} \
        --client-id "${var.github_client_id}" \
        --client-secret "${var.github_client_secret}" \
        --yes
    EOT
  }

  depends_on = [null_resource.configure_auth]
}

# ==============================================================================
# 10. ACR Task for CI/CD (Optional)
# ==============================================================================
resource "azurerm_container_registry_task" "build" {
  count = var.github_repo_url != "" && var.github_pat != "" ? 1 : 0

  name                  = "agentgateway-build-task"
  container_registry_id = azurerm_container_registry.acr.id

  platform {
    os = "Linux"
  }

  docker_step {
    dockerfile_path      = "Dockerfile.acr"
    context_path         = "${var.github_repo_url}#main"
    context_access_token = var.github_pat
    image_names = [
      "unitone-agentgateway:latest",
      "unitone-agentgateway:{{.Run.ID}}",
    ]
    push_enabled = true
  }

  source_trigger {
    name           = "commit-trigger"
    events         = ["commit"]
    repository_url = var.github_repo_url
    source_type    = "Github"
    branch         = "main"

    authentication {
      token      = var.github_pat
      token_type = "PAT"
    }
  }

  base_image_trigger {
    name    = "base-image-trigger"
    type    = "Runtime"
    enabled = true
  }

  agent_setting {
    cpu = 2
  }

  tags = local.tags
}
