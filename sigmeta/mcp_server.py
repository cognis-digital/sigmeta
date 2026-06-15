"""SIGMETA MCP server — exposes classify() as an MCP tool for Cognis.Studio."""
from __future__ import annotations

import json

from sigmeta.core import parse_lines, catalog_summary, ParseError


def _scan(text: str) -> dict:
    """Parse signal metadata text and return a summary catalog dict."""
    lines = text.splitlines()
    records = list(parse_lines(lines, strict=False))
    return {
        "records": [r.to_dict() for r in records],
        "summary": catalog_summary(records),
    }


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
        """Parse and classify signal metadata (freq, modulation, bandwidth)
        into a normalized catalog. Returns JSON findings."""
        try:
            result = _scan(target)
        except (ParseError, ValueError) as exc:
            return json.dumps({"error": str(exc)})
        except Exception as exc:  # pragma: no cover
            return json.dumps({"error": f"unexpected error: {exc}"})
        return json.dumps(result)

    app.run()
    return 0
