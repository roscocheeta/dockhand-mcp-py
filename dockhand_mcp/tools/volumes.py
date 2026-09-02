"""
Volume management tools.
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path


def _compact_volume(v: dict) -> dict:
    """Keep only essential fields for token efficiency."""
    return {
        "Name": v.get("Name"),
        "Driver": v.get("Driver"),
        "Mountpoint": v.get("Mountpoint")
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
    return await client.get(
        f"/api/volumes/{encode_path(volume_name)}", 
        params={"env": environment_id}
    )

async def delete_volume(environment_id: int, volume_name: str, ctx: Context) -> dict:
    """Delete a Docker volume."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(
        f"/api/volumes/{encode_path(volume_name)}", 
        params={"env": environment_id}
    )

def register_volume_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_volumes)
    mcp.add_tool(inspect_volume)
    mcp.add_tool(delete_volume)
