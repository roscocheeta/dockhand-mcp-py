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


@pytest.mark.asyncio
async def test_aligned_v1054_misc_routes(mock_client):
    mock_ctx = MockContext(mock_client)
    from dockhand_mcp.tools.misc import (
        list_secret_providers,
        get_secret_provider,
        get_preferences,
        get_sidebar_preferences,
        get_auto_update,
    )
    with respx.mock:
        sp_list_route = respx.get("http://dockhand.test/api/secret-providers").mock(
            return_value=Response(200, json=[{"id": 1, "name": "vault", "config": {"token": "v_tok"}}])
        )
        sp_get_route = respx.get("http://dockhand.test/api/secret-providers/1").mock(
            return_value=Response(200, json={"id": 1, "name": "vault", "config": {"token": "v_tok"}})
        )
        prefs_route = respx.get("http://dockhand.test/api/profile/preferences").mock(
            return_value=Response(200, json={"defaultEnv": 1})
        )
        sidebar_route = respx.get("http://dockhand.test/api/preferences/sidebar").mock(
            return_value=Response(200, json={"collapsed": False})
        )
        au_route = respx.get("http://dockhand.test/api/auto-update/web?env=1").mock(
            return_value=Response(200, json={"enabled": True})
        )

        sps = await list_secret_providers(ctx=mock_ctx)
        assert sp_list_route.called
        assert sps[0]["config"]["token"] == "***REDACTED***"

        sp = await get_secret_provider(provider_id=1, ctx=mock_ctx)
        assert sp_get_route.called
        assert sp["config"]["token"] == "***REDACTED***"

        prefs = await get_preferences(ctx=mock_ctx)
        assert prefs_route.called
        assert prefs["defaultEnv"] == 1

        sb = await get_sidebar_preferences(ctx=mock_ctx)
        assert sidebar_route.called
        assert sb["collapsed"] is False

        au = await get_auto_update(environment_id=1, container_id="web", ctx=mock_ctx)
        assert au_route.called
        assert au["enabled"] is True


@pytest.mark.asyncio
async def test_remaining_misc_tools(mock_client):
    mock_ctx = MockContext(mock_client)
    from dockhand_mcp.tools.misc import (
        create_notification,
        list_schedules,
        list_templates,
        list_labels,
        set_preferences,
        list_config_sets,
        set_auto_update,
        get_theme_settings,
        update_theme_settings,
        set_grid_preferences,
    )
    with respx.mock:
        respx.post("http://dockhand.test/api/notifications").mock(
            return_value=Response(
                200,
                json={"id": 2, "url": "https://hooks.slack.com/services/T1/B1/sec_tok"},
            )
        )
        respx.get("http://dockhand.test/api/schedules").mock(
            return_value=Response(200, json=[{"id": 1, "name": "Daily"}])
        )
        respx.get("http://dockhand.test/api/templates").mock(
            return_value=Response(200, json=[{"name": "wordpress"}])
        )
        respx.get("http://dockhand.test/api/labels?env=1").mock(
            return_value=Response(200, json=["env=prod"])
        )
        respx.put("http://dockhand.test/api/profile/preferences").mock(
            return_value=Response(200, json={"saved": True})
        )
        respx.get("http://dockhand.test/api/config-sets").mock(
            return_value=Response(200, json=[{"id": 1, "name": "common"}])
        )
        respx.put("http://dockhand.test/api/auto-update/web?env=1").mock(
            return_value=Response(200, json={"enabled": False})
        )
        respx.get("http://dockhand.test/api/users/preferences/theme").mock(
            return_value=Response(200, json={"theme": "dark"})
        )
        respx.put("http://dockhand.test/api/users/preferences/theme").mock(
            return_value=Response(200, json={"theme": "light"})
        )
        respx.put("http://dockhand.test/api/preferences/grid").mock(
            return_value=Response(200, json={"columns": 4})
        )

        notif = await create_notification("Slack", "https://hooks.slack.com/services/T1/B1/sec_tok", mock_ctx)
        assert notif["url"] == "https://hooks.slack.com/services/T1/B1/***REDACTED***"
        assert (await list_schedules(mock_ctx))[0]["name"] == "Daily"
        assert (await list_templates(mock_ctx))[0]["name"] == "wordpress"
        assert (await list_labels(1, mock_ctx)) == ["env=prod"]
        assert (await set_preferences({"defaultEnv": 1}, mock_ctx))["saved"] is True
        assert (await list_config_sets(mock_ctx))[0]["name"] == "common"
        assert (await set_auto_update(1, "web", False, mock_ctx))["enabled"] is False
        assert (await get_theme_settings(mock_ctx))["theme"] == "dark"
        assert (await update_theme_settings("light", mock_ctx))["theme"] == "light"
        assert (await set_grid_preferences({"columns": 4}, mock_ctx))["columns"] == 4

@pytest.mark.asyncio
async def test_language_preference(mock_client):
    from dockhand_mcp.tools.misc import get_language_preference, set_language_preference
    import json
    mock_ctx = MockContext(mock_client)

    with respx.mock:
        get_route = respx.get("http://dockhand.test/api/preferences/language").mock(
            return_value=Response(200, json={"language": "en"})
        )
        put_route = respx.put("http://dockhand.test/api/preferences/language").mock(
            return_value=Response(200, json={"language": "fr-FR"})
        )

        res = await get_language_preference(mock_ctx)
        assert get_route.called
        assert res["language"] == "en"

        updated = await set_language_preference(mock_ctx, language="fr-FR")
        assert put_route.called
        payload = json.loads(put_route.calls.last.request.content)
        assert payload["language"] == "fr-FR"
        assert updated["language"] == "fr-FR"

        # Setting to None follows browser language
        respx.put("http://dockhand.test/api/preferences/language").mock(
            return_value=Response(200, json={"language": None})
        )
        reset = await set_language_preference(mock_ctx, language=None)
        assert reset["language"] is None


@pytest.mark.asyncio
async def test_pinned_digest_report(mock_client):
    from dockhand_mcp.tools.misc import get_pinned_digest_report, set_pinned_digest_report
    import json
    mock_ctx = MockContext(mock_client)

    with respx.mock:
        get_route = respx.get("http://dockhand.test/api/settings/pinned-digest-report").mock(
            return_value=Response(200, json={"enabled": True})
        )
        post_route = respx.post("http://dockhand.test/api/settings/pinned-digest-report").mock(
            return_value=Response(200, json={"success": True})
        )

        res = await get_pinned_digest_report(mock_ctx)
        assert get_route.called
        assert res["enabled"] is True

        updated = await set_pinned_digest_report(False, mock_ctx)
        assert post_route.called
        payload = json.loads(post_route.calls.last.request.content)
        assert payload["enabled"] is False
        assert updated["success"] is True


@pytest.mark.asyncio
async def test_sops_secret_provider_and_redaction(mock_client):
    from dockhand_mcp.tools.misc import create_secret_provider, update_secret_provider
    mock_ctx = MockContext(mock_client)

    with respx.mock:
        create_route = respx.post("http://dockhand.test/api/secret-providers").mock(
            return_value=Response(
                200,
                json={
                    "id": 10,
                    "name": "SOPS Production",
                    "type": "sops",
                    "config": {
                        "ageKey": "AGE-SECRET-KEY-1QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ"
                    },
                },
            )
        )
        update_route = respx.put("http://dockhand.test/api/secret-providers/10").mock(
            return_value=Response(
                200,
                json={
                    "id": 10,
                    "name": "SOPS Production Updated",
                    "type": "sops",
                    "config": {
                        "ageKey": "AGE-SECRET-KEY-2WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW"
                    },
                },
            )
        )

        created = await create_secret_provider(
            name="SOPS Production",
            type="sops",
            config={"ageKey": "AGE-SECRET-KEY-1..."},
            ctx=mock_ctx,
        )
        assert create_route.called
        assert created["id"] == 10
        assert created["type"] == "sops"
        assert created["config"]["ageKey"] == "***REDACTED***"

        updated = await update_secret_provider(
            10,
            mock_ctx,
            name="SOPS Production Updated",
            type="sops",
            config={"ageKey": "AGE-SECRET-KEY-2..."},
        )
        assert update_route.called
        assert updated["name"] == "SOPS Production Updated"
        assert updated["config"]["ageKey"] == "***REDACTED***"


@pytest.mark.asyncio
async def test_execute_batch_operation_string_normalization(mock_client):
    import json
    mock_ctx = MockContext(mock_client)
    from dockhand_mcp.tools.misc import execute_batch_operation

    with respx.mock:
        route = respx.post("http://dockhand.test/api/batch?env=1").mock(
            return_value=Response(200, json={"jobId": "job-123"})
        )

        # 1. Containers with string IDs/names
        await execute_batch_operation(
            operation="start",
            entity_type="containers",
            items=["radarr", "sonarr"],
            ctx=mock_ctx,
            environment_id=1,
        )
        sent = json.loads(route.calls.last.request.content)
        assert sent["items"] == [{"id": "radarr"}, {"id": "sonarr"}]

        # 2. Stacks with string names
        await execute_batch_operation(
            operation="restart",
            entity_type="stacks",
            items=["bazarr", "tautulli"],
            ctx=mock_ctx,
            environment_id=1,
        )
        sent = json.loads(route.calls.last.request.content)
        assert sent["items"] == [{"name": "bazarr"}, {"name": "tautulli"}]

        # 3. Volumes with string names
        await execute_batch_operation(
            operation="remove",
            entity_type="volumes",
            items=["vol1"],
            ctx=mock_ctx,
            environment_id=1,
        )
        sent = json.loads(route.calls.last.request.content)
        assert sent["items"] == [{"name": "vol1"}]

        # 4. Invalid item type raises ValueError
        with pytest.raises(ValueError, match="Invalid batch item"):
            await execute_batch_operation(
                operation="remove",
                entity_type="containers",
                items=[12345],
                ctx=mock_ctx,
                environment_id=1,
            )
