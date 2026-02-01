#!/bin/bash
# Build script for Server Spoofing Guard WASM component
#
# Prerequisites:
#   pip install componentize-py wasmtime
#
# Usage:
#   ./build.sh
#
# Output:
#   server_spoofing_guard.wasm - The compiled WASM component

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for componentize-py
if ! command -v componentize-py &> /dev/null; then
    echo "Error: componentize-py not found. Install with: pip install componentize-py"
    exit 1
fi

echo "Building Server Spoofing Guard WASM component..."

# Generate bindings and compile to WASM
componentize-py \
    --wit-path wit \
    --world security-guard \
    componentize \
    app \
    -o server_spoofing_guard.wasm

echo "Build complete: server_spoofing_guard.wasm"
echo ""
echo "To use this guard, configure it in your AgentGateway config:"
echo ""
echo "security_guards:"
echo "  - id: server-spoofing-guard"
echo "    type: wasm"
echo "    enabled: true"
echo "    priority: 10"
echo "    failure_mode: fail_closed"
echo "    timeout_ms: 100"
echo "    runs_on: [connection, response]"
echo "    module_path: ./guards/server_spoofing_guard.wasm"
echo "    config:"
echo "      whitelist:"
echo '        - name: "finance-tools"'
echo '          url_pattern: "https://finance\\.company\\.com/.*"'
echo "      block_unknown_servers: true"
echo "      typosquat_similarity_threshold: 0.85"
