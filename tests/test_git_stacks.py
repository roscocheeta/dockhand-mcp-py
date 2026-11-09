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


@pytest.mark.asyncio
async def test_git_stack_redacts_webhook_secret_and_env_vars(mock_client):
    from dockhand_mcp.tools.git_stacks import get_git_stack, update_git_stack
    mock_ctx = MockContext(mock_client)
    mock_stack_payload = {
        "id": 10,
        "stackName": "sec-stack",
        "webhookEnabled": True,
        "webhookSecret": "plain_webhook_secret",
        "envVars": [
            {"key": "APP_MODE", "value": "production", "isSecret": False},
            {"key": "DB_PASSWORD", "value": "db_pass_123", "isSecret": False},
            {"key": "INTERNAL_ID", "value": "sec_val", "isSecret": True},
        ],
    }
    with respx.mock:
        get_route = respx.get("http://dockhand.test/api/git/stacks/10").mock(
            return_value=Response(200, json=mock_stack_payload)
        )
        put_route = respx.put("http://dockhand.test/api/git/stacks/10").mock(
            return_value=Response(200, json=mock_stack_payload)
        )

        fetched = await get_git_stack(stack_id=10, ctx=mock_ctx)
        assert get_route.called
        assert fetched["webhookSecret"] == "***REDACTED***"
        assert fetched["envVars"][0]["value"] == "production"
        assert fetched["envVars"][1]["value"] == "***REDACTED***"
        assert fetched["envVars"][2]["value"] == "***REDACTED***"

        updated = await update_git_stack(stack_id=10, ctx=mock_ctx, branch="main")
        assert put_route.called
        assert updated["webhookSecret"] == "***REDACTED***"
        assert "plain_webhook_secret" not in str(updated)
        assert "db_pass_123" not in str(updated)


@pytest.mark.asyncio
async def test_create_and_update_git_credential_redact_secrets(mock_client):
    from dockhand_mcp.tools.git_credentials import create_git_credential, update_git_credential
    mock_ctx = MockContext(mock_client)
    with respx.mock:
        post_route = respx.post("http://dockhand.test/api/git/credentials").mock(
            return_value=Response(200, json={"id": 1, "name": "gh", "password": "secret_pat", "privateKey": "ssh_key_pem"})
        )
        put_route = respx.put("http://dockhand.test/api/git/credentials/1").mock(
            return_value=Response(200, json={"id": 1, "name": "gh", "password": "updated_pat"})
        )

        created = await create_git_credential(name="gh", username="git", ctx=mock_ctx, password="secret_pat")
        assert post_route.called
        assert created["password"] == "***REDACTED***"
        assert created["privateKey"] == "***REDACTED***"

        updated = await update_git_credential(credential_id=1, ctx=mock_ctx, password="updated_pat")
        assert put_route.called
        assert updated["password"] == "***REDACTED***"


@pytest.mark.asyncio
async def test_git_stack_list_deploy_sync_delete_and_cred_delete(mock_client):
    from dockhand_mcp.tools.git_stacks import (
        list_git_stacks,
        deploy_git_stack,
        sync_git_stack,
        delete_git_stack,
    )
    from dockhand_mcp.tools.git_credentials import delete_git_credential
    mock_ctx = MockContext(mock_client)
    with respx.mock:
        list_route = respx.get("http://dockhand.test/api/git/stacks").mock(
            return_value=Response(
                200,
                json=[{"id": 1, "name": "git-app", "repositoryId": 5, "branch": "main", "composePath": "compose.yaml"}],
            )
        )
        deploy_route = respx.post("http://dockhand.test/api/git/stacks/1/deploy-stream").mock(
            return_value=Response(
                200,
                text='data: {"output": "Deployed", "success": true}\n',
                headers={"Content-Type": "text/event-stream"},
            )
        )
        sync_route = respx.post("http://dockhand.test/api/git/stacks/1/sync").mock(
            return_value=Response(200, json={"synced": True})
        )
        del_route = respx.delete("http://dockhand.test/api/git/stacks/1?force=true").mock(
            return_value=Response(200, json={"deleted": True})
        )
        cred_del_route = respx.delete("http://dockhand.test/api/git/credentials/9").mock(
            return_value=Response(200, json={"deleted": True})
        )

        stacks = await list_git_stacks(ctx=mock_ctx)
        assert list_route.called
        assert stacks[0]["Name"] == "git-app"

        dep = await deploy_git_stack(stack_id=1, ctx=mock_ctx)
        assert deploy_route.called
        assert dep["success"] is True

        syn = await sync_git_stack(stack_id=1, ctx=mock_ctx)
        assert sync_route.called
        assert syn["synced"] is True

        deleted = await delete_git_stack(stack_id=1, ctx=mock_ctx, force=True)
        assert del_route.called
        assert deleted["deleted"] is True

        cred_del = await delete_git_credential(credential_id=9, ctx=mock_ctx)
        assert cred_del_route.called
        assert cred_del["deleted"] is True






def test_compact_git_stack_upstream_format():
    from dockhand_mcp.tools.git_stacks import _compact_git_stack
    raw_api_payload = {
        "id": 33,
        "stackName": "bazarr",
        "environmentId": 1,
        "repositoryId": 6,
        "branch": None,
        "composePath": "bazarr.yaml",
        "envFilePath": None,
        "autoUpdate": False,
        "syncStatus": "synced",
        "repository": {
            "id": 6,
            "name": "bazarr",
            "url": "https://github.com/user/stacks",
            "branch": "main",
            "credentialId": 1,
        },
    }
    compact = _compact_git_stack(raw_api_payload)
    assert compact["Id"] == 33
    assert compact["Name"] == "bazarr"
    assert compact["Url"] == "https://github.com/user/stacks"
    assert compact["Branch"] == "main"
    assert compact["Status"] == "synced"
    assert compact["ComposePath"] == "bazarr.yaml"
    assert compact["EnvironmentId"] == 1


@pytest.mark.asyncio
async def test_sync_git_stack_with_deploy_and_atomic_tool(mock_client):
    from dockhand_mcp.tools.git_stacks import sync_git_stack, sync_and_deploy_git_stack
    mock_ctx = MockContext(mock_client)

    with respx.mock:
        # Mock sync returning full bloat payload
        sync_route = respx.post("http://dockhand.test/api/git/stacks/33/sync").mock(
            return_value=Response(
                200,
                json={
                    "success": True,
                    "commit": "abc1234",
                    "updated": True,
                    "changedFiles": ["compose.yaml"],
                    "composeFileName": "compose.yaml",
                    "composeContent": "services:\n  app: ...",
                    "newFiles": {f"file_{i}": "hash" * 10 for i in range(50)},
                    "previousManifest": {"files": {}},
                },
            )
        )
        deploy_route = respx.post("http://dockhand.test/api/git/stacks/33/deploy-stream").mock(
            return_value=Response(
                200,
                text='data: {"output": "Deployed successfully", "success": true}\n',
                headers={"Content-Type": "text/event-stream"},
            )
        )

        # 1. Sync only: verify bloated fields are compacted away
        res_sync_only = await sync_git_stack(33, mock_ctx, deploy=False)
        assert sync_route.called
        assert not deploy_route.called
        assert res_sync_only["success"] is True
        assert res_sync_only["commit"] == "abc1234"
        assert res_sync_only["updated"] is True
        assert "newFiles" not in res_sync_only
        assert "composeContent" not in res_sync_only

        # 2. Sync with deploy=True: verify deploy stream called
        res_deploy = await sync_git_stack(33, mock_ctx, deploy=True)
        assert deploy_route.called
        assert res_deploy["sync"]["success"] is True
        assert res_deploy["deploy"]["success"] is True

        # 3. Dedicated sync_and_deploy_git_stack helper
        res_atomic = await sync_and_deploy_git_stack(33, mock_ctx)
        assert res_atomic["deploy"]["success"] is True


@pytest.mark.asyncio
async def test_sync_git_stack_deploy_skipped_on_sync_failure(mock_client):
    from dockhand_mcp.tools.git_stacks import sync_git_stack
    mock_ctx = MockContext(mock_client)

    with respx.mock:
        respx.post("http://dockhand.test/api/git/stacks/33/sync").mock(
            return_value=Response(200, json={"success": False, "error": "Git pull failed"})
        )
        deploy_route = respx.post("http://dockhand.test/api/git/stacks/33/deploy-stream").mock(
            return_value=Response(200, text='data: {"success": true}\n')
        )

        res = await sync_git_stack(33, mock_ctx, deploy=True)
        assert not deploy_route.called
        assert res["sync"]["success"] is False
        assert res["deploy"]["success"] is False
        assert "skipped" in res["deploy"]["error"]
@pytest.mark.asyncio
async def test_list_git_stacks_wildcard_search(mock_client):
    from dockhand_mcp.tools.git_stacks import list_git_stacks
    mock_ctx = MockContext(mock_client)

    with respx.mock:
        respx.get("http://dockhand.test/api/git/stacks").mock(
            return_value=Response(
                200,
                json=[
                    {"id": 1, "stackName": "prod-monitoring", "syncStatus": "synced"},
                    {"id": 2, "stackName": "prod-logging", "syncStatus": "synced"},
                    {"id": 3, "stackName": "dev-sandbox", "syncStatus": "pending"},
                ],
            )
        )

        all_stacks = await list_git_stacks(ctx=mock_ctx)
        assert len(all_stacks) == 3

        prod_stacks = await list_git_stacks(ctx=mock_ctx, search="prod-*")
        assert len(prod_stacks) == 2
        assert [s["Name"] for s in prod_stacks] == ["prod-monitoring", "prod-logging"]


@pytest.mark.asyncio
async def test_deploy_git_stack_redeploy_flags(mock_client):
    import json
    from dockhand_mcp.tools.git_stacks import deploy_git_stack, sync_git_stack
    mock_ctx = MockContext(mock_client)

    with respx.mock:
        deploy_route = respx.post("http://dockhand.test/api/git/stacks/10/deploy-stream").mock(
            return_value=Response(200, text='data: {"success": true}\n', headers={"Content-Type": "text/event-stream"})
        )
        sync_route = respx.post("http://dockhand.test/api/git/stacks/10/sync").mock(
            return_value=Response(200, json={"success": True, "commit": "123456"})
        )

        await deploy_git_stack(
            stack_id=10,
            ctx=mock_ctx,
            pull=False,
            respect_pull_policy=True,
            build=True,
            pull_base=True,
            no_cache=True,
            force_recreate=True,
        )
        assert deploy_route.called
        req_body = json.loads(deploy_route.calls.last.request.content)
        assert req_body["pull"] is False
        assert req_body["respectPullPolicy"] is True
        assert req_body["build"] is True
        assert req_body["pullBase"] is True
        assert req_body["noCache"] is True
        assert req_body["forceRecreate"] is True

        # Also verify sync_git_stack forwards the flags when deploy=True
        await sync_git_stack(
            stack_id=10,
            ctx=mock_ctx,
            deploy=True,
            respect_pull_policy=True,
            pull_base=True,
            no_cache=True,
        )
        assert sync_route.called
        sync_deploy_body = json.loads(deploy_route.calls.last.request.content)
        assert sync_deploy_body["respectPullPolicy"] is True
        assert sync_deploy_body["pullBase"] is True
        assert sync_deploy_body["noCache"] is True
@pytest.mark.asyncio
async def test_convert_git_stack_to_local(mock_client):
    from dockhand_mcp.tools.git_stacks import convert_git_stack_to_local
    mock_ctx = MockContext(mock_client)

    with respx.mock:
        # Mock numeric ID
        detach_route = respx.post("http://dockhand.test/api/git/stacks/42/detach").mock(
            return_value=Response(200, json={"success": True, "sourceType": "internal"})
        )
        res_id = await convert_git_stack_to_local(42, mock_ctx)
        assert detach_route.called
        assert res_id["success"] is True

        # Mock resolve by stack name
        respx.get("http://dockhand.test/api/git/stacks").mock(
            return_value=Response(
                200,
                json=[
                    {"id": 42, "stackName": "radarr", "syncStatus": "synced"},
                    {"id": 43, "stackName": "sonarr", "syncStatus": "synced"},
                ],
            )
        )
        res_name = await convert_git_stack_to_local("radarr", mock_ctx)
        assert res_name["success"] is True
