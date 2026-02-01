# UnitOne AgentGateway - Authentication

This guide covers authentication options for UnitOne AgentGateway deployed on Azure Container Apps.

## Overview

AgentGateway supports multiple authentication methods:

| Method | Use Case | Configuration |
|--------|----------|---------------|
| **Azure Easy Auth** | Web UI, OAuth providers | Terraform + Azure Portal |
| **Anonymous** | Development, E2E testing | `allow_anonymous_access = true` |
| **API Keys** | Service-to-service | Key Vault + Gateway config |

## Azure Easy Auth (OAuth)

Easy Auth provides OAuth 2.0 authentication with minimal code changes.

### Supported Providers

- **Microsoft (Azure AD)** - Enterprise SSO, recommended for internal use
- **Google** - Consumer/workspace accounts
- **GitHub** - Developer authentication

### Step 1: Create OAuth Applications

#### Microsoft (Azure AD)

1. Go to [Azure Portal](https://portal.azure.com) → **Azure Active Directory** → **App registrations**
2. Click **New registration**
3. Configure:
   - **Name**: `UnitOne AgentGateway`
   - **Supported account types**: Choose based on your needs
   - **Redirect URI**: `https://<your-app>.azurecontainerapps.io/.auth/login/aad/callback`
4. After creation, note the **Application (client) ID**
5. Go to **Certificates & secrets** → **New client secret**
6. Note the secret value (shown only once)

#### Google

1. Go to [Google Cloud Console](https://console.cloud.google.com) → **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Configure:
   - **Application type**: Web application
   - **Authorized redirect URIs**: `https://<your-app>.azurecontainerapps.io/.auth/login/google/callback`
4. Note the **Client ID** and **Client Secret**

#### GitHub

1. Go to [GitHub Settings](https://github.com/settings/developers) → **OAuth Apps** → **New OAuth App**
2. Configure:
   - **Application name**: `UnitOne AgentGateway`
   - **Homepage URL**: `https://<your-app>.azurecontainerapps.io`
   - **Authorization callback URL**: `https://<your-app>.azurecontainerapps.io/.auth/login/github/callback`
3. Note the **Client ID** and generate a **Client Secret**

### Step 2: Configure Terraform

Add OAuth credentials to your `terraform.tfvars`:

```hcl
# Enable Easy Auth
configure_auth         = true
allow_anonymous_access = false

# Microsoft (Azure AD)
microsoft_client_id     = "your-azure-ad-client-id"
microsoft_client_secret = "your-azure-ad-client-secret"

# Google (optional)
google_client_id     = "your-google-client-id"
google_client_secret = "your-google-client-secret"

# GitHub (optional)
github_client_id     = "your-github-client-id"
github_client_secret = "your-github-client-secret"
```

### Step 3: Configure Easy Auth in Azure Portal

After `terraform apply`, complete the setup in Azure Portal:

1. Go to **Container Apps** → Your app → **Authentication**
2. Click **Add identity provider**
3. Select provider (Microsoft, Google, or GitHub)
4. Enter the Client ID and Secret
5. Configure **Allowed token audiences** if needed
6. Set **Restrict access** to "Require authentication"
7. Save

### Step 4: Verify

```bash
# Should redirect to login
curl -I https://<your-app>.azurecontainerapps.io/ui

# After login, check user info
curl https://<your-app>.azurecontainerapps.io/.auth/me \
  -H "Cookie: <your-auth-cookie>"
```

## Anonymous Access (Development)

For development and E2E testing, enable anonymous access:

```hcl
# terraform.tfvars
configure_auth         = true
allow_anonymous_access = true
```

This allows unauthenticated requests while still enabling Easy Auth for optional login.

## API Key Authentication

For service-to-service communication, use API keys stored in Key Vault:

### Store API Key in Key Vault

```bash
# Get Key Vault name from Terraform
KV_NAME=$(cd terraform && terraform output -raw key_vault_name)

# Store API key
az keyvault secret set \
  --vault-name $KV_NAME \
  --name "api-key-service-a" \
  --value "your-secure-api-key"
```

### Configure Gateway Route

In your gateway config, add API key validation:

```yaml
routes:
  - name: api-route
    matches:
      - path:
          pathPrefix: /api
    policies:
      # Add API key header requirement
      requestHeaders:
        add:
          - name: x-api-key
            value: "${API_KEY}"
```

## Troubleshooting

### Login Page Not Showing

1. Verify `allow_anonymous_access = false` in terraform
2. Check Easy Auth is enabled in Azure Portal
3. Verify redirect URIs match exactly

### OAuth Callback Errors

1. Verify redirect URI includes `/.auth/login/<provider>/callback`
2. Check client ID and secret are correct
3. Ensure HTTPS is used (not HTTP)

### Token Issues

```bash
# Check current auth status
curl https://<your-app>.azurecontainerapps.io/.auth/me

# Force re-login
curl https://<your-app>.azurecontainerapps.io/.auth/login/<provider>
```

## Client Certificates (mTLS)

For service-to-service authentication, you can require client certificates (mutual TLS).

### Use Cases

- **Service-to-service auth** - Backend services calling the gateway must prove identity
- **Zero-trust architecture** - Every caller must present a valid certificate
- **Enterprise environments** - Integrate with existing PKI infrastructure

### Configuration

```hcl
# terraform.tfvars
client_certificate_mode = "require"  # or "accept" or "ignore"
```

| Mode | Behavior |
|------|----------|
| `ignore` | Don't request client certs (default) |
| `accept` | Accept certs if provided, but don't require |
| `require` | All requests must have valid client cert |

### How It Works

```
Client Service                  AgentGateway
     │                               │
     │── TLS handshake ─────────────►│
     │◄── Server certificate ───────│
     │── Client certificate ────────►│  ← Gateway verifies
     │◄── Connection established ───│
     │── MCP request ───────────────►│
```

### Generating Client Certificates

For testing, generate a self-signed certificate:

```bash
# Generate CA
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days 365 -key ca.key -out ca.crt -subj "/CN=MyCA"

# Generate client cert
openssl genrsa -out client.key 4096
openssl req -new -key client.key -out client.csr -subj "/CN=my-service"
openssl x509 -req -days 365 -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt
```

For production, use your organization's PKI or Azure Key Vault certificates.

### Testing with curl

```bash
curl --cert client.crt --key client.key \
  https://your-app.azurecontainerapps.io/mcp
```

## Security Best Practices

1. **Never commit secrets** - Use terraform.tfvars (gitignored) or environment variables
2. **Rotate secrets regularly** - Update in OAuth provider and Key Vault
3. **Use Azure AD for enterprise** - Provides SSO, MFA, and audit logs
4. **Enable HTTPS only** - Container Apps enforce this by default
5. **Monitor authentication logs** - Check Application Insights for auth events
6. **Use mTLS for service-to-service** - More secure than API keys for internal services
