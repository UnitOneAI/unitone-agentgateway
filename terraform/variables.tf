# ==============================================================================
# Variables for AgentGateway Terraform Module
# ==============================================================================

# ------------------------------------------------------------------------------
# Required Variables
# ------------------------------------------------------------------------------

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod"
  }
}

variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
}

# ------------------------------------------------------------------------------
# Optional Variables
# ------------------------------------------------------------------------------

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "eastus2"
}

variable "base_name" {
  description = "Base name prefix for all resources"
  type        = string
  default     = "agw"
}

variable "deployment_stamp" {
  description = "Unique deployment identifier (allows multiple deployments in same environment)"
  type        = string
  default     = ""
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "use_placeholder_image" {
  description = "Use a placeholder image for initial deployment (before real image is built)"
  type        = bool
  default     = true
}

variable "placeholder_image" {
  description = "Placeholder image for initial deployment"
  type        = string
  default     = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
}

variable "container_app_env_name" {
  description = "Name of existing Container App Environment (leave empty to create new)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}

# ------------------------------------------------------------------------------
# Authentication Variables
# ------------------------------------------------------------------------------

variable "configure_auth" {
  description = "Configure Azure Easy Auth on Container App"
  type        = bool
  default     = false
}

variable "allow_anonymous_access" {
  description = "Allow anonymous access (useful for dev/test)"
  type        = bool
  default     = false
}

variable "microsoft_client_id" {
  description = "Microsoft OAuth Client ID"
  type        = string
  default     = ""
  sensitive   = true
}

variable "microsoft_client_secret" {
  description = "Microsoft OAuth Client Secret"
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_client_id" {
  description = "Google OAuth Client ID"
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth Client Secret"
  type        = string
  default     = ""
  sensitive   = true
}

variable "github_client_id" {
  description = "GitHub OAuth Client ID"
  type        = string
  default     = ""
  sensitive   = true
}

variable "github_client_secret" {
  description = "GitHub OAuth Client Secret"
  type        = string
  default     = ""
  sensitive   = true
}

# ------------------------------------------------------------------------------
# Client Certificate (mTLS) Variables
# ------------------------------------------------------------------------------

variable "client_certificate_mode" {
  description = "Client certificate mode: ignore, accept, or require"
  type        = string
  default     = "ignore"
  validation {
    condition     = contains(["ignore", "accept", "require"], var.client_certificate_mode)
    error_message = "client_certificate_mode must be ignore, accept, or require"
  }
}

# ------------------------------------------------------------------------------
# Configuration Mount Variables
# ------------------------------------------------------------------------------

variable "enable_config_mount" {
  description = "Mount config from Azure Files (enables hot-reload)"
  type        = bool
  default     = false
}

variable "config_file_path" {
  description = "Path to config.yaml file to upload (optional)"
  type        = string
  default     = ""
}

# ------------------------------------------------------------------------------
# CI/CD Variables
# ------------------------------------------------------------------------------

variable "github_repo_url" {
  description = "GitHub repository URL for ACR Task (e.g., https://github.com/org/repo.git)"
  type        = string
  default     = ""
}

variable "github_pat" {
  description = "GitHub Personal Access Token for ACR Task triggers"
  type        = string
  default     = ""
  sensitive   = true
}

# ------------------------------------------------------------------------------
# Session Affinity Variables
# ------------------------------------------------------------------------------

variable "enable_sticky_sessions" {
  description = "Enable sticky sessions for MCP session affinity. Required for multi-replica deployments with stateful MCP sessions."
  type        = bool
  default     = true
}
