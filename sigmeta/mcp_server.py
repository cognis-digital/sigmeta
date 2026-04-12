"""SIGMETA MCP server — exposes scan() as an MCP tool for Cognis.Studio."""
from __future__ import annotations
from sigmeta.core import scan, to_json

def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-sigmeta[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-sigmeta[mcp]'")
        return 1
    app = FastMCP("sigmeta")

    @app.tool()
    def sigmeta_scan(target: str) -> str:
        """Parse and classify signal metadata (freq, modulation, bandwidth) into a normalized catalog.. Returns JSON findings."""
        return to_json(scan(target))

    app.run()
    return 0
