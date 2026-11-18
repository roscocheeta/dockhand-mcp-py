import pytest
import respx
from httpx import Response
from dockhand_mcp.tools.networks import create_network

class MockContext:
    def __init__(self, client):
        class LifespanContext:
            def __init__(self, client):
                self.lifespan_context = {"dockhand": client}
        self.request_context = LifespanContext(client)

@pytest.mark.asyncio
async def test_create_network_basic(mock_client):
    mock_ctx = MockContext(mock_client)
    
    with respx.mock:
        route = respx.post("http://dockhand.test/api/networks?env=1").mock(
            return_value=Response(200, json={"success": True, "name": "my-net"})
        )
        
        result = await create_network(
            environment_id=1,
            name="my-net",
            ctx=mock_ctx
        )
        
        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload["name"] == "my-net"
        assert payload["driver"] == "bridge"
        assert payload["internal"] is False
        assert payload["attachable"] is False
        assert result["success"] is True

@pytest.mark.asyncio
async def test_create_network_full(mock_client):
    mock_ctx = MockContext(mock_client)
    
    with respx.mock:
        route = respx.post("http://dockhand.test/api/networks?env=2").mock(
            return_value=Response(200, json={"success": True})
        )
        
        result = await create_network(
            environment_id=2,
            name="my-custom-net",
            ctx=mock_ctx,
            driver="overlay",
            options={"encrypted": "true"},
            labels={"app": "db"},
            ipam={"driver": "default", "config": [{"subnet": "10.0.0.0/24"}]},
            internal=True,
            attachable=True
        )
        
        assert route.called
        import json
        payload = json.loads(route.calls.last.request.content)
        assert payload["name"] == "my-custom-net"
        assert payload["driver"] == "overlay"
        assert payload["options"] == {"encrypted": "true"}
        assert payload["labels"] == {"app": "db"}
        assert payload["ipam"] == {"driver": "default", "config": [{"subnet": "10.0.0.0/24"}]}
        assert payload["internal"] is True
        assert payload["attachable"] is True


@pytest.mark.asyncio
async def test_list_get_inspect_delete_network(mock_client):
    from dockhand_mcp.tools.networks import list_networks, get_network, inspect_network, delete_network
    mock_ctx = MockContext(mock_client)
    with respx.mock:
        list_route = respx.get("http://dockhand.test/api/networks?env=1").mock(
            return_value=Response(
                200,
                json=[{"Id": "abcdef1234567890", "Name": "bridge", "Driver": "bridge", "Scope": "local", "Extra": "val"}],
            )
        )
        get_route = respx.get("http://dockhand.test/api/networks/net1?env=1").mock(
            return_value=Response(200, json={"Id": "net1", "Name": "bridge", "NullField": None})
        )
        del_route = respx.delete("http://dockhand.test/api/networks/net1?env=1").mock(
            return_value=Response(200, json={"deleted": True})
        )

        nets = await list_networks(environment_id=1, ctx=mock_ctx)
        assert list_route.called
        assert nets[0] == {"Id": "abcdef123456", "Name": "bridge", "Driver": "bridge", "Scope": "local"}

        net = await get_network(environment_id=1, network_id="net1", ctx=mock_ctx)
        assert get_route.called
        assert net == {"Id": "net1", "Name": "bridge"}

        insp = await inspect_network(environment_id=1, network_id="net1", ctx=mock_ctx)
        assert insp == {"Id": "net1", "Name": "bridge"}

        deleted = await delete_network(environment_id=1, network_id="net1", ctx=mock_ctx)
        assert del_route.called
        assert deleted["deleted"] is True


@pytest.mark.asyncio
async def test_list_networks_search_and_pagination(mock_client):
    from dockhand_mcp.tools.networks import list_networks
    mock_ctx = MockContext(mock_client)
    nets_payload = [
        {"Id": f"n{i:012d}tail{i}", "Name": f"net-{i}", "Driver": "bridge", "Scope": "local"}
        for i in reversed(range(4))
    ]
    with respx.mock:
        respx.get("http://dockhand.test/api/networks?env=1").mock(
            return_value=Response(200, json=nets_payload)
        )
        res = await list_networks(environment_id=1, ctx=mock_ctx, search="net-*", limit=2, offset=2)
        assert res["total"] == 4
        assert res["hasMore"] is False
        assert [n["Name"] for n in res["items"]] == ["net-2", "net-3"]

        # Raw full-ID search (beyond 12-char truncation)
        res_raw_id = await list_networks(environment_id=1, ctx=mock_ctx, search="*tail1", limit=5, offset=0)
        assert res_raw_id["total"] == 1
        assert res_raw_id["items"][0]["Name"] == "net-1"

