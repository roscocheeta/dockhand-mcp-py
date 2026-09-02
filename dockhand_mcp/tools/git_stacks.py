"""
Git Stack management tools.
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path


def _compact_git_stack(s: dict) -> dict:
    """Keep only essential fields for token efficiency."""
    return {
        "Id": s.get("Id") or s.get("id"),
        "Name": s.get("Name") or s.get("name"),
        "Url": s.get("Url") or s.get("url"),
        "Branch": s.get("Branch") or s.get("branch"),
        "Status": s.get("Status") or s.get("status"),
        "EnvironmentId": s.get("EnvironmentId") or s.get("environmentId"),
    }


async def list_git_stacks(ctx: Context) -> list:
    """List all Git-backed stacks."""
    client = ctx.request_context.lifespan_context["dockhand"]
    stacks = await client.get("/api/git/stacks")
    if isinstance(stacks, list):
        return [_compact_git_stack(s) for s in stacks]
    return stacks

async def get_git_stack(stack_id: int, ctx: Context) -> dict:
    """Get details for a specific Git stack."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(f"/api/git/stacks/{encode_path(str(stack_id))}")

async def deploy_git_stack(stack_id: int, ctx: Context) -> dict:
    """Deploy a Git stack. Uses SSE streaming."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post_sse(f"/api/git/stacks/{encode_path(str(stack_id))}/deploy")

async def sync_git_stack(stack_id: int, ctx: Context) -> dict:
    """Sync a Git stack with its remote repository."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(f"/api/git/stacks/{encode_path(str(stack_id))}/sync")

async def list_git_credentials(ctx: Context) -> list:
    """List Git credentials (passwords stripped for security)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    creds = await client.get("/api/git/credentials")
    
    # Security: mask credentials regardless of key casing
    _secret_keys = ("password", "token", "sshkey", "sshKey", "Password", "Token", "SshKey")
    if isinstance(creds, list):
        for c in creds:
            for key in _secret_keys:
                if key in c:
                    c[key] = "***"
    return creds

async def list_git_repositories(ctx: Context) -> list:
    """List Git repositories."""
    client = ctx.request_context.lifespan_context["dockhand"]
    repos = await client.get("/api/git/repositories")
    # Token efficiency
    if isinstance(repos, list):
        return [
            {
                "Id": r.get("id") or r.get("Id"),
                "Name": r.get("name") or r.get("Name"),
                "Url": r.get("url") or r.get("Url"),
                "Branch": r.get("branch") or r.get("Branch"),
            }
            for r in repos
        ]
    return repos

def register_git_stack_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_git_stacks)
    mcp.add_tool(get_git_stack)
    mcp.add_tool(deploy_git_stack)
    mcp.add_tool(sync_git_stack)
    mcp.add_tool(list_git_credentials)
    mcp.add_tool(list_git_repositories)
