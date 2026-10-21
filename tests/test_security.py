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


@pytest.mark.asyncio
async def test_vulnerability_counts_and_scans(mock_client, mock_ctx):
    from dockhand_mcp.tools.security import (
        get_vulnerability_count,
        scan_all_vulnerabilities,
        list_image_scans,
    )
    with respx.mock:
        count_route = respx.get("http://dockhand.test/api/security/vulnerabilities/count?env=1").mock(
            return_value=Response(200, json={"critical": 1, "high": 3})
        )
        scan_all_route = respx.post("http://dockhand.test/api/security/vulnerabilities/scan?env=1").mock(
            return_value=Response(200, json={"started": True})
        )
        list_scans_route = respx.get("http://dockhand.test/api/images/img1/scans?env=1").mock(
            return_value=Response(200, json=[{"image": "nginx:latest", "status": "completed"}])
        )

        cnt = await get_vulnerability_count(1, mock_ctx)
        assert count_route.called
        assert cnt["critical"] == 1

        sa = await scan_all_vulnerabilities(1, mock_ctx)
        assert scan_all_route.called
        assert sa["started"] is True

        scans = await list_image_scans(1, "img1", mock_ctx)
        assert list_scans_route.called
        assert scans[0]["image"] == "nginx:latest"


