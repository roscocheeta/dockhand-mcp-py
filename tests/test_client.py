"""
Tests for DockhandClient HTTP methods, error handling, and path encoding.
"""

import pytest
import respx
import httpx

from dockhand_mcp.client import DockhandClient, DockhandAPIError
from dockhand_mcp.utils import encode_path
from tests.conftest import (
    TEST_BASE_URL,
    TEST_USERNAME,
    TEST_PASSWORD,
    LOGIN_PATH,
    SESSION_COOKIE,
    mock_login_success,
)


class TestGenericHTTPMethods:
    """Tests for get/post/put/delete methods."""

    async def test_get_returns_json(self, mock_client: DockhandClient, mock_router: respx.MockRouter):
        """GET should return parsed JSON."""
        mock_router.get("/api/containers").respond(
            200, json=[{"id": "abc", "name": "nginx"}]
        )
        result = await mock_client.get("/api/containers")
        assert isinstance(result, list)
        assert result[0]["id"] == "abc"

    async def test_get_passes_query_params(self, mock_client: DockhandClient, mock_router: respx.MockRouter):
        """GET should forward query parameters."""
        route = mock_router.get("/api/containers").respond(200, json=[])
        await mock_client.get("/api/containers", params={"env": 1, "all": "true"})

        request = route.calls[0].request
        assert "env=1" in str(request.url)
        assert "all=true" in str(request.url)

    async def test_get_filters_none_params(self, mock_client: DockhandClient, mock_router: respx.MockRouter):
        """GET should filter out None-valued params."""
        route = mock_router.get("/api/containers").respond(200, json=[])
        await mock_client.get("/api/containers", params={"env": 1, "filter": None})

        request = route.calls[0].request
        assert "env=1" in str(request.url)
        assert "filter" not in str(request.url)

    async def test_post_sends_json_body(self, mock_client: DockhandClient, mock_router: respx.MockRouter):
        """POST should send a JSON body."""
        route = mock_router.post("/api/stacks").respond(200, json={"name": "mystack"})
        await mock_client.post("/api/stacks", json={"name": "mystack", "compose": "..."})

        request = route.calls[0].request
        assert b"mystack" in request.content

    async def test_put_sends_json_body(self, mock_client: DockhandClient, mock_router: respx.MockRouter):
        """PUT should send a JSON body."""
        route = mock_router.put("/api/stacks/mystack").respond(200, json={"updated": True})
        await mock_client.put("/api/stacks/mystack", json={"compose": "new"})

        request = route.calls[0].request
        assert b"new" in request.content

    async def test_delete_with_body(self, mock_client: DockhandClient, mock_router: respx.MockRouter):
        """DELETE should support an optional JSON body (some Dockhand endpoints need this)."""
        route = mock_router.delete("/api/users/1/roles").respond(200, json={"ok": True})
        await mock_client.delete("/api/users/1/roles", json={"role": "viewer"})

        request = route.calls[0].request
        assert b"viewer" in request.content


class TestErrorHandling:
    """Tests for API error handling."""

    async def test_404_raises_api_error(self, mock_client: DockhandClient, mock_router: respx.MockRouter):
        """A 404 response should raise DockhandAPIError."""
        mock_router.get("/api/containers/nonexistent").respond(404, text="Not found")

        with pytest.raises(DockhandAPIError) as exc_info:
            await mock_client.get("/api/containers/nonexistent")

        assert exc_info.value.status_code == 404
        assert "Not found" in exc_info.value.detail

    async def test_500_raises_api_error(self, mock_client: DockhandClient, mock_router: respx.MockRouter):
        """A 500 response should raise DockhandAPIError."""
        mock_router.get("/api/health").respond(500, text="Internal server error")

        with pytest.raises(DockhandAPIError) as exc_info:
            await mock_client.get("/api/health")

        assert exc_info.value.status_code == 500

    async def test_api_error_includes_method_and_path(self, mock_client: DockhandClient, mock_router: respx.MockRouter):
        """DockhandAPIError should include the HTTP method and path."""
        mock_router.delete("/api/containers/abc").respond(409, text="Conflict")

        with pytest.raises(DockhandAPIError) as exc_info:
            await mock_client.delete("/api/containers/abc")

        assert exc_info.value.method == "DELETE"
        assert "/api/containers/abc" in exc_info.value.path

    async def test_plain_text_response(self, mock_client: DockhandClient, mock_router: respx.MockRouter):
        """Non-JSON responses should be returned as plain text."""
        mock_router.get("/api/changelog").respond(
            200, text="# Changelog\n- v1.0", headers={"Content-Type": "text/plain"}
        )
        result = await mock_client.get("/api/changelog")
        assert "Changelog" in result


class TestClientLifecycle:
    """Tests for client creation and cleanup."""

    async def test_close_releases_client(self, mock_router: respx.MockRouter):
        """Calling close() should release the httpx client."""
        client = DockhandClient(TEST_BASE_URL, TEST_USERNAME, TEST_PASSWORD)
        await client.close()
        # After close, the internal client should be closed.
        assert client._client.is_closed

    async def test_context_manager(self, mock_router: respx.MockRouter):
        """DockhandClient should support async context manager."""
        async with DockhandClient(TEST_BASE_URL, TEST_USERNAME, TEST_PASSWORD) as client:
            assert not client._client.is_closed
        # After exiting context, client should be closed.
        assert client._client.is_closed


class TestPathEncoding:
    """Tests for URL path encoding utility."""

    def test_encode_plain_string(self):
        assert encode_path("abc123") == "abc123"

    def test_encode_slashes(self):
        assert encode_path("my/container") == "my%2Fcontainer"

    def test_encode_spaces(self):
        assert encode_path("my container") == "my%20container"

    def test_encode_special_chars(self):
        result = encode_path("stack+name@v2")
        assert "+" not in result or "%2B" in result
        assert "@" not in result or "%40" in result


class TestSSEParsing:
    """Tests for Server-Sent Events parsing in _parse_sse_response."""

    def test_parse_sse_success_with_output(self):
        resp = httpx.Response(
            200, 
            text='data: {"output": "pulling image..."}\n\ndata: {"output": "done"}\n\ndata: {"success": true}\n',
            headers={"Content-Type": "text/event-stream"}
        )
        result = DockhandClient._parse_sse_response(resp)
        assert result["success"] is True
        assert result["output"] == "pulling image...\ndone"

    def test_parse_sse_error(self):
        resp = httpx.Response(
            200, 
            text='data: {"output": "starting..."}\n\ndata: {"error": "port 80 already in use"}\n\ndata: {"success": false}\n',
            headers={"Content-Type": "text/event-stream"}
        )
        result = DockhandClient._parse_sse_response(resp)
        assert result["success"] is False
        assert "port 80 already in use" in result["output"]

    def test_parse_sse_invalid_json(self):
        resp = httpx.Response(
            200, 
            text='data: plain text line 1\n\ndata: plain text line 2\n',
            headers={"Content-Type": "text/event-stream"}
        )
        result = DockhandClient._parse_sse_response(resp)
        assert result["success"] is True
        assert "plain text line 1" in result["output"]
        assert "plain text line 2" in result["output"]


class TestReadOnlyAndToolAnnotations:
    """Tests for DOCKHAND_READ_ONLY enforcement and MCP ToolAnnotations."""

    async def test_read_only_mode_allows_get_and_blocks_mutating_methods(self, mock_router: respx.MockRouter):
        """Read-only client should allow login + GET, but reject POST/PUT/DELETE/SSE with 403."""
        mock_login_success(mock_router)
        get_route = mock_router.get("/api/containers").respond(200, json=[{"id": "123"}])
        post_route = mock_router.post("/api/containers").respond(200, json={})

        client = DockhandClient(TEST_BASE_URL, TEST_USERNAME, TEST_PASSWORD, read_only=True)
        try:
            res = await client.get("/api/containers")
            assert res == [{"id": "123"}]
            assert get_route.called

            for coro in (
                client.post("/api/containers", json={}),
                client.put("/api/stacks/web/compose", json={}),
                client.delete("/api/containers/123"),
                client.post_sse("/api/stacks/web/deploy", json={}),
                client.put_sse("/api/stacks/web/compose", json={}),
            ):
                with pytest.raises(DockhandAPIError) as exc_info:
                    await coro
                assert exc_info.value.status_code == 403
                assert "DOCKHAND_READ_ONLY" in exc_info.value.detail

            assert not post_route.called
        finally:
            await client.close()

    def test_register_all_tools_annotations_and_read_only_filtering(self):
        """Verify MCP ToolAnnotations on all tools and tool filtering when read_only=True."""
        from mcp.server.fastmcp import FastMCP
        from dockhand_mcp.tools import register_all_tools, is_read_only_tool

        full_mcp = FastMCP("test-full")
        register_all_tools(full_mcp, read_only=False)
        full_tools = full_mcp._tool_manager._tools
        assert len(full_tools) >= 170

        # Verify annotations on representative tools
        assert full_tools["list_containers"].annotations.readOnlyHint is True
        assert full_tools["list_containers"].annotations.destructiveHint is False

        assert full_tools["start_container"].annotations.readOnlyHint is False
        assert full_tools["start_container"].annotations.destructiveHint is False

        assert full_tools["delete_container"].annotations.readOnlyHint is False
        assert full_tools["delete_container"].annotations.destructiveHint is True

        assert full_tools["run_container_exec"].annotations.readOnlyHint is False
        assert full_tools["run_container_exec"].annotations.destructiveHint is True

        # Verify read_only=True only registers read-only tools
        ro_mcp = FastMCP("test-ro")
        register_all_tools(ro_mcp, read_only=True)
        ro_tools = ro_mcp._tool_manager._tools
        assert len(ro_tools) > 0
        assert len(ro_tools) < len(full_tools)
        assert "list_containers" in ro_tools
        assert "get_stack_env" in ro_tools
        assert "delete_container" not in ro_tools
        assert "run_container_exec" not in ro_tools
        assert "create_stack" not in ro_tools
        assert all(is_read_only_tool(name) for name in ro_tools)

