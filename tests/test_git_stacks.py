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


@pytest.mark.asyncio
async def test_create_git_stack_basic(mock_client):
    """Verify create_git_stack POSTs to /api/git/stacks with correct body shape."""
    from dockhand_mcp.tools.git_stacks import create_git_stack
    mock_ctx = MockContext(mock_client)

    with respx.mock:
        route = respx.post("http://dockhand.test/api/git/stacks").mock(
            return_value=Response(200, json={"id": 5, "stackName": "my-git-app", "success": True})
        )

        result = await create_git_stack(
            environment_id=1,
            stack_name="my-git-app",
            url="https://github.com/user/repo.git",
            ctx=mock_ctx,
            branch="main",
            compose_path="docker-compose.yml",
        )

        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload["stackName"] == "my-git-app"
        assert payload["environmentId"] == 1
        assert payload["url"] == "https://github.com/user/repo.git"
        assert payload["branch"] == "main"
        assert payload["composePath"] == "docker-compose.yml"
        assert payload["deployNow"] is True
        # Should NOT have repositoryId — that was the old broken approach
        assert "repositoryId" not in payload
        assert result["success"] is True


@pytest.mark.asyncio
async def test_create_git_stack_full_options(mock_client):
    """Verify all optional params are correctly serialized."""
    from dockhand_mcp.tools.git_stacks import create_git_stack
    mock_ctx = MockContext(mock_client)

    with respx.mock:
        route = respx.post("http://dockhand.test/api/git/stacks").mock(
            return_value=Response(200, json={"id": 6, "success": True})
        )

        result = await create_git_stack(
            environment_id=2,
            stack_name="full-stack",
            url="git@github.com:user/repo.git",
            ctx=mock_ctx,
            branch="develop",
            compose_path="infra/compose.yml",
            env_file_path=".env.production",
            credential_id=3,
            deploy_now=False,
            auto_update=True,
            auto_update_cron="0 3 * * *",
            webhook_enabled=True,
            webhook_secret="my-secret",
            env_vars=[{"key": "APP_ENV", "value": "prod", "isSecret": False}],
        )

        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload["stackName"] == "full-stack"
        assert payload["environmentId"] == 2
        assert payload["url"] == "git@github.com:user/repo.git"
        assert payload["branch"] == "develop"
        assert payload["composePath"] == "infra/compose.yml"
        assert payload["envFilePath"] == ".env.production"
        assert payload["credentialId"] == 3
        assert payload["deployNow"] is False
        assert payload["autoUpdate"] is True
        assert payload["autoUpdateCron"] == "0 3 * * *"
        assert payload["webhookEnabled"] is True
        assert payload["webhookSecret"] == "my-secret"
        assert payload["envVars"] == [{"key": "APP_ENV", "value": "prod", "isSecret": False}]
        assert result["success"] is True

