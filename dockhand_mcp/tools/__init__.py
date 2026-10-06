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
from .git_credentials import register_git_credential_tools
from .git_repositories import register_git_repository_tools
from .networks import register_network_tools
from .volumes import register_volume_tools
from .registries import register_registry_tools
from .users import register_user_tools
from .audit import register_audit_tools
from .dashboard import register_dashboard_tools
from .misc import register_misc_tools
from .security import register_security_tools
from .auth_providers import register_auth_provider_tools


from .tags import register_tag_tools

def register_all_tools(mcp: FastMCP) -> None:
    """Register all tool modules on the FastMCP/MCPServer instance."""
    register_environment_tools(mcp)
    register_system_tools(mcp)
    register_container_tools(mcp)
    register_image_tools(mcp)
    register_stack_tools(mcp)
    register_git_stack_tools(mcp)
    register_git_credential_tools(mcp)
    register_git_repository_tools(mcp)
    register_network_tools(mcp)
    register_volume_tools(mcp)
    register_registry_tools(mcp)
    register_user_tools(mcp)
    register_audit_tools(mcp)
    register_dashboard_tools(mcp)
    register_misc_tools(mcp)
    register_security_tools(mcp)
    register_auth_provider_tools(mcp)
    register_tag_tools(mcp)
