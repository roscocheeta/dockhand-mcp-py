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
async def test_list_vulnerabilities(mock_client, mock_ctx):
    from dockhand_mcp.tools.security import list_vulnerabilities
    with respx.mock:
        route = respx.get("http://dockhand.test/api/security/vulnerabilities?env=1").mock(
            return_value=Response(200, json=[{"id": "CVE-123"}])
        )
        result = await list_vulnerabilities(1, mock_ctx)
        assert route.called
        assert result == [{"id": "CVE-123"}]
