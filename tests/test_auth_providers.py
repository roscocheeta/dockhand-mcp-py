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
    from dockhand_mcp.tools.auth_providers import list_oidc_providers
    with respx.mock:
        route = respx.get("http://dockhand.test/api/auth/oidc/providers").mock(
            return_value=Response(200, json=[{"id": 1, "name": "Google"}])
        )
        result = await list_oidc_providers(mock_ctx)
        assert route.called
        assert result == [{"id": 1, "name": "Google"}]
