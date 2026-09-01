"""
Register all Dockhand MCP tools.
"""

from mcp.server.fastmcp import FastMCP

from .environments import register_environment_tools
from .system import register_system_tools
from .containers import register_container_tools
from .images import register_image_tools


def register_all_tools(mcp: FastMCP) -> None:
    """Register all tool modules on the FastMCP/MCPServer instance."""
    register_environment_tools(mcp)
    register_system_tools(mcp)
    register_container_tools(mcp)
    register_image_tools(mcp)
