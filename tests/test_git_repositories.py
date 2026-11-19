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


@pytest.mark.asyncio
async def test_git_repository_crud_sync_test_webhook(mock_client):
    import json
    from dockhand_mcp.tools.git_repositories import (
        create_git_repository,
        update_git_repository,
        delete_git_repository,
        sync_git_repository,
        test_git_repository,
        trigger_git_webhook,
    )
    mock_ctx = MockContext(mock_client)
    with respx.mock:
        create_route = respx.post("http://dockhand.test/api/git/repositories").mock(
            return_value=Response(200, json={"id": 2, "name": "infra"})
        )
        update_route = respx.put("http://dockhand.test/api/git/repositories/2").mock(
            return_value=Response(200, json={"id": 2, "branch": "develop"})
        )
        del_route = respx.delete("http://dockhand.test/api/git/repositories/2").mock(
            return_value=Response(200, json={"success": True})
        )
        sync_route = respx.post("http://dockhand.test/api/git/repositories/2/sync").mock(
            return_value=Response(200, json={"synced": True})
        )
        test_route = respx.post("http://dockhand.test/api/git/repositories/2/test").mock(
            return_value=Response(200, json={"reachable": True})
        )
        wh_route = respx.post("http://dockhand.test/api/git/repositories/2/webhook").mock(
            return_value=Response(200, json={"triggered": True})
        )

        created = await create_git_repository(
            name="infra",
            url="https://github.com/org/infra.git",
            branch="main",
            ctx=mock_ctx,
            credential_id=5,
        )
        assert create_route.called
        assert json.loads(create_route.calls.last.request.content)["credentialId"] == 5
        assert created["id"] == 2

        updated = await update_git_repository(
            repository_id=2,
            ctx=mock_ctx,
            name="infra-prod",
            url="https://github.com/org/infra.git",
            branch="develop",
            credential_id=6,
        )
        assert update_route.called
        assert updated["branch"] == "develop"

        synced = await sync_git_repository(repository_id=2, ctx=mock_ctx)
        assert sync_route.called
        assert synced["synced"] is True

        tested = await test_git_repository(repository_id=2, ctx=mock_ctx)
        assert test_route.called
        assert tested["reachable"] is True

        wh = await trigger_git_webhook(repository_id=2, ctx=mock_ctx)
        assert wh_route.called
        assert wh["triggered"] is True

        deleted = await delete_git_repository(repository_id=2, ctx=mock_ctx)
        assert del_route.called
        assert deleted["success"] is True


@pytest.mark.asyncio
async def test_git_repos_non_list_and_credential_private_key(mock_client):
    import json
    from dockhand_mcp.tools.git_credentials import create_git_credential
    from dockhand_mcp.tools.git_repositories import list_git_repositories

    mock_ctx = MockContext(mock_client)
    with respx.mock:
        respx.get("http://dockhand.test/api/git/repositories").mock(
            return_value=Response(200, json={"unexpected": True})
        )
        assert await list_git_repositories(ctx=mock_ctx) == {"unexpected": True}

        cred_route = respx.post("http://dockhand.test/api/git/credentials").mock(
            return_value=Response(200, json={"id": 9, "privateKey": "-----BEGIN KEY-----"})
        )
        res = await create_git_credential(
            name="ssh-cred",
            username="git",
            ctx=mock_ctx,
            private_key="-----BEGIN KEY-----",
        )
        assert json.loads(cred_route.calls.last.request.content)["privateKey"] == "-----BEGIN KEY-----"
        assert res["privateKey"] == "***REDACTED***"

