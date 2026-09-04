"""
Miscellaneous and Tier 3 Dockhand tools.
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path



async def list_notifications(ctx: Context) -> list:
    """List configured notifications/webhooks."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/notifications")

async def create_notification(name: str, webhook_url: str, ctx: Context) -> dict:
    """Create a new notification webhook."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post("/api/notifications", json={"name": name, "url": webhook_url})

async def list_schedules(ctx: Context) -> list:
    """List configured automation schedules."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/schedules")

async def create_schedule(
    name: str, 
    cron_expression: str, 
    action: str, 
    ctx: Context,
    vulnerability_criteria: dict | None = None,
    schedule_type: int | None = None,
    container_name: str | None = None,
    env_id: int | None = None,
    enabled: bool = True
) -> dict:
    """Create a new automation schedule."""
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {
        "name": name, 
        "cron": cron_expression, 
        "action": action,
        "enabled": enabled
    }
    if vulnerability_criteria:
        body["vulnerabilityCriteria"] = vulnerability_criteria
    if schedule_type is not None:
        body["scheduleType"] = schedule_type
    if container_name:
        body["containerName"] = container_name
    if env_id is not None:
        body["env"] = env_id
        
    return await client.post("/api/schedules", json=body)

async def list_templates(ctx: Context) -> list:
    """List available App Templates."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/templates")

async def list_labels(environment_id: int, ctx: Context) -> list:
    """List all unique container labels in the environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/labels", params={"env": environment_id})

async def get_preferences(ctx: Context) -> dict:
    """Get user preferences."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/users/preferences")

async def set_preferences(preferences: dict, ctx: Context) -> dict:
    """Set user preferences."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.put("/api/users/preferences", json=preferences)

async def list_secret_providers(ctx: Context) -> list:
    """List configured external secret providers (e.g. HashiCorp Vault)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/secrets/providers")

async def list_config_sets(ctx: Context) -> list:
    """List configuration sets (environment variable collections)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/config-sets")

async def get_auto_update(environment_id: int, container_id: str, ctx: Context) -> dict:
    """Check the auto-update policy for a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/containers/{encode_path(container_id)}/auto-update", 
        params={"env": environment_id}
    )

async def set_auto_update(environment_id: int, container_id: str, enabled: bool, ctx: Context) -> dict:
    """Set the auto-update policy for a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.put(
        f"/api/containers/{encode_path(container_id)}/auto-update", 
        json={"enabled": enabled},
        params={"env": environment_id}
    )

async def get_notification(notification_id: int, ctx: Context) -> dict:
    """Get details of a specific notification."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(f"/api/notifications/{encode_path(str(notification_id))}")

async def get_secret_provider(provider_id: int, ctx: Context) -> dict:
    """Get details of a specific secret provider."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(f"/api/secrets/providers/{encode_path(str(provider_id))}")

async def get_theme_settings(ctx: Context) -> dict:
    """Get UI theme settings."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/users/preferences/theme")

async def update_theme_settings(theme: str, ctx: Context) -> dict:
    """Update UI theme settings."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.put("/api/users/preferences/theme", json={"theme": theme})

async def get_sidebar_preferences(ctx: Context) -> dict:
    """Get sidebar preferences."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/users/preferences/sidebar")

async def set_grid_preferences(grid: dict, ctx: Context) -> dict:
    """Set UI grid layout preferences."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.put("/api/users/preferences/grid", json=grid)

def register_misc_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_notifications)
    mcp.add_tool(get_notification)
    mcp.add_tool(create_notification)
    mcp.add_tool(list_schedules)
    mcp.add_tool(create_schedule)
    mcp.add_tool(list_templates)
    mcp.add_tool(list_labels)
    mcp.add_tool(get_preferences)
    mcp.add_tool(set_preferences)
    mcp.add_tool(get_theme_settings)
    mcp.add_tool(update_theme_settings)
    mcp.add_tool(get_sidebar_preferences)
    mcp.add_tool(set_grid_preferences)
    mcp.add_tool(list_secret_providers)
    mcp.add_tool(get_secret_provider)
    mcp.add_tool(list_config_sets)
    mcp.add_tool(get_auto_update)
    mcp.add_tool(set_auto_update)

