# AgentGateway Config Hot Reload

AgentGateway supports hot-reloading of configuration without container restarts. Changes are detected and applied within **250ms**.

## Architecture

```
┌──────────────┐   upload    ┌─────────────────┐    mount     ┌─────────────────────────────┐
│  Admin       │ ──────────► │  Azure Files    │ ◄──────────► │  AgentGateway Container     │
│  (CLI/Portal)│             │  config.yaml    │    SMB       │                             │
└──────────────┘             └─────────────────┘              │  /app/mounted-config/       │
                                   │                         │           │                 │
                                   │ file change             │           ▼                 │
                                   ▼                         │  ┌─────────────────────┐   │
                            ┌─────────────────┐              │  │  File Watcher       │   │
                            │  Event detected │ ────────────►│  │  (250ms debounce)   │   │
                            └─────────────────┘              │  └──────────┬──────────┘   │
                                                             │             │              │
                                                             │             ▼              │
                                                             │  ┌─────────────────────┐   │
                                                             │  │  reload_config()    │   │
                                                             │  │  - security guards  │   │
                                                             │  │  - routes/backends  │   │
                                                             │  └─────────────────────┘   │
                                                             └─────────────────────────────┘
```

## Prerequisites

Enable config mounting in Terraform:

```hcl
enable_config_mount = true
config_file_path    = "./config.yaml"  # Initial config
```

This creates:
- Azure Storage Account
- File Share named `agentgateway-config`
- Volume mount at `/app/mounted-config/`

## Updating Configuration

### Method 1: Azure CLI

```bash
# Get your storage account name from Terraform output
STORAGE_ACCOUNT=$(cd terraform && terraform output -raw config_storage_account)

# Get storage key
STORAGE_KEY=$(az storage account keys list \
    --account-name $STORAGE_ACCOUNT \
    --query '[0].value' -o tsv)

# Upload config
az storage file upload \
    --account-name $STORAGE_ACCOUNT \
    --account-key $STORAGE_KEY \
    --share-name agentgateway-config \
    --source ./config.yaml \
    --path config.yaml
```

### Method 2: Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your Storage Account
3. Click **Data storage** → **File shares**
4. Select `agentgateway-config`
5. Click **Upload** or click on `config.yaml` → **Edit**
6. Make changes and save

### Method 3: Terraform Output Command

```bash
# Terraform provides a ready-to-use command
cd terraform
terraform output config_update_command
# Copy and run the output command
```

## What Gets Hot-Reloaded

The following are updated without restart:
- Security guards (tool poisoning, PII, rug pull)
- MCP backend targets
- Routes and path matching
- CORS policies
- Backend configurations

## Config File Format

```yaml
binds:
  - port: 8080
    listeners:
      - name: http-listener
        protocol: HTTP
        routes:
          - name: mcp-route
            matches:
              - path:
                  pathPrefix: /mcp
            backends:
              - mcp:
                  securityGuards:
                    - id: tool-poisoning-detector
                      enabled: true
                      type: tool_poisoning
                  targets:
                    - name: my-server
                      mcp:
                        host: https://my-mcp-server.com/mcp
```

See `examples/config.yaml` for a complete example.

## Verifying Reload

Check container logs for reload confirmation:

```bash
# Get app name from Terraform
APP_NAME=$(cd terraform && terraform output -raw container_app_name)
RG_NAME=$(cd terraform && terraform output -raw resource_group_name)

az containerapp logs show \
    --name $APP_NAME \
    --resource-group $RG_NAME \
    --follow
```

Look for:
```
Config file changed, reloading...
Config reloaded successfully
```

## Troubleshooting

### Config not reloading

1. Verify file was uploaded:
   ```bash
   az storage file list \
       --account-name $STORAGE_ACCOUNT \
       --share-name agentgateway-config
   ```

2. Check container logs for errors

### Invalid YAML

Validate before uploading:
```bash
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"
```
