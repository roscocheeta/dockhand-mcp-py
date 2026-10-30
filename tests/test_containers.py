import pytest
import respx
from httpx import Response
from dockhand_mcp.client import DockhandClient
from mcp.server.fastmcp import Context

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
async def test_list_containers(mock_client, mock_ctx):
    from dockhand_mcp.tools.containers import list_containers
    
    # Dockhand returns lowercase keys natively
    mock_data = [
        {
            "id": "8bf78fa4451123a39f73c62a9bab2516290e9a967cf807357f1092e68d87d108",
            "name": "newrelic-logging",
            "image": "newrelic/newrelic-fluentbit-output:latest",
            "state": "running",
            "status": "Up 13 hours",
            "HostConfig": {"Memory": 1024} # This should be stripped
        }
    ]
    
    with respx.mock:
        route = respx.get("http://dockhand.test/api/containers?env=1").mock(return_value=Response(200, json=mock_data))
        
        result = await list_containers(environment_id=1, ctx=mock_ctx)
        
        # Verify the API was hit correctly
        assert route.called
        
        # Verify token efficiency logic worked
        assert len(result) == 1
        assert result[0]["Id"] == "8bf78fa44511" # Truncated
        assert result[0]["Name"] == "newrelic-logging"
        assert "HostConfig" not in result[0] # Stripped

@pytest.mark.asyncio
async def test_start_container(mock_client, mock_ctx):
    from dockhand_mcp.tools.containers import start_container
    
    with respx.mock:
        route = respx.post("http://dockhand.test/api/containers/my-container/start?env=1").mock(
            return_value=Response(204) # Usually empty 204 response
        )
        
        result = await start_container(environment_id=1, container_id="my-container", ctx=mock_ctx)
        
        assert route.called
        assert result is None or result == "" # 204 no content

@pytest.mark.asyncio
async def test_write_container_file_content(mock_client, mock_ctx):
    from dockhand_mcp.tools.containers import write_container_file_content
    with respx.mock:
        route = respx.put("http://dockhand.test/api/containers/my-container/files/content?env=1&path=/tmp/test.txt").mock(
            return_value=Response(200, json={"success": True})
        )
        result = await write_container_file_content(1, "my-container", "/tmp/test.txt", "hello", mock_ctx)
        assert route.called
        assert result["success"] is True

@pytest.mark.asyncio
async def test_delete_container_file(mock_client, mock_ctx):
    from dockhand_mcp.tools.containers import delete_container_file
    with respx.mock:
        route = respx.delete("http://dockhand.test/api/containers/my-container/files?env=1&path=/tmp/test.txt").mock(
            return_value=Response(204)
        )
        result = await delete_container_file(1, "my-container", "/tmp/test.txt", mock_ctx)
        assert route.called


@pytest.mark.asyncio
async def test_create_container(mock_client, mock_ctx):
    from dockhand_mcp.tools.containers import create_container
    with respx.mock:
        route = respx.post('http://dockhand.test/api/containers?env=1').mock(
            return_value=Response(200, json={'success': True})
        )
        
        result = await create_container(
            environment_id=1,
            name='test-web',
            image='nginx:alpine',
            ctx=mock_ctx,
            start_after_create=True,
            env=['FOO=BAR'],
            ports={'80/tcp': [{'HostPort': '8080'}]},
            volumes=['/data:/data'],
            restart_policy='unless-stopped',
            network_mode='bridge',
            labels={'app': 'web'}
        )
        
        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload['name'] == 'test-web'
        assert payload['image'] == 'nginx:alpine'
        assert payload['startAfterCreate'] is True
        assert payload['Env'] == ['FOO=BAR']
        assert payload['Labels'] == {'app': 'web'}
        assert payload['HostConfig']['RestartPolicy'] == {'Name': 'unless-stopped'}
        assert payload['HostConfig']['PortBindings'] == {'80/tcp': [{'HostPort': '8080'}]}
        assert payload['HostConfig']['Binds'] == ['/data:/data']
        assert payload['HostConfig']['NetworkMode'] == 'bridge'
        assert result['success'] is True


@pytest.mark.asyncio
async def test_run_container_exec(mock_client, mock_ctx):
    from dockhand_mcp.tools.containers import run_container_exec
    with respx.mock:
        route = respx.post('http://dockhand.test/api/containers/123/exec/run').mock(
            return_value=Response(200, json={'stdout': 'hello\\n', 'stderr': '', 'exitCode': 0})
        )
        result = await run_container_exec(environment_id=1, container_id='123', cmd=['echo', 'hello'], ctx=mock_ctx)
        assert route.called
        assert result['stdout'] == 'hello\\n'

@pytest.mark.asyncio
async def test_upload_container_file(mock_client, mock_ctx):
    from dockhand_mcp.tools.containers import upload_container_file
    import base64
    with respx.mock:
        route = respx.post('http://dockhand.test/api/containers/123/files/upload').mock(
            return_value=Response(200, json={'success': True})
        )
        b64 = base64.b64encode(b'test').decode()
        result = await upload_container_file(
            environment_id=1, 
            container_id='123', 
            directory='/app', 
            filename='test.txt',
            base64_content=b64, 
            owner='1000:1000', 
            ctx=mock_ctx
        )
        assert route.called
        assert result['success'] is True



@pytest.mark.asyncio
async def test_create_container_path(mock_client, mock_ctx):
    from dockhand_mcp.tools.containers import create_container_path
    with respx.mock:
        route = respx.post('http://dockhand.test/api/containers/123/files/create').mock(
            return_value=Response(200, json={'success': True, 'path': '/app/data', 'type': 'directory', 'owner': '1000:1000'})
        )
        result = await create_container_path(
            environment_id=1, 
            container_id='123', 
            path='/app/data', 
            type='directory',
            owner='1000:1000', 
            ctx=mock_ctx
        )
        assert route.called
        assert result['success'] is True

@pytest.mark.asyncio
async def test_chown_container_file(mock_client, mock_ctx):
    from dockhand_mcp.tools.containers import chown_container_file
    with respx.mock:
        route = respx.post('http://dockhand.test/api/containers/123/files/chown').mock(
            return_value=Response(200, json={'success': True})
        )
        result = await chown_container_file(
            environment_id=1, 
            container_id='123', 
            path='/app/data', 
            owner='1000:1000',
            recursive=True, 
            ctx=mock_ctx
        )
        assert route.called
        assert result['success'] is True


@pytest.mark.asyncio
async def test_list_containers_v1054_labels_and_health(mock_client, mock_ctx):
    from dockhand_mcp.tools.containers import list_containers
    mock_data = [
        {
            "id": "8bf78fa4451123a39f73c62a9bab2516290e9a967cf807357f1092e68d87d108",
            "name": "web-1",
            "image": "nginx:latest",
            "state": "running",
            "status": "Up 2 hours (healthy)",
            "health": "healthy",
            "labels": {
                "dockhand.tags": "prod,frontend",
                "dockhand.name": "Production Web",
            },
        }
    ]
    with respx.mock:
        route = respx.get("http://dockhand.test/api/containers?env=1").mock(
            return_value=Response(200, json=mock_data)
        )
        result = await list_containers(environment_id=1, ctx=mock_ctx)
        assert route.called
        assert result[0]["Health"] == "healthy"
        assert result[0]["Tags"] == "prod,frontend"
        assert result[0]["DisplayName"] == "Production Web"


@pytest.mark.asyncio
async def test_update_container_repull_and_start(mock_client, mock_ctx):
    import json
    from dockhand_mcp.tools.containers import update_container
    with respx.mock:
        route = respx.post("http://dockhand.test/api/containers/123/update?env=1").mock(
            return_value=Response(200, json={"success": True, "id": "456", "warnings": []})
        )
        result = await update_container(
            environment_id=1,
            container_id="123",
            ctx=mock_ctx,
            image="nginx:latest",
            name="web",
            repull_image=True,
            start_after_update=True,
        )
        assert route.called
        payload = json.loads(route.calls.last.request.content)
        assert payload["repullImage"] is True
        assert payload["startAfterUpdate"] is True
        assert payload["name"] == "web"
        assert result["success"] is True


@pytest.mark.asyncio
async def test_container_compose_and_updates(mock_client, mock_ctx):
    from dockhand_mcp.tools.containers import (
        get_container_compose,
        check_container_updates,
        get_pending_container_updates,
    )
    with respx.mock:
        compose_route = respx.get("http://dockhand.test/api/containers/123/compose?env=1").mock(
            return_value=Response(
                200,
                json={
                    "compose": "services:\n  web:\n    image: nginx\n    environment:\n      - DB_PASSWORD=secret_db_pw\n      - APP_ENV=prod\n",
                    "composeFullEnv": "services:\n  web:\n    environment:\n      API_TOKEN: super_secret_token\n",
                    "serviceName": "web",
                },
            )
        )
        check_route = respx.post("http://dockhand.test/api/containers/check-updates?env=1").mock(
            return_value=Response(
                200,
                text='data: {"total": 2, "updatesFound": 1, "results": []}\n',
                headers={"Content-Type": "text/event-stream"},
            )
        )
        pending_route = respx.get("http://dockhand.test/api/containers/pending-updates?env=1").mock(
            return_value=Response(
                200,
                json={
                    "environmentId": 1,
                    "minimumReleaseAgeHours": 24,
                    "pendingUpdates": [
                        {"containerId": "123", "hasImageUpdate": False, "pinnedToDigest": True}
                    ],
                },
            )
        )

        comp = await get_container_compose(environment_id=1, container_id="123", ctx=mock_ctx)
        assert compose_route.called
        assert comp["serviceName"] == "web"
        assert "DB_PASSWORD=***REDACTED***" in comp["compose"]
        assert "APP_ENV=prod" in comp["compose"]
        assert "secret_db_pw" not in comp["compose"]
        assert "API_TOKEN: ***REDACTED***" in comp["composeFullEnv"]
        assert "super_secret_token" not in comp["composeFullEnv"]

        chk = await check_container_updates(environment_id=1, ctx=mock_ctx)
        assert check_route.called
        assert chk["success"] is True

        pend = await get_pending_container_updates(environment_id=1, ctx=mock_ctx)
        assert pending_route.called
        assert pend["minimumReleaseAgeHours"] == 24
        assert pend["pendingUpdates"][0]["pinnedToDigest"] is True


@pytest.mark.asyncio
async def test_run_container_exec_truncates_output(mock_client, mock_ctx):
    from dockhand_mcp.tools.containers import run_container_exec
    with respx.mock:
        route = respx.post("http://dockhand.test/api/containers/123/exec/run?envId=1").mock(
            return_value=Response(
                200,
                json={"stdout": "A" * 500, "stderr": "B" * 500, "exitCode": 0},
            )
        )
        res = await run_container_exec(
            environment_id=1,
            container_id="123",
            cmd=["ls"],
            ctx=mock_ctx,
            max_bytes=100,
        )
        assert route.called
        assert res["truncated"] is True
        assert res["stdout"].startswith("A" * 100)
        assert "[TRUNCATED AT 100 BYTES]" in res["stdout"]
        assert res["stderr"].startswith("B" * 100)
        assert "[TRUNCATED AT 100 BYTES]" in res["stderr"]


@pytest.mark.asyncio
async def test_container_inspect_logs_stats_top_files_and_lifecycle(mock_client, mock_ctx):
    from dockhand_mcp.tools.containers import (
        get_container,
        inspect_container,
        get_container_logs,
        get_container_stats,
        get_container_top,
        list_container_files,
        get_container_file_content,
        rename_container_file,
        stop_container,
        restart_container,
        pause_container,
        unpause_container,
        delete_container,
        rename_container,
        exec_container,
    )
    inspect_payload = {
        "Id": "abcdef1234567890",
        "Image": "sha256:999888777666555",
        "Config": {
            "Env": ["APP_ENV=prod", "DB_PASSWORD=super_secret_db_pw"],
            "Labels": {"com.docker.compose.project": "myproj", "custom": "kept"},
        },
    }
    with respx.mock:
        respx.get("http://dockhand.test/api/containers/c1?env=1").mock(
            return_value=Response(200, json=inspect_payload)
        )
        respx.get("http://dockhand.test/api/containers/c1/inspect?env=1").mock(
            return_value=Response(200, json=inspect_payload)
        )
        logs_route = respx.get("http://dockhand.test/api/containers/c1/logs?env=1&tail=500").mock(
            return_value=Response(200, text="line1\nline2", headers={"Content-Type": "text/plain"})
        )
        respx.get("http://dockhand.test/api/containers/c1/stats?env=1").mock(
            return_value=Response(200, json={"cpuPercent": 12.5})
        )
        respx.get("http://dockhand.test/api/containers/c1/top?env=1").mock(
            return_value=Response(200, json={"Processes": [["root", "1", "nginx"]]})
        )
        respx.get("http://dockhand.test/api/containers/c1/files?env=1&path=%2Fetc").mock(
            return_value=Response(200, json=[{"name": "nginx.conf"}])
        )
        respx.get("http://dockhand.test/api/containers/c1/files/content?env=1&path=%2Fetc%2Fbig.txt").mock(
            return_value=Response(200, text="Z" * 500, headers={"Content-Type": "text/plain"})
        )
        respx.post("http://dockhand.test/api/containers/c1/files/rename?env=1").mock(
            return_value=Response(200, json={"renamed": True})
        )
        respx.post("http://dockhand.test/api/containers/c1/stop?env=1").mock(
            return_value=Response(200, json={"stopped": True})
        )
        respx.post("http://dockhand.test/api/containers/c1/restart?env=1").mock(
            return_value=Response(200, json={"restarted": True})
        )
        respx.post("http://dockhand.test/api/containers/c1/pause?env=1").mock(
            return_value=Response(200, json={"paused": True})
        )
        respx.post("http://dockhand.test/api/containers/c1/unpause?env=1").mock(
            return_value=Response(200, json={"unpaused": True})
        )
        respx.delete("http://dockhand.test/api/containers/c1?env=1&force=true").mock(
            return_value=Response(200, json={"deleted": True})
        )
        respx.post("http://dockhand.test/api/containers/c1/rename?env=1").mock(
            return_value=Response(200, json={"renamed": True})
        )
        respx.post("http://dockhand.test/api/containers/c1/exec?envId=1").mock(
            return_value=Response(200, json={"execId": "ex1"})
        )

        c_get = await get_container(1, "c1", mock_ctx)
        assert c_get["Id"] == "abcdef123456"
        assert "DB_PASSWORD=***REDACTED***" in c_get["Config"]["Env"]
        assert "super_secret_db_pw" not in str(c_get)

        c_insp = await inspect_container(1, "c1", mock_ctx)
        assert c_insp["Config"]["Labels"] == {"custom": "kept"}

        # Tail > 500 should be capped to 500
        logs = await get_container_logs(1, "c1", mock_ctx, tail=9999)
        assert logs_route.called
        assert "line1" in logs

        stats = await get_container_stats(1, "c1", mock_ctx)
        assert stats["cpuPercent"] == 12.5

        top = await get_container_top(1, "c1", mock_ctx)
        assert top["Processes"][0][2] == "nginx"

        files = await list_container_files(1, "c1", mock_ctx, path="/etc")
        assert files[0]["name"] == "nginx.conf"

        content = await get_container_file_content(1, "c1", "/etc/big.txt", mock_ctx, max_bytes=100)
        assert content.startswith("Z" * 100)
        assert "[...truncated at 100 bytes" in content

        assert (await rename_container_file(1, "c1", "/a", "/b", mock_ctx))["renamed"] is True
        assert (await stop_container(1, "c1", mock_ctx))["stopped"] is True
        assert (await restart_container(1, "c1", mock_ctx))["restarted"] is True
        assert (await pause_container(1, "c1", mock_ctx))["paused"] is True
        assert (await unpause_container(1, "c1", mock_ctx))["unpaused"] is True
        assert (await delete_container(1, "c1", mock_ctx, force=True))["deleted"] is True
        assert (await rename_container(1, "c1", "c2", mock_ctx))["renamed"] is True
        assert (await exec_container(1, "c1", mock_ctx, shell="sh", user="root"))["execId"] == "ex1"

@pytest.mark.asyncio
async def test_container_scheduled_actions(mock_client, mock_ctx):
    from dockhand_mcp.tools.containers import (
        get_container_scheduled_actions,
        set_container_scheduled_actions,
    )
    import json

    with respx.mock:
        get_route = respx.get("http://dockhand.test/api/scheduled-actions/web-app?env=1").mock(
            return_value=Response(
                200,
                json={
                    "startAt": "07:00",
                    "stopAt": "23:00",
                    "enabled": True,
                    "source": "ui",
                    "labelErrors": [],
                    "systemContainer": False,
                    "lastStarted": None,
                    "lastStopped": None,
                },
            )
        )
        put_route = respx.put("http://dockhand.test/api/scheduled-actions/web-app?env=1").mock(
            return_value=Response(
                200,
                json={
                    "startAt": "08:00",
                    "stopAt": "20:00",
                    "enabled": True,
                    "source": "ui",
                    "labelErrors": [],
                    "systemContainer": False,
                    "lastStarted": None,
                    "lastStopped": None,
                },
            )
        )

        schedule = await get_container_scheduled_actions(1, "web-app", mock_ctx)
        assert get_route.called
        assert schedule["startAt"] == "07:00"
        assert schedule["stopAt"] == "23:00"
        assert schedule["enabled"] is True

        updated = await set_container_scheduled_actions(
            1, "web-app", mock_ctx, start_at="08:00", stop_at="20:00", enabled=True
        )
        assert put_route.called
        payload = json.loads(put_route.calls.last.request.content)
        assert payload["startAt"] == "08:00"
        assert payload["stopAt"] == "20:00"
        assert payload["enabled"] is True
        assert updated["startAt"] == "08:00"

        # Test clear schedule without enabled flag
        respx.put("http://dockhand.test/api/scheduled-actions/db-app?env=1").mock(
            return_value=Response(
                200,
                json={
                    "startAt": None,
                    "stopAt": None,
                    "enabled": True,
                    "source": "ui",
                    "labelErrors": [],
                    "systemContainer": False,
                    "lastStarted": None,
                    "lastStopped": None,
                },
            )
        )
        cleared = await set_container_scheduled_actions(1, "db-app", mock_ctx, start_at=None, stop_at=None)
        assert cleared["startAt"] is None


@pytest.mark.asyncio
async def test_run_container_exec_string_and_list(mock_client, mock_ctx):
    import json
    from dockhand_mcp.tools.containers import run_container_exec

    with respx.mock:
        route = respx.post("http://dockhand.test/api/containers/c1/exec/run?envId=1").mock(
            return_value=Response(200, json={"stdout": "ok", "stderr": "", "exitCode": 0})
        )

        # Test string cmd -> wraps with /bin/sh -c
        res_str = await run_container_exec(
            environment_id=1,
            container_id="c1",
            cmd="ps aux | grep nginx",
            ctx=mock_ctx,
        )
        assert route.called
        sent_body = json.loads(route.calls.last.request.content)
        assert sent_body["cmd"] == ["/bin/sh", "-c", "ps aux | grep nginx"]
        assert res_str["stdout"] == "ok"

        # Test list cmd -> sent as-is
        res_list = await run_container_exec(
            environment_id=1,
            container_id="c1",
            cmd=["python3", "app.py"],
            ctx=mock_ctx,
        )
        sent_body = json.loads(route.calls.last.request.content)
        assert sent_body["cmd"] == ["python3", "app.py"]

        # Test invalid cmd type
        with pytest.raises(ValueError, match="cmd must be a string or a list of strings"):
            await run_container_exec(
                environment_id=1,
                container_id="c1",
                cmd=123,
                ctx=mock_ctx,
            )


@pytest.mark.asyncio
async def test_get_container_logs_timestamps_and_since(mock_client, mock_ctx):
    import json
    from dockhand_mcp.tools.containers import get_container_logs

    with respx.mock:
        # Test logs returning JSON dict {"logs": "..."}
        route = respx.get(respx.patterns.M("http://dockhand.test/api/containers/c1/logs")).mock(
            return_value=Response(200, json={"logs": "2026-10-31T00:00:00Z line1\nline2\n"})
        )

        logs = await get_container_logs(
            environment_id=1,
            container_id="c1",
            ctx=mock_ctx,
            timestamps=True,
            since="1h",
        )
        assert route.called
        req_params = dict(route.calls.last.request.url.params)
        assert req_params["timestamps"] == "true"
        assert req_params["since"].isdigit()
        assert int(req_params["since"]) > 0
        # Returned string directly, not dict
        assert isinstance(logs, str)
        assert "line1" in logs
