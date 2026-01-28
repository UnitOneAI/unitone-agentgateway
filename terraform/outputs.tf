# ==============================================================================
# Outputs for AgentGateway Terraform Module
# ==============================================================================

# ------------------------------------------------------------------------------
# URLs and Endpoints
# ------------------------------------------------------------------------------

output "container_app_url" {
  description = "Full URL of the Container App"
  value       = "https://${azurerm_container_app.app.ingress[0].fqdn}"
}

output "ui_url" {
  description = "URL to access the Admin UI"
  value       = "https://${azurerm_container_app.app.ingress[0].fqdn}/ui"
}

output "mcp_endpoint" {
  description = "MCP endpoint URL"
  value       = "https://${azurerm_container_app.app.ingress[0].fqdn}/mcp"
}

# ------------------------------------------------------------------------------
# Resource Names
# ------------------------------------------------------------------------------

output "acr_login_server" {
  description = "ACR login server URL"
  value       = azurerm_container_registry.acr.login_server
}

output "acr_name" {
  description = "ACR name"
  value       = azurerm_container_registry.acr.name
}

output "container_app_name" {
  description = "Container App name"
  value       = azurerm_container_app.app.name
}

output "key_vault_name" {
  description = "Key Vault name"
  value       = azurerm_key_vault.kv.name
}

output "resource_group_name" {
  description = "Resource group name"
  value       = var.resource_group_name
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "deployment_stamp" {
  description = "Deployment stamp (for multiple deployments)"
  value       = var.deployment_stamp
}

# ------------------------------------------------------------------------------
# Sensitive Outputs
# ------------------------------------------------------------------------------

output "acr_username" {
  description = "ACR admin username"
  value       = azurerm_container_registry.acr.admin_username
  sensitive   = true
}

output "acr_password" {
  description = "ACR admin password"
  value       = azurerm_container_registry.acr.admin_password
  sensitive   = true
}

# ------------------------------------------------------------------------------
# Config Storage Outputs (when enabled)
# ------------------------------------------------------------------------------

output "config_storage_account" {
  description = "Storage account name for config files"
  value       = var.enable_config_mount ? azurerm_storage_account.config_mount[0].name : null
}

output "config_update_command" {
  description = "Command to update config file"
  value       = var.enable_config_mount ? "az storage file upload --account-name ${azurerm_storage_account.config_mount[0].name} --share-name ${azurerm_storage_share.config_mount[0].name} --source ./config.yaml --path config.yaml" : null
}

# ------------------------------------------------------------------------------
# Deployment Commands
# ------------------------------------------------------------------------------

output "build_command" {
  description = "Command to build and push image to ACR"
  value       = "az acr build --registry ${azurerm_container_registry.acr.name} --image agentgateway:latest --file Dockerfile.acr --platform linux/amd64 ."
}

output "deploy_command" {
  description = "Command to trigger a new deployment"
  value       = "az containerapp update --name ${azurerm_container_app.app.name} --resource-group ${var.resource_group_name} --image ${azurerm_container_registry.acr.login_server}/unitone-agentgateway:latest"
}

output "logs_command" {
  description = "Command to view logs"
  value       = "az containerapp logs show --name ${azurerm_container_app.app.name} --resource-group ${var.resource_group_name} --follow"
}

# ------------------------------------------------------------------------------
# OAuth Callback URLs (for configuring identity providers)
# ------------------------------------------------------------------------------

output "microsoft_callback_url" {
  description = "Microsoft (Azure AD) OAuth callback URL"
  value       = "https://${azurerm_container_app.app.ingress[0].fqdn}/.auth/login/aad/callback"
}

output "google_callback_url" {
  description = "Google OAuth callback URL"
  value       = "https://${azurerm_container_app.app.ingress[0].fqdn}/.auth/login/google/callback"
}

output "github_callback_url" {
  description = "GitHub OAuth callback URL"
  value       = "https://${azurerm_container_app.app.ingress[0].fqdn}/.auth/login/github/callback"
}
