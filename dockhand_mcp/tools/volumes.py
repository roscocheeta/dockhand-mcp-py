"""
Volume management tools.
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path, strip_nulls


def _compact_volume(v: dict) -> dict:
    """Keep only essential fields for token efficiency."""
    return {
        "Name": v.get("Name") or v.get("name"),
        "Driver": v.get("Driver") or v.get("driver"),
        "Mountpoint": v.get("Mountpoint") or v.get("mountpoint")
    }


async def list_volumes(environment_id: int, ctx: Context) -> list:
    """List all Docker volumes in an environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    volumes = await client.get("/api/volumes", params={"env": environment_id})
    # Note: the Docker API often wraps volumes in a "Volumes" key, but Dockhand
    # might unwrap it. We'll handle both.
    if isinstance(volumes, dict) and "Volumes" in volumes:
        vol_list = volumes["Volumes"]
        if isinstance(vol_list, list):
            volumes["Volumes"] = [_compact_volume(v) for v in vol_list]
        return volumes
    elif isinstance(volumes, list):
        return [_compact_volume(v) for v in volumes]
    return volumes

async def inspect_volume(environment_id: int, volume_name: str, ctx: Context) -> dict:
    """Inspect a specific Docker volume."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/volumes/{encode_path(volume_name)}", 
        params={"env": environment_id}
    )
    return strip_nulls(data)

async def delete_volume(environment_id: int, volume_name: str, ctx: Context) -> dict:
    """⚠️ DESTRUCTIVE: Delete a Docker volume. All data stored in this volume will be permanently lost."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(
        f"/api/volumes/{encode_path(volume_name)}", 
        params={"env": environment_id}
    )

async def get_volume(environment_id: int, volume_name: str, ctx: Context) -> dict:
    """Get details for a specific Docker volume."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/volumes/{encode_path(volume_name)}", 
        params={"env": environment_id}
    )
    return strip_nulls(data)

async def create_volume(
    environment_id: int,
    name: str,
    ctx: Context,
    driver: str = "local",
    driver_opts: dict | None = None,
    labels: dict | None = None,
) -> dict:
    """Create a new Docker volume.

    Args:
        environment_id: Environment ID where the volume will be created.
        name: Name of the new volume.
        ctx: FastMCP Context.
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
        # The Dockhand API expects camelCase 'driverOpts'
        body["driverOpts"] = driver_opts
    if labels is not None:
        body["labels"] = labels
        
    return await client.post("/api/volumes", json=body, params={"env": environment_id})

def register_volume_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_volumes)
    mcp.add_tool(get_volume)
    mcp.add_tool(inspect_volume)
    mcp.add_tool(create_volume)
    mcp.add_tool(delete_volume)
