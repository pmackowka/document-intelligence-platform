from mcp.server.fastmcp import FastMCP

mcp = FastMCP("document-intelligence-platform")


@mcp.tool()
def ping() -> str:
    """Narzędzie testowe spike'u — potwierdza, że transport stdio działa."""
    return "pong"


if __name__ == "__main__":
    mcp.run()
