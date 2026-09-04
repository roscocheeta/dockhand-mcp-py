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
async def test_prune_all(mock_client, mock_ctx):
    from dockhand_mcp.tools.system import prune_all
    
    with respx.mock:
        route = respx.post("http://dockhand.test/api/system/prune/all?env=1").mock(return_value=Response(200, json={"SpaceReclaimed": 12345}))
        
        result = await prune_all(environment_id=1, ctx=mock_ctx)
        
        assert route.called
        assert result["SpaceReclaimed"] == 12345

@pytest.mark.asyncio
async def test_prune_containers(mock_client, mock_ctx):
    from dockhand_mcp.tools.system import prune_containers
    with respx.mock:
        route = respx.post("http://dockhand.test/api/system/prune/containers?env=1").mock(return_value=Response(200, json={"ContainersDeleted": ["id1"]}))
        result = await prune_containers(1, mock_ctx)
        assert route.called
        assert result["ContainersDeleted"] == ["id1"]

@pytest.mark.asyncio
async def test_prune_images(mock_client, mock_ctx):
    from dockhand_mcp.tools.system import prune_images
    with respx.mock:
        route = respx.post("http://dockhand.test/api/system/prune/images?env=1").mock(return_value=Response(200, json={"ImagesDeleted": ["id2"]}))
        result = await prune_images(1, mock_ctx)
        assert route.called
        assert result["ImagesDeleted"] == ["id2"]

@pytest.mark.asyncio
async def test_prune_networks(mock_client, mock_ctx):
    from dockhand_mcp.tools.system import prune_networks
    with respx.mock:
        route = respx.post("http://dockhand.test/api/system/prune/networks?env=1").mock(return_value=Response(200, json={"NetworksDeleted": ["id3"]}))
        result = await prune_networks(1, mock_ctx)
        assert route.called
        assert result["NetworksDeleted"] == ["id3"]

@pytest.mark.asyncio
async def test_prune_volumes(mock_client, mock_ctx):
    from dockhand_mcp.tools.system import prune_volumes
    with respx.mock:
        route = respx.post("http://dockhand.test/api/system/prune/volumes?env=1").mock(return_value=Response(200, json={"VolumesDeleted": ["id4"]}))
        result = await prune_volumes(1, mock_ctx)
        assert route.called
        assert result["VolumesDeleted"] == ["id4"]

@pytest.mark.asyncio
async def test_prune_images_dangling(mock_client, mock_ctx):
    from dockhand_mcp.tools.system import prune_images
    with respx.mock:
        route = respx.post('http://dockhand.test/api/system/prune/images?env=1&dangling=true').mock(
            return_value=Response(200, json={'success': True})
        )
        
        result = await prune_images(environment_id=1, ctx=mock_ctx, dangling=True)
        assert route.called
        assert result['success'] is True

