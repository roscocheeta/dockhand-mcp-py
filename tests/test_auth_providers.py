import pytest
import respx
from httpx import Response
from mcp.server.fastmcp import Context

class MockRequestContext:
    def __init__(self, client):
        self.lifespan_context = {"dockhand": client}

class MockContext:
    def __init__(self, client):
        self.request_context = MockRequestContext(client)

@pytest.fixture
def mock_ctx(mock_client):
    return MockContext(mock_client)

@pytest.mark.asyncio
async def test_list_oidc_providers(mock_client, mock_ctx):
    from dockhand_mcp.tools.auth_providers import list_oidc_providers, list_ldap_providers
    with respx.mock:
        route = respx.get("http://dockhand.test/api/auth/oidc/providers").mock(
            return_value=Response(200, json=[{"id": 1, "name": "Google", "clientSecret": "mock_oidc_client_secret"}])
        )
        ldap_route = respx.get("http://dockhand.test/api/auth/ldap/providers").mock(
            return_value=Response(200, json=[{"id": 2, "name": "Corp LDAP", "bindPassword": "mock_ldap_bind_password"}])
        )
        result = await list_oidc_providers(mock_ctx)
        assert route.called
        assert result == [{"id": 1, "name": "Google", "clientSecret": "***REDACTED***"}]

        ldap_res = await list_ldap_providers(mock_ctx)
        assert ldap_route.called
        assert ldap_res == [{"id": 2, "name": "Corp LDAP", "bindPassword": "***REDACTED***"}]


@pytest.mark.asyncio
async def test_test_oidc_and_ldap_providers(mock_client, mock_ctx):
    from dockhand_mcp.tools.auth_providers import test_oidc_provider, test_ldap_provider
    with respx.mock:
        oidc_test = respx.post("http://dockhand.test/api/auth/oidc/providers/1/test").mock(
            return_value=Response(200, json={"valid": True})
        )
        ldap_test = respx.post("http://dockhand.test/api/auth/ldap/providers/2/test").mock(
            return_value=Response(200, json={"valid": True})
        )

        r1 = await test_oidc_provider(1, mock_ctx)
        assert oidc_test.called
        assert r1["valid"] is True

        r2 = await test_ldap_provider(2, mock_ctx)
        assert ldap_test.called
        assert r2["valid"] is True

