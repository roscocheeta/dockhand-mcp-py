"""
User and Auth/Token management tools.
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path


def _compact_user(u: dict) -> dict:
    """Keep only essential fields for token efficiency."""
    return {
        "Id": u.get("Id") or u.get("id"),
        "Username": u.get("Username") or u.get("username"),
        "Role": u.get("Role") or u.get("role"),
        "Created": u.get("Created") or u.get("created"),
        "Active": u.get("Active") or u.get("active", True),
    }

def _compact_token(t: dict) -> dict:
    """Keep only essential fields for token efficiency."""
    return {
        "Id": t.get("Id") or t.get("id"),
        "Name": t.get("Name") or t.get("name"),
        "Created": t.get("Created") or t.get("created"),
        "LastUsed": t.get("LastUsed") or t.get("lastUsed"),
    }


async def list_users(ctx: Context) -> list:
    """List all users in the Dockhand instance."""
    client = ctx.request_context.lifespan_context["dockhand"]
    users = await client.get("/api/users")
    if isinstance(users, list):
        return [_compact_user(u) for u in users]
    return users

async def create_user(
    username: str, 
    password: str, 
    ctx: Context,
    role: str = "user"
) -> dict:
    """
    SECURITY WARNING: The password parameter is passed in plain text.
    It will be visible in chat history and server logs. For production
    credentials, please create the user via the Dockhand web UI instead.
    
    Create a new user in Dockhand.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {
        "username": username,
        "password": password,
        "role": role
    }
    return await client.post("/api/users", json=body)

async def update_user(
    user_id: int, 
    ctx: Context,
    password: str | None = None,
    role: str | None = None
) -> dict:
    """
    SECURITY WARNING: The password parameter is passed in plain text.
    It will be visible in chat history and server logs. For production
    credentials, please update the user via the Dockhand web UI instead.
    
    Update an existing user.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {}
    if password:
        body["password"] = password
    if role:
        body["role"] = role
        
    return await client.put(f"/api/users/{encode_path(str(user_id))}", json=body)

async def delete_user(user_id: int, ctx: Context) -> dict:
    """Delete a user."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(f"/api/users/{encode_path(str(user_id))}")

async def list_tokens(ctx: Context) -> list:
    """List API tokens for the currently authenticated user."""
    client = ctx.request_context.lifespan_context["dockhand"]
    tokens = await client.get("/api/auth/tokens")
    if isinstance(tokens, list):
        return [_compact_token(t) for t in tokens]
    return tokens

async def create_token(name: str, ctx: Context) -> dict:
    """
    SECURITY WARNING: The raw token value is returned in the response.
    It will be visible in chat history. Please store it securely or
    use the Dockhand web UI instead if creating a production token.
    
    Create a new API token.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post("/api/auth/tokens", json={"name": name})

async def delete_token(token_id: int, ctx: Context) -> dict:
    """Delete an API token."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(f"/api/auth/tokens/{encode_path(str(token_id))}")

def register_user_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_users)
    mcp.add_tool(create_user)
    mcp.add_tool(update_user)
    mcp.add_tool(delete_user)
    mcp.add_tool(list_tokens)
    mcp.add_tool(create_token)
    mcp.add_tool(delete_token)
