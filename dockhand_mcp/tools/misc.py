"""
Miscellaneous and Tier 3 Dockhand tools.
"""

import re
from typing import Any
from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path, redact_sensitive_dict



async def list_notifications(ctx: Context = None) -> list:
    """List configured notifications/webhooks."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get("/api/notifications")
    return redact_sensitive_dict(data)

async def create_notification(name: str, webhook_url: str, ctx: Context = None) -> dict:
    """Create a new notification webhook."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.post("/api/notifications", json={"name": name, "url": webhook_url})
    return redact_sensitive_dict(data)

async def list_schedules(ctx: Context = None) -> list:
    """List configured automation schedules."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/schedules")

async def create_schedule(
    name: str, 
    cron_expression: str, 
    action: str, 
    ctx: Context = None,
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

async def list_templates(ctx: Context = None) -> list:
    """List available App Templates."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/templates")

async def list_labels(environment_id: int, ctx: Context = None) -> list:
    """List all unique container labels in the environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/labels", params={"env": environment_id})

async def get_preferences(ctx: Context = None) -> dict:
    """Get user preferences."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/profile/preferences")

async def set_preferences(preferences: dict, ctx: Context = None) -> dict:
    """Set user preferences."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.put("/api/profile/preferences", json=preferences)

async def list_secret_providers(ctx: Context = None) -> list:
    """List configured external secret providers (e.g. HashiCorp Vault)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get("/api/secret-providers")
    return redact_sensitive_dict(data)

async def list_config_sets(ctx: Context = None) -> list:
    """List configuration sets (environment variable collections)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/config-sets")

async def get_auto_update(environment_id: int, container_id: str, ctx: Context = None) -> dict:
    """Check the auto-update policy for a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(
        f"/api/auto-update/{encode_path(container_id)}", 
        params={"env": environment_id}
    )

async def set_auto_update(environment_id: int, container_id: str, enabled: bool, ctx: Context = None) -> dict:
    """Set the auto-update policy for a container."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.put(
        f"/api/auto-update/{encode_path(container_id)}", 
        json={"enabled": enabled},
        params={"env": environment_id}
    )

async def get_notification(notification_id: int, ctx: Context = None) -> dict:
    """Get details of a specific notification."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(f"/api/notifications/{encode_path(str(notification_id))}")
    return redact_sensitive_dict(data)

async def get_secret_provider(provider_id: int, ctx: Context = None) -> dict:
    """Get details of a specific secret provider."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(f"/api/secret-providers/{encode_path(str(provider_id))}")
    return redact_sensitive_dict(data)

async def get_theme_settings(ctx: Context = None) -> dict:
    """Get UI theme settings."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/users/preferences/theme")

async def update_theme_settings(theme: str, ctx: Context = None) -> dict:
    """Update UI theme settings."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.put("/api/users/preferences/theme", json={"theme": theme})

async def get_sidebar_preferences(ctx: Context = None) -> dict:
    """Get sidebar preferences."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/preferences/sidebar")

async def set_grid_preferences(grid: dict, ctx: Context = None) -> dict:
    """Set UI grid layout preferences."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.put("/api/preferences/grid", json=grid)

async def delete_snapshots(destination_id: int, snapshot_ids: list[str], ctx: Context = None) -> dict:
    """Bulk-delete backup snapshots from a specific destination."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(
        "/api/backup/snapshots/batch-delete",
        json={"destinationId": destination_id, "snapshotIds": snapshot_ids}
    )

async def get_environment_order(ctx: Context = None) -> list[int]:
    """Retrieve the saved environment order (most preferred first)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get('/api/preferences/environment-order')
    return data.get('order', [])

async def set_environment_order(order: list[int], ctx: Context = None) -> list[int]:
    """Save the environment order (array of environment ids)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.post('/api/preferences/environment-order', json={'order': order})
    return data.get('order', [])

async def reset_environment_order(ctx: Context = None) -> list[int]:
    """Reset the environment order back to the default."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.delete('/api/preferences/environment-order')
    return data.get('order', [])

async def get_tag_order(ctx: Context = None) -> list[int]:
    """Retrieve the saved tag order (most preferred first)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get('/api/preferences/tag-order')
    return data.get('order', [])

async def set_tag_order(order: list[int], ctx: Context = None) -> list[int]:
    """Save the tag order (array of tag ids)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.post('/api/preferences/tag-order', json={'order': order})
    return data.get('order', [])

async def reset_tag_order(ctx: Context = None) -> list[int]:
    """Reset the tag order back to the default."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.delete('/api/preferences/tag-order')
    return data.get('order', [])

async def get_minimum_release_age(ctx: Context = None) -> dict:
    """Get the global minimum image age in hours before automatic updates apply."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/settings/minimum-release-age")

async def set_minimum_release_age(hours: int, ctx: Context = None) -> dict:
    """Set the global minimum image age in hours (0 to 720) before automatic updates apply."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post("/api/settings/minimum-release-age", json={"hours": hours})

async def create_secret_provider(name: str, type: str, config: dict, ctx: Context = None) -> dict:
    """Create a secret provider (e.g. Vault, Infisical, Doppler, 1Password Connect, Psono, SOPS).

    SECURITY WARNING: The config parameter may contain sensitive credentials in plain text.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.post("/api/secret-providers", json={"name": name, "type": type, "config": config})
    return redact_sensitive_dict(data)

async def update_secret_provider(
    provider_id: int,
    ctx: Context = None,
    name: str | None = None,
    type: str | None = None,
    config: dict | None = None,
) -> dict:
    """Update a secret provider (name, type, and/or rotate its config).

    SECURITY WARNING: The config parameter may contain sensitive credentials in plain text.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    body: dict = {}
    if name is not None:
        body["name"] = name
    if type is not None:
        body["type"] = type
    if config is not None:
        body["config"] = config
    data = await client.put(f"/api/secret-providers/{encode_path(str(provider_id))}", json=body)
    return redact_sensitive_dict(data)

async def delete_secret_provider(provider_id: int, ctx: Context = None) -> dict:
    """Delete a secret provider."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(f"/api/secret-providers/{encode_path(str(provider_id))}")

async def execute_batch_operation(
    operation: str,
    entity_type: str,
    items: list[str | dict[str, Any]],
    ctx: Context = None,
    environment_id: int | None = None,
    force: bool = False,
    remove_volumes: bool = False,
) -> dict:
    """Run a bulk operation across containers, images, volumes, networks, or stacks.

    Args:
        operation: Action to perform.
            - containers: 'start', 'stop', 'restart', 'pause', 'unpause', 'remove'
            - images: 'remove'
            - volumes: 'remove'
            - networks: 'remove'
            - stacks: 'start', 'stop', 'restart', 'down'
        entity_type: Type of entity ('containers', 'images', 'volumes', 'networks', 'stacks').
        items: List of target identifiers. Can be passed as:
            - Plain strings (e.g. ['radarr', 'sonarr'] or ['sha256:...'])
            - Dictionaries:
                - containers: [{'id': '...'}, {'name': '...'}]
                - images: [{'id': 'sha256:...'}]
                - volumes: [{'name': 'volume_name'}]
                - networks: [{'id': '...'} or {'name': '...'}]
                - stacks: [{'name': 'stack_name'}]
        environment_id: Optional target environment ID.
        force: Force removal for containers, images, or networks (default False).
        remove_volumes: Remove associated volumes when removing containers/stacks (default False).
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    params = {"env": environment_id} if environment_id is not None else None

    normalized_items: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, str):
            if entity_type in ("stacks", "volumes"):
                normalized_items.append({"name": item})
            else:
                normalized_items.append({"id": item})
        elif isinstance(item, dict):
            normalized_items.append(item)
        else:
            raise ValueError(f"Invalid batch item: {item}. Must be a string identifier or a dictionary.")

    body = {
        "operation": operation,
        "entityType": entity_type,
        "items": normalized_items,
        "options": {"force": force, "removeVolumes": remove_volumes},
    }
    return await client.post_sse("/api/batch", json=body, params=params)

async def get_language_preference(ctx: Context = None) -> dict:
    """Get the interface language preference stored on the server (returns {'language': str | None})."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/preferences/language")

VALID_LOCALE_RE = re.compile(r"^[a-zA-Z]{2}(?:-[a-zA-Z0-9]{2,4})?$")

async def set_language_preference(ctx: Context = None, language: str | None = None, *args: Any) -> dict:
    """Set the interface language preference on the server (locale code, or None to follow browser).

    Supported locales include:
      - 'en' (English), 'de' (German), 'es' (Spanish), 'ru' (Russian),
      - 'fr-FR' (French), 'fr-CA' (French - Canada), 'it' (Italian),
      - 'nl' (Dutch), 'nb-NO' (Norwegian Bokmål), 'pt-BR' (Portuguese - Brazil),
      - 'pl' (Polish), 'ja' (Japanese), 'zh-CN' (Simplified Chinese), 'zh-TW' (Traditional Chinese).

    Args:
        ctx: FastMCP Context.
        language: Locale code (e.g. 'es', 'ru', 'en', 'fr-FR') or None to follow browser.
    """
    if isinstance(ctx, str) or (ctx is not None and not hasattr(ctx, "request_context")):
        language, ctx = ctx, language
    elif hasattr(language, "request_context"):
        ctx, language = language, (args[0] if args else None)

    if language is not None:
        clean_lang = language.strip()
        if not VALID_LOCALE_RE.match(clean_lang):
            raise ValueError(
                f"Invalid language locale code: '{language}'. "
                "Expected format like 'en', 'es', 'ru', or 'fr-FR'."
            )
        language = clean_lang

    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.put("/api/preferences/language", json={"language": language})

async def get_pinned_digest_report(ctx: Context = None) -> dict:
    """Get whether moved digests on pinned images are reported globally (returns {'enabled': bool})."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/settings/pinned-digest-report")

async def set_pinned_digest_report(enabled: bool, ctx: Context = None) -> dict:
    """Set whether moved digests on pinned images are reported globally."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post("/api/settings/pinned-digest-report", json={"enabled": enabled})

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
    mcp.add_tool(create_secret_provider)
    mcp.add_tool(update_secret_provider)
    mcp.add_tool(delete_secret_provider)
    mcp.add_tool(list_config_sets)
    mcp.add_tool(get_auto_update)
    mcp.add_tool(set_auto_update)
    mcp.add_tool(delete_snapshots)
    mcp.add_tool(get_environment_order)
    mcp.add_tool(set_environment_order)
    mcp.add_tool(reset_environment_order)
    mcp.add_tool(get_tag_order)
    mcp.add_tool(set_tag_order)
    mcp.add_tool(reset_tag_order)
    mcp.add_tool(get_minimum_release_age)
    mcp.add_tool(set_minimum_release_age)
    mcp.add_tool(execute_batch_operation)
    mcp.add_tool(get_language_preference)
    mcp.add_tool(set_language_preference)
    mcp.add_tool(get_pinned_digest_report)
    mcp.add_tool(set_pinned_digest_report)

