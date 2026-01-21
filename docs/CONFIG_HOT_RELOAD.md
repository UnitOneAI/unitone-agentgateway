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

## Method 1: CLI Script (Recommended)

The easiest way to update config:

```bash
# Update dev environment with azure-config.yaml
./scripts/update-config.sh dev

# Update with a custom config file
./scripts/update-config.sh dev ./my-config.yaml

# Update staging/prod
./scripts/update-config.sh staging ./staging-config.yaml
./scripts/update-config.sh prod ./prod-config.yaml
```

The script will:
1. Validate YAML syntax
2. Upload to Azure Files
3. AgentGateway auto-reloads (no restart needed)

## Method 2: Azure CLI

```bash
# Set variables
ENVIRONMENT="dev"
STORAGE_ACCOUNT="unitoneagwdevcfg"
SHARE_NAME="agentgateway-config"

# Get storage key
STORAGE_KEY=$(az storage account keys list \
    --account-name $STORAGE_ACCOUNT \
    --query '[0].value' -o tsv)

# Upload config
az storage file upload \
    --account-name $STORAGE_ACCOUNT \
    --account-key $STORAGE_KEY \
    --share-name $SHARE_NAME \
    --source ./azure-config.yaml \
    --path config.yaml
```

## Method 3: Azure Portal

### Step 1: Navigate to Storage Account
1. Go to [Azure Portal](https://portal.azure.com)
2. Search for **Storage accounts**
3. Select the storage account:
   - Dev: `unitoneagwdevcfg`
   - Staging: `unitoneagwstagingcfg`
   - Prod: `unitoneagwprodcfg`

### Step 2: Open File Share
1. In the left menu, click **Data storage** → **File shares**
2. Click on `agentgateway-config`

### Step 3: Upload/Edit Config
**To upload a new file:**
1. Click **Upload** in the toolbar
2. Select your config file
3. Set **Upload to folder** to `/` (root)
4. Check **Overwrite if files already exist**
5. Click **Upload**

**To edit directly in portal:**
1. Click on `config.yaml`
2. Click **Edit** in the toolbar
3. Make your changes
4. Click **Save**

### Step 4: Verify Reload
Check container logs to confirm reload:
```bash
az containerapp logs show \
    --name unitone-agw-dev-app \
    --resource-group mcp-gateway-dev-rg \
    --follow
```

Look for:
```
Config file changed, reloading...
Config reloaded successfully
```

## Storage Account Names by Environment

| Environment | Storage Account      | File Share            |
|-------------|---------------------|----------------------|
| dev         | `unitoneagwdevcfg`  | `agentgateway-config` |
| staging     | `unitoneagwstagingcfg` | `agentgateway-config` |
| prod        | `unitoneagwprodcfg` | `agentgateway-config` |

## Config File Format

The config file is YAML format. See `azure-config.yaml` for the full schema.

Key sections:
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
                      # ... guard config
                  targets:
                    - name: my-server
                      mcp:
                        host: https://my-mcp-server.com/mcp
```

## What Gets Hot-Reloaded

The following are updated without restart:
- ✅ Security guards (tool poisoning, PII, rug pull)
- ✅ MCP backend targets
- ✅ Routes and path matching
- ✅ CORS policies
- ✅ Backend configurations

## Troubleshooting

### Config not reloading
1. Check if file was uploaded correctly:
   ```bash
   az storage file list --account-name unitoneagwdevcfg --share-name agentgateway-config
   ```
2. Check container logs for errors:
   ```bash
   az containerapp logs show --name unitone-agw-dev-app --resource-group mcp-gateway-dev-rg
   ```

### Invalid YAML
The script validates YAML before upload. If uploading manually, validate first:
```bash
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

### Permission denied
Ensure you have Storage Blob Data Contributor role on the storage account:
```bash
az role assignment create \
    --assignee $(az ad signed-in-user show --query id -o tsv) \
    --role "Storage Blob Data Contributor" \
    --scope /subscriptions/<sub-id>/resourceGroups/mcp-gateway-dev-rg/providers/Microsoft.Storage/storageAccounts/unitoneagwdevcfg
```
