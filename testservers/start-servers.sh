#!/bin/bash

# Start the PII test server on port 8000
MCP_PORT=8000 mcp-test-server-fastmcp &

# Start the tool-poisoning-test server on port 8010
MCP_PORT=8010 tool-poisoning-test &

# Start the rug-pull-test server on port 8020
MCP_PORT=8020 rug-pull-test &

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
