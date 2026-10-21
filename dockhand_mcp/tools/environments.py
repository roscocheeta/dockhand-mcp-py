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



async def list_environments(ctx: Context) -> dict:
    """List all Dockhand environments (Docker hosts)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    envs = await client.get("/api/environments")
    if isinstance(envs, list):
        return {"environments": [_strip_environment_credentials(e) for e in envs]}
    return {"environments": envs}

async def get_environment(environment_id: int, ctx: Context) -> dict:
    """Get details for a specific environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    env = await client.get(f"/api/environments/{encode_path(str(environment_id))}")
    return _strip_environment_credentials(env)

async def create_environment(
    name: str,
    connection_type: str,
    ctx: Context,
    host: str | None = None,
    port: int | None = None,
    protocol: str = "http",
    socket_path: str = "/var/run/docker.sock",
    tls_ca: str | None = None,
    tls_cert: str | None = None,
    tls_key: str | None = None,
    tls_skip_verify: bool = False,
    hawser_token: str | None = None,
    icon: str = "globe",
    labels: list[str] | None = None,
    collect_activity: bool = True,
    collect_metrics: bool = True,
) -> dict:
    """
    Create a new Docker environment in Dockhand.
    connection_type can be 'socket', 'direct', 'hawser-standard', or 'hawser-edge'.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {
        "name": name, 
        "connectionType": connection_type,
        "protocol": protocol,
        "socketPath": socket_path,
        "tlsSkipVerify": tls_skip_verify,
        "icon": icon,
        "collectActivity": collect_activity,
        "collectMetrics": collect_metrics,
    }
    
    if host:
        body["host"] = host
    if port is not None:
        body["port"] = port
    if tls_ca:
        body["tlsCa"] = tls_ca
    if tls_cert:
        body["tlsCert"] = tls_cert
    if tls_key:
        body["tlsKey"] = tls_key
    if hawser_token:
        body["hawserToken"] = hawser_token
    if labels is not None:
        body["labels"] = labels
            
    env = await client.post("/api/environments", json=body)
    return _strip_environment_credentials(env)

async def update_environment(
    environment_id: int,
    ctx: Context,
    name: str | None = None,
    connection_type: str | None = None,
    host: str | None = None,
    port: int | None = None,
    protocol: str | None = None,
    socket_path: str | None = None,
    tls_ca: str | None = None,
    tls_cert: str | None = None,
    tls_key: str | None = None,
    tls_skip_verify: bool | None = None,
    hawser_token: str | None = None,
    icon: str | None = None,
    labels: list[str] | None = None,
    collect_activity: bool | None = None,
    collect_metrics: bool | None = None,
) -> dict:
    """Update fields on an existing environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {}
    if name is not None:
        body["name"] = name
    if connection_type is not None:
        body["connectionType"] = connection_type
    if host is not None:
        body["host"] = host
    if port is not None:
        body["port"] = port
    if protocol is not None:
        body["protocol"] = protocol
    if socket_path is not None:
        body["socketPath"] = socket_path
    if tls_ca is not None:
        body["tlsCa"] = tls_ca
    if tls_cert is not None:
        body["tlsCert"] = tls_cert
    if tls_key is not None:
        body["tlsKey"] = tls_key
    if tls_skip_verify is not None:
        body["tlsSkipVerify"] = tls_skip_verify
    if hawser_token is not None:
        body["hawserToken"] = hawser_token
    if icon is not None:
        body["icon"] = icon
    if labels is not None:
        body["labels"] = labels
    if collect_activity is not None:
        body["collectActivity"] = collect_activity
    if collect_metrics is not None:
        body["collectMetrics"] = collect_metrics
        
    env = await client.put(f"/api/environments/{encode_path(str(environment_id))}", json=body)
    return _strip_environment_credentials(env)

async def delete_environment(environment_id: int, ctx: Context) -> dict:
    """⚠️ DESTRUCTIVE: Delete an environment from Dockhand. (Does not delete the actual host)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(f"/api/environments/{encode_path(str(environment_id))}")

async def test_environment(environment_id: int, ctx: Context) -> dict:
    """Test the connection to an existing environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(f"/api/environments/{encode_path(str(environment_id))}/test")

async def get_environment_update_check_settings(environment_id: int, ctx: Context) -> dict:
    """Get the automatic container-image update-check schedule and minimum release age settings for an environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(f"/api/environments/{encode_path(str(environment_id))}/update-check")

async def update_environment_update_check_settings(
    environment_id: int,
    ctx: Context,
    enabled: bool | None = None,
    cron: str | None = None,
    auto_update: bool | None = None,
    vulnerability_criteria: str | None = None,
    minimum_release_age_hours: int | None = None,
    minimum_release_age_override: bool | None = None,
) -> dict:
    """Save the automatic image update-check schedule and minimum release age settings for an environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    body: dict = {}
    if enabled is not None:
        body["enabled"] = enabled
    if cron is not None:
        body["cron"] = cron
    if auto_update is not None:
        body["autoUpdate"] = auto_update
    if vulnerability_criteria is not None:
        body["vulnerabilityCriteria"] = vulnerability_criteria
    if minimum_release_age_hours is not None:
        body["minimumReleaseAgeHours"] = minimum_release_age_hours
    if minimum_release_age_override is not None:
        body["minimumReleaseAgeOverride"] = minimum_release_age_override
    return await client.post(f"/api/environments/{encode_path(str(environment_id))}/update-check", json=body)

async def get_environment_report(
    ctx: Context,
    environment_id: int | None = None,
    format: str = "json",
) -> dict | str:
    """Export an environment state report (inventory, vulnerability counts, scan coverage) as json or csv."""
    client = ctx.request_context.lifespan_context["dockhand"]
    params: dict = {"format": format}
    if environment_id is not None:
        params["env"] = environment_id
    return await client.get("/api/environments/report", params=params)

async def get_environment_report_settings(environment_id: int, ctx: Context) -> dict:
    """Get the scheduled state report configuration for an environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get(f"/api/environments/{encode_path(str(environment_id))}/report")

async def update_environment_report_settings(
    environment_id: int,
    ctx: Context,
    enabled: bool | None = None,
    cron: str | None = None,
    format: str | None = None,
    notification_id: int | None = None,
) -> dict:
    """Save the scheduled state report configuration for an environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    body: dict = {}
    if enabled is not None:
        body["enabled"] = enabled
    if cron is not None:
        body["cron"] = cron
    if format is not None:
        body["format"] = format
    if notification_id is not None:
        body["notificationId"] = notification_id
    return await client.post(f"/api/environments/{encode_path(str(environment_id))}/report", json=body)

def register_environment_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_environments)
    mcp.add_tool(get_environment)
    mcp.add_tool(create_environment)
    mcp.add_tool(update_environment)
    mcp.add_tool(delete_environment)
    mcp.add_tool(test_environment)
    mcp.add_tool(get_environment_update_check_settings)
    mcp.add_tool(update_environment_update_check_settings)
    mcp.add_tool(get_environment_report)
    mcp.add_tool(get_environment_report_settings)
    mcp.add_tool(update_environment_report_settings)
