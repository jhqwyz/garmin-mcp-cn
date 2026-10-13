"""Garmin Connect tools for local MCP clients and ChatGPT web."""

def main():
    """Load the server only when invoked, without import-time authentication."""
    from garmin_mcp.server import main as run_server
    run_server()
