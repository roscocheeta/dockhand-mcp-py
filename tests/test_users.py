import pytest
import respx
from httpx import Response
from dockhand_mcp.tools.users import (
    list_users,
    get_user,
    create_user,
    update_user,
    delete_user,
    list_tokens,
    create_token,
    delete_token,
    list_passkeys,
    delete_passkey,
)


class MockContext:
    def __init__(self, client):
        class LifespanContext:
            def __init__(self, client):
                self.lifespan_context = {"dockhand": client}
        self.request_context = LifespanContext(client)


@pytest.mark.asyncio
async def test_users_and_tokens(mock_client):
    mock_ctx = MockContext(mock_client)
    with respx.mock:
        respx.get("http://dockhand.test/api/users").mock(
            return_value=Response(200, json=[{"id": 1, "username": "admin", "role": "admin"}])
        )
        respx.get("http://dockhand.test/api/users/1").mock(
            return_value=Response(200, json={"id": 1, "username": "admin", "role": "admin"})
        )
        respx.post("http://dockhand.test/api/users").mock(
            return_value=Response(200, json={"id": 2, "username": "alice"})
        )
        respx.put("http://dockhand.test/api/users/2").mock(
            return_value=Response(200, json={"success": True})
        )
        respx.delete("http://dockhand.test/api/users/2").mock(
            return_value=Response(200, json={"success": True})
        )
        respx.get("http://dockhand.test/api/auth/tokens").mock(
            return_value=Response(200, json=[{"id": 10, "name": "ci"}])
        )
        respx.post("http://dockhand.test/api/auth/tokens").mock(
            return_value=Response(200, json={"id": 11, "token": "secret"})
        )
        respx.delete("http://dockhand.test/api/auth/tokens/11").mock(
            return_value=Response(200, json={"success": True})
        )

        users = await list_users(ctx=mock_ctx)
        assert users[0]["Username"] == "admin"

        u = await get_user(user_id=1, ctx=mock_ctx)
        assert u["Id"] == 1

        c = await create_user(username="alice", password="pw", ctx=mock_ctx)
        assert c["id"] == 2

        up = await update_user(user_id=2, ctx=mock_ctx, role="admin")
        assert up["success"] is True

        dl = await delete_user(user_id=2, ctx=mock_ctx)
        assert dl["success"] is True

        toks = await list_tokens(ctx=mock_ctx)
        assert toks[0]["Name"] == "ci"

        ct = await create_token(name="ci2", ctx=mock_ctx)
        assert ct["id"] == 11

        dt = await delete_token(token_id=11, ctx=mock_ctx)
        assert dt["success"] is True


@pytest.mark.asyncio
async def test_passkeys(mock_client):
    mock_ctx = MockContext(mock_client)
    with respx.mock:
        list_route = respx.get("http://dockhand.test/api/profile/passkeys").mock(
            return_value=Response(
                200,
                json={"enabled": True, "passkeys": [{"id": 1, "name": "YubiKey", "deviceType": "multiDevice"}]},
            )
        )
        del_route = respx.delete("http://dockhand.test/api/profile/passkeys/1").mock(
            return_value=Response(200, json={"success": True})
        )

        pks = await list_passkeys(ctx=mock_ctx)
        assert list_route.called
        assert pks["enabled"] is True
        assert pks["passkeys"][0]["name"] == "YubiKey"

        deleted = await delete_passkey(passkey_id=1, ctx=mock_ctx)
        assert del_route.called
        assert deleted["success"] is True


@pytest.mark.asyncio
async def test_users_and_tokens_non_list_fallbacks(mock_client):
    mock_ctx = MockContext(mock_client)
    with respx.mock:
        respx.get("http://dockhand.test/api/users").mock(
            return_value=Response(200, json={"unexpected": True})
        )
        respx.get("http://dockhand.test/api/auth/tokens").mock(
            return_value=Response(200, json={"unexpected": True})
        )
        assert await list_users(ctx=mock_ctx) == {"unexpected": True}
        assert await list_tokens(ctx=mock_ctx) == {"unexpected": True}
