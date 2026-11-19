"""
Security and vulnerability scanning tools.
"""

from typing import Any
from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path


def _clean_env_ctx(env_val: Any, ctx_val: Any) -> tuple[int | None, Any]:
    if env_val is not None and not isinstance(env_val, int):
        return None, env_val
    return env_val, ctx_val


async def list_vulnerabilities(environment_id: int | None = None, ctx: Context = None) -> dict:
    """List all known vulnerabilities for the given environment."""
    environment_id, ctx = _clean_env_ctx(environment_id, ctx)
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/security/vulnerabilities", params={"env": await client.resolve_environment_id(environment_id)})

async def get_vulnerability_count(environment_id: int | None = None, ctx: Context = None) -> dict:
    """Get the count of vulnerabilities for the given environment."""
    environment_id, ctx = _clean_env_ctx(environment_id, ctx)
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/security/vulnerabilities/count", params={"env": await client.resolve_environment_id(environment_id)})

async def scan_all_vulnerabilities(environment_id: int | None = None, ctx: Context = None) -> dict:
    """Trigger a vulnerability scan across all resources in the environment."""
    environment_id, ctx = _clean_env_ctx(environment_id, ctx)
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post("/api/security/vulnerabilities/scan", params={"env": await client.resolve_environment_id(environment_id)})

async def list_image_scans(image_id: str, ctx: Context = None, environment_id: int | None = None) -> dict:
    """List vulnerability scans for a specific image."""
    if isinstance(image_id, int):
        environment_id, image_id, ctx = image_id, str(ctx), environment_id
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(f"/api/images/{encode_path(image_id)}/scans", params={"env": await client.resolve_environment_id(environment_id)})

async def scan_image(
    image_name: str, 
    ctx: Context = None,
    environment_id: int | None = None, 
    scanner: str | None = None,
) -> dict:
    """Run vulnerability scan on a Docker image using Grype or Trivy.
    
    Args:
        image_name: Image name or ID to scan (e.g., 'nginx:latest' or sha256).
        ctx: FastMCP Context.
        environment_id: Environment ID containing the image (optional; defaults to active environment).
        scanner: Force specific scanner ('grype' or 'trivy'). If not specified, uses environment settings.
    """
    if isinstance(image_name, int):
        environment_id, image_name, ctx = image_name, str(ctx), environment_id
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {"imageName": image_name}
    if scanner is not None:
        body["scanner"] = scanner
        
    return await client.post("/api/images/scan", json=body, params={"env": await client.resolve_environment_id(environment_id)})

def register_security_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_vulnerabilities)
    mcp.add_tool(get_vulnerability_count)
    mcp.add_tool(scan_all_vulnerabilities)
    mcp.add_tool(list_image_scans)
    mcp.add_tool(scan_image)
