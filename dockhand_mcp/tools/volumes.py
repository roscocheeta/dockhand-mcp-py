"""
Volume management tools.
"""

import fnmatch
from typing import Any
from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path, paginate_items, strip_nulls


def _compact_volume(v: dict) -> dict:
    """Keep only essential fields for token efficiency."""
    return {
        "Name": v.get("Name") or v.get("name"),
        "Driver": v.get("Driver") or v.get("driver"),
        "Mountpoint": v.get("Mountpoint") or v.get("mountpoint")
    }


async def list_volumes(
    environment_id: int | None = None,
    ctx: Context = None,
    search: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list | dict:
    """List all Docker volumes in an environment.

    Args:
        environment_id: Environment ID (optional, auto-resolves to default).
        ctx: FastMCP Context.
        search: Optional volume name wildcard filter ('*' and '?').
        limit: Optional maximum number of items to return (returns pagination envelope when set).
        offset: Zero-based starting offset for pagination (default 0).
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    volumes = await client.get("/api/volumes", params={"env": await client.resolve_environment_id(environment_id)})
    if isinstance(volumes, dict) and "Volumes" in volumes:
        vol_list = volumes["Volumes"]
        if vol_list is None:
            vol_list = []
        if isinstance(vol_list, list):
            items = [_compact_volume(v) for v in vol_list]
            if search:
                pat = search.strip().lower()
                items = [v for v in items if fnmatch.fnmatchcase((v.get("Name") or "").lower(), pat)]
            items.sort(key=lambda v: (v.get("Name") or "").lower())
            paginated = paginate_items(items, limit=limit, offset=offset)
            if isinstance(paginated, dict):
                return paginated
            volumes["Volumes"] = paginated
        return volumes
    elif isinstance(volumes, list):
        items = [_compact_volume(v) for v in volumes]
        if search:
            pat = search.strip().lower()
            items = [v for v in items if fnmatch.fnmatchcase((v.get("Name") or "").lower(), pat)]
        items.sort(key=lambda v: (v.get("Name") or "").lower())
        return paginate_items(items, limit=limit, offset=offset)
    return volumes

async def inspect_volume(volume_name: str, ctx: Context = None, environment_id: int | None = None) -> dict:
    if isinstance(volume_name, int):
        environment_id, volume_name, ctx = volume_name, str(ctx), environment_id
    """Inspect a specific Docker volume."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/volumes/{encode_path(volume_name)}", 
        params={"env": await client.resolve_environment_id(environment_id)}
    )
    return strip_nulls(data)

async def delete_volume(volume_name: str, ctx: Context = None, environment_id: int | None = None) -> dict:
    if isinstance(volume_name, int):
        environment_id, volume_name, ctx = volume_name, str(ctx), environment_id
    """⚠️ DESTRUCTIVE: Delete a Docker volume. All data stored in this volume will be permanently lost."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(
        f"/api/volumes/{encode_path(volume_name)}", 
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def get_volume(volume_name: str, ctx: Context = None, environment_id: int | None = None) -> dict:
    if isinstance(volume_name, int):
        environment_id, volume_name, ctx = volume_name, str(ctx), environment_id
    """Get details for a specific Docker volume."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/volumes/{encode_path(volume_name)}", 
        params={"env": await client.resolve_environment_id(environment_id)}
    )
    return strip_nulls(data)

async def create_volume(
    name: str,
    ctx: Context = None,
    environment_id: int | None = None,
    driver: str = "local",
    driver_opts: dict | None = None,
    labels: dict | None = None,
) -> dict:
    if isinstance(name, int):
        environment_id, name, ctx = name, str(ctx), environment_id
    """Create a new Docker volume.

    Args:
        name: Name of the new volume.
        ctx: FastMCP Context.
        environment_id: Environment ID where the volume will be created (optional; defaults to active environment).
        driver: Volume driver to use (default: 'local').
        driver_opts: Volume driver options as key-value pairs (e.g. for NFS mounts).
        labels: User-defined labels for organizing volumes.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {
        "name": name,
        "driver": driver
    }
    if driver_opts is not None:
        body["driverOpts"] = driver_opts
    if labels is not None:
        body["labels"] = labels
        
    return await client.post("/api/volumes", json=body, params={"env": await client.resolve_environment_id(environment_id)})

def register_volume_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_volumes)
    mcp.add_tool(get_volume)
    mcp.add_tool(inspect_volume)
    mcp.add_tool(create_volume)
    mcp.add_tool(delete_volume)
