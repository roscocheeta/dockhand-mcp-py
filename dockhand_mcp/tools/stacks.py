"""
Stack (Docker Compose) management tools.
"""

import fnmatch
from typing import Any
from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path, paginate_items, redact_env_text, redact_sensitive_dict, validate_repo_url


def _compact_stack(s: dict) -> dict:
    """Keep only essential fields for token efficiency."""
    res: dict[str, Any] = {
        "Id": s.get("Id") or s.get("id"),
        "Name": s.get("Name") or s.get("name"),
        "Status": s.get("Status") or s.get("status"),
        "EnvironmentId": s.get("EnvironmentId") or s.get("environmentId"),
        "Type": s.get("Type") or s.get("type") or s.get("sourceType"),
    }
    if "health" in s:
        res["Health"] = s["health"]
    if "labelTags" in s:
        res["LabelTags"] = s["labelTags"]
    if "updateCount" in s:
        res["UpdateCount"] = s["updateCount"]
    if "newerVersionCount" in s:
        res["NewerVersionCount"] = s["newerVersionCount"]
    if "coolingDownCount" in s:
        res["CoolingDownCount"] = s["coolingDownCount"]
    if "pinnedDigestCount" in s:
        res["PinnedDigestCount"] = s["pinnedDigestCount"]
    return res


def _normalize_stack_args(name: Any, ctx: Any, env: Any) -> tuple[str, Any, int | None]:
    if isinstance(name, int):
        return str(ctx), env, name
    return name, ctx, env


async def list_stacks(
    environment_id: int | None = None,
    ctx: Context = None,
    search: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list | dict:
    """List all Docker Compose stacks in an environment.

    Args:
        environment_id: Environment ID (optional, auto-resolves to default).
        ctx: FastMCP Context.
        search: Optional stack name filter supporting wildcards ('*' and '?'), e.g. 'prod-*' or '*media*'.
        limit: Optional maximum number of items to return (returns pagination envelope when set).
        offset: Zero-based starting offset for pagination (default 0).
    """
    if environment_id is not None and not isinstance(environment_id, int):
        if hasattr(environment_id, "request_context"):
            ctx, environment_id = environment_id, None
        elif isinstance(environment_id, str) and search is None and not environment_id.isdigit():
            search, environment_id = environment_id, None
        else:
            ctx, environment_id = environment_id, None
    client = ctx.request_context.lifespan_context["dockhand"]
    env_id = await client.resolve_environment_id(environment_id)
    stacks = await client.get("/api/stacks", params={"env": env_id})
    if isinstance(stacks, list):
        items = [_compact_stack(s) for s in stacks]
        if search:
            search_pat = search.strip().lower()
            items = [s for s in items if fnmatch.fnmatchcase((s.get("Name") or "").lower(), search_pat)]
        return paginate_items(items, limit=limit, offset=offset)
    return stacks

async def create_stack(
    name: str,
    compose: str,
    ctx: Context = None,
    environment_id: int | None = None,
    compose_path: str | None = None,
    env_path: str | None = None,
    start: bool = True,
    env_vars: list[dict[str, Any]] | None = None,
    raw_env_content: str | None = None,
    secret_provider_id: int | None = None,
    respect_pull_policy: bool | None = None,
    pull_base: bool | None = None,
    no_cache: bool | None = None,
    *args: Any
) -> dict:
    """Create a new internal Docker Compose stack from a raw YAML string.

    For Git-backed stacks, use the `create_git_stack` tool instead.

    Args:
        name: Name of the new stack.
        compose: Docker Compose YAML file content as string (required).
        ctx: FastMCP Context.
        environment_id: Environment ID where the stack will be created (optional; defaults to active environment).
        compose_path: Optional explicit path on disk for the compose file.
        env_path: Optional explicit path on disk for the .env file.
        start: Start/deploy the stack immediately after creation (default: True).
        env_vars: Optional environment variables list (dicts with 'key', 'value', and optional 'isSecret').
        raw_env_content: Optional raw .env file content string.
        secret_provider_id: Optional secret provider ID to bind to the stack.
    """
    if isinstance(name, int):
        environment_id, name, compose, ctx = name, str(compose), str(ctx), environment_id
    client = ctx.request_context.lifespan_context["dockhand"]
    body: dict[str, Any] = {
        "name": name,
        "compose": compose,
        "start": start,
    }
    if compose_path is not None:
        body["composePath"] = compose_path
    if env_path is not None:
        body["envPath"] = env_path
    if env_vars is not None:
        body["envVars"] = env_vars
    if raw_env_content is not None:
        body["rawEnvContent"] = raw_env_content
    if secret_provider_id is not None:
        body["secretProviderId"] = secret_provider_id
    if respect_pull_policy is not None:
        body["respectPullPolicy"] = bool(respect_pull_policy)
    if pull_base is not None:
        body["pullBase"] = bool(pull_base)
    if no_cache is not None:
        body["noCache"] = bool(no_cache)

    return await client.post_sse("/api/stacks", json=body, params={"env": await client.resolve_environment_id(environment_id)})

async def get_stack_compose(name: str, ctx: Context = None, environment_id: int | None = None, *args: Any) -> dict:
    """Get the docker-compose.yml content for a stack. Inline secret environment variables are redacted."""
    name, ctx, environment_id = _normalize_stack_args(name, ctx, environment_id)
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/stacks/{encode_path(name)}/compose", 
        params={"env": await client.resolve_environment_id(environment_id)}
    )
    if isinstance(data, dict):
        data = dict(data)
        for key in ("content", "compose"):
            if isinstance(data.get(key), str):
                data[key] = redact_env_text(data[key])
        return data
    if isinstance(data, str):
        return redact_env_text(data)
    return data

async def update_stack_compose(
    name: str, 
    content: str, 
    ctx: Context = None,
    environment_id: int | None = None, 
    restart: bool = False,
    pull: bool | None = None,
    build: bool | None = None,
    force_recreate: bool | None = None,
    respect_pull_policy: bool | None = None,
    pull_base: bool | None = None,
    no_cache: bool | None = None,
    *args: Any
) -> dict:
    """Update the compose file content for a stack. Optionally redeploy after update."""
    if isinstance(name, int):
        environment_id, name, content, ctx = name, str(content), str(ctx), environment_id
    client = ctx.request_context.lifespan_context["dockhand"]
    body: dict[str, Any] = {"content": content}
    if pull is not None:
        body["pull"] = bool(pull)
    if build is not None:
        body["build"] = bool(build)
    if force_recreate is not None:
        body["forceRecreate"] = bool(force_recreate)
    if respect_pull_policy is not None:
        body["respectPullPolicy"] = bool(respect_pull_policy)
    if pull_base is not None:
        body["pullBase"] = bool(pull_base)
    if no_cache is not None:
        body["noCache"] = bool(no_cache)
    if restart:
        body["restart"] = True
        return await client.put_sse(
            f"/api/stacks/{encode_path(name)}/compose", 
            json=body, 
            params={"env": await client.resolve_environment_id(environment_id)}
        )
    return await client.put(
        f"/api/stacks/{encode_path(name)}/compose", 
        json=body, 
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def get_stack_env(name: str, ctx: Context = None, environment_id: int | None = None, *args: Any) -> dict:
    """Get the structured environment variables (.env) for a stack. Secret values are redacted."""
    name, ctx, environment_id = _normalize_stack_args(name, ctx, environment_id)
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/stacks/{encode_path(name)}/env", 
        params={"env": await client.resolve_environment_id(environment_id)}
    )
    return redact_sensitive_dict(data)

async def get_stack_env_raw(name: str, ctx: Context = None, environment_id: int | None = None, *args: Any) -> dict:
    """Get the raw .env file contents for a stack. Secret values are redacted."""
    name, ctx, environment_id = _normalize_stack_args(name, ctx, environment_id)
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/stacks/{encode_path(name)}/env/raw", 
        params={"env": await client.resolve_environment_id(environment_id)}
    )
    if isinstance(data, dict) and isinstance(data.get("content"), str):
        data = dict(data)
        data["content"] = redact_env_text(data["content"])
        return data
    if isinstance(data, str):
        return redact_env_text(data)
    return data

async def update_stack_env_raw(
    name: str, 
    content: str, 
    ctx: Context = None,
    environment_id: int | None = None, 
    *args: Any
) -> dict:
    """
    Update the full .env file content for a stack. Empty string deletes it.
    ⚠️ SECURITY WARNING: Passing secret values in content exposes them in plain text within your chat history.
    """
    if isinstance(name, int):
        environment_id, name, content, ctx = name, str(content), str(ctx), environment_id
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.put(
        f"/api/stacks/{encode_path(name)}/env/raw", 
        json={"content": content}, 
        params={"env": await client.resolve_environment_id(environment_id)}
    )
    if isinstance(data, dict) and isinstance(data.get("content"), str):
        data = dict(data)
        data["content"] = redact_env_text(data["content"])
    return redact_sensitive_dict(data)

async def deploy_stack(
    name: str, 
    ctx: Context = None,
    environment_id: int | None = None, 
    pull: bool = True,
    build: bool = False,
    force_recreate: bool = False,
    respect_pull_policy: bool = False,
    pull_base: bool = False,
    no_cache: bool = False,
    *args: Any
) -> dict:
    """Deploy or update a stack (Docker Compose up).

    Args:
        name: Stack name.
        ctx: FastMCP Context.
        environment_id: Environment ID (optional, auto-resolves to default).
        pull: Pull latest image tags before deploy (default: True).
        build: Build images before starting containers (default: False).
        force_recreate: Recreate containers even if configuration and image haven't changed (default: False).
        respect_pull_policy: Respect each service's individual pull_policy defined in compose (default: False).
        pull_base: Refresh Dockerfile FROM base images before building (docker compose build --pull, default: False).
        no_cache: Do not use cache when building images (docker compose build --no-cache, default: False).
    """
    name, ctx, environment_id = _normalize_stack_args(name, ctx, environment_id)
    client = ctx.request_context.lifespan_context["dockhand"]
    body: dict[str, Any] = {
        "pull": bool(pull),
        "build": bool(build),
        "forceRecreate": bool(force_recreate),
    }
    if respect_pull_policy:
        body["respectPullPolicy"] = True
    if pull_base:
        body["pullBase"] = True
    if no_cache:
        body["noCache"] = True

    return await client.post_sse(
        f"/api/stacks/{encode_path(name)}/deploy", 
        json=body, 
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def start_stack(name: str, ctx: Context = None, environment_id: int | None = None, *args: Any) -> dict:
    """Start a stopped stack."""
    name, ctx, environment_id = _normalize_stack_args(name, ctx, environment_id)
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post_sse(
        f"/api/stacks/{encode_path(name)}/start", 
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def stop_stack(name: str, ctx: Context = None, environment_id: int | None = None, *args: Any) -> dict:
    """Stop a running stack."""
    name, ctx, environment_id = _normalize_stack_args(name, ctx, environment_id)
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post_sse(
        f"/api/stacks/{encode_path(name)}/stop", 
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def restart_stack(
    name: str,
    ctx: Context = None,
    environment_id: int | None = None,
    mode: str | None = None,
    *args: Any
) -> dict:
    """Restart a stack (mode='restart' | 'ordered' | 'recreate')."""
    name, ctx, environment_id = _normalize_stack_args(name, ctx, environment_id)
    client = ctx.request_context.lifespan_context["dockhand"]
    params: dict[str, Any] = {"env": await client.resolve_environment_id(environment_id)}
    if mode is not None:
        params["mode"] = mode
    return await client.post_sse(
        f"/api/stacks/{encode_path(name)}/restart", 
        params=params
    )

async def down_stack(
    name: str, 
    ctx: Context = None,
    environment_id: int | None = None, 
    remove_volumes: bool = False,
    *args: Any
) -> dict:
    """⚠️ DESTRUCTIVE: Tear down a stack (Docker Compose down). If remove_volumes is True, all data is lost."""
    name, ctx, environment_id = _normalize_stack_args(name, ctx, environment_id)
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {"removeVolumes": remove_volumes} if remove_volumes else None
    return await client.post_sse(
        f"/api/stacks/{encode_path(name)}/down", 
        json=body,
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def delete_stack(
    name: str, 
    ctx: Context = None,
    environment_id: int | None = None, 
    force: bool = False,
    files: bool = True,
    *args: Any
) -> dict:
    """⚠️ DESTRUCTIVE: Delete a stack and optionally its files from disk. Permanent deletion."""
    name, ctx, environment_id = _normalize_stack_args(name, ctx, environment_id)
    client = ctx.request_context.lifespan_context["dockhand"]
    params = {"env": await client.resolve_environment_id(environment_id)}
    if force:
        params["force"] = "true"
    if not files:
        params["files"] = "false"
    return await client.delete(
        f"/api/stacks/{encode_path(name)}", 
        params=params
    )

async def update_stack_env(
    name: str,
    env_vars: list[dict[str, Any]],
    ctx: Context = None,
    environment_id: int | None = None,
    *args: Any
) -> dict:
    """
    Update stack environment variables with structured merge/replace.
    ⚠️ SECURITY WARNING: Passing secret env_vars exposes them in plain text within your chat history.
    """
    if isinstance(name, int):
        environment_id, name, env_vars, ctx = name, str(env_vars), ctx, environment_id
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.put(
        f"/api/stacks/{encode_path(name)}/env",
        json={"envVars": env_vars},
        params={"env": await client.resolve_environment_id(environment_id)}
    )
    return redact_sensitive_dict(data)

async def remove_stack_env_vars(
    name: str,
    keys: list[str],
    ctx: Context = None,
    environment_id: int | None = None,
    *args: Any
) -> dict:
    """Selectively remove environment variables from a stack's .env or DB."""
    if isinstance(name, int):
        environment_id, name, keys, ctx = name, str(keys), ctx, environment_id
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(
        f"/api/stacks/{encode_path(name)}/env",
        json={"keys": keys},
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def check_stack_env_collisions(
    name: str,
    ctx: Context = None,
    environment_id: int | None = None,
    *args: Any
) -> dict:
    """Check for environment variable collisions."""
    name, ctx, environment_id = _normalize_stack_args(name, ctx, environment_id)
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/stacks/{encode_path(name)}/env/collisions",
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def validate_stack_env(
    name: str,
    ctx: Context = None,
    environment_id: int | None = None,
    *args: Any
) -> dict:
    """Validate a stack's environment configuration."""
    name, ctx, environment_id = _normalize_stack_args(name, ctx, environment_id)
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/stacks/{encode_path(name)}/env/validate",
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def get_stack_delete_preview(
    name: str,
    ctx: Context = None,
    environment_id: int | None = None,
    *args: Any
) -> dict:
    """Get a preview of what will be deleted when removing a stack."""
    name, ctx, environment_id = _normalize_stack_args(name, ctx, environment_id)
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/stacks/{encode_path(name)}/delete-preview",
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def adopt_stack(
    name: str,
    ctx: Context = None,
    environment_id: int | None = None,
    *args: Any
) -> dict:
    """Adopt an existing unmanaged stack into Dockhand."""
    name, ctx, environment_id = _normalize_stack_args(name, ctx, environment_id)
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(
        f"/api/stacks/{encode_path(name)}/adopt",
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def relocate_stack(
    name: str,
    new_path: str,
    ctx: Context = None,
    environment_id: int | None = None,
    *args: Any
) -> dict:
    """Relocate a stack to a new path on the host."""
    if isinstance(name, int):
        environment_id, name, new_path, ctx = name, str(new_path), str(ctx), environment_id
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(
        f"/api/stacks/{encode_path(name)}/relocate",
        json={"newPath": new_path},
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def get_stack_deploy_history(name: str, ctx: Context = None, environment_id: int | None = None, *args: Any) -> dict:
    """Get the deployment history runs for a stack."""
    name, ctx, environment_id = _normalize_stack_args(name, ctx, environment_id)
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/stacks/{encode_path(name)}/deploys",
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def get_stack_deploy_log(
    name: str,
    run_id: int,
    ctx: Context = None,
    environment_id: int | None = None,
    max_bytes: int = 20480,
    *args: Any
) -> dict:
    """Get the raw deployment log text for a specific stack deploy run (truncated to max_bytes, default 20KB)."""
    if isinstance(name, int):
        environment_id, name, run_id, ctx = name, str(run_id), int(ctx), environment_id
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/stacks/{encode_path(name)}/deploys/{encode_path(str(run_id))}/log",
        params={"env": await client.resolve_environment_id(environment_id)}
    )
    if max_bytes and max_bytes > 0:
        if isinstance(data, dict):
            data = dict(data)
            for key in ("log", "output", "content"):
                val = data.get(key)
                if isinstance(val, str) and len(val) > max_bytes:
                    data[key] = val[:max_bytes] + f"\n... [TRUNCATED AT {max_bytes} BYTES]"
                    data["truncated"] = True
        elif isinstance(data, str) and len(data) > max_bytes:
            return data[:max_bytes] + f"\n... [TRUNCATED AT {max_bytes} BYTES]"
    return data

async def get_stack_stats(environment_id: int | None = None, ctx: Context = None, *args: Any) -> list:
    """Return a CPU/memory/network/block-IO stats snapshot per compose stack in an environment."""
    if environment_id is not None and not isinstance(environment_id, int):
        ctx, environment_id = environment_id, None
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/stack-stats", params={"env": await client.resolve_environment_id(environment_id)})

async def get_stack_path_hints(name: str, ctx: Context = None, environment_id: int | None = None, *args: Any) -> dict:
    """Return path hints (working directory and config file paths) extracted from a stack's Docker container labels."""
    name, ctx, environment_id = _normalize_stack_args(name, ctx, environment_id)
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/stacks/path-hints", params={"name": name, "env": await client.resolve_environment_id(environment_id)})


async def convert_stack_to_git(
    name: str,
    ctx: Context = None,
    environment_id: int | None = None,
    repository_id: int | None = None,
    url: str | None = None,
    repo_name: str | None = None,
    branch: str = "main",
    credential_id: int | None = None,
    compose_path: str = "compose.yaml",
    env_file_path: str | None = None,
    auto_update: bool = False,
    auto_update_schedule: str = "daily",
    auto_update_cron: str = "0 3 * * *",
    webhook_enabled: bool = False,
    webhook_secret: str | None = None,
    context_dir: str | None = None,
    build_on_deploy: bool = False,
    no_build_cache: bool = False,
    repull_images: bool = False,
    force_redeploy: bool = False,
    deploy_now: bool = False,
    secret_provider_id: int | None = None,
    env_vars: list[dict[str, Any]] | None = None,
    *args: Any,
) -> dict:
    """Convert an internal/local Docker Compose stack to Git management without recreating it.

    Allows transitioning an existing local stack to track a remote Git repository.
    The stack's running containers and existing environment variables are preserved.

    ⚠️ SECURITY WARNING: Passing webhook_secret or secret env_vars exposes them in plain text within your chat history.

    Args:
        name: Name of the existing local stack to convert.
        ctx: FastMCP Context.
        environment_id: Environment ID (optional; defaults to active environment).
        repository_id: Optional ID of an already registered Git repository.
        url: Git repository URL (required if repository_id is not specified).
        repo_name: Optional name when registering a new repository (defaults to stack name).
        branch: Git branch to track (default: 'main').
        credential_id: Optional Git credential ID for private repositories.
        compose_path: Relative path to Compose file inside repository (default: 'compose.yaml').
        env_file_path: Optional relative path to .env file inside repository.
        auto_update: Automatically pull changes and redeploy (default: False).
        auto_update_schedule: Auto-sync schedule preset ('hourly', 'daily', 'weekly', 'custom').
        auto_update_cron: 5-field cron expression for custom schedule (default: '0 3 * * *').
        webhook_enabled: Enable webhook endpoint for automated CI/CD deployments (default: False).
        webhook_secret: Optional secret token required for webhook triggering.
        context_dir: Optional subfolder within repo to use as docker compose context.
        build_on_deploy: Build images during deploy (default: False).
        no_build_cache: Disable cache when building images (default: False).
        repull_images: Force repull of images on deploy (default: False).
        force_redeploy: Force recreate containers even if unchanged (default: False).
        deploy_now: Immediately deploy the stack from Git upon conversion (default: False).
        secret_provider_id: Optional secret provider ID to bind to the stack.
        env_vars: Optional environment variable overrides (dicts with 'key', 'value', 'isSecret').
    """
    name, ctx, environment_id = _normalize_stack_args(name, ctx, environment_id)
    client = ctx.request_context.lifespan_context["dockhand"]
    env_id = await client.resolve_environment_id(environment_id)
    body: dict[str, Any] = {
        "branch": branch,
        "composePath": compose_path,
        "autoUpdate": bool(auto_update),
        "autoUpdateSchedule": auto_update_schedule,
        "autoUpdateCron": auto_update_cron,
        "webhookEnabled": bool(webhook_enabled),
        "buildOnDeploy": bool(build_on_deploy),
        "noBuildCache": bool(no_build_cache),
        "repullImages": bool(repull_images),
        "forceRedeploy": bool(force_redeploy),
        "deployNow": bool(deploy_now),
    }
    if repository_id is not None:
        body["repositoryId"] = repository_id
    if url is not None:
        body["url"] = validate_repo_url(url)
    if repo_name is not None:
        body["repoName"] = repo_name
    if credential_id is not None:
        body["credentialId"] = credential_id
    if env_file_path is not None:
        body["envFilePath"] = env_file_path
    if webhook_secret is not None:
        body["webhookSecret"] = webhook_secret
    if context_dir is not None:
        body["contextDir"] = context_dir
    if secret_provider_id is not None:
        body["secretProviderId"] = secret_provider_id
    if env_vars is not None:
        body["envVars"] = env_vars

    if deploy_now:
        res = await client.post_sse(
            f"/api/stacks/{encode_path(name)}/attach",
            json=body,
            params={"env": env_id},
        )
    else:
        res = await client.post(
            f"/api/stacks/{encode_path(name)}/attach",
            json=body,
            params={"env": env_id},
        )
    return redact_sensitive_dict(res)

def register_stack_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_stacks)
    mcp.add_tool(create_stack)
    mcp.add_tool(get_stack_compose)
    mcp.add_tool(update_stack_compose)
    mcp.add_tool(get_stack_env)
    mcp.add_tool(get_stack_env_raw)
    mcp.add_tool(update_stack_env)
    mcp.add_tool(update_stack_env_raw)
    mcp.add_tool(remove_stack_env_vars)
    mcp.add_tool(check_stack_env_collisions)
    mcp.add_tool(validate_stack_env)
    mcp.add_tool(get_stack_delete_preview)
    mcp.add_tool(adopt_stack)
    mcp.add_tool(relocate_stack)
    mcp.add_tool(deploy_stack)
    mcp.add_tool(start_stack)
    mcp.add_tool(stop_stack)
    mcp.add_tool(restart_stack)
    mcp.add_tool(down_stack)
    mcp.add_tool(delete_stack)
    mcp.add_tool(get_stack_deploy_history)
    mcp.add_tool(get_stack_deploy_log)
    mcp.add_tool(get_stack_stats)
    mcp.add_tool(get_stack_path_hints)
    mcp.add_tool(convert_stack_to_git)
