import pytest
import respx
from httpx import Response
from dockhand_mcp.tools.misc import create_schedule

class MockContext:
    def __init__(self, client):
        class LifespanContext:
            def __init__(self, client):
                self.lifespan_context = {"dockhand": client}
        self.request_context = LifespanContext(client)

@pytest.mark.asyncio
async def test_create_schedule_basic(mock_client):
    mock_ctx = MockContext(mock_client)
    
    with respx.mock:
        route = respx.post("http://dockhand.test/api/schedules").mock(
            return_value=Response(200, json={"success": True})
        )
        
        result = await create_schedule(
            name="Daily Backup",
            cron_expression="0 0 * * *",
            action="backup",
            ctx=mock_ctx
        )
        
        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload["name"] == "Daily Backup"
        assert payload["cron"] == "0 0 * * *"
        assert payload["action"] == "backup"
        assert payload["enabled"] is True
        assert "scheduleType" not in payload

@pytest.mark.asyncio
async def test_create_schedule_full(mock_client):
    mock_ctx = MockContext(mock_client)
    
    with respx.mock:
        route = respx.post("http://dockhand.test/api/schedules").mock(
            return_value=Response(200, json={"success": True})
        )
        
        result = await create_schedule(
            name="Scan Schedule",
            cron_expression="0 2 * * *",
            action="scan",
            ctx=mock_ctx,
            vulnerability_criteria={"level": "high"},
            schedule_type=2,
            container_name="db",
            env_id=1,
            enabled=False
        )
        
        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload["name"] == "Scan Schedule"
        assert payload["vulnerabilityCriteria"] == {"level": "high"}
        assert payload["scheduleType"] == 2
        assert payload["containerName"] == "db"
        assert payload["env"] == 1
        assert payload["enabled"] is False

@pytest.mark.asyncio
async def test_delete_snapshots(mock_client):
    class MockContext:
        def __init__(self, client):
            class LifespanContext:
                def __init__(self, client):
                    self.lifespan_context = {"dockhand": client}
            self.request_context = LifespanContext(client)
    mock_ctx = MockContext(mock_client)
    from dockhand_mcp.tools.misc import delete_snapshots
    with respx.mock:
        route = respx.post('http://dockhand.test/api/backup/snapshots/batch-delete').mock(
            return_value=Response(200, json={'success': True, 'deleted': ['1a2b3c4d']})
        )
        result = await delete_snapshots(destination_id=3, snapshot_ids=['1a2b3c4d'], ctx=mock_ctx)
        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload['destinationId'] == 3
        assert payload['snapshotIds'] == ['1a2b3c4d']
        assert result['deleted'] == ['1a2b3c4d']

