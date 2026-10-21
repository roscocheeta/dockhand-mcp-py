import pytest
import respx
from httpx import Response
from dockhand_mcp.tools.audit import get_audit_log, get_audit_users
from dockhand_mcp.tools.dashboard import get_dashboard, get_activity


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
async def test_audit_log_and_users(mock_client, mock_ctx):
    mock_logs = [
        {
            "id": 10,
            "timestamp": "2026-10-21T00:00:00Z",
            "username": "admin",
            "action": "container.start",
            "target": "web",
            "environmentId": 1,
            "extraVerbosePayload": {"huge": "blob"},
        }
    ]
    with respx.mock:
        list_route = respx.get(
            "http://dockhand.test/api/audit?limit=25&offset=5&env=1&username=admin&action=container.start"
        ).mock(return_value=Response(200, json=mock_logs))
        dict_route = respx.get("http://dockhand.test/api/audit?limit=100&offset=0").mock(
            return_value=Response(200, json={"data": mock_logs, "total": 1})
        )
        users_route = respx.get("http://dockhand.test/api/audit/users").mock(
            return_value=Response(200, json=["admin", "ops"])
        )

        res = await get_audit_log(
            ctx=mock_ctx,
            environment_id=1,
            limit=25,
            offset=5,
            username="admin",
            action="container.start",
        )
        assert list_route.called
        assert len(res) == 1
        assert res[0]["Id"] == 10
        assert res[0]["Username"] == "admin"
        assert "extraVerbosePayload" not in res[0]

        res_dict = await get_audit_log(ctx=mock_ctx)
        assert dict_route.called
        assert res_dict["data"][0]["Action"] == "container.start"

        users = await get_audit_users(ctx=mock_ctx)
        assert users_route.called
        assert users == ["admin", "ops"]


@pytest.mark.asyncio
async def test_dashboard_and_activity(mock_client, mock_ctx):
    with respx.mock:
        dash_route = respx.get("http://dockhand.test/api/dashboard?env=1").mock(
            return_value=Response(200, json={"containersRunning": 5, "imagesCount": 12})
        )
        act_route = respx.get("http://dockhand.test/api/dashboard/activity?limit=20").mock(
            return_value=Response(200, json=[{"event": "start", "container": "web"}])
        )

        dash = await get_dashboard(environment_id=1, ctx=mock_ctx)
        assert dash_route.called
        assert dash["containersRunning"] == 5

        act = await get_activity(limit=20, ctx=mock_ctx)
        assert act_route.called
        assert act[0]["container"] == "web"
