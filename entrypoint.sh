#!/bin/sh
# Entrypoint script for agentgateway
# Supports mounted config override with priority:
#   1. /app/mounted-config/config.yaml (Azure Files mount)
#   2. /app/config.yaml (default baked into image)

MOUNTED_CONFIG="/app/mounted-config/config.yaml"
DEFAULT_CONFIG="/app/config.yaml"

# Check if --file is already in the arguments
HAS_FILE_ARG=0
for arg in "$@"; do
    if [ "$arg" = "--file" ] || echo "$arg" | grep -q "^--file="; then
        HAS_FILE_ARG=1
        break
    fi
done

if [ "$HAS_FILE_ARG" = "1" ]; then
    # --file already provided in args, just pass through
    echo "mounted config: $MOUNTED_CONFIG"
    exec /app/agentgateway "$@"
else
    # No --file arg, use default logic
    if [ -f "$MOUNTED_CONFIG" ]; then
        echo "Using mounted config: $MOUNTED_CONFIG"
        CONFIG_FILE="$MOUNTED_CONFIG"
    else
        echo "Using default config: $DEFAULT_CONFIG"
        CONFIG_FILE="$DEFAULT_CONFIG"
    fi
    exec /app/agentgateway --file "$CONFIG_FILE" "$@"
fi
