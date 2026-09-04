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

@pytest.mark.asyncio
async def test_scan_image(mock_client):
    from dockhand_mcp.tools.security import scan_image
    mock_ctx = MockContext(mock_client)
    
    with respx.mock:
        route = respx.post('http://dockhand.test/api/images/scan?env=1').mock(
            return_value=Response(200, json={'jobId': '123'})
        )
        
        result = await scan_image(
            environment_id=1,
            image_name='nginx:latest',
            ctx=mock_ctx,
            scanner='trivy'
        )
        
        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload['imageName'] == 'nginx:latest'
        assert payload['scanner'] == 'trivy'
        assert result['jobId'] == '123'

