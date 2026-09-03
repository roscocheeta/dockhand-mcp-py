import pytest
import respx
from httpx import Response
from dockhand_mcp.tools.git_credentials import list_git_credentials

class MockContext:
    def __init__(self, client):
        class LifespanContext:
            def __init__(self, client):
                self.lifespan_context = {"dockhand": client}
        self.request_context = LifespanContext(client)

@pytest.mark.asyncio
async def test_list_git_credentials_masks_all_casings(mock_client):
    mock_ctx = MockContext(mock_client)
    
    mock_data = [
        {"id": 1, "password": "abc", "Token": "123"},
        {"id": 2, "Password": "xyz", "sshKey": "key", "SshKey": "key2"}
    ]
    
    with respx.mock:
        respx.get("http://dockhand.test/api/git/credentials").mock(return_value=Response(200, json=mock_data))
        
        result = await list_git_credentials(ctx=mock_ctx)
        
        # Verify first item
        assert result[0]["password"] == "***"
        assert result[0]["Token"] == "***"
        assert "abc" not in result[0].values()
        assert "123" not in result[0].values()
        
        # Verify second item
        assert result[1]["Password"] == "***"
        assert result[1]["sshKey"] == "***"
        assert result[1]["SshKey"] == "***"
        assert "xyz" not in result[1].values()
        assert "key" not in result[1].values()
        assert "key2" not in result[1].values()
