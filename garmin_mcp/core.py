import datetime
from typing import List, Literal
from mcp.server.fastmcp import FastMCP


def crate_mcp_server(**setting) -> FastMCP:
    fast_mcp = FastMCP(
        name="garmin-mcp",
        **setting,
    )



    return fast_mcp
