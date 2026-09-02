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


async def list_registries(environment_id: int, ctx: Context) -> list:
    """List all Docker registries configured in an environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    registries = await client.get("/api/registries", params={"env": environment_id})
    if isinstance(registries, list):
        return [_compact_registry(r) for r in registries]
    return registries

async def create_registry(
    environment_id: int,
    name: str,
    registry_type: str,
    url: str,
    ctx: Context,
    username: str | None = None,
    password: str | None = None,
) -> dict:
    """
    ⚠️ SECURITY WARNING: The password parameter is passed in plain text.
    It will be visible in chat history and server logs. For production
    credentials, please create the registry via the Dockhand web UI instead.
    
    Create a new container registry connection.
    registry_type is typically 'dockerhub', 'ghcr', 'gitlab', 'ecr', or 'custom'.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {
        "name": name,
        "type": registry_type,
        "url": url,
    }
    if username:
        body["username"] = username
    if password:
        body["password"] = password
        
    reg = await client.post("/api/registries", json=body, params={"env": environment_id})
    return _compact_registry(reg)

async def update_registry(
    environment_id: int, 
    registry_id: int, 
    ctx: Context,
    name: str | None = None,
    url: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> dict:
    """
    ⚠️ SECURITY WARNING: The password parameter is passed in plain text.
    It will be visible in chat history and server logs. For production
    credentials, please update the registry via the Dockhand web UI instead.
    
    Update an existing registry connection.
    """
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

async def delete_registry(environment_id: int, registry_id: int, ctx: Context) -> dict:
    """Delete a Docker registry configuration."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(
        f"/api/registries/{encode_path(str(registry_id))}", 
        params={"env": environment_id}
    )

async def test_registry(environment_id: int, registry_id: int, ctx: Context) -> dict:
    """Test connection/authentication to a Docker registry."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(
        f"/api/registries/{encode_path(str(registry_id))}/test", 
        params={"env": environment_id}
    )

def register_registry_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_registries)
    mcp.add_tool(create_registry)
    mcp.add_tool(update_registry)
    mcp.add_tool(delete_registry)
    mcp.add_tool(test_registry)
