"""
Network management tools.
"""

from typing import Any
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


async def list_networks(environment_id: int | None = None, ctx: Context = None) -> list:
    """List all Docker networks in an environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    networks = await client.get("/api/networks", params={"env": await client.resolve_environment_id(environment_id)})
    if isinstance(networks, list):
        return [_compact_network(n) for n in networks]
    return networks

async def inspect_network(network_id: str, ctx: Context = None, environment_id: int | None = None, *args: Any) -> dict:
    if isinstance(network_id, int):
        environment_id, network_id, ctx = network_id, str(ctx), environment_id
    """Inspect a specific Docker network."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/networks/{encode_path(network_id)}", 
        params={"env": await client.resolve_environment_id(environment_id)}
    )
    return strip_nulls(data)

async def delete_network(network_id: str, ctx: Context = None, environment_id: int | None = None, *args: Any) -> dict:
    if isinstance(network_id, int):
        environment_id, network_id, ctx = network_id, str(ctx), environment_id
    """⚠️ DESTRUCTIVE: Delete a Docker network. Connected containers will lose connectivity."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(
        f"/api/networks/{encode_path(network_id)}", 
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def create_network(
    name: str,
    ctx: Context = None,
    environment_id: int | None = None,
    driver: str = "bridge",
    options: dict | None = None,
    labels: dict | None = None,
    ipam: dict | None = None,
    internal: bool = False,
    attachable: bool = False,
    *args: Any
) -> dict:
    if isinstance(name, int):
        environment_id, name, ctx = name, str(ctx), environment_id
    """Create a new Docker network.

    Args:
        name: Name of the new network.
        ctx: FastMCP Context.
        environment_id: Environment ID where the network will be created (optional; defaults to active environment).
        driver: Network driver to use (default: 'bridge').
        options: Network driver options as key-value dict.
        labels: User-defined labels for organizing networks.
        ipam: IP Address Management configuration (IPAM).
        internal: Restrict external access to the network (default: False).
        attachable: Allow manual container attachment (default: False).
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {
        "name": name,
        "driver": driver,
        "internal": internal,
        "attachable": attachable
    }
    if options is not None:
        body["options"] = options
    if labels is not None:
        body["labels"] = labels
    if ipam is not None:
        body["ipam"] = ipam
        
    return await client.post("/api/networks", json=body, params={"env": await client.resolve_environment_id(environment_id)})

async def get_network(network_id: str, ctx: Context = None, environment_id: int | None = None, *args: Any) -> dict:
    if isinstance(network_id, int):
        environment_id, network_id, ctx = network_id, str(ctx), environment_id
    """Get details for a specific Docker network."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/networks/{encode_path(network_id)}", 
        params={"env": await client.resolve_environment_id(environment_id)}
    )
    return strip_nulls(data)

def register_network_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_networks)
    mcp.add_tool(get_network)
    mcp.add_tool(inspect_network)
    mcp.add_tool(create_network)
    mcp.add_tool(delete_network)
