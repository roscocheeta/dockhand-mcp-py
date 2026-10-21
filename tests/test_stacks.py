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



