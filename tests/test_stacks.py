import pytest
import respx
from httpx import Response
from dockhand_mcp.tools.stacks import (
    create_stack,
    list_stacks,
    get_stack_compose,
    update_stack_compose,
    deploy_stack,
    restart_stack,
    get_stack_stats,
    get_stack_path_hints,
)


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
async def test_create_stack_default_params(mock_client, mock_ctx):
    compose_content = "services:\n  web:\n    image: nginx:latest\n"
    sse_response_text = (
        'data: {"output": "Creating stack my-stack..."}\n\n'
        'data: {"output": "Stack created successfully"}\n\n'
        'data: {"success": true}\n'
    )

    with respx.mock:
        route = respx.post("http://dockhand.test/api/stacks?env=1").mock(
            return_value=Response(
                200,
                text=sse_response_text,
                headers={"Content-Type": "text/event-stream"},
            )
        )

        result = await create_stack(
            environment_id=1,
            name="my-stack",
            compose=compose_content,
            ctx=mock_ctx,
        )

        assert route.called
        request = route.calls.last.request
        import json
        payload = json.loads(request.content)
        assert payload["name"] == "my-stack"
        assert payload["compose"] == compose_content
        assert payload["start"] is True
        assert "composePath" not in payload

        assert result["success"] is True
        assert "Creating stack my-stack..." in result["output"]
        assert "Stack created successfully" in result["output"]


@pytest.mark.asyncio
async def test_create_stack_with_optional_params(mock_client, mock_ctx):
    compose_content = "version: '3.8'\nservices:\n  app:\n    image: redis:alpine\n"
    env_vars = [{"key": "PORT", "value": "6379", "isSecret": False}]
    sse_response_text = 'data: {"success": true}\n'

    with respx.mock:
        route = respx.post("http://dockhand.test/api/stacks?env=2").mock(
            return_value=Response(
                200,
                text=sse_response_text,
                headers={"Content-Type": "text/event-stream"},
            )
        )

        result = await create_stack(
            environment_id=2,
            name="redis-stack",
            compose=compose_content,
            ctx=mock_ctx,
            compose_path="/opt/stacks/redis/docker-compose.yml",
            env_path="/opt/stacks/redis/.env",
            start=False,
            env_vars=env_vars,
            raw_env_content="PORT=6379\n",
            secret_provider_id=42,
        )

        assert route.called
        request = route.calls.last.request
        import json
        payload = json.loads(request.content)
        assert payload["name"] == "redis-stack"
        assert payload["compose"] == compose_content
        assert payload["composePath"] == "/opt/stacks/redis/docker-compose.yml"
        assert payload["envPath"] == "/opt/stacks/redis/.env"
        assert payload["start"] is False
        assert payload["envVars"] == env_vars
        assert payload["rawEnvContent"] == "PORT=6379\n"
        assert payload["secretProviderId"] == 42

        assert result["success"] is True


@pytest.mark.asyncio
async def test_list_stacks_compact_v1054_fields(mock_client, mock_ctx):
    mock_stacks = [
        {
            "name": "nextcloud",
            "status": "running",
            "sourceType": "internal",
            "health": "healthy",
            "labelTags": [{"name": "prod", "color": "#ff0000"}],
            "updateCount": 1,
            "newerVersionCount": 2,
            "coolingDownCount": 0,
            "pinnedDigestCount": 1,
            "containers": ["abc"],
        }
    ]
    with respx.mock:
        route = respx.get("http://dockhand.test/api/stacks?env=1").mock(
            return_value=Response(200, json=mock_stacks)
        )
        result = await list_stacks(environment_id=1, ctx=mock_ctx)
        assert route.called
        assert len(result) == 1
        assert result[0]["Name"] == "nextcloud"
        assert result[0]["Type"] == "internal"
        assert result[0]["Health"] == "healthy"
        assert result[0]["LabelTags"] == [{"name": "prod", "color": "#ff0000"}]
        assert result[0]["UpdateCount"] == 1
        assert result[0]["NewerVersionCount"] == 2
        assert result[0]["CoolingDownCount"] == 0
        assert result[0]["PinnedDigestCount"] == 1
        assert "containers" not in result[0]


@pytest.mark.asyncio
async def test_restart_stack_with_mode(mock_client, mock_ctx):
    with respx.mock:
        route = respx.post("http://dockhand.test/api/stacks/web/restart?env=1&mode=ordered").mock(
            return_value=Response(
                200,
                text='data: {"success": true, "output": "Restarted"}\n',
                headers={"Content-Type": "text/event-stream"},
            )
        )
        result = await restart_stack(environment_id=1, name="web", ctx=mock_ctx, mode="ordered")
        assert route.called
        assert result["success"] is True


@pytest.mark.asyncio
async def test_update_stack_compose_redeploy_options(mock_client, mock_ctx):
    import json
    with respx.mock:
        route = respx.put("http://dockhand.test/api/stacks/web/compose?env=1").mock(
            return_value=Response(
                200,
                text='data: {"success": true}\n',
                headers={"Content-Type": "text/event-stream"},
            )
        )
        result = await update_stack_compose(
            environment_id=1,
            name="web",
            content="services: {}",
            ctx=mock_ctx,
            restart=True,
            pull=True,
            build=False,
            force_recreate=True,
        )
        assert route.called
        payload = json.loads(route.calls.last.request.content)
        assert payload["restart"] is True
        assert payload["pull"] is True
        assert payload["build"] is False
        assert payload["forceRecreate"] is True
        assert result["success"] is True


@pytest.mark.asyncio
async def test_get_stack_stats_and_path_hints(mock_client, mock_ctx):
    with respx.mock:
        stats_route = respx.get("http://dockhand.test/api/stack-stats?env=1").mock(
            return_value=Response(200, json=[{"name": "web", "cpuPercent": 1.5, "runningCount": 2}])
        )
        hints_route = respx.get("http://dockhand.test/api/stacks/path-hints?name=web&env=1").mock(
            return_value=Response(200, json={"stackName": "web", "workingDir": "/opt/stacks/web", "configFiles": ["/opt/stacks/web/compose.yaml"]})
        )
        stats = await get_stack_stats(environment_id=1, ctx=mock_ctx)
        assert stats_route.called
        assert stats[0]["name"] == "web"

        hints = await get_stack_path_hints(environment_id=1, name="web", ctx=mock_ctx)
        assert hints_route.called
        assert hints["workingDir"] == "/opt/stacks/web"


@pytest.mark.asyncio
async def test_get_stack_env_and_raw_redact_secrets(mock_client, mock_ctx):
    from dockhand_mcp.tools.stacks import get_stack_env, get_stack_env_raw
    with respx.mock:
        env_route = respx.get("http://dockhand.test/api/stacks/web/env?env=1").mock(
            return_value=Response(
                200,
                json={
                    "variables": {"APP_ENV": "prod", "DB_PASSWORD": "plain_password"},
                    "envVars": [
                        {"key": "REDIS_HOST", "value": "redis", "isSecret": False},
                        {"key": "API_SECRET", "value": "top_secret", "isSecret": False},
                        {"key": "CUSTOM_VAL", "value": "marked_secret", "isSecret": True},
                    ],
                },
            )
        )
        raw_route = respx.get("http://dockhand.test/api/stacks/web/env/raw?env=1").mock(
            return_value=Response(
                200,
                json={"content": "APP_ENV=prod\nDB_PASSWORD=plain_password\nAPI_TOKEN=tok_123\n"},
            )
        )

        env_res = await get_stack_env(environment_id=1, name="web", ctx=mock_ctx)
        assert env_route.called
        assert env_res["variables"]["APP_ENV"] == "prod"
        assert env_res["variables"]["DB_PASSWORD"] == "***REDACTED***"
        assert env_res["envVars"][0]["value"] == "redis"
        assert env_res["envVars"][1]["value"] == "***REDACTED***"
        assert env_res["envVars"][2]["value"] == "***REDACTED***"

        raw_res = await get_stack_env_raw(environment_id=1, name="web", ctx=mock_ctx)
        assert raw_route.called
        assert "APP_ENV=prod" in raw_res["content"]
        assert "DB_PASSWORD=***REDACTED***" in raw_res["content"]
        assert "API_TOKEN=***REDACTED***" in raw_res["content"]
        assert "plain_password" not in raw_res["content"]
        assert "tok_123" not in raw_res["content"]


@pytest.mark.asyncio
async def test_get_stack_deploy_log_truncates_output(mock_client, mock_ctx):
    from dockhand_mcp.tools.stacks import get_stack_deploy_log
    with respx.mock:
        route = respx.get("http://dockhand.test/api/stacks/web/deploys/7/log?env=1").mock(
            return_value=Response(200, json={"log": "L" * 1000})
        )
        res = await get_stack_deploy_log(
            environment_id=1,
            name="web",
            run_id=7,
            ctx=mock_ctx,
            max_bytes=200,
        )
        assert route.called
        assert res["truncated"] is True
        assert res["log"].startswith("L" * 200)
        assert "[TRUNCATED AT 200 BYTES]" in res["log"]


@pytest.mark.asyncio
async def test_get_stack_delete_preview_route(mock_client, mock_ctx):
    from dockhand_mcp.tools.stacks import get_stack_delete_preview
    with respx.mock:
        route = respx.get("http://dockhand.test/api/stacks/web/delete-preview?env=1").mock(
            return_value=Response(200, json={"files": ["compose.yaml"], "containers": ["web-1"]})
        )
        res = await get_stack_delete_preview(environment_id=1, name="web", ctx=mock_ctx)
        assert route.called
        assert res["containers"] == ["web-1"]


@pytest.mark.asyncio
async def test_stack_compose_env_and_lifecycle_operations(mock_client, mock_ctx):
    from dockhand_mcp.tools.stacks import (
        get_stack_compose,
        update_stack_compose,
        update_stack_env,
        update_stack_env_raw,
        remove_stack_env_vars,
        check_stack_env_collisions,
        validate_stack_env,
        deploy_stack,
        start_stack,
        stop_stack,
        down_stack,
        delete_stack,
        adopt_stack,
        relocate_stack,
        get_stack_deploy_history,
    )
    sse_ok = Response(200, text='data: {"success": true}\n', headers={"Content-Type": "text/event-stream"})
    with respx.mock:
        respx.get("http://dockhand.test/api/stacks/web/compose?env=1").mock(
            return_value=Response(
                200,
                json={"content": "services:\n  db:\n    environment:\n      - MYSQL_PASSWORD=inline_pw\n      - MYSQL_USER=app\n"},
            )
        )
        respx.put("http://dockhand.test/api/stacks/web/compose?env=1").mock(
            return_value=Response(200, json={"saved": True})
        )
        respx.put("http://dockhand.test/api/stacks/web/env?env=1").mock(
            return_value=Response(
                200,
                json={"envVars": [{"key": "API_SECRET", "value": "sec_123", "isSecret": True}]},
            )
        )
        respx.put("http://dockhand.test/api/stacks/web/env/raw?env=1").mock(
            return_value=Response(200, json={"content": "API_SECRET=sec_123\nPORT=8080\n"})
        )
        respx.delete("http://dockhand.test/api/stacks/web/env?env=1").mock(
            return_value=Response(200, json={"removed": ["OLD_VAR"]})
        )
        respx.get("http://dockhand.test/api/stacks/web/env/collisions?env=1").mock(
            return_value=Response(200, json={"collisions": []})
        )
        respx.get("http://dockhand.test/api/stacks/web/env/validate?env=1").mock(
            return_value=Response(200, json={"valid": True})
        )
        respx.post("http://dockhand.test/api/stacks/web/deploy?env=1").mock(return_value=sse_ok)
        respx.post("http://dockhand.test/api/stacks/web/start?env=1").mock(return_value=sse_ok)
        respx.post("http://dockhand.test/api/stacks/web/stop?env=1").mock(return_value=sse_ok)
        respx.post("http://dockhand.test/api/stacks/web/down?env=1").mock(return_value=sse_ok)
        respx.delete("http://dockhand.test/api/stacks/web?env=1&force=true&files=false").mock(
            return_value=Response(200, json={"deleted": True})
        )
        respx.post("http://dockhand.test/api/stacks/web/adopt?env=1").mock(
            return_value=Response(200, json={"adopted": True})
        )
        respx.post("http://dockhand.test/api/stacks/web/relocate?env=1").mock(
            return_value=Response(200, json={"relocated": True})
        )
        respx.get("http://dockhand.test/api/stacks/web/deploys?env=1").mock(
            return_value=Response(200, json=[{"id": 1, "status": "success"}])
        )

        comp = await get_stack_compose(1, "web", mock_ctx)
        assert "MYSQL_PASSWORD=***REDACTED***" in comp["content"]
        assert "MYSQL_USER=app" in comp["content"]
        assert "inline_pw" not in comp["content"]

        saved = await update_stack_compose(1, "web", "services: {}", mock_ctx, restart=False)
        assert saved["saved"] is True

        upd_env = await update_stack_env(1, "web", [{"key": "API_SECRET", "value": "sec_123"}], mock_ctx)
        assert upd_env["envVars"][0]["value"] == "***REDACTED***"

        upd_raw = await update_stack_env_raw(1, "web", "API_SECRET=sec_123\nPORT=8080\n", mock_ctx)
        assert "API_SECRET=***REDACTED***" in upd_raw["content"]
        assert "sec_123" not in upd_raw["content"]

        assert (await remove_stack_env_vars(1, "web", ["OLD_VAR"], mock_ctx))["removed"] == ["OLD_VAR"]
        assert (await check_stack_env_collisions(1, "web", mock_ctx))["collisions"] == []
        assert (await validate_stack_env(1, "web", mock_ctx))["valid"] is True
        assert (await deploy_stack(1, "web", mock_ctx))["success"] is True
        assert (await start_stack(1, "web", mock_ctx))["success"] is True
        assert (await stop_stack(1, "web", mock_ctx))["success"] is True
        assert (await down_stack(1, "web", mock_ctx, remove_volumes=True))["success"] is True
        assert (await delete_stack(1, "web", mock_ctx, force=True, files=False))["deleted"] is True
        assert (await adopt_stack(1, "web", mock_ctx))["adopted"] is True
        assert (await relocate_stack(1, "web", "/new/path", mock_ctx))["relocated"] is True
        assert (await get_stack_deploy_history(1, "web", mock_ctx))[0]["id"] == 1
@pytest.mark.asyncio
async def test_stacks_wildcard_search(mock_client, mock_ctx):
    with respx.mock:
        respx.get("http://dockhand.test/api/stacks?env=1").mock(
            return_value=Response(
                200,
                json=[
                    {"id": "s1", "name": "prod-web", "status": "running"},
                    {"id": "s2", "name": "prod-db", "status": "running"},
                    {"id": "s3", "name": "dev-api", "status": "stopped"},
                    {"id": "s4", "name": "media-arr", "status": "running"},
                ],
            )
        )

        all_stacks = await list_stacks(environment_id=1, ctx=mock_ctx)
        assert len(all_stacks) == 4

        prod_stacks = await list_stacks(environment_id=1, ctx=mock_ctx, search="prod-*")
        assert len(prod_stacks) == 2
        assert [s["Name"] for s in prod_stacks] == ["prod-db", "prod-web"]

        media_stacks = await list_stacks(environment_id=1, ctx=mock_ctx, search="*arr*")
        assert len(media_stacks) == 1
        assert media_stacks[0]["Name"] == "media-arr"


@pytest.mark.asyncio
async def test_stack_deploy_pull_policy_and_build_flags(mock_client, mock_ctx):
    import json
    sse_ok = Response(
        200,
        text='data: {"output": "deploying"}\n\ndata: {"success": true}\n',
        headers={"Content-Type": "text/event-stream"},
    )
    with respx.mock:
        deploy_route = respx.post("http://dockhand.test/api/stacks/my-stack/deploy?env=1").mock(return_value=sse_ok)
        compose_route = respx.put("http://dockhand.test/api/stacks/my-stack/compose?env=1").mock(return_value=sse_ok)
        create_route = respx.post("http://dockhand.test/api/stacks?env=1").mock(return_value=sse_ok)

        # 1. deploy_stack with v1.0.56 redeploy flags
        await deploy_stack(
            name="my-stack",
            ctx=mock_ctx,
            environment_id=1,
            pull=False,
            respect_pull_policy=True,
            build=True,
            pull_base=True,
            no_cache=True,
            force_recreate=True,
        )
        assert deploy_route.called
        deploy_body = json.loads(deploy_route.calls.last.request.content)
        assert deploy_body["pull"] is False
        assert deploy_body["respectPullPolicy"] is True
        assert deploy_body["build"] is True
        assert deploy_body["pullBase"] is True
        assert deploy_body["noCache"] is True
        assert deploy_body["forceRecreate"] is True

        # 2. update_stack_compose with redeploy flags
        await update_stack_compose(
            name="my-stack",
            content="services: {web: {image: nginx}}",
            ctx=mock_ctx,
            environment_id=1,
            restart=True,
            respect_pull_policy=True,
            pull_base=True,
            no_cache=True,
        )
        assert compose_route.called
        compose_body = json.loads(compose_route.calls.last.request.content)
        assert compose_body["restart"] is True
        assert compose_body["respectPullPolicy"] is True
        assert compose_body["pullBase"] is True
        assert compose_body["noCache"] is True

        # 3. create_stack with flags
        await create_stack(
            name="new-stack",
            compose="services: {}",
            ctx=mock_ctx,
            environment_id=1,
            respect_pull_policy=True,
            pull_base=True,
            no_cache=True,
        )
        assert create_route.called
        create_body = json.loads(create_route.calls.last.request.content)
        assert create_body["respectPullPolicy"] is True
        assert create_body["pullBase"] is True
        assert create_body["noCache"] is True
@pytest.mark.asyncio
async def test_convert_stack_to_git(mock_client, mock_ctx):
    import json
    from dockhand_mcp.tools.stacks import convert_stack_to_git

    with respx.mock:
        # 1. deploy_now=False (standard POST returning JSON)
        attach_route = respx.post("http://dockhand.test/api/stacks/my-local-stack/attach?env=1").mock(
            return_value=Response(
                200,
                json={
                    "id": 99,
                    "stackName": "my-local-stack",
                    "sourceType": "git",
                    "webhookSecret": "top_secret_wh_token",
                    "envVars": [{"key": "DB_PASS", "value": "secret_db_pass", "isSecret": True}],
                },
            )
        )

        res = await convert_stack_to_git(
            name="my-local-stack",
            ctx=mock_ctx,
            environment_id=1,
            url="https://github.com/myorg/myrepo.git",
            branch="staging",
            compose_path="docker/compose.yml",
            env_file_path=".env.production",
            webhook_enabled=True,
            webhook_secret="wh_secret_xyz",
            deploy_now=False,
        )

        assert attach_route.called
        req_body = json.loads(attach_route.calls.last.request.content)
        assert req_body["url"] == "https://github.com/myorg/myrepo.git"
        assert req_body["branch"] == "staging"
        assert req_body["composePath"] == "docker/compose.yml"
        assert req_body["envFilePath"] == ".env.production"
        assert req_body["webhookEnabled"] is True
        assert req_body["webhookSecret"] == "wh_secret_xyz"
        assert req_body["deployNow"] is False

        # Verify sensitive response redaction
        assert res["webhookSecret"] == "***REDACTED***"
        assert res["envVars"][0]["value"] == "***REDACTED***"

        # 2. deploy_now=True (SSE response stream)
        sse_attach_route = respx.post("http://dockhand.test/api/stacks/my-local-stack/attach?env=1").mock(
            return_value=Response(
                200,
                text='data: {"progress": "deploying"}\n\ndata: {"result": {"id": 99, "deployed": true}}\n',
                headers={"Content-Type": "text/event-stream"},
            )
        )

        res_sse = await convert_stack_to_git(
            name="my-local-stack",
            ctx=mock_ctx,
            environment_id=1,
            repository_id=5,
            branch="main",
            deploy_now=True,
        )
        assert sse_attach_route.called
        req_body_sse = json.loads(sse_attach_route.calls.last.request.content)
        assert req_body_sse["repositoryId"] == 5
        assert req_body_sse["deployNow"] is True


@pytest.mark.asyncio
async def test_list_stacks_pagination(mock_client):
    from mcp.server.fastmcp import FastMCP
    from dockhand_mcp.tools import register_all_tools
    from dockhand_mcp.tools.stacks import list_stacks
    mock_ctx = MockContext(mock_client)

    mcp = FastMCP("test-stacks")
    register_all_tools(mcp, read_only=True)
    stacks_tool = mcp._tool_manager.get_tool("list_stacks")
    assert stacks_tool is not None
    assert "args" not in stacks_tool.parameters.get("properties", {})

    payload = [{"id": i, "name": f"stack-{i}", "status": "running", "environmentId": 1} for i in reversed(range(5))]
    with respx.mock:
        respx.get("http://dockhand.test/api/stacks?env=1").mock(
            return_value=Response(200, json=payload)
        )
        res = await stacks_tool.fn(environment_id=1, ctx=mock_ctx, search="stack-*", limit=2, offset=2)
        assert res["total"] == 5
        assert res["hasMore"] is True
        assert [s["Name"] for s in res["items"]] == ["stack-2", "stack-3"]

        res_direct = await list_stacks(environment_id=1, ctx=mock_ctx, limit=2, offset=0)
        assert [s["Name"] for s in res_direct["items"]] == ["stack-0", "stack-1"]
