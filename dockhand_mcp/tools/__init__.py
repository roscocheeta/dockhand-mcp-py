"""
Register all Dockhand MCP tools with MCP ToolAnnotations and optional read-only filtering.
"""

import os
from typing import Any, Callable, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

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

_READ_ONLY_PREFIXES = ("get_", "list_", "inspect_")
_READ_ONLY_EXACT = frozenset({
    "health_check",
    "check_stack_env_collisions",
    "validate_stack_env",
})

_DESTRUCTIVE_PREFIXES = ("delete_", "remove_", "prune_", "down_", "reset_", "exec_")
_DESTRUCTIVE_EXACT = frozenset({
    "run_container_exec",
    "write_container_file_content",
    "upload_container_file",
    "chown_container_file",
    "execute_batch_operation",
})


def is_read_only_tool(tool_name: str) -> bool:
    """Return True if the tool only performs non-mutating read queries."""
    return tool_name.startswith(_READ_ONLY_PREFIXES) or tool_name in _READ_ONLY_EXACT


def is_destructive_tool(tool_name: str) -> bool:
    """Return True if the tool deletes resources, overwrites files, or runs container exec."""
    return tool_name.startswith(_DESTRUCTIVE_PREFIXES) or tool_name in _DESTRUCTIVE_EXACT


def get_tool_annotations(tool_name: str) -> ToolAnnotations:
    """Build MCP ToolAnnotations (readOnlyHint, destructiveHint) for a given tool name."""
    if is_read_only_tool(tool_name):
        return ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    return ToolAnnotations(readOnlyHint=False, destructiveHint=is_destructive_tool(tool_name))


class _AnnotatedToolRegistrar:
    """
    Wraps a FastMCP instance to automatically attach MCP ToolAnnotations
    and skip non-read-only tools when DOCKHAND_READ_ONLY is enabled.
    """

    def __init__(self, mcp: FastMCP, read_only: bool = False):
        self._mcp = mcp
        self._read_only = read_only

    def add_tool(
        self,
        fn: Callable[..., Any],
        name: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        annotations: Optional[ToolAnnotations] = None,
        **kwargs: Any,
    ) -> None:
        tool_name = name or fn.__name__
        if self._read_only and not is_read_only_tool(tool_name):
            return
        effective_annotations = annotations or get_tool_annotations(tool_name)
        self._mcp.add_tool(
            fn,
            name=name,
            title=title,
            description=description,
            annotations=effective_annotations,
            **kwargs,
        )

    def tool(
        self,
        name: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        annotations: Optional[ToolAnnotations] = None,
        **kwargs: Any,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self.add_tool(
                fn,
                name=name,
                title=title,
                description=description,
                annotations=annotations,
                **kwargs,
            )
            return fn

        return decorator

    def __getattr__(self, item: str) -> Any:
        return getattr(self._mcp, item)


def register_all_tools(mcp: FastMCP, read_only: Optional[bool] = None) -> None:
    """Register all tool modules on the FastMCP/MCPServer instance."""
    if read_only is None:
        read_only = os.environ.get("DOCKHAND_READ_ONLY", "false").lower() in ("true", "1", "yes")
    registrar: Any = _AnnotatedToolRegistrar(mcp, read_only=read_only)
    register_environment_tools(registrar)
    register_system_tools(registrar)
    register_container_tools(registrar)
    register_image_tools(registrar)
    register_stack_tools(registrar)
    register_git_stack_tools(registrar)
    register_git_credential_tools(registrar)
    register_git_repository_tools(registrar)
    register_network_tools(registrar)
    register_volume_tools(registrar)
    register_registry_tools(registrar)
    register_user_tools(registrar)
    register_audit_tools(registrar)
    register_dashboard_tools(registrar)
    register_misc_tools(registrar)
    register_security_tools(registrar)
    register_auth_provider_tools(registrar)
    register_tag_tools(registrar)
