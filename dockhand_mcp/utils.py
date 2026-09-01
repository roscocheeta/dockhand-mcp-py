"""
Utility functions for the Dockhand MCP server.
"""

from urllib.parse import quote


def encode_path(value: str) -> str:
    """
    URI-encode a path parameter value.

    Container IDs, stack names, and other identifiers can contain characters
    that are not safe in URL path segments (e.g. '/', '+', spaces).
    """
    return quote(str(value), safe="")
