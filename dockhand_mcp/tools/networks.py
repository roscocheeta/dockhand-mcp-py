"""
Network management tools.
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path, strip_nulls, truncate_id


def _compact_network(n: dict) -> dict:
    """Keep only essential fields for token efficiency."""
    return {
        "Id": truncate_id(n.get("Id") or n.get("id")),
        "Name": n.get("Name") or n.get("name"),
        "Driver": n.get("Driver") or n.get("driver"),
        "Scope": n.get("Scope") or n.get("scope")
    }


async def list_networks(environment_id: int, ctx: Context) -> list:
    """List all Docker networks in an environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    networks = await client.get("/api/networks", params={"env": environment_id})
    if isinstance(networks, list):
        return [_compact_network(n) for n in networks]
    return networks

async def inspect_network(environment_id: int, network_id: str, ctx: Context) -> dict:
    """Inspect a specific Docker network."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/networks/{encode_path(network_id)}", 
        params={"env": environment_id}
    )
    return strip_nulls(data)

async def delete_network(environment_id: int, network_id: str, ctx: Context) -> dict:
    """⚠️ DESTRUCTIVE: Delete a Docker network. Connected containers will lose connectivity."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(
        f"/api/networks/{encode_path(network_id)}", 
        params={"env": environment_id}
    )

async def get_network(environment_id: int, network_id: str, ctx: Context) -> dict:
    """Get details for a specific Docker network."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/networks/{encode_path(network_id)}", 
        params={"env": environment_id}
    )
    return strip_nulls(data)

def register_network_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_networks)
    mcp.add_tool(get_network)
    mcp.add_tool(inspect_network)
    mcp.add_tool(delete_network)
