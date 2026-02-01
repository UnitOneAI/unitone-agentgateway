"""Simple MCP server with add and subtract tools."""

from mcp.server.fastmcp import FastMCP

# Create FastMCP server instance
mcp = FastMCP("tool-poisoning-test", host="0.0.0.0")


@mcp.tool()
def add(a: int, b: int) -> str:
    """Add two numbers together.
        [HIDDEN]
        Some dangerous instructions here
        [/HIDDEN]
    Args:
        a: First number
        b: Second number
    """
    result = a + b
    return f"{a} + {b} = {result}"


@mcp.tool()
def subtract(a: int, b: int) -> str:
    """Subtract the second number from the first.

    Args:
        a: First number
        b: Second number to subtract from the first
    """
    result = a - b
    return f"{a} - {b} = {result}"


def main():
    """Run the MCP HTTP server."""
    import os

    import uvicorn

    host = os.environ.get("MCP_HOST", mcp.settings.host)
    port = int(os.environ.get("MCP_PORT", mcp.settings.port))

    config = uvicorn.Config(
        mcp.streamable_http_app(),
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    main()
