"""
Audit log management tools.
"""

from mcp.server.fastmcp import FastMCP, Context


def _compact_audit(a: dict) -> dict:
    """Keep only essential fields for token efficiency."""
    return {
        "Id": a.get("Id") or a.get("id"),
        "Timestamp": a.get("Timestamp") or a.get("timestamp"),
        "Username": a.get("Username") or a.get("username"),
        "Action": a.get("Action") or a.get("action"),
        "Target": a.get("Target") or a.get("target"),
        "EnvironmentId": a.get("EnvironmentId") or a.get("environmentId"),
    }


async def get_audit_log(
    ctx: Context = None,
    environment_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    username: str | None = None,
    action: str | None = None
) -> list:
    """Get the audit log of actions performed in Dockhand."""
    client = ctx.request_context.lifespan_context["dockhand"]
    params = {"limit": limit, "offset": offset}
    if environment_id is not None:
        params["env"] = environment_id
    if username:
        params["username"] = username
    if action:
        params["action"] = action
        
    logs = await client.get("/api/audit", params=params)
    if isinstance(logs, list):
        return [_compact_audit(l) for l in logs]
    elif isinstance(logs, dict) and "data" in logs:
        data = logs["data"]
        if isinstance(data, list):
            logs["data"] = [_compact_audit(l) for l in data]
        return logs
    return logs

async def get_audit_users(ctx: Context = None) -> list:
    """Get a list of users who have generated audit events."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/audit/users")

def register_audit_tools(mcp: FastMCP) -> None:
    mcp.add_tool(get_audit_log)
    mcp.add_tool(get_audit_users)
