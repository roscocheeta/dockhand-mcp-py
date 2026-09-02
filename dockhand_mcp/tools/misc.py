"""
Miscellaneous and Tier 3 Dockhand tools.
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path


def register_misc_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_notifications(ctx: Context) -> list:
        """List configured notifications/webhooks."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get("/api/notifications")

    @mcp.tool()
    async def create_notification(name: str, webhook_url: str, ctx: Context) -> dict:
        """Create a new notification webhook."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.post("/api/notifications", json={"name": name, "url": webhook_url})

    @mcp.tool()
    async def list_schedules(ctx: Context) -> list:
        """List configured automation schedules."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get("/api/schedules")

    @mcp.tool()
    async def create_schedule(name: str, cron_expression: str, action: str, ctx: Context) -> dict:
        """Create a new automation schedule."""
        client = ctx.request_context.lifespan_context["dockhand"]
        body = {"name": name, "cron": cron_expression, "action": action}
        return await client.post("/api/schedules", json=body)

    @mcp.tool()
    async def list_templates(ctx: Context) -> list:
        """List available App Templates."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get("/api/templates")

    @mcp.tool()
    async def list_labels(environment_id: int, ctx: Context) -> list:
        """List all unique container labels in the environment."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get("/api/labels", params={"env": environment_id})

    @mcp.tool()
    async def get_preferences(ctx: Context) -> dict:
        """Get user preferences."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get("/api/users/preferences")

    @mcp.tool()
    async def set_preferences(preferences: dict, ctx: Context) -> dict:
        """Set user preferences."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.put("/api/users/preferences", json=preferences)

    @mcp.tool()
    async def list_secret_providers(ctx: Context) -> list:
        """List configured external secret providers (e.g. HashiCorp Vault)."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get("/api/secrets/providers")

    @mcp.tool()
    async def list_config_sets(ctx: Context) -> list:
        """List configuration sets (environment variable collections)."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get("/api/config-sets")

    @mcp.tool()
    async def get_auto_update(environment_id: int, container_id: str, ctx: Context) -> dict:
        """Check the auto-update policy for a container."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get(
            f"/api/containers/{encode_path(container_id)}/auto-update", 
            params={"env": environment_id}
        )

    @mcp.tool()
    async def set_auto_update(environment_id: int, container_id: str, enabled: bool, ctx: Context) -> dict:
        """Set the auto-update policy for a container."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.put(
            f"/api/containers/{encode_path(container_id)}/auto-update", 
            json={"enabled": enabled},
            params={"env": environment_id}
        )

    @mcp.tool()
    async def scan_image(environment_id: int, image_id: str, ctx: Context) -> dict:
        """Trigger a vulnerability scan for an image."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.post(
            f"/api/images/{encode_path(image_id)}/scan",
            params={"env": environment_id}
        )
