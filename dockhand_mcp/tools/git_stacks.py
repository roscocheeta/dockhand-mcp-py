"""
Git Stack management tools.
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path, strip_nulls


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
    data = await client.get(f"/api/git/stacks/{encode_path(str(stack_id))}")
    return strip_nulls(data)

async def deploy_git_stack(stack_id: int, ctx: Context) -> dict:
    """Deploy a Git stack. Uses SSE streaming."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post_sse(f"/api/git/stacks/{encode_path(str(stack_id))}/deploy")

async def sync_git_stack(stack_id: int, ctx: Context) -> dict:
    """Sync a Git stack with its remote repository."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(f"/api/git/stacks/{encode_path(str(stack_id))}/sync")

async def create_git_stack(environment_id: int, name: str, repository_id: int, branch: str, compose_path: str, ctx: Context, env_vars: list | None = None) -> dict:
    """Create a Git stack."""
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {
        "name": name,
        "repositoryId": repository_id,
        "branch": branch,
        "composePath": compose_path
    }
    if env_vars:
        body["envVars"] = env_vars
    return await client.post("/api/git/stacks", json=body, params={"env": environment_id})

async def update_git_stack(stack_id: int, ctx: Context, branch: str | None = None, compose_path: str | None = None, env_vars: list | None = None) -> dict:
    """Update a Git stack."""
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {}
    if branch is not None: body["branch"] = branch
    if compose_path is not None: body["composePath"] = compose_path
    if env_vars is not None: body["envVars"] = env_vars
    return await client.put(f"/api/git/stacks/{encode_path(str(stack_id))}", json=body)

async def delete_git_stack(stack_id: int, ctx: Context, force: bool = False) -> dict:
    """Delete a Git stack."""
    client = ctx.request_context.lifespan_context["dockhand"]
    params = {}
    if force: params["force"] = "true"
    return await client.delete(f"/api/git/stacks/{encode_path(str(stack_id))}", params=params)

def register_git_stack_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_git_stacks)
    mcp.add_tool(get_git_stack)
    mcp.add_tool(deploy_git_stack)
    mcp.add_tool(sync_git_stack)
    mcp.add_tool(create_git_stack)
    mcp.add_tool(update_git_stack)
    mcp.add_tool(delete_git_stack)
