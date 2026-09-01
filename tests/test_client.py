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
