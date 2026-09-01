"""
Environment (Docker Host) management tools.
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path


ENVIRONMENT_CREDENTIAL_FIELDS = {"hawserToken", "tlsKey"}


def _strip_environment_credentials(env: dict) -> dict:
    """Strip sensitive fields from an environment payload."""
    if not isinstance(env, dict):
        return env
    return {k: v for k, v in env.items() if k not in ENVIRONMENT_CREDENTIAL_FIELDS}


def register_environment_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_environments(ctx: Context) -> dict:
        """List all Dockhand environments (Docker hosts)."""
        client = ctx.request_context.lifespan_context["dockhand"]
        envs = await client.get("/api/environments")
        if isinstance(envs, list):
            return {"environments": [_strip_environment_credentials(e) for e in envs]}
        return {"environments": envs}

    @mcp.tool()
    async def get_environment(environment_id: int, ctx: Context) -> dict:
        """Get details for a specific environment."""
        client = ctx.request_context.lifespan_context["dockhand"]
        env = await client.get(f"/api/environments/{encode_path(str(environment_id))}")
        return _strip_environment_credentials(env)

    @mcp.tool()
    async def create_environment(
        name: str,
        connection_type: str,
        ctx: Context,
        host: str | None = None,
        port: int | None = None,
        url: str | None = None,
    ) -> dict:
        """
        Create a new Docker environment in Dockhand.
        connection_type is typically 'hawser-standard' or 'hawser-edge'.
        For hawser-standard, provide host/port.
        """
        client = ctx.request_context.lifespan_context["dockhand"]
        body = {"name": name, "connectionType": connection_type}
        
        if connection_type == "hawser-standard":
            if host:
                body["host"] = host
                body["port"] = port if port is not None else 2376
            elif url:
                # Basic best-effort fallback if caller sends 'url'
                body["url"] = url
                
        env = await client.post("/api/environments", json=body)
        return _strip_environment_credentials(env)

    @mcp.tool()
    async def update_environment(
        environment_id: int,
        ctx: Context,
        name: str | None = None,
        icon: str | None = None,
        labels: list[str] | None = None,
    ) -> dict:
        """Update basic fields on an existing environment."""
        client = ctx.request_context.lifespan_context["dockhand"]
        body = {}
        if name is not None:
            body["name"] = name
        if icon is not None:
            body["icon"] = icon
        if labels is not None:
            body["labels"] = labels
            
        env = await client.put(f"/api/environments/{encode_path(str(environment_id))}", json=body)
        return _strip_environment_credentials(env)

    @mcp.tool()
    async def delete_environment(environment_id: int, ctx: Context) -> dict:
        """Delete an environment from Dockhand."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.delete(f"/api/environments/{encode_path(str(environment_id))}")

    @mcp.tool()
    async def test_environment(environment_id: int, ctx: Context) -> dict:
        """Test the connection to an existing environment."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.post(f"/api/environments/{encode_path(str(environment_id))}/test")
