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


@pytest.mark.asyncio
async def test_environment_order(mock_client):
    mock_ctx = MockContext(mock_client)
    from dockhand_mcp.tools.misc import get_environment_order, set_environment_order, reset_environment_order
    with respx.mock:
        get_route = respx.get('http://dockhand.test/api/preferences/environment-order').mock(
            return_value=Response(200, json={'order': [3, 1, 2]})
        )
        post_route = respx.post('http://dockhand.test/api/preferences/environment-order').mock(
            return_value=Response(200, json={'order': [1, 2, 3]})
        )
        delete_route = respx.delete('http://dockhand.test/api/preferences/environment-order').mock(
            return_value=Response(200, json={'order': []})
        )
        
        get_res = await get_environment_order(ctx=mock_ctx)
        assert get_route.called
        assert get_res == [3, 1, 2]
        
        post_res = await set_environment_order([1, 2, 3], ctx=mock_ctx)
        assert post_route.called
        assert post_res == [1, 2, 3]
        
        del_res = await reset_environment_order(ctx=mock_ctx)
        assert delete_route.called
        assert del_res == []

@pytest.mark.asyncio
async def test_tag_order(mock_client):
    mock_ctx = MockContext(mock_client)
    from dockhand_mcp.tools.misc import get_tag_order, set_tag_order, reset_tag_order
    with respx.mock:
        get_route = respx.get('http://dockhand.test/api/preferences/tag-order').mock(
            return_value=Response(200, json={'order': [3, 1, 2]})
        )
        post_route = respx.post('http://dockhand.test/api/preferences/tag-order').mock(
            return_value=Response(200, json={'order': [1, 2, 3]})
        )
        delete_route = respx.delete('http://dockhand.test/api/preferences/tag-order').mock(
            return_value=Response(200, json={'order': []})
        )
        
        get_res = await get_tag_order(ctx=mock_ctx)
        assert get_route.called
        assert get_res == [3, 1, 2]
        
        post_res = await set_tag_order([1, 2, 3], ctx=mock_ctx)
        assert post_route.called
        assert post_res == [1, 2, 3]
        
        del_res = await reset_tag_order(ctx=mock_ctx)
        assert delete_route.called
        assert del_res == []


@pytest.mark.asyncio
async def test_minimum_release_age(mock_client):
    mock_ctx = MockContext(mock_client)
    from dockhand_mcp.tools.misc import get_minimum_release_age, set_minimum_release_age
    with respx.mock:
        get_route = respx.get("http://dockhand.test/api/settings/minimum-release-age").mock(
            return_value=Response(200, json={"hours": 24, "overridden": False, "inherited": False})
        )
        post_route = respx.post("http://dockhand.test/api/settings/minimum-release-age").mock(
            return_value=Response(200, json={"hours": 48, "overridden": False})
        )

        get_res = await get_minimum_release_age(ctx=mock_ctx)
        assert get_route.called
        assert get_res["hours"] == 24

        post_res = await set_minimum_release_age(hours=48, ctx=mock_ctx)
        assert post_route.called
        assert post_res["hours"] == 48


@pytest.mark.asyncio
async def test_secret_provider_crud(mock_client):
    import json
    mock_ctx = MockContext(mock_client)
    from dockhand_mcp.tools.misc import (
        create_secret_provider,
        update_secret_provider,
        delete_secret_provider,
    )
    with respx.mock:
        create_route = respx.post("http://dockhand.test/api/secret-providers").mock(
            return_value=Response(
                200,
                json={
                    "id": 5,
                    "name": "psono-prod",
                    "type": "psono",
                    "config": {"serverUrl": "https://psono.example.com", "secretKey": "psono_secret_abc"},
                },
            )
        )
        update_route = respx.put("http://dockhand.test/api/secret-providers/5").mock(
            return_value=Response(
                200,
                json={
                    "id": 5,
                    "name": "psono-updated",
                    "type": "psono",
                    "config": {"apiKeyId": "key_id_1", "apiKeySecret": "raw_api_secret"},
                },
            )
        )
        delete_route = respx.delete("http://dockhand.test/api/secret-providers/5").mock(
            return_value=Response(200, json={"success": True})
        )

        created = await create_secret_provider(
            name="psono-prod",
            type="psono",
            config={"serverUrl": "https://psono.example.com"},
            ctx=mock_ctx,
        )
        assert create_route.called
        assert created["type"] == "psono"
        assert created["config"]["serverUrl"] == "https://psono.example.com"
        assert created["config"]["secretKey"] == "***REDACTED***"

        updated = await update_secret_provider(
            provider_id=5,
            ctx=mock_ctx,
            name="psono-updated",
        )
        assert update_route.called
        payload = json.loads(update_route.calls.last.request.content)
        assert payload == {"name": "psono-updated"}
        assert updated["name"] == "psono-updated"
        assert updated["config"]["apiKeySecret"] == "***REDACTED***"

        deleted = await delete_secret_provider(provider_id=5, ctx=mock_ctx)
        assert delete_route.called
        assert deleted["success"] is True


@pytest.mark.asyncio
async def test_execute_batch_operation(mock_client):
    import json
    mock_ctx = MockContext(mock_client)
    from dockhand_mcp.tools.misc import execute_batch_operation
    with respx.mock:
        route = respx.post("http://dockhand.test/api/batch?env=1").mock(
            return_value=Response(
                200,
                json={"type": "complete", "summary": {"total": 2, "success": 2, "failed": 0}},
            )
        )
        res = await execute_batch_operation(
            operation="restart",
            entity_type="stacks",
            items=[{"id": "web", "name": "web"}, {"id": "db", "name": "db"}],
            ctx=mock_ctx,
            environment_id=1,
        )
        assert route.called
        payload = json.loads(route.calls.last.request.content)
        assert payload["entityType"] == "stacks"
        assert payload["operation"] == "restart"
        assert res["summary"]["success"] == 2


@pytest.mark.asyncio
async def test_notifications_redact_secrets_and_urls(mock_client):
    mock_ctx = MockContext(mock_client)
    from dockhand_mcp.tools.misc import list_notifications, get_notification
    with respx.mock:
        list_route = respx.get("http://dockhand.test/api/notifications").mock(
            return_value=Response(
                200,
                json=[
                    {
                        "id": 1,
                        "name": "Discord Alert",
                        "type": "discord",
                        "config": {
                            "webhookUrl": "https://discord.com/api/webhooks/111222/secret_webhook_tok",
                            "smtpPassword": "smtp_pw_value",
                        },
                    }
                ],
            )
        )
        get_route = respx.get("http://dockhand.test/api/notifications/1").mock(
            return_value=Response(
                200,
                json={
                    "id": 1,
                    "name": "Apprise Channel",
                    "config": {"urls": ["discord://111222/secret_webhook_tok"]},
                },
            )
        )

        items = await list_notifications(ctx=mock_ctx)
        assert list_route.called
        assert items[0]["config"]["webhookUrl"] == "https://discord.com/api/webhooks/111222/***REDACTED***"
        assert items[0]["config"]["smtpPassword"] == "***REDACTED***"

        single = await get_notification(notification_id=1, ctx=mock_ctx)
        assert get_route.called
        assert single["config"]["urls"] == ["discord://***REDACTED***"]

