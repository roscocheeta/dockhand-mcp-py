import pytest
import respx
from httpx import Response
from dockhand_mcp.tools.stacks import create_stack, list_stacks, get_stack_compose, deploy_stack


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

