"""
SSO and Enterprise Auth tools.
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path, redact_sensitive_dict

async def list_oidc_providers(ctx: Context = None) -> list:
    """List configured OIDC providers."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get("/api/auth/oidc/providers")
    return redact_sensitive_dict(data)

async def test_oidc_provider(provider_id: int, ctx: Context = None) -> dict:
    """Test connection to an OIDC provider."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(f"/api/auth/oidc/providers/{encode_path(str(provider_id))}/test")

async def list_ldap_providers(ctx: Context = None) -> list:
    """List configured LDAP providers."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get("/api/auth/ldap/providers")
    return redact_sensitive_dict(data)

async def test_ldap_provider(provider_id: int, ctx: Context = None) -> dict:
    """Test connection to an LDAP provider."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(f"/api/auth/ldap/providers/{encode_path(str(provider_id))}/test")

def register_auth_provider_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_oidc_providers)
    mcp.add_tool(test_oidc_provider)
    mcp.add_tool(list_ldap_providers)
    mcp.add_tool(test_ldap_provider)
