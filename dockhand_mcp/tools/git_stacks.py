"""
Git Stack management tools.
"""

import fnmatch
from typing import Any
from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import (
    encode_path,
    paginate_items,
    redact_sensitive_dict,
    redact_url_credentials,
    strip_nulls,
    validate_repo_url,
)


def _compact_git_stack(s: dict) -> dict:
    """Keep only essential fields for token efficiency."""
    repo = s.get("repository") if isinstance(s.get("repository"), dict) else {}
    raw_url = s.get("Url") or s.get("url") or repo.get("url")
    return {
        "Id": s.get("Id") or s.get("id"),
        "Name": s.get("stackName") or s.get("Name") or s.get("name"),
        "Url": redact_url_credentials(raw_url) if isinstance(raw_url, str) else raw_url,
        "Branch": s.get("Branch") or s.get("branch") or repo.get("branch"),
        "Status": s.get("syncStatus") or s.get("Status") or s.get("status"),
        "EnvironmentId": s.get("EnvironmentId") or s.get("environmentId"),
        "ComposePath": s.get("composePath") or s.get("ComposePath"),
    }


def _compact_sync_result(res: dict) -> dict:
    """Strip massive file hash manifests and raw compose dumps from sync response to save tokens."""
    if not isinstance(res, dict):
        return res
    success = res.get("success", res.get("synced", False))
    compact = {
        "success": success,
        "synced": success,
        "commit": res.get("commit"),
        "updated": res.get("updated", False),
        "changedFiles": res.get("changedFiles", []),
        "composeFileName": res.get("composeFileName"),
    }
    if res.get("error"):
        compact["error"] = res["error"]
    if res.get("deletionPlan") and res["deletionPlan"].get("toDelete"):
        compact["toDelete"] = res["deletionPlan"]["toDelete"]
    return compact


async def list_git_stacks(
    ctx: Context = None,
    search: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list | dict:
    """List all Git-backed stacks.

    Args:
        ctx: FastMCP Context.
        search: Optional stack name filter supporting wildcards ('*' and '?'), e.g. 'prod-*'.
        limit: Optional maximum number of items to return (returns pagination envelope when set).
        offset: Zero-based starting offset for pagination (default 0).
    """
    if hasattr(ctx, "request_context") is False and isinstance(ctx, str):
        search, ctx = ctx, None
    client = ctx.request_context.lifespan_context["dockhand"]
    stacks = await client.get("/api/git/stacks")
    if isinstance(stacks, list):
        items = [_compact_git_stack(s) for s in stacks]
        if search:
            search_pat = search.strip().lower()
            items = [s for s in items if fnmatch.fnmatchcase((s.get("Name") or "").lower(), search_pat)]
        return paginate_items(items, limit=limit, offset=offset)
    return stacks

async def get_git_stack(stack_id: int | str, ctx: Context = None) -> dict:
    """Get details for a specific Git stack by numeric ID or stack name. Webhook secrets and secret env vars are redacted."""
    client = ctx.request_context.lifespan_context["dockhand"]
    resolved_id = await client.resolve_git_stack_id(stack_id)
    data = await client.get(f"/api/git/stacks/{encode_path(str(resolved_id))}")
    return redact_sensitive_dict(strip_nulls(data))

async def deploy_git_stack(
    stack_id: int | str,
    ctx: Context = None,
    pull: bool | None = None,
    respect_pull_policy: bool | None = None,
    build: bool | None = None,
    pull_base: bool | None = None,
    no_cache: bool | None = None,
    force_recreate: bool | None = None,
    *args: Any,
) -> dict:
    """Deploy a Git stack by numeric ID or stack name. Uses SSE streaming.

    Args:
        stack_id: Numeric ID or name of the Git stack.
        ctx: FastMCP Context.
        pull: Pull latest images before deployment.
        respect_pull_policy: Respect each service's individual pull_policy defined in compose.
        build: Build images before starting containers.
        pull_base: Refresh Dockerfile FROM base images before building (docker compose build --pull).
        no_cache: Do not use cache when building images (docker compose build --no-cache).
        force_recreate: Recreate containers even if unchanged.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    resolved_id = await client.resolve_git_stack_id(stack_id)
    body: dict[str, Any] = {}
    if pull is not None:
        body["pull"] = bool(pull)
    if respect_pull_policy is not None:
        body["respectPullPolicy"] = bool(respect_pull_policy)
    if build is not None:
        body["build"] = bool(build)
    if pull_base is not None:
        body["pullBase"] = bool(pull_base)
    if no_cache is not None:
        body["noCache"] = bool(no_cache)
    if force_recreate is not None:
        body["forceRecreate"] = bool(force_recreate)

    return await client.post_sse(
        f"/api/git/stacks/{encode_path(str(resolved_id))}/deploy-stream",
        json=body if body else None,
    )

async def sync_git_stack(
    stack_id: int | str,
    ctx: Context = None,
    deploy: bool = False,
    pull: bool | None = None,
    respect_pull_policy: bool | None = None,
    build: bool | None = None,
    pull_base: bool | None = None,
    no_cache: bool | None = None,
    force_recreate: bool | None = None,
    *args: Any,
) -> dict:
    """Sync a Git stack with its remote repository by numeric ID or stack name.

    Args:
        stack_id: Numeric ID or name of the Git stack (e.g. 33 or 'radarr').
        ctx: FastMCP Context.
        deploy: If True, automatically deploys the stack after a successful sync.
        pull: Pull latest images before deployment.
        respect_pull_policy: Respect each service's individual pull_policy defined in compose.
        build: Build images before starting containers.
        pull_base: Refresh Dockerfile FROM base images before building.
        no_cache: Do not use cache when building images.
        force_recreate: Recreate containers even if unchanged.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    resolved_id = await client.resolve_git_stack_id(stack_id)
    raw_sync = await client.post(f"/api/git/stacks/{encode_path(str(resolved_id))}/sync")
    compact_sync = _compact_sync_result(raw_sync)

    if not deploy:
        return compact_sync

    if not compact_sync.get("success", False):
        return {
            "sync": compact_sync,
            "deploy": {"success": False, "error": "Deployment skipped because sync failed"},
        }

    deploy_res = await deploy_git_stack(
        stack_id=resolved_id,
        ctx=ctx,
        pull=pull,
        respect_pull_policy=respect_pull_policy,
        build=build,
        pull_base=pull_base,
        no_cache=no_cache,
        force_recreate=force_recreate,
    )
    return {
        "sync": compact_sync,
        "deploy": deploy_res,
    }


async def sync_and_deploy_git_stack(
    stack_id: int | str,
    ctx: Context = None,
    pull: bool | None = None,
    respect_pull_policy: bool | None = None,
    build: bool | None = None,
    pull_base: bool | None = None,
    no_cache: bool | None = None,
    force_recreate: bool | None = None,
    *args: Any,
) -> dict:
    """Atomically sync a Git stack by numeric ID or name with its remote repository and immediately deploy it."""
    return await sync_git_stack(
        stack_id=stack_id,
        ctx=ctx,
        deploy=True,
        pull=pull,
        respect_pull_policy=respect_pull_policy,
        build=build,
        pull_base=pull_base,
        no_cache=no_cache,
        force_recreate=force_recreate,
    )

async def create_git_stack(
    stack_name: str,
    url: str,
    ctx: Context = None,
    environment_id: int | None = None,
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
    ⚠️ SECURITY WARNING: Passing webhook_secret or secret env_vars exposes them in plain text within your chat history.

    Args:
        environment_id: Environment ID where the stack will be created.
        stack_name: Unique stack name.
        url: Git repository URL (HTTPS or SSH).
        branch: Git branch to track (default: 'main').
        compose_path: Path to compose file in repository relative to repo root (default: 'docker-compose.yml').
        env_file_path: Path to .env file in repository (optional).
        credential_id: Git credential ID for private repositories (optional; SSH URLs require an SSH key credential, not username/password).
        deploy_now: Whether to deploy the stack immediately after creation (default: True).
        auto_update: Enable automatic syncing on a schedule (default: False).
        auto_update_cron: Cron expression for auto-sync schedule (e.g., '0 3 * * *' for 3 AM daily).
        webhook_enabled: Enable webhook for push-triggered deploys (default: False).
        webhook_secret: Secret for webhook verification (auto-generated if not provided).
        env_vars: Optional environment variable overrides (list of dicts with 'key', 'value', optional 'isSecret').
    """
    url = validate_repo_url(url)
    client = ctx.request_context.lifespan_context["dockhand"]
    env_id = await client.resolve_environment_id(environment_id)
    body: dict = {
        "stackName": stack_name,
        "environmentId": env_id,
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
    data = await client.post("/api/git/stacks", json=body)
    return redact_sensitive_dict(data)

async def update_git_stack(stack_id: int | str, ctx: Context = None, branch: str | None = None, compose_path: str | None = None, env_vars: list | None = None) -> dict:
    """
    Update a Git stack by numeric ID or stack name.
    ⚠️ SECURITY WARNING: Passing secret env_vars exposes them in plain text within your chat history.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    resolved_id = await client.resolve_git_stack_id(stack_id)
    body = {}
    if branch is not None: body["branch"] = branch
    if compose_path is not None: body["composePath"] = compose_path
    if env_vars is not None: body["envVars"] = env_vars
    data = await client.put(f"/api/git/stacks/{encode_path(str(resolved_id))}", json=body)
    return redact_sensitive_dict(data)

async def delete_git_stack(stack_id: int | str, ctx: Context = None, force: bool = False) -> dict:
    """Delete a Git stack by numeric ID or stack name."""
    client = ctx.request_context.lifespan_context["dockhand"]
    resolved_id = await client.resolve_git_stack_id(stack_id)
    params = {}
    if force: params["force"] = "true"
    return await client.delete(f"/api/git/stacks/{encode_path(str(resolved_id))}", params=params)


async def convert_git_stack_to_local(
    stack_id: int | str,
    ctx: Context = None,
    *args: Any,
) -> dict:
    """Convert a Git-managed Docker Compose stack back to local management without recreating it.

    Detaches Git management while keeping containers and configurations running in place.
    Note: The Git stack must have been deployed at least once so its compose file is present on disk.

    Args:
        stack_id: Numeric ID or name of the Git stack (e.g. 12 or 'my-app').
        ctx: FastMCP Context.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    resolved_id = await client.resolve_git_stack_id(stack_id)
    res = await client.post(f"/api/git/stacks/{encode_path(str(resolved_id))}/detach")
    return redact_sensitive_dict(strip_nulls(res))

def register_git_stack_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_git_stacks)
    mcp.add_tool(get_git_stack)
    mcp.add_tool(deploy_git_stack)
    mcp.add_tool(sync_git_stack)
    mcp.add_tool(sync_and_deploy_git_stack)
    mcp.add_tool(create_git_stack)
    mcp.add_tool(update_git_stack)
    mcp.add_tool(delete_git_stack)
    mcp.add_tool(convert_git_stack_to_local)
