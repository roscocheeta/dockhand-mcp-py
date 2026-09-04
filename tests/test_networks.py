import pytest
import respx
from httpx import Response
from dockhand_mcp.tools.networks import create_network

class MockContext:
    def __init__(self, client):
        class LifespanContext:
            def __init__(self, client):
                self.lifespan_context = {"dockhand": client}
        self.request_context = LifespanContext(client)

@pytest.mark.asyncio
async def test_create_network_basic(mock_client):
    mock_ctx = MockContext(mock_client)
    
    with respx.mock:
        route = respx.post("http://dockhand.test/api/networks?env=1").mock(
            return_value=Response(200, json={"success": True, "name": "my-net"})
        )
        
        result = await create_network(
            environment_id=1,
            name="my-net",
            ctx=mock_ctx
        )
        
        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload["name"] == "my-net"
        assert payload["driver"] == "bridge"
        assert payload["internal"] is False
        assert payload["attachable"] is False
        assert result["success"] is True

@pytest.mark.asyncio
async def test_create_network_full(mock_client):
    mock_ctx = MockContext(mock_client)
    
    with respx.mock:
        route = respx.post("http://dockhand.test/api/networks?env=2").mock(
            return_value=Response(200, json={"success": True})
        )
        
        result = await create_network(
            environment_id=2,
            name="my-custom-net",
            ctx=mock_ctx,
            driver="overlay",
            options={"encrypted": "true"},
            labels={"app": "db"},
            ipam={"driver": "default", "config": [{"subnet": "10.0.0.0/24"}]},
            internal=True,
            attachable=True
        )
        
        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload["name"] == "my-custom-net"
        assert payload["driver"] == "overlay"
        assert payload["options"] == {"encrypted": "true"}
        assert payload["labels"] == {"app": "db"}
        assert payload["ipam"] == {"driver": "default", "config": [{"subnet": "10.0.0.0/24"}]}
        assert payload["internal"] is True
        assert payload["attachable"] is True
