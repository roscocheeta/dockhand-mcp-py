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


@pytest.mark.asyncio
async def test_update_registry_strips_passwords(mock_client):
    from dockhand_mcp.tools.registries import update_registry
    mock_ctx = MockContext(mock_client)
    mock_resp = {
        "id": 1,
        "name": "GHCR",
        "url": "https://ghcr.io",
        "username": "octocat",
        "password": "ghp_super_secret_token",
    }
    with respx.mock:
        route = respx.put("http://dockhand.test/api/registries/1?env=1").mock(
            return_value=Response(200, json=mock_resp)
        )
        result = await update_registry(registry_id=1, name="GHCR", ctx=mock_ctx, environment_id=1)
        assert route.called
        assert result["Id"] == 1
        assert result["Name"] == "GHCR"
        assert result["Username"] == "octocat"
        assert "password" not in result
        assert "Password" not in result
        assert "ghp_super_secret_token" not in str(result)


@pytest.mark.asyncio
async def test_get_create_delete_test_registry_strip_passwords(mock_client):
    from dockhand_mcp.tools.registries import get_registry, create_registry, delete_registry, test_registry
    mock_ctx = MockContext(mock_client)
    mock_resp = {
        "id": 2,
        "name": "GitLab",
        "url": "https://registry.gitlab.com",
        "username": "gluser",
        "password": "glpat_secret_password",
        "type": "gitlab",
    }
    with respx.mock:
        get_route = respx.get("http://dockhand.test/api/registries/2?env=1").mock(
            return_value=Response(200, json=mock_resp)
        )
        create_route = respx.post("http://dockhand.test/api/registries?env=1").mock(
            return_value=Response(200, json=mock_resp)
        )
        test_route = respx.post("http://dockhand.test/api/registries/2/test?env=1").mock(
            return_value=Response(200, json={"success": True})
        )
        del_route = respx.delete("http://dockhand.test/api/registries/2?env=1").mock(
            return_value=Response(200, json={"deleted": True})
        )

        fetched = await get_registry(environment_id=1, registry_id=2, ctx=mock_ctx)
        assert get_route.called
        assert fetched["Name"] == "GitLab"
        assert "glpat_secret_password" not in str(fetched)

        created = await create_registry(
            environment_id=1,
            name="GitLab",
            registry_type="gitlab",
            url="https://registry.gitlab.com",
            ctx=mock_ctx,
            username="gluser",
            password="glpat_secret_password",
        )
        assert create_route.called
        assert "glpat_secret_password" not in str(created)

        tested = await test_registry(environment_id=1, registry_id=2, ctx=mock_ctx)
        assert test_route.called
        assert tested["success"] is True

        deleted = await delete_registry(environment_id=1, registry_id=2, ctx=mock_ctx)
        assert del_route.called
        assert deleted["deleted"] is True


