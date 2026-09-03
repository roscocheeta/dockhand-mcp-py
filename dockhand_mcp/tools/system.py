"""
System, meta, and health tools.
"""

from mcp.server.fastmcp import FastMCP, Context



async def get_server_info(ctx: Context) -> dict:
    """Get system info about the Dockhand instance."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/system")
    
async def get_host_info(ctx: Context) -> dict:
    """Get OS/host info of the Dockhand server."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.get("/api/host")

async def health_check(ctx: Context) -> dict:
    """
    Check the health status of the Dockhand server.
    Returns connectivity and server status information.
    Use this tool first to verify the Dockhand server is reachable.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.health_check()

async def get_changelog(ctx: Context, max_lines: int = 50) -> str:
    """Get the Dockhand version changelog. Truncated to max_lines (default 50) to save tokens."""
    client = ctx.request_context.lifespan_context["dockhand"]
    content = await client.get("/api/changelog")
    if isinstance(content, str):
        lines = content.splitlines()
        if len(lines) > max_lines:
            return "\n".join(lines[:max_lines]) + f"\n\n[...truncated at {max_lines} lines. Use max_lines parameter to see more.]"
    return content

async def prune_all(environment_id: int, ctx: Context) -> dict:
    """Prune all unused Docker resources (containers, networks, images, volumes)."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post("/api/system/prune/all", params={"env": environment_id})

async def prune_containers(environment_id: int, ctx: Context) -> dict:
    """Prune unused Docker containers."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post("/api/system/prune/containers", params={"env": environment_id})

async def prune_images(environment_id: int, ctx: Context) -> dict:
    """Prune unused Docker images."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post("/api/system/prune/images", params={"env": environment_id})

async def prune_networks(environment_id: int, ctx: Context) -> dict:
    """Prune unused Docker networks."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post("/api/system/prune/networks", params={"env": environment_id})

async def prune_volumes(environment_id: int, ctx: Context) -> dict:
    """Prune unused Docker volumes."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post("/api/system/prune/volumes", params={"env": environment_id})


def register_system_tools(mcp: FastMCP) -> None:
    mcp.add_tool(get_server_info)
    mcp.add_tool(get_host_info)
    mcp.add_tool(health_check)
    mcp.add_tool(get_changelog)
    mcp.add_tool(prune_all)
    mcp.add_tool(prune_containers)
    mcp.add_tool(prune_images)
    mcp.add_tool(prune_networks)
    mcp.add_tool(prune_volumes)
