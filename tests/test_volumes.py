import pytest
import respx
from httpx import Response
from dockhand_mcp.tools.volumes import create_volume

class MockContext:
    def __init__(self, client):
        class LifespanContext:
            def __init__(self, client):
                self.lifespan_context = {"dockhand": client}
        self.request_context = LifespanContext(client)

@pytest.mark.asyncio
async def test_create_volume_basic(mock_client):
    mock_ctx = MockContext(mock_client)
    
    with respx.mock:
        route = respx.post("http://dockhand.test/api/volumes?env=1").mock(
            return_value=Response(200, json={"success": True, "name": "my-vol"})
        )
        
        result = await create_volume(
            environment_id=1,
            name="my-vol",
            ctx=mock_ctx
        )
        
        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload["name"] == "my-vol"
        assert payload["driver"] == "local"
        assert "driverOpts" not in payload
        assert "labels" not in payload
        assert result["success"] is True

@pytest.mark.asyncio
async def test_create_volume_full(mock_client):
    mock_ctx = MockContext(mock_client)
    
    with respx.mock:
        route = respx.post("http://dockhand.test/api/volumes?env=2").mock(
            return_value=Response(200, json={"success": True})
        )
        
        result = await create_volume(
            environment_id=2,
            name="nfs-vol",
            ctx=mock_ctx,
            driver="local",
            driver_opts={"type": "nfs", "device": ":/data/shared", "o": "addr=192.168.1.100,rw"},
            labels={"app": "file-server"}
        )
        
        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload["name"] == "nfs-vol"
        assert payload["driver"] == "local"
        assert payload["driverOpts"] == {"type": "nfs", "device": ":/data/shared", "o": "addr=192.168.1.100,rw"}
        assert payload["labels"] == {"app": "file-server"}
        assert result["success"] is True
