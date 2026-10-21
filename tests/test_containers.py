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
            return_value=Response(200, json={"compose": "services:\n  web:\n    image: nginx\n", "serviceName": "web"})
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

        chk = await check_container_updates(environment_id=1, ctx=mock_ctx)
        assert check_route.called
        assert chk["success"] is True

        pend = await get_pending_container_updates(environment_id=1, ctx=mock_ctx)
        assert pending_route.called
        assert pend["minimumReleaseAgeHours"] == 24
        assert pend["pendingUpdates"][0]["pinnedToDigest"] is True
