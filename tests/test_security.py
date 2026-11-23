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
        route = respx.get(
            "http://dockhand.test/api/vulnerabilities?env=1&limit=50&offset=0"
        ).mock(return_value=Response(200, json={"findings": [{"id": "CVE-123"}], "total": 1}))
        result = await list_vulnerabilities(1, mock_ctx)
        assert route.called
        assert result == {"findings": [{"id": "CVE-123"}], "total": 1}

        filtered_route = respx.get(
            "http://dockhand.test/api/vulnerabilities?env=1&limit=10&offset=5&q=openssl&severity=high&image=nginx&container=web&stack=prod"
        ).mock(return_value=Response(200, json={"findings": [], "total": 0}))
        filtered = await list_vulnerabilities(
            environment_id=1,
            ctx=mock_ctx,
            limit=10,
            offset=5,
            q=" openssl ",
            severity="high",
            image="nginx",
            container="web",
            stack="prod",
        )
        assert filtered_route.called
        assert filtered == {"findings": [], "total": 0}

    with pytest.raises(ValueError, match="Invalid 'limit'"):
        await list_vulnerabilities(1, mock_ctx, limit=0)
    with pytest.raises(ValueError, match="Invalid 'offset'"):
        await list_vulnerabilities(1, mock_ctx, offset=-1)

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
        count_route = respx.get("http://dockhand.test/api/vulnerabilities/count?env=1").mock(
            return_value=Response(200, json={"total": 4, "summary": {"critical": 1, "high": 3}})
        )
        grouped_route = respx.get("http://dockhand.test/api/vulnerabilities/count?groupBy=container&env=1").mock(
            return_value=Response(
                200,
                json={"groupBy": "container", "groups": [{"id": "c1", "name": "web", "critical": 1, "total": 4}]},
            )
        )
        scan_all_route = respx.post("http://dockhand.test/api/vulnerabilities/scan-all?env=1").mock(
            return_value=Response(200, json={"jobId": "123"})
        )
        list_scans_route = respx.get("http://dockhand.test/api/images/img1/scans?env=1").mock(
            return_value=Response(200, json=[{"image": "nginx:latest", "status": "completed"}])
        )

        cnt = await get_vulnerability_count(1, mock_ctx)
        assert count_route.called
        assert cnt["summary"]["critical"] == 1

        grouped = await get_vulnerability_count(environment_id=1, ctx=mock_ctx, group_by="Container")
        assert grouped_route.called
        assert grouped["groupBy"] == "container"
        assert grouped["groups"][0]["name"] == "web"

        with pytest.raises(ValueError, match="Invalid group_by"):
            await get_vulnerability_count(environment_id=1, ctx=mock_ctx, group_by="node")

        sa = await scan_all_vulnerabilities(1, mock_ctx)
        assert scan_all_route.called
        assert sa["jobId"] == "123"

        scans = await list_image_scans(1, "img1", mock_ctx)
        assert list_scans_route.called
        assert scans[0]["image"] == "nginx:latest"


@pytest.mark.asyncio
async def test_security_positional_arg_swaps(mock_client, mock_ctx):
    from dockhand_mcp.tools.security import list_vulnerabilities, scan_image

    with respx.mock:
        respx.get("http://dockhand.test/api/environments").mock(
            return_value=Response(200, json=[{"id": 1, "name": "default", "isDefault": True}])
        )
        respx.get("http://dockhand.test/api/vulnerabilities?env=1&limit=50&offset=0").mock(
            return_value=Response(200, json={"findings": [], "total": 0})
        )
        assert await list_vulnerabilities(mock_ctx) == {"findings": [], "total": 0}

        respx.post("http://dockhand.test/api/images/scan?env=1").mock(
            return_value=Response(200, json={"jobId": "456"})
        )
        assert (await scan_image(1, "nginx:latest", mock_ctx))["jobId"] == "456"  # type: ignore[arg-type]


