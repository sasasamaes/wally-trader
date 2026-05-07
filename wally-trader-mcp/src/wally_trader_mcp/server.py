"""Wally Trader MCP server — exposes 12 trading tools."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("wally-trader")


@mcp.tool()
def ping() -> dict:
    """Health check — returns server version + status."""
    return {"name": "wally-trader", "version": "0.1.0", "status": "ok"}


def main():
    mcp.run()


if __name__ == "__main__":
    main()
