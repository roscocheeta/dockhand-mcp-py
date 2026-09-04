"""
Container management tools (Read-only for Phase 2b).
"""

import json
from typing import Any
from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path, truncate_id, clean_container_inspect


def _compact_container(c: dict) -> dict:
    """Keep only essential fields for token efficiency."""
    return {
        "Id": truncate_id(c.get("Id") or c.get("id")),
        "Name": c.get("Name") or c.get("name") or (c.get("Names", [""])[0] if c.get("Names") else ""),
        "Image": c.get("Image") or c.get("image"),
        "State": c.get("State") or c.get("state"),
        "Status": c.get("Status") or c.get("status"),
        "Ports": c.get("Ports") or c.get("ports") or []
    }


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
) -> str:
    """
    Get stdout/stderr logs from a container.
    tail: Number of lines from the end (default 100, max 500).
    """
    tail = min(tail, 500)
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/containers/{encode_path(container_id)}/logs",
        params={"env": environment_id, "tail": tail},
    )

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
    cmd: list[str] | None = None,
    env: list[str] | None = None,
    restart_policy: str | None = None,
    network_mode: str | None = None,
) -> dict:
    """Update a container (Note: Dockhand will recreate it)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {}
    if image:
        body["image"] = image
    if cmd:
        body["cmd"] = cmd
    if env:
        body["env"] = env
    if restart_policy:
        body["restartPolicy"] = restart_policy
    if network_mode:
        body["networkMode"] = network_mode
        
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

async def upload_container_file(
    environment_id: int,
    container_id: str,
    path: str,
    base64_content: str,
    ctx: Context,
) -> dict:
    """Upload a file to a container using base64 encoded content."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(
        f"/api/containers/{encode_path(container_id)}/files/upload",
        json={"content": base64_content},
        params={"env": environment_id, "path": path},
    )

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
