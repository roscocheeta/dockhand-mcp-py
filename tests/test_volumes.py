import pytest
import respx
from httpx import Response
from dockhand_mcp.tools.volumes import create_volume

class MockContext:
    def __init__(self, client):
        class LifespanContext:
            def __init__(self, client):
                self.lifespan_context = {"dockhand": client}
        self.request_context = LifespanContext(client)

@pytest.mark.asyncio
async def test_create_volume_basic(mock_client):
    mock_ctx = MockContext(mock_client)
    
    with respx.mock:
        route = respx.post("http://dockhand.test/api/volumes?env=1").mock(
            return_value=Response(200, json={"success": True, "name": "my-vol"})
        )
        
        result = await create_volume(
            environment_id=1,
            name="my-vol",
            ctx=mock_ctx
        )
        
        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload["name"] == "my-vol"
        assert payload["driver"] == "local"
        assert "driverOpts" not in payload
        assert "labels" not in payload
        assert result["success"] is True

@pytest.mark.asyncio
async def test_create_volume_full(mock_client):
    mock_ctx = MockContext(mock_client)
    
    with respx.mock:
        route = respx.post("http://dockhand.test/api/volumes?env=2").mock(
            return_value=Response(200, json={"success": True})
        )
        
        result = await create_volume(
            environment_id=2,
            name="nfs-vol",
            ctx=mock_ctx,
            driver="local",
            driver_opts={"type": "nfs", "device": ":/data/shared", "o": "addr=192.168.1.100,rw"},
            labels={"app": "file-server"}
        )
        
        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload["name"] == "nfs-vol"
        assert payload["driver"] == "local"
        assert payload["driverOpts"] == {"type": "nfs", "device": ":/data/shared", "o": "addr=192.168.1.100,rw"}
        assert payload["labels"] == {"app": "file-server"}
        assert result["success"] is True


@pytest.mark.asyncio
async def test_list_get_inspect_delete_volume(mock_client):
    from dockhand_mcp.tools.volumes import list_volumes, get_volume, inspect_volume, delete_volume
    mock_ctx = MockContext(mock_client)
    with respx.mock:
        list_route = respx.get("http://dockhand.test/api/volumes?env=1").mock(
            return_value=Response(
                200,
                json={"Volumes": [{"Name": "vol1", "Driver": "local", "Mountpoint": "/var/lib/docker/volumes/vol1", "Extra": 1}]},
            )
        )
        list_flat_route = respx.get("http://dockhand.test/api/volumes?env=2").mock(
            return_value=Response(
                200,
                json=[{"name": "vol2", "driver": "local", "mountpoint": "/mnt/vol2"}],
            )
        )
        get_route = respx.get("http://dockhand.test/api/volumes/vol1?env=1").mock(
            return_value=Response(200, json={"Name": "vol1", "Driver": "local", "Options": None})
        )
        del_route = respx.delete("http://dockhand.test/api/volumes/vol1?env=1").mock(
            return_value=Response(200, json={"deleted": True})
        )

        vols = await list_volumes(environment_id=1, ctx=mock_ctx)
        assert list_route.called
        assert vols["Volumes"] == [{"Name": "vol1", "Driver": "local", "Mountpoint": "/var/lib/docker/volumes/vol1"}]

        vols_flat = await list_volumes(environment_id=2, ctx=mock_ctx)
        assert list_flat_route.called
        assert vols_flat == [{"Name": "vol2", "Driver": "local", "Mountpoint": "/mnt/vol2"}]

        v = await get_volume(environment_id=1, volume_name="vol1", ctx=mock_ctx)
        assert get_route.called
        assert v == {"Name": "vol1", "Driver": "local"}

        insp = await inspect_volume(environment_id=1, volume_name="vol1", ctx=mock_ctx)
        assert insp == {"Name": "vol1", "Driver": "local"}

        deleted = await delete_volume(environment_id=1, volume_name="vol1", ctx=mock_ctx)
        assert del_route.called
        assert deleted["deleted"] is True


@pytest.mark.asyncio
async def test_list_volumes_search_and_pagination(mock_client):
    from dockhand_mcp.tools.volumes import list_volumes
    mock_ctx = MockContext(mock_client)
    vols_payload = {
        "Volumes": [
            {"Name": f"data-{i}", "Driver": "local", "Mountpoint": f"/mnt/{i}"}
            for i in reversed(range(4))
        ]
    }
    with respx.mock:
        respx.get("http://dockhand.test/api/volumes?env=1").mock(
            return_value=Response(200, json=vols_payload)
        )
        res = await list_volumes(environment_id=1, ctx=mock_ctx, search="data-*", limit=2, offset=0)
        assert res["total"] == 4
        assert res["hasMore"] is True
        assert [v["Name"] for v in res["items"]] == ["data-0", "data-1"]

        respx.get("http://dockhand.test/api/volumes?env=2").mock(
            return_value=Response(
                200,
                json=[{"Name": f"flat-{i}", "Driver": "local", "Mountpoint": f"/flat/{i}"} for i in range(3)],
            )
        )
        res_flat = await list_volumes(environment_id=2, ctx=mock_ctx, search="flat-*", limit=2, offset=1)
        assert res_flat["total"] == 3
        assert res_flat["hasMore"] is False
        assert [v["Name"] for v in res_flat["items"]] == ["flat-1", "flat-2"]

        respx.get("http://dockhand.test/api/volumes?env=3").mock(
            return_value=Response(200, json={"Volumes": None})
        )
        res_null = await list_volumes(environment_id=3, ctx=mock_ctx, limit=10, offset=0)
        assert res_null == {"items": [], "total": 0, "limit": 10, "offset": 0, "hasMore": False}

