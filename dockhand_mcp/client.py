"""
Dockhand API client with session-based cookie authentication.

Handles:
- Login via POST /api/auth/login with cookie jar
- Proactive session refresh (23h window, Dockhand sessions last 24h)
- Concurrent login guard via asyncio.Lock
- Transparent 401 retry
- Generic get/post/put/delete with JSON parsing
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class DockhandAuthError(Exception):
    """Raised when authentication with Dockhand fails."""


class DockhandAPIError(Exception):
    """Raised when a Dockhand API call returns a non-2xx status."""

    def __init__(self, status_code: int, detail: str, method: str = "", path: str = ""):
        self.status_code = status_code
        self.detail = detail
        self.method = method
        self.path = path
        super().__init__(f"HTTP {status_code} on {method} {path}: {detail}")


class DockhandAuth:
    """
    Manages Dockhand session lifecycle.

    - Uses httpx's built-in cookie jar (not manual Set-Cookie parsing).
    - Tracks a 23-hour expiry window for proactive session refresh.
    - Uses asyncio.Lock to prevent concurrent login storms.
    """

    SESSION_TIMEOUT = timedelta(hours=23)

    def __init__(self, base_url: str, username: str, password: str):
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._login_lock = asyncio.Lock()
        self._session_expires_at: Optional[datetime] = None
        self.session_version = 0

    def _is_valid(self) -> bool:
        """Check if the current session is still within the expiry window."""
        if self._session_expires_at is None:
            return False
        return datetime.now(timezone.utc) < self._session_expires_at

    async def ensure_authenticated(self, client: httpx.AsyncClient) -> None:
        """Re-authenticate if expired or not yet logged in."""
        if self._is_valid():
            return

        async with self._login_lock:
            if self._is_valid():
                return
            await self._login(client)

    async def invalidate_and_retry(self, client: httpx.AsyncClient, failed_version: int) -> None:
        """
        Called when a request receives a 401. Invalidates the current session
        and forces a re-login, but ONLY if the session hasn't already been
        refreshed by another concurrent request.
        """
        async with self._login_lock:
            if self.session_version == failed_version:
                self._session_expires_at = None
                await self._login(client)

    async def _login(self, client: httpx.AsyncClient) -> None:
        """
        Perform the actual login request.

        Uses the SAME httpx.AsyncClient as the main client so that:
        - TLS settings (verify, cert) are shared
        - Timeouts are shared
        - Cookies are stored in the client's cookie jar automatically
        """
        login_url = f"{self._base_url}/api/auth/login"
        payload = {
            "username": self._username,
            "password": self._password,
            "provider": "local",
        }

        logger.info("Authenticating with Dockhand as %s", self._username)

        try:
            resp = await client.post(login_url, json=payload)
        except httpx.RequestError as exc:
            raise DockhandAuthError(
                f"Failed to connect to Dockhand at {self._base_url}: {exc}"
            ) from exc

        if resp.status_code != 200:
            detail = resp.text[:500] if resp.text else resp.reason_phrase
            raise DockhandAuthError(
                f"Dockhand login failed (HTTP {resp.status_code}): {detail}"
            )

        # httpx automatically stores Set-Cookie headers in client.cookies.
        # Verify that at least one cookie was set.
        if not client.cookies:
            raise DockhandAuthError(
                "Dockhand login succeeded but no session cookies were returned. "
                f"Response: {resp.text[:200]}"
            )

        self._session_expires_at = datetime.now(timezone.utc) + self.SESSION_TIMEOUT
        self.session_version += 1
        logger.info("Authenticated with Dockhand (session valid for ~23h)")


class DockhandClient:
    """
    Async HTTP client for the Dockhand REST API.

    Wraps httpx.AsyncClient with:
    - Session-based cookie auth (managed by DockhandAuth)
    - Transparent 401 retry with re-login
    - Generic get/post/put/delete returning parsed JSON
    - Proper async lifecycle (close / context manager)
    """

    def __init__(self, base_url: str, username: str, password: str, verify_ssl: bool = True):
        self._base_url = base_url.rstrip("/")
        self._auth = DockhandAuth(self._base_url, username, password)
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=False,
            verify=verify_ssl,
        )

    async def close(self) -> None:
        """Close the underlying httpx client and release connections."""
        await self._client.aclose()

    async def __aenter__(self) -> "DockhandClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ── Generic HTTP methods ─────────────────────────────────────────────

    async def get(
        self, path: str, params: Optional[dict[str, Any]] = None
    ) -> Any:
        """Authenticated GET returning parsed JSON."""
        return await self._request("GET", path, params=params)

    async def post(
        self,
        path: str,
        json: Any = None,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        files: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Authenticated POST returning parsed JSON."""
        return await self._request("POST", path, json_body=json, params=params, data=data, files=files)

    async def put(
        self,
        path: str,
        json: Any = None,
        params: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Authenticated PUT returning parsed JSON."""
        return await self._request("PUT", path, json_body=json, params=params)

    async def delete(
        self,
        path: str,
        params: Optional[dict[str, Any]] = None,
        json: Any = None,
    ) -> Any:
        """Authenticated DELETE returning parsed JSON. Some Dockhand DELETE
        endpoints accept a request body."""
        return await self._request("DELETE", path, json_body=json, params=params)

    # ── Health check shorthand ───────────────────────────────────────────

    async def post_sse(
        self, path: str, json: Any = None, params: Optional[dict[str, Any]] = None
    ) -> Any:
        """POST returning Server-Sent Events. Parses the events and returns combined output."""
        return await self._request_sse("POST", path, json_body=json, params=params)

    async def put_sse(
        self, path: str, json: Any = None, params: Optional[dict[str, Any]] = None
    ) -> Any:
        """PUT returning Server-Sent Events. Parses the events and returns combined output."""
        return await self._request_sse("PUT", path, json_body=json, params=params)

    async def _request_sse(
        self,
        method: str,
        path: str,
        json_body: Any = None,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make a request expecting an SSE stream and parse the data lines."""
        await self._auth.ensure_authenticated(self._client)

        clean_params = {k: v for k, v in params.items() if v is not None} if params else None
        
        headers = {"Accept": "text/event-stream"}
        kwargs = {"headers": headers}
        if json_body is not None:
            kwargs["json"] = json_body
        if clean_params:
            kwargs["params"] = clean_params

        current_version = self._auth.session_version
        
        # Dockhand deploy streams can take a long time, use a longer timeout (5 mins)
        kwargs["timeout"] = httpx.Timeout(300.0, connect=10.0)
        resp = await self._client.request(method, path, **kwargs)

        if resp.status_code == 401:
            await self._auth.invalidate_and_retry(self._client, current_version)
            resp = await self._client.request(method, path, **kwargs)

        if resp.status_code >= 400:
            detail = resp.text[:1000] if resp.text else resp.reason_phrase
            raise DockhandAPIError(resp.status_code, detail, method, path)

        return self._parse_sse_response(resp)

    @staticmethod
    def _parse_sse_response(resp: httpx.Response) -> dict[str, Any]:
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            return resp.json()

        import json as json_lib
        
        text = resp.text
        lines = text.split('\n')
        combined_output = []
        last_success = True
        
        for line in lines:
            trimmed = line.strip()
            if trimmed.startswith('data: '):
                payload = trimmed[6:]
                try:
                    data = json_lib.loads(payload)
                    if isinstance(data, dict):
                        if 'output' in data:
                            combined_output.append(str(data['output']))
                        if 'error' in data:
                            combined_output.append(str(data['error']))
                        if 'success' in data:
                            last_success = bool(data['success'])
                except json_lib.JSONDecodeError:
                    combined_output.append(payload)

        if not combined_output:
            return {"success": True, "output": text}
            
        return {
            "success": last_success,
            "output": "\n".join(combined_output)
        }

    async def health_check(self) -> dict[str, Any]:
        """Check Dockhand server health. Returns parsed JSON or a status dict."""
        resp = await self._request_raw("GET", "/api/health")
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            return resp.json()
        return {"status": resp.text.strip() or "ok", "statusCode": resp.status_code}

    # ── Internal request plumbing ────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        json_body: Any = None,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        files: Optional[dict[str, Any]] = None,
    ) -> Any:
        """
        Make an authenticated request, parse JSON, and handle errors.
        Retries once on 401 after re-login.
        """
        resp = await self._request_raw(method, path, json_body=json_body, params=params, data=data, files=files)
        return self._parse_response(resp)

    async def _request_raw(
        self,
        method: str,
        path: str,
        json_body: Any = None,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        files: Optional[dict[str, Any]] = None,
    ) -> httpx.Response:
        """
        Make an authenticated request with transparent 401 retry.
        Returns the raw httpx.Response (caller is responsible for parsing).
        """
        # Ensure we have a valid session before the first attempt.
        await self._auth.ensure_authenticated(self._client)

        # Filter out None values from params.
        clean_params = (
            {k: v for k, v in params.items() if v is not None} if params else None
        )

        kwargs: dict[str, Any] = {}
        if json_body is not None:
            kwargs["json"] = json_body
        if data is not None:
            kwargs["data"] = data
        if files is not None:
            kwargs["files"] = files
        if clean_params:
            kwargs["params"] = clean_params

        # Capture current session version before making the request
        current_version = self._auth.session_version
        
        resp = await self._client.request(method, path, **kwargs)

        # Transparent 401 retry - re-login and try once more.
        if resp.status_code == 401:
            logger.info("Received 401 on %s %s, re-authenticating...", method, path)
            await self._auth.invalidate_and_retry(self._client, current_version)
            resp = await self._client.request(method, path, **kwargs)

        # Raise on non-2xx (after any retry).
        if resp.status_code >= 400:
            detail = resp.text[:1000] if resp.text else resp.reason_phrase
            raise DockhandAPIError(resp.status_code, detail, method, path)

        return resp

    @staticmethod
    def _parse_response(resp: httpx.Response) -> Any:
        """Parse response body as JSON, falling back to plain text."""
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            return resp.json()
        text = resp.text.strip()
        if text:
            return text
        return None
