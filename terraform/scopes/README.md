# AgentGateway Scopes

Scopes allow you to switch between different deployment environments (dev, staging, prod) without reconfiguring.

## Directory Structure

```
terraform/scopes/
├── global/           # Team-shared scopes (everyone uses these)
│   ├── dev.env
│   ├── staging.env
│   └── prod.env
├── users/            # Personal overrides (per-user customizations)
│   ├── alice/
│   │   └── dev.env   # Alice's personal dev settings
│   └── bob/
│       └── dev.env   # Bob's personal dev settings
└── example.env.template
```

## Resolution Order

When you run `./agw scope set dev`, the CLI looks for scopes in this order:

1. `terraform/scopes/users/<your-username>/dev.env` (personal)
2. `terraform/scopes/global/dev.env` (team default)

Personal scopes override global scopes with the same name.

## Creating Scopes

### Guided (recommended)

```bash
./agw setup
# Choose: "Import existing" or "Create new environment"
```

### Quick commands

```bash
# Import from terraform outputs
./agw scope import --name dev --global --from ./terraform

# Add manually
./agw scope add dev --global
./agw scope add dev --user     # Personal scope
```

## Scope File Format

```bash
# Required - identifies the Azure deployment
AGW_RESOURCE_GROUP=unitone-agw-dev-rg
AGW_CONTAINER_APP=unitone-agw-dev-app
AGW_ACR_NAME=unitoneagwdevacr

# Optional
AGW_CONTAINER_APP_ENV=unitone-agw-dev-env
AGW_DESCRIPTION=Development environment
AGW_URL=https://unitone-agw-dev-app.azurecontainerapps.io
```

## Commands

| Command | Description |
|---------|-------------|
| `./agw scope` | Show current scope |
| `./agw scope list` | List all available scopes |
| `./agw scope set <name>` | Switch to a scope |
| `./agw scope add <name> --global` | Add a global scope |
| `./agw scope add <name> --user` | Add a personal scope |
| `./agw scope remove <name>` | Remove a scope |
| `./agw scope migrate` | Migrate legacy scopes from .agw/ |

## Best Practices

1. **Global scopes** - Use for team-shared environments (dev, staging, prod)
2. **Personal scopes** - Use for individual experiments or overrides
3. **Version control** - Commit global scopes, personal scopes are optional
4. **No secrets** - Scope files contain only resource identifiers, not credentials
