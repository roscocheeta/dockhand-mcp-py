import pytest
import respx
from httpx import Response
from dockhand_mcp.client import DockhandClient
from mcp.server.fastmcp import Context

# We need a mock Context object since FastMCP handles the real one
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
async def test_list_environments(mock_client, mock_ctx):
    # The tools are imported inside the test so they don't break if run outside FastMCP context
    from dockhand_mcp.tools.environments import list_environments
    
    mock_data = [
        {"Id": 1, "Name": "local", "URL": "unix:///var/run/docker.sock", "hawserToken": "secret"},
        {"Id": 2, "Name": "remote", "URL": "tcp://1.2.3.4:2375"}
    ]
    
    with respx.mock:
        respx.get("http://dockhand.test/api/environments").mock(return_value=Response(200, json=mock_data))
        
        # Test the tool
        result = await list_environments(ctx=mock_ctx)
        
        # Ensure hawserToken is stripped out for security
        assert "environments" in result
        envs = result["environments"]
        assert len(envs) == 2
        assert envs[0]["Id"] == 1
        assert "hawserToken" not in envs[0]
        assert "tlsKey" not in envs[0]

@pytest.mark.asyncio
async def test_get_environment(mock_client, mock_ctx):
    from dockhand_mcp.tools.environments import get_environment
    
    mock_data = {"Id": 1, "Name": "local", "hawserToken": "secret"}
    
    with respx.mock:
        respx.get("http://dockhand.test/api/environments/1").mock(return_value=Response(200, json=mock_data))
        
        result = await get_environment(environment_id=1, ctx=mock_ctx)
        
        assert result["Id"] == 1
        assert "hawserToken" not in result

@pytest.mark.asyncio
async def test_create_environment_advanced(mock_client, mock_ctx):
    from dockhand_mcp.tools.environments import create_environment
    with respx.mock:
        route = respx.post('http://dockhand.test/api/environments').mock(
            return_value=Response(200, json={'id': 2, 'name': 'Edge Node'})
        )
        
        result = await create_environment(
            name='Edge Node',
            connection_type='hawser-edge',
            ctx=mock_ctx,
            protocol='https',
            tls_skip_verify=True,
            icon='server',
            hawser_token='secret-token',
            labels=['prod', 'edge'],
            collect_metrics=False
        )
        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload['name'] == 'Edge Node'
        assert payload['connectionType'] == 'hawser-edge'
        assert payload['protocol'] == 'https'
        assert payload['tlsSkipVerify'] is True
        assert payload['icon'] == 'server'
        assert payload['hawserToken'] == 'secret-token'
        assert payload['labels'] == ['prod', 'edge']
        assert payload['collectMetrics'] is False
        assert result['name'] == 'Edge Node'

@pytest.mark.asyncio
async def test_update_environment_advanced(mock_client, mock_ctx):
    from dockhand_mcp.tools.environments import update_environment
    with respx.mock:
        route = respx.put('http://dockhand.test/api/environments/1').mock(
            return_value=Response(200, json={'id': 1, 'name': 'Updated'})
        )
        
        result = await update_environment(
            environment_id=1,
            ctx=mock_ctx,
            tls_ca='-----BEGIN CERTIFICATE-----...',
            port=2376
        )
        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload['tlsCa'] == '-----BEGIN CERTIFICATE-----...'
        assert payload['port'] == 2376


@pytest.mark.asyncio
async def test_environment_update_check_settings(mock_client, mock_ctx):
    import json
    from dockhand_mcp.tools.environments import (
        get_environment_update_check_settings,
        update_environment_update_check_settings,
    )
    with respx.mock:
        get_route = respx.get("http://dockhand.test/api/environments/1/update-check").mock(
            return_value=Response(
                200,
                json={
                    "settings": {
                        "enabled": True,
                        "cron": "0 4 * * *",
                        "autoUpdate": False,
                        "minimumReleaseAgeHours": 48,
                        "minimumReleaseAgeOverride": True,
                    }
                },
            )
        )
        post_route = respx.post("http://dockhand.test/api/environments/1/update-check").mock(
            return_value=Response(200, json={"success": True})
        )

        res = await get_environment_update_check_settings(environment_id=1, ctx=mock_ctx)
        assert get_route.called
        assert res["settings"]["minimumReleaseAgeHours"] == 48

        up = await update_environment_update_check_settings(
            environment_id=1,
            ctx=mock_ctx,
            enabled=True,
            minimum_release_age_hours=24,
            minimum_release_age_override=True,
        )
        assert post_route.called
        payload = json.loads(post_route.calls.last.request.content)
        assert payload["minimumReleaseAgeHours"] == 24
        assert payload["minimumReleaseAgeOverride"] is True
        assert up["success"] is True


@pytest.mark.asyncio
async def test_environment_reports(mock_client, mock_ctx):
    import json
    from dockhand_mcp.tools.environments import (
        get_environment_report,
        get_environment_report_settings,
        update_environment_report_settings,
    )
    with respx.mock:
        rep_route = respx.get("http://dockhand.test/api/environments/report?format=json&env=1").mock(
            return_value=Response(200, json={"environments": [{"id": 1, "name": "local"}]})
        )
        get_set_route = respx.get("http://dockhand.test/api/environments/1/report").mock(
            return_value=Response(200, json={"settings": {"enabled": False, "format": "pdf"}})
        )
        post_set_route = respx.post("http://dockhand.test/api/environments/1/report").mock(
            return_value=Response(200, json={"success": True})
        )

        rep = await get_environment_report(ctx=mock_ctx, environment_id=1, format="json")
        assert rep_route.called
        assert rep["environments"][0]["id"] == 1

        settings = await get_environment_report_settings(environment_id=1, ctx=mock_ctx)
        assert get_set_route.called
        assert settings["settings"]["format"] == "pdf"

        saved = await update_environment_report_settings(
            environment_id=1,
            ctx=mock_ctx,
            enabled=True,
            cron="0 6 1 * *",
            format="csv",
            notification_id=3,
        )
        assert post_set_route.called
        payload = json.loads(post_set_route.calls.last.request.content)
        assert payload["notificationId"] == 3
        assert payload["format"] == "csv"
        assert saved["success"] is True

