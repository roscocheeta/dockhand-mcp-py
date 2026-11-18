"""
Container management tools (Read-only for Phase 2b).
"""

import fnmatch
import json
from typing import Any
from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import (
    encode_path,
    truncate_id,
    clean_container_inspect,
    compact_container_inspect,
    redact_env_text,
    parse_since_to_epoch,
    paginate_items,
    parse_memory_bytes,
)


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


async def list_containers(
    environment_id: int | None = None,
    ctx: Context = None,
    status: str | None = None,
    search: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list | dict:
    """List all containers in a Dockhand environment.

    Args:
        environment_id: Environment ID (optional, auto-resolves to default).
        ctx: FastMCP Context.
        status: Optional state filter (e.g. 'running', 'exited').
        search: Optional container name, display name, or ID filter supporting wildcards ('*' and '?'), e.g. 'web-*' or '*redis*'.
        limit: Optional maximum number of items to return (returns pagination envelope when set).
        offset: Zero-based starting offset for pagination (default 0).
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    env_id = await client.resolve_environment_id(environment_id)
    containers = await client.get("/api/containers", params={"env": env_id})
    if isinstance(containers, list):
        items = [_compact_container(c) for c in containers]
        if status:
            s_clean = status.strip().lower()
            items = [c for c in items if (c.get("State") or "").lower() == s_clean]
        if search:
            search_pat = search.strip().lower()
            items = [
                c for c in items
                if fnmatch.fnmatchcase((c.get("Name") or "").lower().lstrip("/"), search_pat)
                or fnmatch.fnmatchcase((c.get("DisplayName") or "").lower(), search_pat)
                or fnmatch.fnmatchcase((c.get("Id") or "").lower(), search_pat)
            ]
        return paginate_items(items, limit=limit, offset=offset)
    return containers

def _normalize_container_args(env: Any, cid: Any, ctx: Any) -> tuple[int | None, str, Any]:
    if isinstance(env, str):
        if hasattr(cid, "request_context") or not cid:
            return None, env, (cid if hasattr(cid, "request_context") else ctx)
    return env, str(cid) if cid is not None else "", ctx

async def get_container(
    environment_id: int | None = None,
    container_id: str = "",
    ctx: Context = None,
    compact: bool = False,
    *args: Any,
) -> dict:
    """Get detailed inspection data for a specific container.

    Args:
        environment_id: Environment ID (optional, auto-resolves to default).
        container_id: Container name or ID.
        ctx: FastMCP Context.
        compact: If True, returns only essential runtime fields (state, health, ports, mounts, networks, redacted env).
    """
    environment_id, container_id, ctx = _normalize_container_args(environment_id, container_id, ctx)
    client = ctx.request_context.lifespan_context["dockhand"]
    env_id = await client.resolve_environment_id(environment_id)
    data = await client.get(
        f"/api/containers/{encode_path(container_id)}",
        params={"env": env_id},
    )
    if compact:
        return compact_container_inspect(data)
    return clean_container_inspect(data)

async def inspect_container(
    environment_id: int | None = None,
    container_id: str = "",
    ctx: Context = None,
    compact: bool = False,
    *args: Any,
) -> dict:
    """Get low-level docker inspect information for a container. Secrets in environment variables are redacted.

    Args:
        environment_id: Environment ID (optional, auto-resolves to default).
        container_id: Container name or ID.
        ctx: FastMCP Context.
        compact: If True, returns only essential runtime fields (state, health, ports, mounts, networks, redacted env).
    """
    environment_id, container_id, ctx = _normalize_container_args(environment_id, container_id, ctx)
    client = ctx.request_context.lifespan_context["dockhand"]
    env_id = await client.resolve_environment_id(environment_id)
    data = await client.get(
        f"/api/containers/{encode_path(container_id)}/inspect",
        params={"env": env_id},
    )
    if compact:
        return compact_container_inspect(data)
    return clean_container_inspect(data)

async def get_container_logs(
    environment_id: int | None = None,
    container_id: str = "",
    ctx: Context = None,
    tail: int = 100,
    timestamps: bool = False,
    since: str | int | None = None,
    *args: Any,
) -> str:
    """
    Get stdout/stderr logs from a container.
    tail: Number of lines from the end (default 100, max 500).
    """
    environment_id, container_id, ctx = _normalize_container_args(environment_id, container_id, ctx)
    tail = min(tail, 500)
    client = ctx.request_context.lifespan_context["dockhand"]
    env_id = await client.resolve_environment_id(environment_id)
    params: dict[str, Any] = {"env": env_id, "tail": tail}
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

async def get_container_stats(
    environment_id: int | None = None,
    container_id: str = "",
    ctx: Context = None,
    *args: Any,
) -> dict:
    environment_id, container_id, ctx = _normalize_container_args(environment_id, container_id, ctx)
    """Get live resource usage statistics (CPU, memory, net I/O) for a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    env_id = await client.resolve_environment_id(environment_id)
    return await client.get(
        f"/api/containers/{encode_path(container_id)}/stats",
        params={"env": env_id},
    )

async def get_container_top(
    environment_id: int | None = None,
    container_id: str = "",
    ctx: Context = None,
    *args: Any,
) -> dict:
    environment_id, container_id, ctx = _normalize_container_args(environment_id, container_id, ctx)
    """Get the running processes inside a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    env_id = await client.resolve_environment_id(environment_id)
    return await client.get(
        f"/api/containers/{encode_path(container_id)}/top",
        params={"env": env_id},
    )

async def list_container_files(
    environment_id: int | None = None,
    container_id: str = "",
    ctx: Context = None,
    path: str = "/",
    *args: Any,
) -> list | dict:
    environment_id, container_id, ctx = _normalize_container_args(environment_id, container_id, ctx)
    """
    List files and directories inside a container.
    path: Absolute path inside the container to list (default: /).
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/containers/{encode_path(container_id)}/files",
        params={"env": await client.resolve_environment_id(environment_id), "path": path},
    )

async def get_container_file_content(
    environment_id: int | None = None,
    container_id: str = "",
    path: str = "",
    ctx: Context = None,
    max_bytes: int = 10240,
    *args: Any,
) -> str:
    """
    Read the text content of a file inside a container.
    path: Absolute path to the file inside the container.
    max_bytes: Maximum bytes to return (default 10KB). Content beyond this is truncated.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    content = await client.get(
        f"/api/containers/{encode_path(container_id)}/files/content",
        params={"env": await client.resolve_environment_id(environment_id), "path": path},
    )
    if isinstance(content, str) and len(content.encode("utf-8")) > max_bytes:
        truncated = content.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
        return truncated + f"\n\n[...truncated at {max_bytes} bytes. Use max_bytes parameter to read more.]"
    return content


async def start_container(
    environment_id: int | None = None,
    container_id: str = "",
    ctx: Context = None,
    *args: Any,
) -> dict:
    environment_id, container_id, ctx = _normalize_container_args(environment_id, container_id, ctx)
    """Start a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    env_id = await client.resolve_environment_id(environment_id)
    return await client.post(f"/api/containers/{encode_path(container_id)}/start", params={"env": env_id})

async def stop_container(
    environment_id: int | None = None,
    container_id: str = "",
    ctx: Context = None,
    *args: Any,
) -> dict:
    environment_id, container_id, ctx = _normalize_container_args(environment_id, container_id, ctx)
    """Stop a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    env_id = await client.resolve_environment_id(environment_id)
    return await client.post(f"/api/containers/{encode_path(container_id)}/stop", params={"env": env_id})

async def restart_container(
    environment_id: int | None = None,
    container_id: str = "",
    ctx: Context = None,
    *args: Any,
) -> dict:
    environment_id, container_id, ctx = _normalize_container_args(environment_id, container_id, ctx)
    """Restart a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    env_id = await client.resolve_environment_id(environment_id)
    return await client.post(f"/api/containers/{encode_path(container_id)}/restart", params={"env": env_id})

async def pause_container(
    environment_id: int | None = None,
    container_id: str = "",
    ctx: Context = None,
    *args: Any,
) -> dict:
    environment_id, container_id, ctx = _normalize_container_args(environment_id, container_id, ctx)
    """Pause a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    env_id = await client.resolve_environment_id(environment_id)
    return await client.post(f"/api/containers/{encode_path(container_id)}/pause", params={"env": env_id})

async def unpause_container(
    environment_id: int | None = None,
    container_id: str = "",
    ctx: Context = None,
    *args: Any,
) -> dict:
    environment_id, container_id, ctx = _normalize_container_args(environment_id, container_id, ctx)
    """Unpause a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    env_id = await client.resolve_environment_id(environment_id)
    return await client.post(f"/api/containers/{encode_path(container_id)}/unpause", params={"env": env_id})

async def delete_container(environment_id: int | None = None, container_id: str = "", ctx: Context = None, force: bool = False, *args: Any) -> dict:
    environment_id, container_id, ctx = _normalize_container_args(environment_id, container_id, ctx)
    """⚠️ DESTRUCTIVE: Delete a container (optionally force-kill it first). Permanent unless re-created."""
    client = ctx.request_context.lifespan_context["dockhand"]
    params = {"env": await client.resolve_environment_id(environment_id)}
    if force:
        params["force"] = "true"
    return await client.delete(f"/api/containers/{encode_path(container_id)}", params=params)

async def rename_container(environment_id: int | None = None, container_id: str = "", name: str = "", ctx: Context = None, *args: Any) -> dict:
    """Rename a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(f"/api/containers/{encode_path(container_id)}/rename", json={"name": name}, params={"env": await client.resolve_environment_id(environment_id)})

async def create_container(
    name: str = "",
    image: str = "",
    ctx: Context = None,
    environment_id: int | None = None,
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
        
    return await client.post("/api/containers", json=body, params={"env": await client.resolve_environment_id(environment_id)})


async def update_container(
    environment_id: int | None = None,
    container_id: str = "",
    ctx: Context = None,
    image: str | None = None,
    name: str | None = None,
    cmd: list[str] | None = None,
    env: list[str] | None = None,
    restart_policy: str | None = None,
    network_mode: str | None = None,
    repull_image: bool | None = None,
    start_after_update: bool | None = None,
    *args: Any,
) -> dict:
    environment_id, container_id, ctx = _normalize_container_args(environment_id, container_id, ctx)
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
        params={"env": await client.resolve_environment_id(environment_id)}
    )


_VALID_RESTART_POLICIES = frozenset({"no", "always", "unless-stopped", "on-failure"})


async def update_container_runtime(
    container_id: str,
    ctx: Context = None,
    environment_id: int | None = None,
    cpus: float | None = None,
    memory: int | str | None = None,
    memory_reservation: int | str | None = None,
    memory_swap: int | str | None = None,
    restart_policy: str | None = None,
    restart_max_retries: int | None = None,
    cpu_shares: int | None = None,
    cpu_period: int | None = None,
    cpu_quota: int | None = None,
    cpuset_cpus: str | None = None,
    cpuset_mems: str | None = None,
    pids_limit: int | None = None,
    blkio_weight: int | None = None,
    *args: Any,
) -> dict:
    """Update a container's CPU, memory, PIDs, blkio, or restart policy in-place without recreating it.

    Calls Dockhand's ``POST /api/containers/{id}/update-runtime`` endpoint, which
    applies Docker live-update fields (no container restart or recreation). Pass ``0``
    for ``cpus``, ``memory``, ``memory_reservation``, ``cpu_shares``, ``cpu_period``,
    or ``cpu_quota`` to clear an existing limit.

    Args:
        container_id: Container name or ID.
        ctx: FastMCP Context.
        environment_id: Environment ID (optional, auto-resolves to default).
        cpus: CPU limit in cores (e.g. 1.5 or 0.5; converted to NanoCpus).
        memory: Hard memory limit in bytes or size string (e.g. '512m', '2g', or 0 to clear).
        memory_reservation: Soft memory limit in bytes or size string (e.g. '256m').
        memory_swap: Total memory + swap limit in bytes or size string ('-1' for unlimited).
        restart_policy: Restart policy ('no', 'always', 'unless-stopped', 'on-failure').
        restart_max_retries: Maximum retry count when restart_policy is 'on-failure'.
        cpu_shares: Relative CPU weight (integer >= 0).
        cpu_period: CPU CFS period in microseconds (integer >= 0).
        cpu_quota: CPU CFS quota in microseconds (integer >= 0).
        cpuset_cpus: CPUs in which to allow execution (e.g. '0-3', '0,1').
        cpuset_mems: Memory nodes in which to allow execution (e.g. '0-1').
        pids_limit: Maximum number of PIDs (-1 for unlimited, 0 to clear).
        blkio_weight: Block IO weight (10-1000).
    """
    if isinstance(container_id, int):
        environment_id, container_id, ctx = container_id, str(ctx), environment_id

    body: dict[str, Any] = {}
    if cpus is not None:
        if isinstance(cpus, bool) or cpus < 0:
            raise ValueError(f"Invalid 'cpus' value {cpus!r}: must be >= 0.")
        body["NanoCpus"] = int(round(cpus * 1_000_000_000))
    if memory is not None:
        body["Memory"] = parse_memory_bytes(memory)
    if memory_reservation is not None:
        body["MemoryReservation"] = parse_memory_bytes(memory_reservation)
    if memory_swap is not None:
        body["MemorySwap"] = parse_memory_bytes(memory_swap, allow_negative_one=True)
    if restart_policy is not None:
        policy_name = restart_policy.strip().lower()
        if policy_name not in _VALID_RESTART_POLICIES:
            raise ValueError(
                f"Invalid restart_policy {restart_policy!r}; expected one of {sorted(_VALID_RESTART_POLICIES)}."
            )
        rp: dict[str, Any] = {"Name": policy_name}
        if policy_name == "on-failure" and restart_max_retries is not None:
            if isinstance(restart_max_retries, bool) or restart_max_retries < 0:
                raise ValueError(f"Invalid restart_max_retries {restart_max_retries!r}: must be >= 0.")
            rp["MaximumRetryCount"] = restart_max_retries
        body["RestartPolicy"] = rp
    if cpu_shares is not None:
        body["CpuShares"] = cpu_shares
    if cpu_period is not None:
        body["CpuPeriod"] = cpu_period
    if cpu_quota is not None:
        body["CpuQuota"] = cpu_quota
    if cpuset_cpus is not None:
        body["CpusetCpus"] = cpuset_cpus
    if cpuset_mems is not None:
        body["CpusetMems"] = cpuset_mems
    if pids_limit is not None:
        body["PidsLimit"] = pids_limit
    if blkio_weight is not None:
        body["BlkioWeight"] = blkio_weight

    if not body:
        raise ValueError("At least one runtime update field (e.g. cpus, memory, restart_policy, pids_limit) must be provided.")

    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(
        f"/api/containers/{encode_path(container_id)}/update-runtime",
        json=body,
        params={"env": await client.resolve_environment_id(environment_id)},
    )

async def exec_container(
    environment_id: int | None = None,
    container_id: str = "",
    ctx: Context = None,
    shell: str | None = None,
    user: str | None = None,
    *args: Any,
) -> dict:
    environment_id, container_id, ctx = _normalize_container_args(environment_id, container_id, ctx)
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
        params={"envId": await client.resolve_environment_id(environment_id)}
    )

async def write_container_file_content(
    environment_id: int | None = None,
    container_id: str = "",
    path: str = "",
    content: str = "",
    ctx: Context = None,
    *args: Any,
) -> dict:
    """Write text content to a file inside a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.put(
        f"/api/containers/{encode_path(container_id)}/files/content",
        json={"content": content},
        params={"env": await client.resolve_environment_id(environment_id), "path": path},
    )

import base64

async def upload_container_file(
    environment_id: int | None = None,
    container_id: str = "",
    directory: str = "",
    filename: str = "",
    base64_content: str = "",
    ctx: Context = None,
    owner: str | None = None,
    *args: Any,
) -> dict:
    """Upload a file to a container directory using base64 encoded content. Owner format: 'user', 'uid', 'user:group', 'uid:gid'."""
    if not filename or filename in (".", "..") or "/" in filename or "\\" in filename:
        raise ValueError(f"Invalid upload filename {filename!r}: must be a plain filename without path separators.")

    client = ctx.request_context.lifespan_context["dockhand"]
    try:
        file_bytes = base64.b64decode(base64_content, validate=True)
    except Exception as e:
        raise ValueError(f"Invalid base64_content: {e}")

    max_upload_bytes = 10 * 1024 * 1024
    if len(file_bytes) > max_upload_bytes:
        raise ValueError(f"Upload exceeds maximum allowed size of {max_upload_bytes} bytes.")

    files = {"files": (filename, file_bytes)}
    data = {}
    if owner:
        data["owner"] = owner

    return await client.post(
        f"/api/containers/{encode_path(container_id)}/files/upload",
        files=files,
        data=data,
        params={"env": await client.resolve_environment_id(environment_id), "path": directory},
    )

async def create_container_path(
    environment_id: int | None = None,
    container_id: str = "",
    path: str = "",
    type: str = "",
    ctx: Context = None,
    owner: str | None = None,
    *args: Any,
) -> dict:
    """Create an empty file or directory inside a container. Type must be 'file' or 'directory'."""
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {"path": path, "type": type}
    if owner:
        body["owner"] = owner
    return await client.post(
        f"/api/containers/{encode_path(container_id)}/files/create",
        json=body,
        params={"env": await client.resolve_environment_id(environment_id)},
    )

async def chown_container_file(
    environment_id: int | None = None,
    container_id: str = "",
    path: str = "",
    owner: str = "",
    ctx: Context = None,
    recursive: bool = False,
    *args: Any,
) -> dict:
    """Change the owner/group of a file or directory inside a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(
        f"/api/containers/{encode_path(container_id)}/files/chown",
        json={"path": path, "owner": owner, "recursive": recursive},
        params={"env": await client.resolve_environment_id(environment_id)},
    )

async def run_container_exec(
    container_id: str | int = "",
    cmd: str | list[str] = None,
    ctx: Context = None,
    environment_id: int | None = None,
    user: str | None = None,
    working_dir: str | None = None,
    max_bytes: int = 10240,
    *args: Any,
) -> dict:
    if isinstance(container_id, int):
        environment_id, container_id, cmd, ctx = container_id, str(cmd), ctx, environment_id
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
        params={"envId": await client.resolve_environment_id(environment_id)}
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
    environment_id: int | None = None,
    container_id: str = "",
    path: str = "",
    ctx: Context = None,
    *args: Any,
) -> dict:
    """Delete a file or directory inside a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(
        f"/api/containers/{encode_path(container_id)}/files",
        params={"env": await client.resolve_environment_id(environment_id), "path": path},
    )

async def rename_container_file(
    environment_id: int | None = None,
    container_id: str = "",
    old_path: str = "",
    new_path: str = "",
    ctx: Context = None,
    *args: Any,
) -> dict:
    """Rename a file or directory inside a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(
        f"/api/containers/{encode_path(container_id)}/files/rename",
        json={"oldPath": old_path, "newPath": new_path},
        params={"env": await client.resolve_environment_id(environment_id)},
    )

async def get_container_compose(
    environment_id: int | None = None,
    container_id: str = "",
    ctx: Context = None,
    *args: Any,
) -> dict:
    environment_id, container_id, ctx = _normalize_container_args(environment_id, container_id, ctx)
    """Generate a docker-compose service definition from a running container's inspect. Secret env vars are redacted."""
    client = ctx.request_context.lifespan_context["dockhand"]
    env_id = await client.resolve_environment_id(environment_id)
    data = await client.get(
        f"/api/containers/{encode_path(container_id)}/compose",
        params={"env": env_id},
    )
    if isinstance(data, dict):
        data = dict(data)
        if isinstance(data.get("compose"), str):
            data["compose"] = redact_env_text(data["compose"])
        if isinstance(data.get("composeFullEnv"), str):
            data["composeFullEnv"] = redact_env_text(data["composeFullEnv"])
    return data

async def check_container_updates(environment_id: int | None = None, ctx: Context = None, *args: Any) -> dict:
    if environment_id is not None and not isinstance(environment_id, int):
        ctx, environment_id = environment_id, None
    """Trigger a fresh image-update check across all containers in an environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post_sse(
        "/api/containers/check-updates",
        params={"env": await client.resolve_environment_id(environment_id)},
    )

async def get_pending_container_updates(
    environment_id: int | None = None,
    ctx: Context = None,
    compact: bool = False,
    include_release_notes: bool = True,
    max_release_notes_bytes: int = 2048,
) -> dict:
    """List the containers in an environment that have a pending image update, newer version, cooldown, or moved pinned digest.

    Note: In Dockhand v1.0.56+, release notes for held container updates are accessible during cooldown periods.

    Args:
        environment_id: Environment ID (optional, auto-resolves to default).
        ctx: FastMCP Context.
        compact: If True, strips verbose release notes and changelogs to minimize token consumption.
        include_release_notes: If False, omits release notes entirely (default: True).
        max_release_notes_bytes: Maximum bytes per release note before truncation (default: 2048).
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    env_id = await client.resolve_environment_id(environment_id)
    data = await client.get(
        "/api/containers/pending-updates",
        params={"env": env_id},
    )

    def _sanitize_update_item(item: Any) -> Any:
        if not isinstance(item, dict):
            return item
        res = dict(item)
        for note_field in ("releaseNotes", "release_notes", "changelog", "notes"):
            if note_field in res:
                if compact or not include_release_notes:
                    del res[note_field]
                elif isinstance(res[note_field], str) and max_release_notes_bytes > 0:
                    val = res[note_field]
                    if len(val) > max_release_notes_bytes:
                        res[note_field] = val[:max_release_notes_bytes] + f"\n... [TRUNCATED AT {max_release_notes_bytes} BYTES]"
                        res[f"{note_field}Truncated"] = True
        return res

    if isinstance(data, dict):
        data = dict(data)
        for key, val in list(data.items()):
            if isinstance(val, list):
                data[key] = [_sanitize_update_item(it) for it in val]
            elif isinstance(val, dict):
                data[key] = _sanitize_update_item(val)
    elif isinstance(data, list):
        data = [_sanitize_update_item(it) for it in data]
    return data

async def get_container_scheduled_actions(
    container_name: str = "",
    ctx: Context = None,
    environment_id: int | None = None,
    *args: Any,
) -> dict:
    if isinstance(container_name, int):
        environment_id, container_name, ctx = container_name, str(ctx), environment_id
    """Get a container's scheduled start and stop times (HH:MM or cron), along with status, source ('ui' vs 'label'), and error state."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/scheduled-actions/{encode_path(container_name)}",
        params={"env": await client.resolve_environment_id(environment_id)},
    )

async def set_container_scheduled_actions(
    container_name: str = "",
    ctx: Context = None,
    environment_id: int | None = None,
    start_at: str | None = None,
    stop_at: str | None = None,
    enabled: bool | None = None,
    *args: Any,
) -> dict:
    if isinstance(container_name, int):
        environment_id, container_name, ctx = container_name, str(ctx), environment_id
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
        params={"env": await client.resolve_environment_id(environment_id)},
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
    mcp.add_tool(update_container_runtime)
    mcp.add_tool(exec_container)
    mcp.add_tool(run_container_exec)
    mcp.add_tool(get_container_compose)
    mcp.add_tool(check_container_updates)
    mcp.add_tool(get_pending_container_updates)
    mcp.add_tool(get_container_scheduled_actions)
    mcp.add_tool(set_container_scheduled_actions)
