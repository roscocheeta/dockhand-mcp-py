import pytest
import respx
from httpx import Response
from dockhand_mcp.client import DockhandClient
from mcp.server.fastmcp import Context

# We need a mock Context object since FastMCP handles the real one
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
async def test_list_environments(mock_client, mock_ctx):
    # The tools are imported inside the test so they don't break if run outside FastMCP context
    from dockhand_mcp.tools.environments import list_environments
    
    mock_data = [
        {"Id": 1, "Name": "local", "URL": "unix:///var/run/docker.sock", "hawserToken": "secret"},
        {"Id": 2, "Name": "remote", "URL": "tcp://1.2.3.4:2375"}
    ]
    
    with respx.mock:
        respx.get("http://dockhand.test/api/environments").mock(return_value=Response(200, json=mock_data))
        
        # Test the tool
        result = await list_environments(ctx=mock_ctx)
        
        # Ensure hawserToken is stripped out for security
        assert "environments" in result
        envs = result["environments"]
        assert len(envs) == 2
        assert envs[0]["Id"] == 1
        assert "hawserToken" not in envs[0]
        assert "tlsKey" not in envs[0]

@pytest.mark.asyncio
async def test_get_environment(mock_client, mock_ctx):
    from dockhand_mcp.tools.environments import get_environment
    
    mock_data = {"Id": 1, "Name": "local", "hawserToken": "secret"}
    
    with respx.mock:
        respx.get("http://dockhand.test/api/environments/1").mock(return_value=Response(200, json=mock_data))
        
        result = await get_environment(environment_id=1, ctx=mock_ctx)
        
        assert result["Id"] == 1
        assert "hawserToken" not in result
