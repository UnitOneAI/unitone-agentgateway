#!/bin/bash
set -e

# Unified MCP Test Server startup script
# Runs different servers based on SERVER_TYPE environment variable

echo "Starting MCP Test Server with SERVER_TYPE=${SERVER_TYPE}"

case "${SERVER_TYPE}" in
  pii)
    echo "Starting PII test server on port ${MCP_PORT:-8000}..."
    exec mcp-test-server-fastmcp
    ;;
  tool-poison|tool-poisoning)
    echo "Starting Tool Poisoning test server on port ${MCP_PORT:-9000}..."
    exec tool-poisoning-test
    ;;
  rug-pull|rugpull)
    echo "Starting Rug Pull test server on port ${MCP_PORT:-8020}..."
    echo "  RUG_PULL_TRIGGER: ${RUG_PULL_TRIGGER:-3}"
    echo "  RUG_PULL_MODE: ${RUG_PULL_MODE:-remove}"
    exec rug-pull-test
    ;;
  all)
    echo "Starting ALL servers..."
    MCP_PORT=8000 mcp-test-server-fastmcp &
    MCP_PORT=8010 tool-poisoning-test &
    MCP_PORT=8020 rug-pull-test &
    wait -n
    exit $?
    ;;
  *)
    echo "ERROR: Unknown SERVER_TYPE '${SERVER_TYPE}'"
    echo "Valid options: pii, tool-poison, rug-pull, all"
    exit 1
    ;;
esac
