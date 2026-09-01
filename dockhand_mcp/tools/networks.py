"""
Network management tools.
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path


def _compact_network(n: dict) -> dict:
    """Keep only essential fields for token efficiency."""
    return {
        "Id": n.get("Id"),
        "Name": n.get("Name"),
        "Driver": n.get("Driver"),
        "Scope": n.get("Scope")
    }

def register_network_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_networks(environment_id: int, ctx: Context) -> list:
        """List all Docker networks in an environment."""
        client = ctx.request_context.lifespan_context["dockhand"]
        networks = await client.get("/api/networks", params={"env": environment_id})
        if isinstance(networks, list):
            return [_compact_network(n) for n in networks]
        return networks

    @mcp.tool()
    async def inspect_network(environment_id: int, network_id: str, ctx: Context) -> dict:
        """Inspect a specific Docker network."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get(
            f"/api/networks/{encode_path(network_id)}", 
            params={"env": environment_id}
        )

    @mcp.tool()
    async def delete_network(environment_id: int, network_id: str, ctx: Context) -> dict:
        """Delete a Docker network."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.delete(
            f"/api/networks/{encode_path(network_id)}", 
            params={"env": environment_id}
        )
