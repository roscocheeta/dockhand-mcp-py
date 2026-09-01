"""
Stack (Docker Compose) management tools.
"""

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

def register_stack_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_stacks(environment_id: int, ctx: Context) -> list:
        """List all Docker Compose stacks in an environment."""
        client = ctx.request_context.lifespan_context["dockhand"]
        stacks = await client.get("/api/stacks", params={"env": environment_id})
        if isinstance(stacks, list):
            return [_compact_stack(s) for s in stacks]
        return stacks

    @mcp.tool()
    async def get_stack_compose(environment_id: int, name: str, ctx: Context) -> dict:
        """Get the docker-compose.yml content for a stack."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get(
            f"/api/stacks/{encode_path(name)}/compose", 
            params={"env": environment_id}
        )

    @mcp.tool()
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

    @mcp.tool()
    async def get_stack_env(environment_id: int, name: str, ctx: Context) -> dict:
        """Get the structured environment variables (.env) for a stack."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get(
            f"/api/stacks/{encode_path(name)}/env", 
            params={"env": environment_id}
        )

    @mcp.tool()
    async def get_stack_env_raw(environment_id: int, name: str, ctx: Context) -> dict:
        """Get the raw .env file contents for a stack."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get(
            f"/api/stacks/{encode_path(name)}/env/raw", 
            params={"env": environment_id}
        )

    @mcp.tool()
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

    @mcp.tool()
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

    @mcp.tool()
    async def start_stack(environment_id: int, name: str, ctx: Context) -> dict:
        """Start a stopped stack."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.post_sse(
            f"/api/stacks/{encode_path(name)}/start", 
            params={"env": environment_id}
        )

    @mcp.tool()
    async def stop_stack(environment_id: int, name: str, ctx: Context) -> dict:
        """Stop a running stack."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.post_sse(
            f"/api/stacks/{encode_path(name)}/stop", 
            params={"env": environment_id}
        )

    @mcp.tool()
    async def restart_stack(environment_id: int, name: str, ctx: Context) -> dict:
        """Restart a stack."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.post_sse(
            f"/api/stacks/{encode_path(name)}/restart", 
            params={"env": environment_id}
        )

    @mcp.tool()
    async def down_stack(
        environment_id: int, 
        name: str, 
        ctx: Context,
        remove_volumes: bool = False
    ) -> dict:
        """Tear down a stack (Docker Compose down)."""
        client = ctx.request_context.lifespan_context["dockhand"]
        body = {"removeVolumes": remove_volumes} if remove_volumes else None
        return await client.post_sse(
            f"/api/stacks/{encode_path(name)}/down", 
            json=body,
            params={"env": environment_id}
        )

    @mcp.tool()
    async def delete_stack(
        environment_id: int, 
        name: str, 
        ctx: Context,
        force: bool = False,
        files: bool = True
    ) -> dict:
        """Delete a stack and optionally its files from disk."""
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
