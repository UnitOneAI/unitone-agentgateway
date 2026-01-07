# New Engineer Guide: UnitOne AgentGateway

Welcome to the UnitOne AgentGateway project! This guide will help you understand the architecture, development workflow, testing procedures, and how to work with MCP servers.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Repository Structure](#repository-structure)
3. [When to Make Changes to agentgateway vs unitone-agentgateway](#when-to-make-changes)
4. [Development Setup](#development-setup)
5. [Making and Testing Changes](#making-and-testing-changes)
6. [Deployment Workflow](#deployment-workflow)
7. [Working with MCP Servers](#working-with-mcp-servers)
8. [Using the Playground UI](#using-the-playground-ui)
9. [Testing MCP Servers with Postman/curl](#testing-mcp-servers-with-postmancurl)
10. [Common Tasks](#common-tasks)
11. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### The Wrapper Repository Pattern

UnitOne AgentGateway uses a **wrapper repository pattern** with git submodules:

```
┌────────────────────────────────────────────────────────────┐
│ unitone-agentgateway (wrapper)                             │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ UnitOne-Specific:                                      │ │
│ │ - .github/workflows/     (CI/CD)                       │ │
│ │ - Dockerfile.acr         (Azure build config)          │ │
│ │ - docs/                  (UnitOne docs)                │ │
│ │ - Makefile              (automation scripts)           │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ agentgateway/ (submodule - core source)                │ │
│ │ ┌────────────────────────────────────────────────────┐ │ │
│ │ │ - src/           (Rust backend)                    │ │ │
│ │ │ - ui/            (Next.js frontend)                │ │ │
│ │ │ - Cargo.toml     (Rust project config)             │ │ │
│ │ └────────────────────────────────────────────────────┘ │ │
│ └────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

### Why This Pattern?

1. **Separation of Concerns**: Core AgentGateway features are separate from UnitOne customizations
2. **Easy Syncing**: Pull upstream agentgateway updates easily
3. **Clean Customizations**: UnitOne-specific changes are clearly isolated
4. **Future Open Source**: Prepares the core agentgateway for potential open-sourcing

---

## Repository Structure

### unitone-agentgateway (Wrapper Repository)
- **Location**: `~/unitone-agentgateway`
- **Purpose**: UnitOne-specific configurations, branding, and deployment automation
- **Key Files**:
  - `.github/workflows/azure-deploy.yml` - CI/CD pipeline
  - `Dockerfile.acr` - Azure Container Registry build configuration
  - `docs/` - UnitOne-specific documentation
  - `Makefile` - Build and deployment automation

### agentgateway (Core Submodule)
- **Location**: `~/unitone-agentgateway/agentgateway`
- **Purpose**: Core AgentGateway source code
- **Key Directories**:
  - `src/` - Rust backend implementation
  - `ui/` - Next.js web interface
  - `tests/` - Test suites

### terraform (Sibling Repository)
- **Location**: `~/terraform`
- **Purpose**: Infrastructure as Code for Azure resources
- **Structure**:
  ```
  terraform/
  ├── modules/azure/agentgateway/    # Reusable module
  └── environments/
      ├── dev/agentgateway/          # Dev environment config
      ├── staging/agentgateway/      # Staging config (if exists)
      └── prod/agentgateway/         # Prod config (if exists)
  ```

---

## When to Make Changes

### Changes to `agentgateway` (Core Submodule)

Make changes in the core `agentgateway` submodule when:

- **Adding core features** that benefit all users (not UnitOne-specific)
- **Fixing bugs** in the gateway logic, routing, or MCP handling
- **Improving performance** or security
- **Adding new backend types** (e.g., AWS, GCP support)
- **Enhancing UI functionality** that's universally useful

**Example scenarios**:
- Adding support for a new MCP server type
- Fixing a bug in request routing
- Optimizing Docker image size
- Adding a new authentication method

**Workflow**:
```bash
cd ~/unitone-agentgateway/agentgateway

# Create feature branch in submodule
git checkout -b feature/new-mcp-backend

# Make changes
vim src/backends/my_new_backend.rs

# Commit to submodule
git add src/backends/my_new_backend.rs
git commit -m "Add new MCP backend support"

# Push to agentgateway repository
git push origin feature/new-mcp-backend

# Create PR in agentgateway repository
# Once merged, update wrapper to use new version (see below)
```

### Changes to `unitone-agentgateway` (Wrapper)

Make changes in the wrapper repository when:

- **Customizing UnitOne branding** (logos, colors, themes)
- **Modifying deployment configuration** (Dockerfile, CI/CD)
- **Adding UnitOne-specific documentation**
- **Configuring Azure-specific settings**
- **Adding UnitOne-specific features** (e.g., custom OAuth providers)

**Example scenarios**:
- Updating the UnitOne logo
- Changing CI/CD workflow
- Adding UnitOne-specific environment variables
- Customizing UI theme colors

**Workflow**:
```bash
cd ~/unitone-agentgateway

# Make changes to wrapper files (NOT in agentgateway/ subdirectory)
vim Dockerfile.acr

# Commit and push
git add Dockerfile.acr
git commit -m "Optimize Docker build for Azure"
git push origin main

# Deployment triggers automatically via GitHub Actions
```

### Changes to `terraform` (Infrastructure)

Make changes in the terraform repository when:

- **Modifying Azure infrastructure** (Container Apps, ACR, Key Vault)
- **Adding new environments** (staging, prod)
- **Changing resource configurations** (scaling, networking)
- **Managing secrets and OAuth configuration**

**Example scenarios**:
- Scaling up Container App resources
- Adding a new OAuth provider
- Configuring staging environment

**Workflow**:
```bash
cd ~/terraform/environments/dev/agentgateway

# Make changes
vim main.tf

# Plan and apply
terraform plan
terraform apply

# Commit changes
git add .
git commit -m "Update scaling configuration"
git push origin main
```

---

## Development Setup

### Prerequisites

1. **Install Required Tools**:
   ```bash
   # Rust (for backend development)
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

   # Node.js (for UI development)
   brew install node

   # Azure CLI
   brew install azure-cli

   # Docker
   brew install docker
   ```

2. **Clone with Submodules**:
   ```bash
   git clone --recursive https://github.com/UnitOneAI/unitone-agentgateway.git
   cd unitone-agentgateway

   # If already cloned, initialize submodules
   git submodule update --init --recursive
   ```

3. **Verify Setup**:
   ```bash
   # Check submodule is initialized
   git submodule status

   # Should show something like:
   # abc123def456... agentgateway (heads/main)

   # Verify agentgateway directory has content
   ls agentgateway/
   # Should show: Cargo.toml, src/, ui/, etc.
   ```

4. **Azure Authentication**:
   ```bash
   az login
   az account set --subscription <subscription-id>
   ```

---

## Making and Testing Changes

### Scenario 1: Making Changes to Core AgentGateway (Submodule)

#### Step 1: Create Feature Branch in Submodule
```bash
cd unitone-agentgateway/agentgateway

# Create feature branch
git checkout -b feature/my-new-feature

# Make changes
vim src/my_file.rs
vim ui/src/components/MyComponent.tsx
```

#### Step 2: Test Locally (Rust Backend)
```bash
# Build and run backend locally
cargo build
cargo test

# Run backend server
cargo run

# In another terminal, test endpoint
curl http://localhost:8080/health
```

#### Step 3: Test Locally (UI)
```bash
cd ui

# Install dependencies
npm install

# Run development server
npm run dev

# Access UI at http://localhost:3000
```

#### Step 4: Build Docker Image Locally (Optional)
```bash
cd ~/unitone-agentgateway

# Build using Azure Container Registry (production-like)
az acr build \
  --registry agwimages \
  --image unitone-agentgateway:my-test-tag \
  --file Dockerfile.acr \
  --platform linux/amd64 \
  .
```

#### Step 5: Commit Changes to Submodule
```bash
cd agentgateway

git add .
git commit -m "Add new feature X"
git push origin feature/my-new-feature

# Create PR in agentgateway repository
```

#### Step 6: Update Wrapper to Use New Version
Once the PR is merged to `agentgateway/main`:

```bash
cd ~/unitone-agentgateway

# Navigate to submodule
cd agentgateway

# Fetch latest changes
git fetch origin
git checkout origin/main

# Return to wrapper
cd ..

# The submodule pointer is now updated
git status
# Shows: modified:   agentgateway (new commits)

# Commit the submodule update
git add agentgateway
git commit -m "Update agentgateway to include feature X"
git push origin main

# This triggers automatic deployment to dev via GitHub Actions
```

### Scenario 2: Making Changes to UnitOne Wrapper

#### Step 1: Make Changes
```bash
cd ~/unitone-agentgateway

# Example: Update Dockerfile
vim Dockerfile.acr

# Example: Update CI/CD workflow
vim .github/workflows/azure-deploy.yml
```

#### Step 2: Test Locally (if applicable)
```bash
# If changing Dockerfile, test build locally
docker build -f Dockerfile.acr -t test-image .

# Run container
docker run -p 8080:8080 test-image
```

#### Step 3: Commit and Push
```bash
git add .
git commit -m "Update Dockerfile for better caching"
git push origin main

# GitHub Actions automatically:
# 1. Builds Docker image
# 2. Pushes to ACR
# 3. Deploys to dev environment
```

---

## Deployment Workflow

### Automated Deployment (Recommended)

#### Development Environment
Deployments to **dev** are **fully automated** via GitHub Actions:

```
┌─────────────┐
│ Push to     │
│ main branch │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│ GitHub Actions Workflow Starts  │
│ (.github/workflows/azure-deploy.yml) │
└──────┬──────────────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Checkout with Submodules │
│ (submodules: recursive)  │
└──────┬───────────────────┘
       │
       ▼
┌───────────────────────────┐
│ Build Docker Image        │
│ (az acr build)            │
│ Tags: <commit-sha>, latest │
└──────┬────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Deploy to Azure Container App │
│ (az containerapp update)      │
│ Environment: dev              │
└──────┬───────────────────────┘
       │
       ▼
┌────────────────────────┐
│ Health Check & Verify  │
│ Deployment Status      │
└────────────────────────┘
```

**Trigger**: Push to `main` branch
**Environment**: `mcp-gateway-dev-rg` (dev)
**Image Tag**: `<short-commit-sha>`, `latest`
**URL**: https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io

#### Staging/Production Deployment
Use GitHub Actions **manual workflow dispatch**:

```bash
# Via GitHub Web UI:
# 1. Go to: https://github.com/UnitOneAI/unitone-agentgateway/actions
# 2. Click "Azure Deployment"
# 3. Click "Run workflow"
# 4. Select environment: staging or prod
# 5. (Optional) Enter custom image tag
# 6. Click "Run workflow"
```

### Manual Deployment (Backup Method)

If you need to deploy manually:

```bash
cd ~/unitone-agentgateway

# Step 1: Build image in ACR
az acr build \
  --registry agwimages \
  --image unitone-agentgateway:manual-v1 \
  --file Dockerfile.acr \
  --platform linux/amd64 \
  .

# Step 2: Deploy to Container App
az containerapp update \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --image agwimages.azurecr.io/unitone-agentgateway:manual-v1

# Step 3: Verify deployment
az containerapp show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --query "{Status:properties.runningStatus, URL:properties.configuration.ingress.fqdn}"
```

### Monitoring Deployments

#### GitHub Actions
```bash
# Via Web UI
# https://github.com/UnitOneAI/unitone-agentgateway/actions

# Via CLI
gh run list
gh run view <run-id>
gh run watch
```

#### Azure Container App
```bash
# Check status
az containerapp show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --query "{Provisioning:properties.provisioningState, Running:properties.runningStatus}"

# View logs
az containerapp logs show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --follow

# List revisions
az containerapp revision list \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --query "[].{Name:name, Active:properties.active, Image:properties.template.containers[0].image, Traffic:properties.trafficWeight}" \
  -o table
```

---

## Working with MCP Servers

### What is MCP?

**MCP (Model Context Protocol)** is a protocol for AI agents to communicate with external services. AgentGateway acts as a proxy/router for MCP servers.

### MCP Architecture

```
┌─────────────┐
│   Client    │ (Claude, API consumer)
│  (AI Agent) │
└──────┬──────┘
       │
       │ HTTP/SSE Request
       ▼
┌────────────────────────┐
│   AgentGateway         │
│   (unitone-agentgateway)│
│   ┌──────────────────┐ │
│   │  Router          │ │
│   │  /mcp/{server}   │ │
│   └────────┬─────────┘ │
└────────────┼───────────┘
             │
             ▼
    ┌────────────────────┐
    │   MCP Server       │
    │   (e.g., pii-test) │
    │   ┌──────────────┐ │
    │   │ Tools/APIs   │ │
    │   └──────────────┘ │
    └────────────────────┘
```

### Configuring MCP Servers

MCP servers are configured in `azure-config.yaml`:

**Location**: `~/unitone-agentgateway/agentgateway/azure-config.yaml`

**Example Configuration**:
```yaml
binds:
  - port: 8080
    listeners:
      - name: main
        routes:
          # MCP Server Route
          - path: /mcp/pii-test-server
            backends:
              - mcp:
                  name: pii-test-server
                  targets:
                    - name: pii-server-target
                      http:
                        url: https://mcp-pii-test-server.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp
```

**Key Fields**:
- `path`: URL path on AgentGateway (e.g., `/mcp/pii-test-server`)
- `name`: Unique identifier for this MCP backend
- `targets[].http.url`: URL of the actual MCP server

---

## Using the Playground UI

### Accessing the Playground

**URL**: https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/ui

### Authentication
1. Navigate to the UI URL
2. Sign in with Microsoft or Google OAuth
3. You'll be redirected to the playground after authentication

### Configuring an MCP Server in the UI

#### Step 1: Navigate to Playground
After logging in, you'll see the playground interface with sections for:
- **Servers**: List of configured MCP servers
- **Tools**: Available tools from each server
- **Chat**: Interactive chat interface

#### Step 2: Add/Configure MCP Server

**Option A: Using Pre-configured Server**
If the MCP server is already configured in `azure-config.yaml`, it will appear in the servers list:

1. Click on the server name (e.g., "pii-test-server")
2. View available tools
3. Test tools directly from the UI

**Option B: Add New Server via UI**
1. Click "Add Server" or "+" button
2. Fill in server details:
   - **Name**: `pii-test-server`
   - **URL**: `https://mcp-pii-test-server.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp`
   - **Type**: `HTTP` or `SSE`
3. Click "Save"
4. The server will be added to your session (note: this is session-only, not persisted to config)

#### Step 3: Explore Available Tools
1. Select the MCP server from the list
2. View available tools/methods:
   - `tools/list` - List all available tools
   - `prompts/list` - List available prompts
   - `resources/list` - List available resources
3. Click on a tool to see its schema and parameters

#### Step 4: Test Tools via Chat
1. Use the chat interface to interact with the MCP server
2. Example prompts:
   ```
   "List all available tools from the PII server"
   "Scan this text for PII: My email is john@example.com"
   "Help me detect PII in a document"
   ```

### Example: Configuring PII MCP Server

Let's configure the PII MCP Test Server as an example:

**Server Details**:
- **Name**: `pii-test-server`
- **URL**: `https://mcp-pii-test-server.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp`
- **Purpose**: Detects PII (Personally Identifiable Information) in text

**Configuration in azure-config.yaml**:
```yaml
- path: /mcp/pii-test-server
  backends:
    - mcp:
        name: pii-test-server
        targets:
          - name: pii-server-target
            http:
              url: https://mcp-pii-test-server.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp
```

**Testing in UI**:
1. Navigate to playground
2. Select "pii-test-server" from servers list
3. Click "Test Connection" to verify it's accessible
4. Use chat to test PII detection:
   ```
   "Scan this text: My SSN is 123-45-6789 and email is john@example.com"
   ```

---

## Testing MCP Servers with Postman/curl

### Testing with curl

#### 1. Test Gateway Health
```bash
curl https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/health
```

**Expected Response**:
```json
{
  "status": "ok"
}
```

#### 2. Test MCP Endpoint (SSE)
```bash
# Initialize connection
curl -i \
  -X POST \
  "https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp/pii-test-server?sessionId=test123" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {
        "name": "curl-client",
        "version": "1.0.0"
      }
    }
  }'
```

**Expected Response Headers**:
```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

**Expected Response Body** (SSE format):
```
data: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"pii-test-server","version":"1.0.0"}}}
```

#### 3. List Available Tools
```bash
curl -i \
  -X POST \
  "https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp/pii-test-server?sessionId=test123" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'
```

#### 4. Call a Tool (Example: PII Detection)
```bash
curl -i \
  -X POST \
  "https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp/pii-test-server?sessionId=test123" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "detect_pii",
      "arguments": {
        "text": "My email is john@example.com and SSN is 123-45-6789"
      }
    }
  }'
```

### Testing with Postman

#### Setup Postman Collection

**Collection Name**: `AgentGateway MCP Tests`

**Request 1: Health Check**
- **Method**: GET
- **URL**: `https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/health`
- **Expected Status**: 200 OK

**Request 2: MCP Initialize**
- **Method**: POST
- **URL**: `https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp/pii-test-server?sessionId={{$randomUUID}}`
- **Headers**:
  - `Content-Type`: `application/json`
  - `Accept`: `text/event-stream`
- **Body** (raw JSON):
  ```json
  {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {
        "name": "postman-client",
        "version": "1.0.0"
      }
    }
  }
  ```

**Request 3: List Tools**
- **Method**: POST
- **URL**: `https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp/pii-test-server?sessionId={{$randomUUID}}`
- **Headers**: Same as above
- **Body**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }
  ```

**Request 4: Call PII Detection Tool**
- **Method**: POST
- **URL**: `https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp/pii-test-server?sessionId={{$randomUUID}}`
- **Headers**: Same as above
- **Body**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "detect_pii",
      "arguments": {
        "text": "Contact: john.doe@example.com, Phone: 555-1234"
      }
    }
  }
  ```

#### Postman Variables
Create environment variables:
- `gateway_url`: `https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io`
- `mcp_server`: `pii-test-server`

Then use in requests: `{{gateway_url}}/mcp/{{mcp_server}}`

---

## Common Tasks

### Task 1: Add a New MCP Server

#### Step 1: Deploy the MCP Server
```bash
# Example: Deploy new MCP server to Azure
cd /path/to/mcp-server

az containerapp create \
  --name my-new-mcp-server \
  --resource-group mcp-gateway-dev-rg \
  --image myregistry.azurecr.io/my-mcp-server:latest \
  --target-port 8080 \
  --ingress external \
  --env-vars KEY=VALUE
```

#### Step 2: Add Configuration to azure-config.yaml
```bash
cd ~/unitone-agentgateway/agentgateway

vim azure-config.yaml
```

Add new route:
```yaml
- path: /mcp/my-new-server
  backends:
    - mcp:
        name: my-new-server
        targets:
          - name: my-server-target
            http:
              url: https://my-new-mcp-server.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp
```

#### Step 3: Commit and Deploy
```bash
# Commit changes to submodule
cd agentgateway
git add azure-config.yaml
git commit -m "Add new MCP server configuration"
git push origin main

# Update wrapper to use new version
cd ..
git add agentgateway
git commit -m "Update agentgateway with new MCP server config"
git push origin main

# Deployment happens automatically via GitHub Actions
```

#### Step 4: Test New Server
```bash
# Test via curl
curl -i -X POST \
  "https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp/my-new-server?sessionId=test" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

### Task 2: Update AgentGateway to Latest Version

```bash
cd ~/unitone-agentgateway

# Navigate to submodule
cd agentgateway

# Fetch latest from upstream
git fetch origin

# Checkout latest main
git checkout origin/main

# Return to wrapper
cd ..

# Verify what changed
git diff agentgateway

# Commit the update
git add agentgateway
git commit -m "Update agentgateway to latest version ($(cd agentgateway && git rev-parse --short HEAD))"
git push origin main

# Monitor deployment
gh run watch
```

### Task 3: Rollback a Deployment

```bash
# List recent revisions
az containerapp revision list \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --query "[].{Name:name, Active:properties.active, Created:properties.createdTime, Image:properties.template.containers[0].image}" \
  -o table

# Activate previous revision
az containerapp revision activate \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --revision <previous-revision-name>

# Set traffic to 100% on previous revision
az containerapp ingress traffic set \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --revision-weight <previous-revision-name>=100
```

### Task 4: View Deployment Logs

```bash
# Real-time logs
az containerapp logs show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --follow

# Last 100 lines
az containerapp logs show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --tail 100

# Filter for errors
az containerapp logs show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --tail 100 \
  | grep -i error
```

### Task 5: Update UnitOne Branding

```bash
cd ~/unitone-agentgateway/agentgateway

# Update logo
cp /path/to/new-logo.svg ui/public/images/logo.svg

# Update theme colors in Next.js config
vim ui/src/app/globals.css

# Example: Change primary color
# --primary: #3b82f6;  /* UnitOne blue */

# Commit to submodule
git add ui/
git commit -m "Update UnitOne branding"
git push origin main

# Update wrapper
cd ..
git add agentgateway
git commit -m "Update agentgateway with new branding"
git push origin main
```

---

## Troubleshooting

### Issue 1: Submodule Not Initialized

**Symptom**: `agentgateway/` directory is empty

**Solution**:
```bash
cd ~/unitone-agentgateway
git submodule update --init --recursive
```

### Issue 2: Deployment Failed

**Symptom**: GitHub Actions workflow fails

**Steps**:
1. Check workflow logs:
   ```bash
   gh run list
   gh run view <run-id>
   ```

2. Common causes:
   - **Build failure**: Check Dockerfile.acr syntax
   - **ACR authentication**: Verify `AZURE_CREDENTIALS` secret
   - **Container startup failure**: Check application logs

3. Manual verification:
   ```bash
   # Check Container App status
   az containerapp show \
     --name unitone-agentgateway \
     --resource-group mcp-gateway-dev-rg \
     --query "{Provisioning:properties.provisioningState, Running:properties.runningStatus}"
   ```

### Issue 3: MCP Server Not Responding

**Symptom**: 404 or connection errors when accessing `/mcp/{server}`

**Diagnosis**:
```bash
# 1. Check agentgateway logs
az containerapp logs show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --tail 50 \
  | grep -i "mcp\|error"

# 2. Verify MCP server is running
az containerapp show \
  --name mcp-pii-test-server \
  --resource-group mcp-gateway-dev-rg \
  --query "{Status:properties.runningStatus, URL:properties.configuration.ingress.fqdn}"

# 3. Test MCP server directly (bypass gateway)
curl https://mcp-pii-test-server.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp

# 4. Verify azure-config.yaml configuration
cd ~/unitone-agentgateway/agentgateway
cat azure-config.yaml | grep -A 10 "mcp"
```

**Solution**:
- Verify URL in `azure-config.yaml` matches actual MCP server URL
- Ensure path in route matches request path
- Check MCP server logs for errors

### Issue 4: OAuth Authentication Not Working

**Symptom**: Cannot login to UI

**Steps**:
1. Check OAuth configuration:
   ```bash
   az containerapp show \
     --name unitone-agentgateway \
     --resource-group mcp-gateway-dev-rg \
     --query "properties.configuration.secrets"
   ```

2. Verify redirect URIs in OAuth provider settings:
   - Microsoft: https://portal.azure.com
   - Google: https://console.cloud.google.com

3. Check environment variables:
   ```bash
   az containerapp show \
     --name unitone-agentgateway \
     --resource-group mcp-gateway-dev-rg \
     --query "properties.template.containers[0].env"
   ```

### Issue 5: UI Not Loading

**Symptom**: UI returns 404 or doesn't load

**Diagnosis**:
```bash
# Check if UI is built in Docker image
az containerapp logs show \
  --name unitone-agentgateway \
  --resource-group mcp-gateway-dev-rg \
  --tail 100 \
  | grep -i "ui\|serving\|static"

# Test UI endpoint
curl -I https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/ui
```

**Solution**:
- Verify Dockerfile.acr includes UI build steps
- Check that UI build completes successfully in GitHub Actions logs
- Verify ingress configuration allows `/ui` path

---

## Additional Resources

### Documentation
- **Main README**: [README.md](../README.md)
- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **CI/CD Options**: [CICD_OPTIONS.md](CICD_OPTIONS.md)
- **Easy Auth Setup**: [EASY_AUTH_DEPLOYMENT.md](EASY_AUTH_DEPLOYMENT.md)
- **Branding Changes**: [UNITONE_BRANDING_CHANGES.md](UNITONE_BRANDING_CHANGES.md)

### Key URLs
- **Dev UI**: https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/ui
- **Dev MCP Endpoint**: https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/mcp/{server}
- **Health Check**: https://unitone-agentgateway.whitecliff-a0c9f0f7.eastus2.azurecontainerapps.io/health
- **GitHub Actions**: https://github.com/UnitOneAI/unitone-agentgateway/actions

### Contact
- **DevOps Team**: For deployment issues
- **On-Call**: For production emergencies
- **GitHub Issues**: For bugs and feature requests

---

**Last Updated**: January 2026
**Maintained By**: UnitOne DevOps Team
