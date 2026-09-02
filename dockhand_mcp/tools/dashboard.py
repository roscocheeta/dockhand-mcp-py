"""
Dashboard and overview tools.
"""

from mcp.server.fastmcp import FastMCP, Context

def register_dashboard_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_dashboard(environment_id: int | None = None, ctx: Context = None) -> dict:
        """Get high-level dashboard metrics (e.g. container counts, image sizes)."""
        client = ctx.request_context.lifespan_context["dockhand"]
        params = {}
        if environment_id is not None:
            params["env"] = environment_id
        return await client.get("/api/dashboard", params=params)

    @mcp.tool()
    async def get_activity(limit: int = 50, ctx: Context = None) -> list:
        """Get recent activity events across all environments."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get("/api/dashboard/activity", params={"limit": limit})
