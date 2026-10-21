"""
Stack (Docker Compose) management tools.
"""

from typing import Any
from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path, redact_env_text, redact_sensitive_dict


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


async def list_stacks(environment_id: int, ctx: Context) -> list:
    """List all Docker Compose stacks in an environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    stacks = await client.get("/api/stacks", params={"env": environment_id})
    if isinstance(stacks, list):
        return [_compact_stack(s) for s in stacks]
    return stacks

async def create_stack(
    environment_id: int,
    name: str,
    compose: str,
    ctx: Context,
    compose_path: str | None = None,
    env_path: str | None = None,
    start: bool = True,
    env_vars: list[dict[str, Any]] | None = None,
    raw_env_content: str | None = None,
    secret_provider_id: int | None = None,
) -> dict:
    """Create a new internal Docker Compose stack from a raw YAML string.

    For Git-backed stacks, use the `create_git_stack` tool instead.

    Args:
        environment_id: Environment ID where the stack will be created.
        name: Name of the new stack.
        compose: Docker Compose YAML file content as string (required).
        compose_path: Optional explicit path on disk for the compose file.
        env_path: Optional explicit path on disk for the .env file.
        start: Start/deploy the stack immediately after creation (default: True).
        env_vars: Optional environment variables list (dicts with 'key', 'value', and optional 'isSecret').
        raw_env_content: Optional raw .env file content string.
        secret_provider_id: Optional secret provider ID to bind to the stack.
    """
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

    return await client.post_sse("/api/stacks", json=body, params={"env": environment_id})

async def get_stack_compose(environment_id: int, name: str, ctx: Context) -> dict:
    """Get the docker-compose.yml content for a stack."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/stacks/{encode_path(name)}/compose", 
        params={"env": environment_id}
    )

async def update_stack_compose(
    environment_id: int, 
    name: str, 
    content: str, 
    ctx: Context,
    restart: bool = False,
    pull: bool | None = None,
    build: bool | None = None,
    force_recreate: bool | None = None,
) -> dict:
    """Update the compose file content for a stack. Optionally redeploy after update."""
    client = ctx.request_context.lifespan_context["dockhand"]
    body: dict[str, Any] = {"content": content}
    if pull is not None:
        body["pull"] = pull
    if build is not None:
        body["build"] = build
    if force_recreate is not None:
        body["forceRecreate"] = force_recreate
    if restart:
        body["restart"] = True
        return await client.put_sse(
            f"/api/stacks/{encode_path(name)}/compose", 
            json=body, 
            params={"env": environment_id}
        )
    return await client.put(
        f"/api/stacks/{encode_path(name)}/compose", 
        json=body, 
        params={"env": environment_id}
    )

async def get_stack_env(environment_id: int, name: str, ctx: Context) -> dict:
    """Get the structured environment variables (.env) for a stack. Secret values are redacted."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/stacks/{encode_path(name)}/env", 
        params={"env": environment_id}
    )
    return redact_sensitive_dict(data)

async def get_stack_env_raw(environment_id: int, name: str, ctx: Context) -> dict:
    """Get the raw .env file contents for a stack. Secret values are redacted."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/stacks/{encode_path(name)}/env/raw", 
        params={"env": environment_id}
    )
    if isinstance(data, dict) and isinstance(data.get("content"), str):
        data = dict(data)
        data["content"] = redact_env_text(data["content"])
        return data
    if isinstance(data, str):
        return redact_env_text(data)
    return data

async def update_stack_env_raw(
    environment_id: int, 
    name: str, 
    content: str, 
    ctx: Context
) -> dict:
    """Update the full .env file content for a stack. Empty string deletes it."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.put(
        f"/api/stacks/{encode_path(name)}/env/raw", 
        json={"content": content}, 
        params={"env": environment_id}
    )

async def deploy_stack(
    environment_id: int, 
    name: str, 
    ctx: Context,
    pull: bool = True,
    build: bool = False,
    force_recreate: bool = False
) -> dict:
    """Deploy or update a stack (Docker Compose up)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {
        "pull": pull,
        "build": build,
        "forceRecreate": force_recreate
    }
    return await client.post_sse(
        f"/api/stacks/{encode_path(name)}/deploy", 
        json=body, 
        params={"env": environment_id}
    )

async def start_stack(environment_id: int, name: str, ctx: Context) -> dict:
    """Start a stopped stack."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post_sse(
        f"/api/stacks/{encode_path(name)}/start", 
        params={"env": environment_id}
    )

async def stop_stack(environment_id: int, name: str, ctx: Context) -> dict:
    """Stop a running stack."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post_sse(
        f"/api/stacks/{encode_path(name)}/stop", 
        params={"env": environment_id}
    )

async def restart_stack(
    environment_id: int,
    name: str,
    ctx: Context,
    mode: str | None = None,
) -> dict:
    """Restart a stack (mode='restart' | 'ordered' | 'recreate')."""
    client = ctx.request_context.lifespan_context["dockhand"]
    params: dict[str, Any] = {"env": environment_id}
    if mode is not None:
        params["mode"] = mode
    return await client.post_sse(
        f"/api/stacks/{encode_path(name)}/restart", 
        params=params
    )

async def down_stack(
    environment_id: int, 
    name: str, 
    ctx: Context,
    remove_volumes: bool = False
) -> dict:
    """⚠️ DESTRUCTIVE: Tear down a stack (Docker Compose down). If remove_volumes is True, all data is lost."""
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {"removeVolumes": remove_volumes} if remove_volumes else None
    return await client.post_sse(
        f"/api/stacks/{encode_path(name)}/down", 
        json=body,
        params={"env": environment_id}
    )

async def delete_stack(
    environment_id: int, 
    name: str, 
    ctx: Context,
    force: bool = False,
    files: bool = True
) -> dict:
    """⚠️ DESTRUCTIVE: Delete a stack and optionally its files from disk. Permanent deletion."""
    client = ctx.request_context.lifespan_context["dockhand"]
    params = {"env": environment_id}
    if force:
        params["force"] = "true"
    if not files:
        params["files"] = "false"
    return await client.delete(
        f"/api/stacks/{encode_path(name)}", 
        params=params
    )

async def update_stack_env(
    environment_id: int,
    name: str,
    env_vars: list[dict[str, Any]],
    ctx: Context,
) -> dict:
    """Update stack environment variables with structured merge/replace."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.put(
        f"/api/stacks/{encode_path(name)}/env",
        json={"envVars": env_vars},
        params={"env": environment_id}
    )

async def remove_stack_env_vars(
    environment_id: int,
    name: str,
    keys: list[str],
    ctx: Context,
) -> dict:
    """Selectively remove environment variables from a stack's .env or DB."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(
        f"/api/stacks/{encode_path(name)}/env",
        json={"keys": keys},
        params={"env": environment_id}
    )

async def check_stack_env_collisions(
    environment_id: int,
    name: str,
    ctx: Context,
) -> dict:
    """Check for environment variable collisions."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/stacks/{encode_path(name)}/env/collisions",
        params={"env": environment_id}
    )

async def validate_stack_env(
    environment_id: int,
    name: str,
    ctx: Context,
) -> dict:
    """Validate a stack's environment configuration."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/stacks/{encode_path(name)}/env/validate",
        params={"env": environment_id}
    )

async def get_stack_delete_preview(
    environment_id: int,
    name: str,
    ctx: Context,
) -> dict:
    """Get a preview of what will be deleted when removing a stack."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/stacks/{encode_path(name)}/delete/preview",
        params={"env": environment_id}
    )

async def adopt_stack(
    environment_id: int,
    name: str,
    ctx: Context,
) -> dict:
    """Adopt an existing unmanaged stack into Dockhand."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(
        f"/api/stacks/{encode_path(name)}/adopt",
        params={"env": environment_id}
    )

async def relocate_stack(
    environment_id: int,
    name: str,
    new_path: str,
    ctx: Context,
) -> dict:
    """Relocate a stack to a new path on the host."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(
        f"/api/stacks/{encode_path(name)}/relocate",
        json={"newPath": new_path},
        params={"env": environment_id}
    )

async def get_stack_deploy_history(environment_id: int, name: str, ctx: Context) -> dict:
    """Get the deployment history runs for a stack."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/stacks/{encode_path(name)}/deploys",
        params={"env": environment_id}
    )

async def get_stack_deploy_log(
    environment_id: int,
    name: str,
    run_id: int,
    ctx: Context,
    max_bytes: int = 20480,
) -> dict:
    """Get the raw deployment log text for a specific stack deploy run (truncated to max_bytes, default 20KB)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/stacks/{encode_path(name)}/deploys/{encode_path(str(run_id))}/log",
        params={"env": environment_id}
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

async def get_stack_stats(environment_id: int, ctx: Context) -> list:
    """Return a CPU/memory/network/block-IO stats snapshot per compose stack in an environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/stack-stats", params={"env": environment_id})

async def get_stack_path_hints(environment_id: int, name: str, ctx: Context) -> dict:
    """Return path hints (working directory and config file paths) extracted from a stack's Docker container labels."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/stacks/path-hints", params={"name": name, "env": environment_id})

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

