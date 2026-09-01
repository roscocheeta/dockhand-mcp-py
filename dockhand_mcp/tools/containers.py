"""
Container management tools (Read-only for Phase 2b).
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path


def register_container_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_containers(environment_id: int, ctx: Context) -> list:
        """List all containers in a Dockhand environment."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get("/api/containers", params={"env": environment_id})

    @mcp.tool()
    async def get_container(environment_id: int, container_id: str, ctx: Context) -> dict:
        """Get details for a specific container."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get(
            f"/api/containers/{encode_path(container_id)}",
            params={"env": environment_id},
        )

    @mcp.tool()
    async def inspect_container(environment_id: int, container_id: str, ctx: Context) -> dict:
        """Get low-level docker inspect information for a container."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get(
            f"/api/containers/{encode_path(container_id)}/inspect",
            params={"env": environment_id},
        )

    @mcp.tool()
    async def get_container_logs(
        environment_id: int,
        container_id: str,
        ctx: Context,
        tail: int = 100,
    ) -> str:
        """
        Get stdout/stderr logs from a container.
        tail: Number of lines to return from the end of the logs (default: 100)
        """
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get(
            f"/api/containers/{encode_path(container_id)}/logs",
            params={"env": environment_id, "tail": tail},
        )

    @mcp.tool()
    async def get_container_stats(environment_id: int, container_id: str, ctx: Context) -> dict:
        """Get live resource usage statistics (CPU, memory, net I/O) for a container."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get(
            f"/api/containers/{encode_path(container_id)}/stats",
            params={"env": environment_id},
        )

    @mcp.tool()
    async def get_container_top(environment_id: int, container_id: str, ctx: Context) -> dict:
        """Get the running processes inside a container."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get(
            f"/api/containers/{encode_path(container_id)}/top",
            params={"env": environment_id},
        )

    @mcp.tool()
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

    @mcp.tool()
    async def get_container_file_content(
        environment_id: int,
        container_id: str,
        path: str,
        ctx: Context,
    ) -> str:
        """
        Read the text content of a file inside a container.
        path: Absolute path to the file inside the container.
        """
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get(
            f"/api/containers/{encode_path(container_id)}/files/content",
            params={"env": environment_id, "path": path},
        )


    @mcp.tool()
    async def start_container(environment_id: int, container_id: str, ctx: Context) -> dict:
        """Start a container."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.post(f"/api/containers/{encode_path(container_id)}/start", params={"env": environment_id})

    @mcp.tool()
    async def stop_container(environment_id: int, container_id: str, ctx: Context) -> dict:
        """Stop a container."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.post(f"/api/containers/{encode_path(container_id)}/stop", params={"env": environment_id})

    @mcp.tool()
    async def restart_container(environment_id: int, container_id: str, ctx: Context) -> dict:
        """Restart a container."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.post(f"/api/containers/{encode_path(container_id)}/restart", params={"env": environment_id})

    @mcp.tool()
    async def pause_container(environment_id: int, container_id: str, ctx: Context) -> dict:
        """Pause a container."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.post(f"/api/containers/{encode_path(container_id)}/pause", params={"env": environment_id})

    @mcp.tool()
    async def unpause_container(environment_id: int, container_id: str, ctx: Context) -> dict:
        """Unpause a container."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.post(f"/api/containers/{encode_path(container_id)}/unpause", params={"env": environment_id})

    @mcp.tool()
    async def delete_container(environment_id: int, container_id: str, ctx: Context, force: bool = False) -> dict:
        """Delete a container (optionally force-kill it first)."""
        client = ctx.request_context.lifespan_context["dockhand"]
        params = {"env": environment_id}
        if force:
            params["force"] = "true"
        return await client.delete(f"/api/containers/{encode_path(container_id)}", params=params)

    @mcp.tool()
    async def rename_container(environment_id: int, container_id: str, name: str, ctx: Context) -> dict:
        """Rename a container."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.post(f"/api/containers/{encode_path(container_id)}/rename", json={"name": name}, params={"env": environment_id})

    @mcp.tool()
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
    ) -> dict:
        """Create a new container."""
        client = ctx.request_context.lifespan_context["dockhand"]
        body = {"name": name, "image": image}
        if start_after_create:
            body["startAfterCreate"] = True
        if env:
            body["Env"] = env
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


    @mcp.tool()
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
