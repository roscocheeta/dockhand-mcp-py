"""
Container management tools (Read-only for Phase 2b).
"""

import json
from typing import Any
from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path, truncate_id, clean_container_inspect, redact_env_text, parse_since_to_epoch


def _compact_container(c: dict) -> dict:
    """Keep only essential fields for token efficiency."""
    res: dict[str, Any] = {
        "Id": truncate_id(c.get("Id") or c.get("id")),
        "Name": c.get("Name") or c.get("name") or (c.get("Names", [""])[0] if c.get("Names") else ""),
        "Image": c.get("Image") or c.get("image"),
        "State": c.get("State") or c.get("state"),
        "Status": c.get("Status") or c.get("status"),
        "Ports": c.get("Ports") or c.get("ports") or []
    }
    health = c.get("Health") or c.get("health")
    if health:
        res["Health"] = health
    labels = c.get("Labels") or c.get("labels")
    if isinstance(labels, dict):
        if "dockhand.tags" in labels:
            res["Tags"] = labels["dockhand.tags"]
        if "dockhand.name" in labels:
            res["DisplayName"] = labels["dockhand.name"]
    return res


async def list_containers(environment_id: int, ctx: Context) -> list:
    """List all containers in a Dockhand environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    containers = await client.get("/api/containers", params={"env": environment_id})
    if isinstance(containers, list):
        return [_compact_container(c) for c in containers]
    return containers

async def get_container(environment_id: int, container_id: str, ctx: Context) -> dict:
    """Get detailed inspection data for a specific container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/containers/{encode_path(container_id)}",
        params={"env": environment_id},
    )
    return clean_container_inspect(data)

async def inspect_container(environment_id: int, container_id: str, ctx: Context) -> dict:
    """Get low-level docker inspect information for a container. Secrets in environment variables are redacted."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/containers/{encode_path(container_id)}/inspect",
        params={"env": environment_id},
    )
    return clean_container_inspect(data)

async def get_container_logs(
    environment_id: int,
    container_id: str,
    ctx: Context,
    tail: int = 100,
    timestamps: bool = False,
    since: str | int | None = None,
) -> str:
    """
    Get stdout/stderr logs from a container.
    tail: Number of lines from the end (default 100, max 500).
    """
    tail = min(tail, 500)
    client = ctx.request_context.lifespan_context["dockhand"]
    params: dict[str, Any] = {"env": environment_id, "tail": tail}
    if timestamps:
        params["timestamps"] = "true"
    if since is not None:
        epoch = parse_since_to_epoch(since)
        if epoch is not None:
            params["since"] = epoch

    data = await client.get(
        f"/api/containers/{encode_path(container_id)}/logs",
        params=params,
    )
    if isinstance(data, dict) and "logs" in data:
        return data["logs"]
    return data if isinstance(data, str) else str(data)

async def get_container_stats(environment_id: int, container_id: str, ctx: Context) -> dict:
    """Get live resource usage statistics (CPU, memory, net I/O) for a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/containers/{encode_path(container_id)}/stats",
        params={"env": environment_id},
    )

async def get_container_top(environment_id: int, container_id: str, ctx: Context) -> dict:
    """Get the running processes inside a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/containers/{encode_path(container_id)}/top",
        params={"env": environment_id},
    )

async def list_container_files(
    environment_id: int,
    container_id: str,
    ctx: Context,
    path: str = "/",
) -> list | dict:
    """
    List files and directories inside a container.
    path: Absolute path inside the container to list (default: /).
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/containers/{encode_path(container_id)}/files",
        params={"env": environment_id, "path": path},
    )

async def get_container_file_content(
    environment_id: int,
    container_id: str,
    path: str,
    ctx: Context,
    max_bytes: int = 10240,
) -> str:
    """
    Read the text content of a file inside a container.
    path: Absolute path to the file inside the container.
    max_bytes: Maximum bytes to return (default 10KB). Content beyond this is truncated.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    content = await client.get(
        f"/api/containers/{encode_path(container_id)}/files/content",
        params={"env": environment_id, "path": path},
    )
    if isinstance(content, str) and len(content.encode("utf-8")) > max_bytes:
        truncated = content.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
        return truncated + f"\n\n[...truncated at {max_bytes} bytes. Use max_bytes parameter to read more.]"
    return content


async def start_container(environment_id: int, container_id: str, ctx: Context) -> dict:
    """Start a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(f"/api/containers/{encode_path(container_id)}/start", params={"env": environment_id})

async def stop_container(environment_id: int, container_id: str, ctx: Context) -> dict:
    """Stop a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(f"/api/containers/{encode_path(container_id)}/stop", params={"env": environment_id})

async def restart_container(environment_id: int, container_id: str, ctx: Context) -> dict:
    """Restart a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(f"/api/containers/{encode_path(container_id)}/restart", params={"env": environment_id})

async def pause_container(environment_id: int, container_id: str, ctx: Context) -> dict:
    """Pause a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(f"/api/containers/{encode_path(container_id)}/pause", params={"env": environment_id})

async def unpause_container(environment_id: int, container_id: str, ctx: Context) -> dict:
    """Unpause a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(f"/api/containers/{encode_path(container_id)}/unpause", params={"env": environment_id})

async def delete_container(environment_id: int, container_id: str, ctx: Context, force: bool = False) -> dict:
    """⚠️ DESTRUCTIVE: Delete a container (optionally force-kill it first). Permanent unless re-created."""
    client = ctx.request_context.lifespan_context["dockhand"]
    params = {"env": environment_id}
    if force:
        params["force"] = "true"
    return await client.delete(f"/api/containers/{encode_path(container_id)}", params=params)

async def rename_container(environment_id: int, container_id: str, name: str, ctx: Context) -> dict:
    """Rename a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(f"/api/containers/{encode_path(container_id)}/rename", json={"name": name}, params={"env": environment_id})

async def create_container(
    environment_id: int,
    name: str,
    image: str,
    ctx: Context,
    start_after_create: bool = False,
    env: list[str] | None = None,
    ports: dict | None = None,
    volumes: list[str] | None = None,
    restart_policy: str | None = None,
    network_mode: str | None = None,
    labels: dict[str, str] | None = None,
) -> dict:
    """Create a new container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {"name": name, "image": image}
    if start_after_create:
        body["startAfterCreate"] = True
    if env:
        body["Env"] = env
    if labels:
        body["Labels"] = labels
    host_config = {}
    if restart_policy:
        host_config["RestartPolicy"] = {"Name": restart_policy}
    if ports:
        host_config["PortBindings"] = ports
    if volumes:
        host_config["Binds"] = volumes
    if network_mode:
        host_config["NetworkMode"] = network_mode
    if host_config:
        body["HostConfig"] = host_config
        
    return await client.post("/api/containers", json=body, params={"env": environment_id})


async def update_container(
    environment_id: int,
    container_id: str,
    ctx: Context,
    image: str | None = None,
    name: str | None = None,
    cmd: list[str] | None = None,
    env: list[str] | None = None,
    restart_policy: str | None = None,
    network_mode: str | None = None,
    repull_image: bool | None = None,
    start_after_update: bool | None = None,
) -> dict:
    """Update a container (Note: Dockhand will recreate it)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    body: dict[str, Any] = {}
    if image:
        body["image"] = image
    if name:
        body["name"] = name
    if cmd:
        body["cmd"] = cmd
    if env:
        body["env"] = env
    if restart_policy:
        body["restartPolicy"] = restart_policy
    if network_mode:
        body["networkMode"] = network_mode
    if repull_image is not None:
        body["repullImage"] = repull_image
    if start_after_update is not None:
        body["startAfterUpdate"] = start_after_update
        
    return await client.post(
        f"/api/containers/{encode_path(container_id)}/update", 
        json=body, 
        params={"env": environment_id}
    )

async def exec_container(
    environment_id: int,
    container_id: str,
    ctx: Context,
    shell: str | None = None,
    user: str | None = None,
) -> dict:
    """Execute a command/create an interactive terminal session in a container.
    Returns an execId which can be used to attach via WebSocket.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {}
    if shell:
        body["shell"] = shell
    if user:
        body["user"] = user
        
    return await client.post(
        f"/api/containers/{encode_path(container_id)}/exec", 
        json=body, 
        params={"envId": environment_id}
    )

async def write_container_file_content(
    environment_id: int,
    container_id: str,
    path: str,
    content: str,
    ctx: Context,
) -> dict:
    """Write text content to a file inside a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.put(
        f"/api/containers/{encode_path(container_id)}/files/content",
        json={"content": content},
        params={"env": environment_id, "path": path},
    )

import base64

async def upload_container_file(
    environment_id: int,
    container_id: str,
    directory: str,
    filename: str,
    base64_content: str,
    ctx: Context,
    owner: str | None = None,
) -> dict:
    """Upload a file to a container directory using base64 encoded content. Owner format: 'user', 'uid', 'user:group', 'uid:gid'."""
    client = ctx.request_context.lifespan_context["dockhand"]
    try:
        file_bytes = base64.b64decode(base64_content)
    except Exception as e:
        raise ValueError(f"Invalid base64_content: {e}")

    files = {"files": (filename, file_bytes)}
    data = {}
    if owner:
        data["owner"] = owner

    return await client.post(
        f"/api/containers/{encode_path(container_id)}/files/upload",
        files=files,
        data=data,
        params={"env": environment_id, "path": directory},
    )

async def create_container_path(
    environment_id: int,
    container_id: str,
    path: str,
    type: str,
    ctx: Context,
    owner: str | None = None,
) -> dict:
    """Create an empty file or directory inside a container. Type must be 'file' or 'directory'."""
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {"path": path, "type": type}
    if owner:
        body["owner"] = owner
    return await client.post(
        f"/api/containers/{encode_path(container_id)}/files/create",
        json=body,
        params={"env": environment_id},
    )

async def chown_container_file(
    environment_id: int,
    container_id: str,
    path: str,
    owner: str,
    ctx: Context,
    recursive: bool = False,
) -> dict:
    """Change the owner/group of a file or directory inside a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(
        f"/api/containers/{encode_path(container_id)}/files/chown",
        json={"path": path, "owner": owner, "recursive": recursive},
        params={"env": environment_id},
    )

async def run_container_exec(
    environment_id: int,
    container_id: str,
    cmd: str | list[str],
    ctx: Context,
    user: str | None = None,
    working_dir: str | None = None,
    max_bytes: int = 10240,
) -> dict:
    """
    Run a one-shot command in a container and wait for the result (returns stdout, stderr, exitCode).
    ⚠️ SECURITY WARNING: Executes arbitrary commands inside the target container and streams output into the chat context.

    Args:
        environment_id: Target environment ID.
        container_id: Container name or ID.
        cmd: Command to execute, either as a shell string (e.g. 'ps aux | grep nginx', run via /bin/sh -c)
             or as a list of strings (e.g. ['ls', '-la']).
        user: Optional user to execute the command as.
        working_dir: Optional working directory.
        max_bytes: Maximum output bytes to capture before truncation (default 10240).
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    if isinstance(cmd, str):
        cmd_list = ["/bin/sh", "-c", cmd]
    elif isinstance(cmd, list):
        cmd_list = cmd
    else:
        raise ValueError("cmd must be a string or a list of strings")

    body: dict[str, Any] = {"cmd": cmd_list}
    if user:
        body["user"] = user
    if working_dir:
        body["workingDir"] = working_dir
        
    data = await client.post(
        f"/api/containers/{encode_path(container_id)}/exec/run", 
        json=body, 
        params={"envId": environment_id}
    )
    if isinstance(data, dict) and max_bytes and max_bytes > 0:
        data = dict(data)
        for stream_key in ("stdout", "stderr", "output"):
            val = data.get(stream_key)
            if isinstance(val, str) and len(val) > max_bytes:
                data[stream_key] = val[:max_bytes] + f"\n... [TRUNCATED AT {max_bytes} BYTES]"
                data["truncated"] = True
    return data

async def delete_container_file(
    environment_id: int,
    container_id: str,
    path: str,
    ctx: Context,
) -> dict:
    """Delete a file or directory inside a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(
        f"/api/containers/{encode_path(container_id)}/files",
        params={"env": environment_id, "path": path},
    )

async def rename_container_file(
    environment_id: int,
    container_id: str,
    old_path: str,
    new_path: str,
    ctx: Context,
) -> dict:
    """Rename a file or directory inside a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(
        f"/api/containers/{encode_path(container_id)}/files/rename",
        json={"oldPath": old_path, "newPath": new_path},
        params={"env": environment_id},
    )

async def get_container_compose(environment_id: int, container_id: str, ctx: Context) -> dict:
    """Generate a docker-compose service definition from a running container's inspect. Secret env vars are redacted."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/containers/{encode_path(container_id)}/compose",
        params={"env": environment_id},
    )
    if isinstance(data, dict):
        data = dict(data)
        if isinstance(data.get("compose"), str):
            data["compose"] = redact_env_text(data["compose"])
        if isinstance(data.get("composeFullEnv"), str):
            data["composeFullEnv"] = redact_env_text(data["composeFullEnv"])
    return data

async def check_container_updates(environment_id: int, ctx: Context) -> dict:
    """Trigger a fresh image-update check across all containers in an environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post_sse(
        "/api/containers/check-updates",
        params={"env": environment_id},
    )

async def get_pending_container_updates(environment_id: int, ctx: Context) -> dict:
    """List the containers in an environment that have a pending image update, newer version, cooldown, or moved pinned digest."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        "/api/containers/pending-updates",
        params={"env": environment_id},
    )

async def get_container_scheduled_actions(
    environment_id: int,
    container_name: str,
    ctx: Context,
) -> dict:
    """Get a container's scheduled start and stop times (HH:MM or cron), along with status, source ('ui' vs 'label'), and error state."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/scheduled-actions/{encode_path(container_name)}",
        params={"env": environment_id},
    )

async def set_container_scheduled_actions(
    environment_id: int,
    container_name: str,
    ctx: Context,
    start_at: str | None = None,
    stop_at: str | None = None,
    enabled: bool | None = None,
) -> dict:
    """Set or remove a container's scheduled start and stop times (HH:MM every day, or a 5-field cron expression).

    Setting both start_at and stop_at to null/empty removes the schedule.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    body: dict[str, Any] = {
        "startAt": start_at,
        "stopAt": stop_at,
    }
    if enabled is not None:
        body["enabled"] = enabled
    return await client.put(
        f"/api/scheduled-actions/{encode_path(container_name)}",
        json=body,
        params={"env": environment_id},
    )

def register_container_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_containers)
    mcp.add_tool(get_container)
    mcp.add_tool(inspect_container)
    mcp.add_tool(get_container_logs)
    mcp.add_tool(get_container_stats)
    mcp.add_tool(get_container_top)
    mcp.add_tool(list_container_files)
    mcp.add_tool(get_container_file_content)
    mcp.add_tool(write_container_file_content)
    mcp.add_tool(upload_container_file)
    mcp.add_tool(create_container_path)
    mcp.add_tool(chown_container_file)
    mcp.add_tool(delete_container_file)
    mcp.add_tool(rename_container_file)
    mcp.add_tool(start_container)
    mcp.add_tool(stop_container)
    mcp.add_tool(restart_container)
    mcp.add_tool(pause_container)
    mcp.add_tool(unpause_container)
    mcp.add_tool(delete_container)
    mcp.add_tool(rename_container)
    mcp.add_tool(create_container)
    mcp.add_tool(update_container)
    mcp.add_tool(exec_container)
    mcp.add_tool(run_container_exec)
    mcp.add_tool(get_container_compose)
    mcp.add_tool(check_container_updates)
    mcp.add_tool(get_pending_container_updates)
    mcp.add_tool(get_container_scheduled_actions)
    mcp.add_tool(set_container_scheduled_actions)
