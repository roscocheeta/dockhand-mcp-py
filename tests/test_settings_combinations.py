import os
import pytest
import respx
from httpx import Response
from mcp.server.fastmcp import FastMCP
from dockhand_mcp.client import DockhandClient, DockhandAPIError, DockhandAuthError
from dockhand_mcp.server import _get_config, lifespan, mcp as server_mcp
from dockhand_mcp.tools import register_all_tools, is_read_only_tool, is_destructive_tool


class MockRequestContext:
    def __init__(self, client):
        self.lifespan_context = {"dockhand": client}


class MockContext:
    def __init__(self, client):
        self.request_context = MockRequestContext(client)


class TestConfigCombinations:
    """Tests all combinations of environment variables for _get_config()."""

    def test_missing_dockhand_url(self, monkeypatch):
        monkeypatch.delenv("DOCKHAND_URL", raising=False)
        monkeypatch.setenv("DOCKHAND_API_TOKEN", "dh_token_123")
        with pytest.raises(SystemExit):
            _get_config()

    def test_invalid_url_schemes(self, monkeypatch):
        for bad_url in ("ftp://localhost:3866", "javascript:alert(1)", "file:///etc/passwd", "http://", "ws://localhost"):
            monkeypatch.setenv("DOCKHAND_URL", bad_url)
            monkeypatch.setenv("DOCKHAND_API_TOKEN", "dh_token_123")
            with pytest.raises(SystemExit):
                _get_config()

    def test_valid_http_and_https_urls(self, monkeypatch):
        for good_url in ("http://localhost:3866", "https://dockhand.example.com", "http://192.168.1.100:3866/"):
            monkeypatch.setenv("DOCKHAND_URL", good_url)
            monkeypatch.setenv("DOCKHAND_API_TOKEN", "dh_tok")
            cfg = _get_config()
            assert cfg["url"] == good_url.strip()

    def test_api_token_auth_alone(self, monkeypatch):
        monkeypatch.setenv("DOCKHAND_URL", "http://dockhand.test")
        monkeypatch.setenv("DOCKHAND_API_TOKEN", "dh_tok_abc")
        monkeypatch.delenv("DOCKHAND_USERNAME", raising=False)
        monkeypatch.delenv("DOCKHAND_PASSWORD", raising=False)

        cfg = _get_config()
        assert cfg["api_token"] == "dh_tok_abc"
        assert cfg["username"] == ""
        assert cfg["password"] == ""

    def test_username_password_auth_alone(self, monkeypatch):
        monkeypatch.setenv("DOCKHAND_URL", "http://dockhand.test")
        monkeypatch.delenv("DOCKHAND_API_TOKEN", raising=False)
        monkeypatch.setenv("DOCKHAND_USERNAME", "admin")
        monkeypatch.setenv("DOCKHAND_PASSWORD", "secret")

        cfg = _get_config()
        assert cfg["api_token"] == ""
        assert cfg["username"] == "admin"
        assert cfg["password"] == "secret"

    def test_missing_username_or_password(self, monkeypatch):
        monkeypatch.setenv("DOCKHAND_URL", "http://dockhand.test")
        monkeypatch.delenv("DOCKHAND_API_TOKEN", raising=False)

        # Missing password
        monkeypatch.setenv("DOCKHAND_USERNAME", "admin")
        monkeypatch.delenv("DOCKHAND_PASSWORD", raising=False)
        with pytest.raises(SystemExit):
            _get_config()

        # Missing username
        monkeypatch.delenv("DOCKHAND_USERNAME", raising=False)
        monkeypatch.setenv("DOCKHAND_PASSWORD", "secret")
        with pytest.raises(SystemExit):
            _get_config()

    def test_both_token_and_user_pass_set(self, monkeypatch):
        monkeypatch.setenv("DOCKHAND_URL", "http://dockhand.test")
        monkeypatch.setenv("DOCKHAND_API_TOKEN", "dh_token_preferred")
        monkeypatch.setenv("DOCKHAND_USERNAME", "admin")
        monkeypatch.setenv("DOCKHAND_PASSWORD", "secret")

        cfg = _get_config()
        assert cfg["api_token"] == "dh_token_preferred"
        assert cfg["username"] == "admin"
        assert cfg["password"] == "secret"

    def test_read_only_truthy_and_falsy_values(self, monkeypatch):
        monkeypatch.setenv("DOCKHAND_URL", "http://dockhand.test")
        monkeypatch.setenv("DOCKHAND_API_TOKEN", "dh_tok")

        for val in ("true", "1", "yes", "True", "TRUE"):
            monkeypatch.setenv("DOCKHAND_READ_ONLY", val)
            assert _get_config()["read_only"] is True

        for val in ("false", "0", "no", "False", "", "random"):
            monkeypatch.setenv("DOCKHAND_READ_ONLY", val)
            assert _get_config()["read_only"] is False

        monkeypatch.delenv("DOCKHAND_READ_ONLY", raising=False)
        assert _get_config()["read_only"] is False

    def test_verify_ssl_truthy_and_falsy_values(self, monkeypatch, caplog):
        monkeypatch.setenv("DOCKHAND_URL", "https://dockhand.test")
        monkeypatch.setenv("DOCKHAND_API_TOKEN", "dh_tok")

        for val in ("true", "1", "yes", "True", ""):
            monkeypatch.setenv("DOCKHAND_VERIFY_SSL", val)
            assert _get_config()["verify_ssl"] is True

        for val in ("false", "0", "no", "FALSE"):
            monkeypatch.setenv("DOCKHAND_VERIFY_SSL", val)
            with caplog.at_level("WARNING"):
                assert _get_config()["verify_ssl"] is False
            assert "SSL certificate verification is DISABLED" in caplog.text


class TestReadOnlyModeEndToEnd:
    """Verifies DOCKHAND_READ_ONLY across both client and tool registration layers."""

    @pytest.mark.asyncio
    async def test_client_blocks_all_mutating_verbs(self):
        client = DockhandClient(
            base_url="http://dockhand.test",
            api_token="dh_test_token",
            read_only=True,
        )
        try:
            # All mutating verbs must raise 403 before any network request
            for coro in (
                client.post("/api/containers", json={}),
                client.put("/api/stacks/web/compose", json={}),
                client.delete("/api/volumes/vol1"),
                client.post_sse("/api/stacks/web/deploy", json={}),
                client.put_sse("/api/stacks/web/compose", json={}),
            ):
                with pytest.raises(DockhandAPIError) as exc_info:
                    await coro
                assert exc_info.value.status_code == 403
                assert "DOCKHAND_READ_ONLY" in exc_info.value.detail
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_client_read_only_with_cookie_auth(self):
        """Cookie authentication should still be able to POST to /api/auth/login even when read_only=True."""
        with respx.mock(base_url="http://dockhand.test") as router:
            router.post("/api/auth/login").respond(
                200,
                json={"user": {"username": "admin"}},
                headers={"Set-Cookie": "session=abc; Path=/"},
            )
            router.get("/api/containers").respond(200, json=[{"id": "c1"}])

            client = DockhandClient(
                base_url="http://dockhand.test",
                username="admin",
                password="password",
                read_only=True,
            )
            try:
                # GET should trigger login and succeed
                containers = await client.get("/api/containers")
                assert containers == [{"id": "c1"}]

                # But mutating calls through the client must be blocked
                with pytest.raises(DockhandAPIError) as exc_info:
                    await client.post("/api/containers", json={})
                assert exc_info.value.status_code == 403
            finally:
                await client.close()

    def test_registration_layer_filtering(self):
        """Verify that read_only=True registers ONLY read-only tools."""
        ro_mcp = FastMCP("test-ro")
        register_all_tools(ro_mcp, read_only=True)
        tools = ro_mcp._tool_manager._tools

        assert len(tools) > 0
        for name, tool in tools.items():
            assert is_read_only_tool(name), f"Tool {name} should be read-only but is not!"
            assert tool.annotations.readOnlyHint is True
            assert tool.annotations.destructiveHint is False

        # Ensure no destructive or mutating tools leaked in
        assert "create_container" not in tools
        assert "delete_container" not in tools
        assert "run_container_exec" not in tools
        assert "deploy_stack" not in tools
        assert "prune_all" not in tools

    def test_registration_layer_full_mode(self):
        """Verify that read_only=False registers all tools with correct annotations."""
        full_mcp = FastMCP("test-full")
        register_all_tools(full_mcp, read_only=False)
        tools = full_mcp._tool_manager._tools

        assert len(tools) >= 170
        for name, tool in tools.items():
            if is_read_only_tool(name):
                assert tool.annotations.readOnlyHint is True
                assert tool.annotations.destructiveHint is False
            elif is_destructive_tool(name):
                assert tool.annotations.readOnlyHint is False
                assert tool.annotations.destructiveHint is True
            else:
                assert tool.annotations.readOnlyHint is False
                assert tool.annotations.destructiveHint is False
