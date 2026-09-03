"""
Stack (Docker Compose) management tools.
"""

from typing import Any
from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path


def _compact_stack(s: dict) -> dict:
    """Keep only essential fields for token efficiency."""
    return {
        "Id": s.get("Id") or s.get("id"),
        "Name": s.get("Name") or s.get("name"),
        "Status": s.get("Status") or s.get("status"),
        "EnvironmentId": s.get("EnvironmentId") or s.get("environmentId"),
        "Type": s.get("Type") or s.get("type"),
    }


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
    ctx: Context,
    compose: str | None = None,
    compose_path: str | None = None,
    env_path: str | None = None,
    start: bool = True,
    env_vars: list[dict[str, Any]] | None = None,
    raw_env_content: str | None = None,
    secret_provider_id: int | None = None,
    repository_id: int | None = None,
    branch: str | None = None,
) -> dict:
    """Create a new Docker Compose stack.

    Args:
        environment_id: Environment ID where the stack will be created.
        name: Name of the new stack.
        ctx: FastMCP Context.
        compose: Docker Compose YAML file content as string. Required if not using repository_id.
        compose_path: Optional explicit path on disk for the compose file (or relative path in git repo).
        env_path: Optional explicit path on disk for the .env file.
        start: Start/deploy the stack immediately after creation (default: True).
        env_vars: Optional environment variables list (dicts with 'key', 'value', and optional 'isSecret').
        raw_env_content: Optional raw .env file content string.
        secret_provider_id: Optional secret provider ID to bind to the stack.
        repository_id: Optional Git Repository ID to use for the stack.
        branch: Optional Git branch to use (e.g., 'main' or 'master') when repository_id is provided.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    body: dict[str, Any] = {
        "name": name,
        "start": start,
    }
    
    if compose is not None:
        body["compose"] = compose
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
    if repository_id is not None:
        body["repositoryId"] = repository_id
    if branch is not None:
        body["branch"] = branch

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
    restart: bool = False
) -> dict:
    """Update the compose file content for a stack. Optionally redeploy after update."""
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {"content": content}
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
    """Get the structured environment variables (.env) for a stack."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/stacks/{encode_path(name)}/env", 
        params={"env": environment_id}
    )

async def get_stack_env_raw(environment_id: int, name: str, ctx: Context) -> dict:
    """Get the raw .env file contents for a stack."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/stacks/{encode_path(name)}/env/raw", 
        params={"env": environment_id}
    )

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

async def restart_stack(environment_id: int, name: str, ctx: Context) -> dict:
    """Restart a stack."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post_sse(
        f"/api/stacks/{encode_path(name)}/restart", 
        params={"env": environment_id}
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
