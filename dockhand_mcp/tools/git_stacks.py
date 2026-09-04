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
    return await client.post_sse(f"/api/git/stacks/{encode_path(str(stack_id))}/deploy-stream")

async def sync_git_stack(stack_id: int, ctx: Context) -> dict:
    """Sync a Git stack with its remote repository."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(f"/api/git/stacks/{encode_path(str(stack_id))}/sync")

async def create_git_stack(
    environment_id: int,
    stack_name: str,
    url: str,
    ctx: Context,
    branch: str = "main",
    compose_path: str = "docker-compose.yml",
    env_file_path: str | None = None,
    credential_id: int | None = None,
    deploy_now: bool = True,
    auto_update: bool = False,
    auto_update_cron: str | None = None,
    webhook_enabled: bool = False,
    webhook_secret: str | None = None,
    env_vars: list | None = None,
) -> dict:
    """Create a new Git-backed Docker Compose stack.

    This creates a stack linked to a Git repository. The compose file
    is pulled from the repo and deployed. For internal string stacks
    (no Git), use the `create_stack` tool instead.

    Args:
        environment_id: Environment ID where the stack will be created.
        stack_name: Unique stack name.
        url: Git repository URL (HTTPS or SSH).
        branch: Git branch to track (default: 'main').
        compose_path: Path to compose file in repository relative to repo root (default: 'docker-compose.yml').
        env_file_path: Path to .env file in repository (optional).
        credential_id: Git credential ID for private repositories (optional).
        deploy_now: Whether to deploy the stack immediately after creation (default: True).
        auto_update: Enable automatic syncing on a schedule (default: False).
        auto_update_cron: Cron expression for auto-sync schedule (e.g., '0 3 * * *' for 3 AM daily).
        webhook_enabled: Enable webhook for push-triggered deploys (default: False).
        webhook_secret: Secret for webhook verification (auto-generated if not provided).
        env_vars: Optional environment variable overrides (list of dicts with 'key', 'value', optional 'isSecret').
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    body: dict = {
        "stackName": stack_name,
        "environmentId": environment_id,
        "url": url,
        "branch": branch,
        "composePath": compose_path,
        "deployNow": deploy_now,
    }
    if env_file_path is not None:
        body["envFilePath"] = env_file_path
    if credential_id is not None:
        body["credentialId"] = credential_id
    if auto_update:
        body["autoUpdate"] = True
        if auto_update_cron is not None:
            body["autoUpdateCron"] = auto_update_cron
    if webhook_enabled:
        body["webhookEnabled"] = True
        if webhook_secret is not None:
            body["webhookSecret"] = webhook_secret
    if env_vars is not None:
        body["envVars"] = env_vars
    return await client.post("/api/git/stacks", json=body)

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
