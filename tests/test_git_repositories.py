import pytest
import respx
from httpx import Response

class MockContext:
    def __init__(self, client):
        class LifespanContext:
            def __init__(self, client):
                self.lifespan_context = {"dockhand": client}
        self.request_context = LifespanContext(client)

@pytest.mark.asyncio
async def test_list_git_repositories(mock_client):
    from dockhand_mcp.tools.git_repositories import list_git_repositories
    mock_ctx = MockContext(mock_client)
    
    mock_data = [
        {"id": 1, "name": "repo1", "url": "http://repo1", "branch": "main"}
    ]
    
    with respx.mock:
        route = respx.get("http://dockhand.test/api/git/repositories").mock(return_value=Response(200, json=mock_data))
        
        result = await list_git_repositories(ctx=mock_ctx)
        
        assert route.called
        assert result[0]["Name"] == "repo1"
