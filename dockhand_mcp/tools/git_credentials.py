"""
Git Credential management tools.
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path, redact_sensitive_dict

async def list_git_credentials(ctx: Context) -> list:
    """List Git credentials (passwords stripped for security)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    creds = await client.get("/api/git/credentials")
    
    _secret_keys = ("password", "token", "sshkey", "sshKey", "Password", "Token", "SshKey")
    if isinstance(creds, list):
        for c in creds:
            for key in _secret_keys:
                if key in c:
                    c[key] = "***"
    return creds

async def create_git_credential(name: str, username: str, ctx: Context, password: str | None = None, private_key: str | None = None) -> dict:
    """
    Create a new Git credential.
    ⚠️ SECURITY WARNING: Passing password or private_key exposes secrets in plain text within your chat history.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {"name": name, "username": username}
    if password is not None:
        body["password"] = password
    if private_key is not None:
        body["privateKey"] = private_key
    data = await client.post("/api/git/credentials", json=body)
    return redact_sensitive_dict(data)

async def update_git_credential(credential_id: int, ctx: Context, name: str | None = None, username: str | None = None, password: str | None = None, private_key: str | None = None) -> dict:
    """
    Update an existing Git credential.
    ⚠️ SECURITY WARNING: Passing password or private_key exposes secrets in plain text within your chat history.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {}
    if name is not None: body["name"] = name
    if username is not None: body["username"] = username
    if password is not None: body["password"] = password
    if private_key is not None: body["privateKey"] = private_key
    data = await client.put(f"/api/git/credentials/{encode_path(str(credential_id))}", json=body)
    return redact_sensitive_dict(data)

async def delete_git_credential(credential_id: int, ctx: Context) -> dict:
    """Delete a Git credential."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(f"/api/git/credentials/{encode_path(str(credential_id))}")

def register_git_credential_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_git_credentials)
    mcp.add_tool(create_git_credential)
    mcp.add_tool(update_git_credential)
    mcp.add_tool(delete_git_credential)
