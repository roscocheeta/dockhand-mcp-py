"""
Docker Registry management tools.
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path


def _compact_registry(r: dict) -> dict:
    """Keep only essential fields and strip passwords for security/efficiency."""
    compact = {
        "Id": r.get("Id") or r.get("id"),
        "Name": r.get("Name") or r.get("name"),
        "Url": r.get("Url") or r.get("url"),
        "Username": r.get("Username") or r.get("username"),
        "Type": r.get("Type") or r.get("type"),
        "EnvironmentId": r.get("EnvironmentId") or r.get("environmentId"),
    }
    return compact

def register_registry_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_registries(environment_id: int, ctx: Context) -> list:
        """List all Docker registries configured in an environment."""
        client = ctx.request_context.lifespan_context["dockhand"]
        registries = await client.get("/api/registries", params={"env": environment_id})
        if isinstance(registries, list):
            return [_compact_registry(r) for r in registries]
        return registries

    @mcp.tool()
    async def create_registry(
        environment_id: int, 
        name: str, 
        url: str, 
        username: str, 
        password: str, 
        ctx: Context,
        registry_type: str = "custom"
    ) -> dict:
        """Create a new Docker registry configuration."""
        client = ctx.request_context.lifespan_context["dockhand"]
        body = {
            "name": name,
            "url": url,
            "username": username,
            "password": password,
            "type": registry_type
        }
        return await client.post("/api/registries", json=body, params={"env": environment_id})

    @mcp.tool()
    async def update_registry(
        environment_id: int, 
        registry_id: int, 
        ctx: Context,
        name: str | None = None,
        url: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Update an existing Docker registry configuration."""
        client = ctx.request_context.lifespan_context["dockhand"]
        body = {}
        if name:
            body["name"] = name
        if url:
            body["url"] = url
        if username:
            body["username"] = username
        if password:
            body["password"] = password
            
        return await client.put(
            f"/api/registries/{encode_path(str(registry_id))}", 
            json=body, 
            params={"env": environment_id}
        )

    @mcp.tool()
    async def delete_registry(environment_id: int, registry_id: int, ctx: Context) -> dict:
        """Delete a Docker registry configuration."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.delete(
            f"/api/registries/{encode_path(str(registry_id))}", 
            params={"env": environment_id}
        )

    @mcp.tool()
    async def test_registry(environment_id: int, registry_id: int, ctx: Context) -> dict:
        """Test connection/authentication to a Docker registry."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.post(
            f"/api/registries/{encode_path(str(registry_id))}/test", 
            params={"env": environment_id}
        )
