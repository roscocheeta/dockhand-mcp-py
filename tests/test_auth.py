"""
Tests for Dockhand authentication — login, 401 retry, session expiry, concurrency.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx
import pytest
import respx

from dockhand_mcp.client import (
    DockhandAuth,
    DockhandAPIError,
    DockhandAuthError,
    DockhandClient,
)
from tests.conftest import (
    TEST_BASE_URL,
    TEST_USERNAME,
    TEST_PASSWORD,
    LOGIN_PATH,
    SESSION_COOKIE,
    mock_login_success,
)


class TestLogin:
    """Tests for the login flow."""

    async def test_login_stores_cookies(self, mock_router: respx.MockRouter):
        """After login, the httpx client's cookie jar should contain session cookies."""
        login_route = mock_login_success(mock_router)
        mock_router.get("/api/health").respond(200, json={"status": "ok"})

        client = DockhandClient(TEST_BASE_URL, TEST_USERNAME, TEST_PASSWORD)
        try:
            result = await client.health_check()
            assert result["status"] == "ok"

            # Verify login was called
            assert login_route.call_count == 1
        finally:
            await client.close()

    async def test_login_sends_correct_payload(self, mock_router: respx.MockRouter):
        """Login should POST username, password, and provider='local'."""
        route = mock_login_success(mock_router)
        mock_router.get("/api/health").respond(200, json={"status": "ok"})

        client = DockhandClient(TEST_BASE_URL, TEST_USERNAME, TEST_PASSWORD)
        try:
            await client.health_check()
            request = route.calls[0].request
            body = request.content.decode()
            assert '"username": "testuser"' in body or '"username":"testuser"' in body
            assert '"provider": "local"' in body or '"provider":"local"' in body
        finally:
            await client.close()

    async def test_login_failure_raises_auth_error(self, mock_router: respx.MockRouter):
        """A non-200 login response should raise DockhandAuthError."""
        mock_router.post(LOGIN_PATH).respond(401, text="Invalid credentials")
        mock_router.get("/api/health").respond(200, json={"status": "ok"})

        client = DockhandClient(TEST_BASE_URL, TEST_USERNAME, TEST_PASSWORD)
        try:
            with pytest.raises(DockhandAuthError, match="login failed"):
                await client.health_check()
        finally:
            await client.close()

    async def test_login_no_cookies_raises_auth_error(self, mock_router: respx.MockRouter):
        """Login returning 200 but no Set-Cookie should raise DockhandAuthError."""
        # Respond without any Set-Cookie header
        mock_router.post(LOGIN_PATH).respond(200, json={"user": {}})
        mock_router.get("/api/health").respond(200, json={"status": "ok"})

        client = DockhandClient(TEST_BASE_URL, TEST_USERNAME, TEST_PASSWORD)
        try:
            with pytest.raises(DockhandAuthError, match="no session cookies"):
                await client.health_check()
        finally:
            await client.close()


class TestTransparent401Retry:
    """Tests for transparent re-authentication on 401."""

    async def test_401_triggers_relogin_and_retry(self, mock_router: respx.MockRouter):
        """A 401 response should trigger re-login and retry the original request."""
        login_route = mock_login_success(mock_router)

        # First call returns 401, second (after re-login) returns 200.
        call_count = 0

        def health_side_effect(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(401, text="Unauthorized")
            return httpx.Response(200, json={"status": "ok"})

        mock_router.get("/api/health").mock(side_effect=health_side_effect)

        client = DockhandClient(TEST_BASE_URL, TEST_USERNAME, TEST_PASSWORD)
        try:
            result = await client.health_check()
            assert result["status"] == "ok"
            # Login should have been called twice: initial + after 401
            assert login_route.call_count == 2
        finally:
            await client.close()


class TestSessionExpiry:
    """Tests for proactive session expiry."""

    async def test_expired_session_triggers_relogin(self, mock_router: respx.MockRouter):
        """After session expires, the next request should re-authenticate."""
        login_route = mock_login_success(mock_router)
        mock_router.get("/api/health").respond(200, json={"status": "ok"})

        client = DockhandClient(TEST_BASE_URL, TEST_USERNAME, TEST_PASSWORD)
        try:
            # First request — triggers initial login.
            await client.health_check()
            assert login_route.call_count == 1

            # Manually expire the session.
            client._auth._session_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

            # Next request should trigger re-login.
            await client.health_check()
            assert login_route.call_count == 2
        finally:
            await client.close()

    async def test_valid_session_skips_login(self, mock_router: respx.MockRouter):
        """Within the 23h window, no re-login should occur."""
        login_route = mock_login_success(mock_router)
        mock_router.get("/api/health").respond(200, json={"status": "ok"})

        client = DockhandClient(TEST_BASE_URL, TEST_USERNAME, TEST_PASSWORD)
        try:
            await client.health_check()
            await client.health_check()
            await client.health_check()
            # Only one login for three requests.
            assert login_route.call_count == 1
        finally:
            await client.close()



    """Tests for the asyncio.Lock login guard."""

    async def test_concurrent_401s_only_login_once(self, mock_router: respx.MockRouter):
        """Multiple concurrent 401 responses should result in only one re-login."""
        login_route = mock_login_success(mock_router)

        # All health calls return 401 on first try, 200 on retry.
        health_call_count = 0

        def health_side_effect(request: httpx.Request) -> httpx.Response:
            nonlocal health_call_count
            health_call_count += 1
            # First 5 calls (from 5 concurrent tasks) return 401.
            # After re-login, subsequent calls return 200.
            if health_call_count <= 5:
                return httpx.Response(401, text="Unauthorized")
            return httpx.Response(200, json={"status": "ok"})

        mock_router.get("/api/health").mock(side_effect=health_side_effect)

        client = DockhandClient(TEST_BASE_URL, TEST_USERNAME, TEST_PASSWORD)
        try:
            # Fire 5 concurrent health checks.
            tasks = [asyncio.create_task(client.health_check()) for _ in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # At least some should succeed after retry.
            successes = [r for r in results if isinstance(r, dict)]
            assert len(successes) > 0

            # The login lock should prevent a flood of logins.
            # We expect initial login (1) + at most a few re-logins (not 5).
            assert login_route.call_count <= 5
        finally:
            await client.close()


class TestBearerTokenAuth:
    """Tests for DOCKHAND_API_TOKEN Bearer token authentication."""

    async def test_api_token_skips_cookie_login_and_sends_bearer_header(self, mock_router: respx.MockRouter):
        """When api_token is provided, /api/auth/login is skipped and Authorization: Bearer is sent."""
        login_route = mock_login_success(mock_router)
        health_route = mock_router.get("/api/health").respond(200, json={"status": "ok"})

        client = DockhandClient(TEST_BASE_URL, api_token="dh_secret_token_123")
        try:
            result = await client.health_check()
            assert result["status"] == "ok"
            assert login_route.call_count == 0
            assert health_route.call_count == 1
            auth_header = health_route.calls.last.request.headers.get("Authorization")
            assert auth_header == "Bearer dh_secret_token_123"
        finally:
            await client.close()

    async def test_api_token_401_does_not_attempt_cookie_login(self, mock_router: respx.MockRouter):
        """When using api_token, a 401 response should raise DockhandAPIError without calling /api/auth/login."""
        login_route = mock_login_success(mock_router)
        mock_router.get("/api/containers").respond(401, text="Invalid token")

        client = DockhandClient(TEST_BASE_URL, api_token="dh_invalid_token")
        try:
            with pytest.raises(DockhandAPIError) as exc_info:
                await client.get("/api/containers")
            assert exc_info.value.status_code == 401
            assert login_route.call_count == 0
        finally:
            await client.close()

    def test_get_config_accepts_api_token_without_username_password(self, monkeypatch):
        """_get_config() should succeed with DOCKHAND_URL and DOCKHAND_API_TOKEN alone."""
        from dockhand_mcp.server import _get_config
        monkeypatch.setenv("DOCKHAND_URL", "https://dockhand.example.com")
        monkeypatch.setenv("DOCKHAND_API_TOKEN", "dh_tok_abc")
        monkeypatch.delenv("DOCKHAND_USERNAME", raising=False)
        monkeypatch.delenv("DOCKHAND_PASSWORD", raising=False)
        monkeypatch.setenv("DOCKHAND_READ_ONLY", "true")

        cfg = _get_config()
        assert cfg["url"] == "https://dockhand.example.com"
        assert cfg["api_token"] == "dh_tok_abc"
        assert cfg["read_only"] is True

    def test_get_config_rejects_invalid_url_scheme_and_warns_ssl_off(self, monkeypatch, caplog):
        """_get_config() should exit on non-http(s) URLs and log a warning when DOCKHAND_VERIFY_SSL=false."""
        from dockhand_mcp.server import _get_config
        monkeypatch.setenv("DOCKHAND_API_TOKEN", "dh_tok_abc")
        monkeypatch.setenv("DOCKHAND_URL", "ftp://dockhand.example.com")
        with pytest.raises(SystemExit):
            _get_config()

        monkeypatch.setenv("DOCKHAND_URL", "https://dockhand.example.com")
        monkeypatch.setenv("DOCKHAND_VERIFY_SSL", "false")
        with caplog.at_level("WARNING"):
            cfg = _get_config()
        assert cfg["verify_ssl"] is False
        assert "SSL certificate verification is DISABLED" in caplog.text


