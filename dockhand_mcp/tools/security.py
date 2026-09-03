"""
Security and vulnerability scanning tools.
"""

from typing import Any
from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path

async def list_vulnerabilities(environment_id: int, ctx: Context) -> dict:
    """List all known vulnerabilities for the given environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/security/vulnerabilities", params={"env": environment_id})

async def get_vulnerability_count(environment_id: int, ctx: Context) -> dict:
    """Get the count of vulnerabilities for the given environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/security/vulnerabilities/count", params={"env": environment_id})

async def scan_all_vulnerabilities(environment_id: int, ctx: Context) -> dict:
    """Trigger a vulnerability scan across all resources in the environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post("/api/security/vulnerabilities/scan", params={"env": environment_id})

async def list_image_scans(environment_id: int, image_id: str, ctx: Context) -> dict:
    """List vulnerability scans for a specific image."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(f"/api/images/{encode_path(image_id)}/scans", params={"env": environment_id})

def register_security_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_vulnerabilities)
    mcp.add_tool(get_vulnerability_count)
    mcp.add_tool(scan_all_vulnerabilities)
    mcp.add_tool(list_image_scans)
