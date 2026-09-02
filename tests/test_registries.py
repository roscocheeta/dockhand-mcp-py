import pytest
import respx
from httpx import Response
from dockhand_mcp.tools.registries import list_registries

class MockContext:
    def __init__(self, client):
        class LifespanContext:
            def __init__(self, client):
                self.lifespan_context = {"dockhand": client}
        self.request_context = LifespanContext(client)

@pytest.mark.asyncio
async def test_list_registries_strips_passwords(mock_client):
    mock_ctx = MockContext(mock_client)
    
    mock_data = [
        {
            "Id": 1, 
            "Name": "Docker Hub", 
            "Username": "myuser", 
            "Password": "supersecretpassword",
            "Type": "dockerhub"
        }
    ]
    
    with respx.mock:
        respx.get("http://dockhand.test/api/registries?env=1").mock(return_value=Response(200, json=mock_data))
        
        result = await list_registries(environment_id=1, ctx=mock_ctx)
        
        assert len(result) == 1
        assert result[0]["Id"] == 1
        assert result[0]["Username"] == "myuser"
        # The crucial security assertion: password must NOT be in the compact output
        assert "Password" not in result[0]
        assert "password" not in result[0]
