import pytest
import respx
from httpx import Response
from dockhand_mcp.client import DockhandClient
from dockhand_mcp.utils import compact_container_inspect
from dockhand_mcp.tools.containers import (
    list_containers,
    get_container,
    inspect_container,
    start_container,
    get_container_logs,
    delete_container,
)
from dockhand_mcp.tools.git_stacks import (
    get_git_stack,
    sync_git_stack,
    sync_and_deploy_git_stack,
    deploy_git_stack,
    delete_git_stack,
)


class MockContext:
    def __init__(self, client: DockhandClient):
        self.request_context = type("RequestContext", (), {"lifespan_context": {"dockhand": client}})()


@pytest.mark.asyncio
async def test_resolve_environment_id_single_env():
    client = DockhandClient(base_url="http://dockhand.test", api_token="secret")
    with respx.mock:
        respx.get("http://dockhand.test/api/environments").mock(
            return_value=Response(200, json=[{"id": 1, "name": "Homelab", "isDefault": False}])
        )
        resolved = await client.resolve_environment_id(None)
        assert resolved == 1
        # Test caching: second call should not re-query
        resolved_cached = await client.resolve_environment_id(None)
        assert resolved_cached == 1

        # Explicit environment_id passes through directly
        assert await client.resolve_environment_id(42) == 42


@pytest.mark.asyncio
async def test_resolve_environment_id_env_var_override(monkeypatch):
    monkeypatch.setenv("DOCKHAND_DEFAULT_ENV", "5")
    client = DockhandClient(base_url="http://dockhand.test", api_token="secret")
    resolved = await client.resolve_environment_id(None)
    assert resolved == 5


@pytest.mark.asyncio
async def test_resolve_environment_id_multiple_envs_disambiguation():
    client = DockhandClient(base_url="http://dockhand.test", api_token="secret")
    with respx.mock:
        respx.get("http://dockhand.test/api/environments").mock(
            return_value=Response(
                200,
                json=[
                    {"id": 1, "name": "Homelab-Primary", "isDefault": False},
                    {"id": 2, "name": "Homelab-Backup", "isDefault": False},
                ],
            )
        )
        with pytest.raises(ValueError) as excinfo:
            await client.resolve_environment_id(None)
        assert "Multiple Dockhand environments found" in str(excinfo.value)
        assert "Homelab-Primary" in str(excinfo.value)
        assert "Homelab-Backup" in str(excinfo.value)


@pytest.mark.asyncio
async def test_resolve_environment_id_marked_default():
    client = DockhandClient(base_url="http://dockhand.test", api_token="secret")
    with respx.mock:
        respx.get("http://dockhand.test/api/environments").mock(
            return_value=Response(
                200,
                json=[
                    {"id": 1, "name": "Dev", "isDefault": False},
                    {"id": 2, "name": "Prod", "isDefault": True},
                ],
            )
        )
        resolved = await client.resolve_environment_id(None)
        assert resolved == 2


@pytest.mark.asyncio
async def test_resolve_git_stack_id():
    client = DockhandClient(base_url="http://dockhand.test", api_token="secret")
    
    # 1. Integer returns as-is
    assert await client.resolve_git_stack_id(33) == 33
    # 2. Numeric string returns as int
    assert await client.resolve_git_stack_id("33") == 33

    # 3. String name resolves via list_git_stacks (GET /api/git/stacks)
    with respx.mock:
        respx.get("http://dockhand.test/api/git/stacks").mock(
            return_value=Response(
                200,
                json=[
                    {"id": 10, "stackName": "sonarr"},
                    {"id": 33, "stackName": "radarr"},
                ],
            )
        )
        resolved = await client.resolve_git_stack_id("radarr")
        assert resolved == 33

        # Case-insensitive check
        resolved_upper = await client.resolve_git_stack_id("RADARR")
        assert resolved_upper == 33

        # Not found raises ValueError
        with pytest.raises(ValueError) as exc:
            await client.resolve_git_stack_id("plex")
        assert "not found" in str(exc.value)
        assert "sonarr" in str(exc.value)


def test_compact_container_inspect():
    raw_payload = {
        "Id": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "Name": "/my-app",
        "Created": "2026-01-01T00:00:00Z",
        "State": {
            "Status": "running",
            "Running": True,
            "Health": {"Status": "healthy"},
            "StartedAt": "2026-01-01T00:01:00Z",
            "OOMKilled": False,
        },
        "Config": {
            "Image": "my-app:v1",
            "Cmd": ["python", "main.py"],
            "Env": [
                "PORT=8080",
                "DB_PASSWORD=secretpass",
                "API_KEY=supersecretkey",
            ],
            "Labels": {"com.docker.compose.project": "my-stack"},
        },
        "NetworkSettings": {
            "Ports": {"8080/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]},
            "Networks": {
                "bridge": {"IPAddress": "172.17.0.2", "Gateway": "172.17.0.1"}
            },
        },
        "Mounts": [
            {
                "Type": "bind",
                "Source": "/host/data",
                "Destination": "/container/data",
                "Mode": "rw",
                "RW": True,
            }
        ],
        "HostConfig": {
            "RestartPolicy": {"Name": "unless-stopped", "MaximumRetryCount": 0},
            "BulkyDriverOptions": {"huge": "payload" * 500},
        },
        "GraphDriver": {"Data": {"Bulky": "LayerData" * 1000}},
    }

    compact = compact_container_inspect(raw_payload)

    assert compact["Id"] == "abcdef123456"
    assert compact["Name"] == "my-app"
    assert compact["State"]["Status"] == "running"
    assert compact["State"]["Health"]["Status"] == "healthy"
    assert "GraphDriver" not in compact
    assert "BulkyDriverOptions" not in compact.get("HostConfig", {})
    assert compact["HostConfig"]["RestartPolicy"]["Name"] == "unless-stopped"

    # Verify secret redaction in Env
    env_str = str(compact["Config"]["Env"])
    assert "supersecretkey" not in env_str
    assert "secretpass" not in env_str
    assert "[REDACTED]" in env_str or "***REDACTED***" in env_str


@pytest.mark.asyncio
async def test_container_tools_auto_resolve_and_compact(monkeypatch):
    monkeypatch.setenv("DOCKHAND_DEFAULT_ENV", "1")
    client = DockhandClient(base_url="http://dockhand.test", api_token="secret")
    ctx = MockContext(client)

    with respx.mock:
        # list_containers with status filter and no explicit environment_id
        respx.get("http://dockhand.test/api/containers?env=1").mock(
            return_value=Response(
                200,
                json=[
                    {"Id": "c111", "Names": ["/c1"], "State": "running", "Status": "Up 2 hours"},
                    {"Id": "c222", "Names": ["/c2"], "State": "exited", "Status": "Exited (0)"},
                ],
            )
        )
        res = await list_containers(status="running", ctx=ctx)
        assert len(res) == 1
        assert res[0]["Id"] == "c111"

        # get_container with compact=True and no environment_id
        respx.get("http://dockhand.test/api/containers/c111?env=1").mock(
            return_value=Response(
                200,
                json={
                    "Id": "c111222333444",
                    "Name": "/c1",
                    "State": {"Status": "running"},
                    "Config": {"Image": "alpine:latest", "Env": ["DEBUG=true"]},
                    "GraphDriver": {"huge": "blob"},
                },
            )
        )
        res_compact = await get_container(container_id="c111", compact=True, ctx=ctx)
        assert res_compact["Id"] == "c11122233344"
        assert "GraphDriver" not in res_compact

        # inspect_container with compact=True
        respx.get("http://dockhand.test/api/containers/c111/inspect?env=1").mock(
            return_value=Response(
                200,
                json={
                    "Id": "c111222333444",
                    "Name": "/c1",
                    "State": {"Status": "running"},
                    "Config": {"Image": "alpine:latest", "Env": ["DEBUG=true"]},
                },
            )
        )
        inspect_res = await inspect_container(container_id="c111", compact=True, ctx=ctx)
        assert inspect_res["Name"] == "c1"

        # start_container without environment_id
        respx.post("http://dockhand.test/api/containers/c111/start?env=1").mock(
            return_value=Response(200, json={"success": True})
        )
        assert await start_container("c111", ctx) == {"success": True}

        # get_container_logs without environment_id
        respx.get("http://dockhand.test/api/containers/c111/logs?env=1&tail=10").mock(
            return_value=Response(200, text="sample log line\n")
        )
        logs = await get_container_logs(container_id="c111", tail=10, ctx=ctx)
        assert "sample log line" in logs

        # delete_container without environment_id
        respx.delete("http://dockhand.test/api/containers/c111?env=1").mock(
            return_value=Response(200, json={"deleted": True})
        )
        assert await delete_container("c111", ctx) == {"deleted": True}


@pytest.mark.asyncio
async def test_git_stacks_name_resolution():
    client = DockhandClient(base_url="http://dockhand.test", api_token="secret")
    ctx = MockContext(client)

    with respx.mock:
        # Mock git-stacks listing for name resolution
        respx.get("http://dockhand.test/api/git/stacks").mock(
            return_value=Response(
                200,
                json=[
                    {
                        "id": 42,
                        "stackName": "radarr",
                        "repository": {"url": "https://github.com/org/radarr", "branch": "main"},
                        "syncStatus": "synced",
                    }
                ],
            )
        )

        # get_git_stack by name
        respx.get("http://dockhand.test/api/git/stacks/42").mock(
            return_value=Response(
                200,
                json={
                    "id": 42,
                    "stackName": "radarr",
                    "repository": {"url": "https://github.com/org/radarr", "branch": "main"},
                    "syncStatus": "synced",
                },
            )
        )
        stack = await get_git_stack(stack_id="radarr", ctx=ctx)
        assert stack["id"] == 42
        assert stack["stackName"] == "radarr"

        # sync_git_stack with deploy=True by name
        respx.post("http://dockhand.test/api/git/stacks/42/sync").mock(
            return_value=Response(200, json={"success": True, "commit": "abc1234"})
        )
        respx.post("http://dockhand.test/api/git/stacks/42/deploy-stream").mock(
            return_value=Response(200, headers={'Content-Type': 'text/event-stream'}, text='data: {"status": "deployed"}\n\n')
        )
        respx.post("http://dockhand.test/api/git/stacks/42/deploy").mock(
            return_value=Response(200, json={"status": "deployed"})
        )
        sync_res = await sync_git_stack(stack_id="radarr", deploy=True, ctx=ctx)
        assert sync_res["sync"]["success"] is True
        assert sync_res["deploy"]["success"] is True

        # deploy_git_stack by name
        deploy_res = await deploy_git_stack(stack_id="radarr", ctx=ctx)
        assert deploy_res["success"] is True

        # delete_git_stack by name
        respx.delete("http://dockhand.test/api/git/stacks/42").mock(
            return_value=Response(200, json={"deleted": True})
        )
        del_res = await delete_git_stack(stack_id="radarr", ctx=ctx)
        assert del_res["deleted"] is True
