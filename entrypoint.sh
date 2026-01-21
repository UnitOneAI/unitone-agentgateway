#!/bin/sh
# Entrypoint script for agentgateway
# Supports mounted config override: if /app/mounted-config.yaml exists, use it
# Otherwise, fall back to the default baked-in config at /app/config.yaml

MOUNTED_CONFIG="/app/mounted-config.yaml"
DEFAULT_CONFIG="/app/config.yaml"

if [ -f "$MOUNTED_CONFIG" ]; then
    echo "Using mounted config: $MOUNTED_CONFIG"
    CONFIG_FILE="$MOUNTED_CONFIG"
else
    echo "Using default config: $DEFAULT_CONFIG"
    CONFIG_FILE="$DEFAULT_CONFIG"
fi

exec /app/agentgateway --file "$CONFIG_FILE" "$@"
