"""
Register all Dockhand MCP tools.
"""

from mcp.server.fastmcp import FastMCP

from .environments import register_environment_tools
from .system import register_system_tools
from .containers import register_container_tools
from .images import register_image_tools
from .stacks import register_stack_tools
from .git_stacks import register_git_stack_tools
from .networks import register_network_tools
from .volumes import register_volume_tools


def register_all_tools(mcp: FastMCP) -> None:
    """Register all tool modules on the FastMCP/MCPServer instance."""
    register_environment_tools(mcp)
    register_system_tools(mcp)
    register_container_tools(mcp)
    register_image_tools(mcp)
    register_stack_tools(mcp)
    register_git_stack_tools(mcp)
    register_network_tools(mcp)
    register_volume_tools(mcp)
