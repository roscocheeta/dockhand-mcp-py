import pytest
import respx
from httpx import Response
from dockhand_mcp.client import DockhandClient
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
async def test_list_containers(mock_client, mock_ctx):
    from dockhand_mcp.tools.containers import list_containers
    
    # Dockhand returns lowercase keys natively
    mock_data = [
        {
            "id": "8bf78fa4451123a39f73c62a9bab2516290e9a967cf807357f1092e68d87d108",
            "name": "newrelic-logging",
            "image": "newrelic/newrelic-fluentbit-output:latest",
            "state": "running",
            "status": "Up 13 hours",
            "HostConfig": {"Memory": 1024} # This should be stripped
        }
    ]
    
    with respx.mock:
        route = respx.get("http://dockhand.test/api/containers?env=1").mock(return_value=Response(200, json=mock_data))
        
        result = await list_containers(environment_id=1, ctx=mock_ctx)
        
        # Verify the API was hit correctly
        assert route.called
        
        # Verify token efficiency logic worked
        assert len(result) == 1
        assert result[0]["Id"] == "8bf78fa44511" # Truncated
        assert result[0]["Name"] == "newrelic-logging"
        assert "HostConfig" not in result[0] # Stripped

@pytest.mark.asyncio
async def test_start_container(mock_client, mock_ctx):
    from dockhand_mcp.tools.containers import start_container
    
    with respx.mock:
        route = respx.post("http://dockhand.test/api/containers/my-container/start?env=1").mock(
            return_value=Response(204) # Usually empty 204 response
        )
        
        result = await start_container(environment_id=1, container_id="my-container", ctx=mock_ctx)
        
        assert route.called
        assert result is None or result == "" # 204 no content
