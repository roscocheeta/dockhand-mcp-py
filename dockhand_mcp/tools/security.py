"""
Security and vulnerability scanning tools.
"""

from typing import Any
from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path


_VALID_VULN_GROUP_BY = frozenset({"container", "image", "stack"})


def _clean_env_ctx(env_val: Any, ctx_val: Any) -> tuple[int | None, Any]:
    if env_val is not None and not isinstance(env_val, int):
        return None, env_val
    return env_val, ctx_val


async def list_vulnerabilities(
    environment_id: int | None = None,
    ctx: Context = None,
    limit: int = 50,
    offset: int = 0,
    q: str | None = None,
    severity: str | None = None,
    image: str | None = None,
    container: str | None = None,
    stack: str | None = None,
) -> dict:
    """List aggregated vulnerability findings for the given environment with server-side filtering and pagination.

    Args:
        environment_id: Environment ID (optional, auto-resolves to default).
        ctx: FastMCP Context.
        limit: Maximum number of findings to return (default: 50, to keep context compact).
        offset: Zero-based pagination offset (default: 0).
        q: Optional search query across CVE, package, or image.
        severity: Optional severity filter (e.g. 'critical', 'high', 'medium', 'low').
        image: Optional image name filter.
        container: Optional container name filter.
        stack: Optional stack name filter.
    """
    environment_id, ctx = _clean_env_ctx(environment_id, ctx)
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError(f"Invalid 'limit' value {limit!r}: must be a positive integer (>= 1).")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError(f"Invalid 'offset' value {offset!r}: must be a non-negative integer.")

    client = ctx.request_context.lifespan_context["dockhand"]
    params: dict[str, Any] = {
        "env": await client.resolve_environment_id(environment_id),
        "limit": limit,
        "offset": offset,
    }
    for key, val in (
        ("q", q),
        ("severity", severity),
        ("image", image),
        ("container", container),
        ("stack", stack),
    ):
        if val is not None and val.strip():
            params[key] = val.strip()

    return await client.get("/api/vulnerabilities", params=params)

async def get_vulnerability_count(
    environment_id: int | None = None,
    ctx: Context = None,
    group_by: str | None = None,
) -> dict:
    """Get vulnerability counts for the given environment, optionally grouped by container, image, or stack.

    Args:
        environment_id: Environment ID (optional, auto-resolves to default).
        ctx: FastMCP Context.
        group_by: Optional grouping ('container', 'image', or 'stack') introduced in Dockhand v1.0.59.
                  When omitted, returns total, severity summary, and filter options.
                  When set, returns {'groupBy': ..., 'groups': [...]} sorted most severe first.
    """
    environment_id, ctx = _clean_env_ctx(environment_id, ctx)
    params: dict[str, Any] = {}
    if group_by is not None:
        normalized = group_by.strip().lower()
        if normalized not in _VALID_VULN_GROUP_BY:
            raise ValueError(
                f"Invalid group_by {group_by!r}; expected one of {sorted(_VALID_VULN_GROUP_BY)}."
            )
        params["groupBy"] = normalized

    client = ctx.request_context.lifespan_context["dockhand"]
    params["env"] = await client.resolve_environment_id(environment_id)
    return await client.get("/api/vulnerabilities/count", params=params)

async def scan_all_vulnerabilities(environment_id: int | None = None, ctx: Context = None) -> dict:
    """Trigger a vulnerability scan across all images in the environment (SSE stream)."""
    environment_id, ctx = _clean_env_ctx(environment_id, ctx)
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post_sse("/api/vulnerabilities/scan-all", params={"env": await client.resolve_environment_id(environment_id)})

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
