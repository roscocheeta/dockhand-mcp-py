"""
System, meta, and health tools.
"""

from mcp.server.fastmcp import FastMCP, Context


def register_system_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_server_info(ctx: Context) -> dict:
        """Get system info about the Dockhand instance."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get("/api/system")
        
    @mcp.tool()
    async def get_host_info(ctx: Context) -> dict:
        """Get OS/host info of the Dockhand server."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get("/api/host")

    @mcp.tool()
    async def health_check(ctx: Context) -> dict:
        """
        Check the health status of the Dockhand server.
        Returns connectivity and server status information.
        Use this tool first to verify the Dockhand server is reachable.
        """
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.health_check()

    @mcp.tool()
    async def get_changelog(ctx: Context) -> str:
        """Get the Dockhand version changelog."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get("/api/changelog")
