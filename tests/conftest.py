"""
Shared test fixtures for the Dockhand MCP server tests.
"""

import pytest
import httpx
import respx

from dockhand_mcp.client import DockhandClient


# ── Constants ────────────────────────────────────────────────────────────

TEST_BASE_URL = "http://dockhand.test"
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpass"
LOGIN_PATH = "/api/auth/login"
HEALTH_PATH = "/api/health"

SESSION_COOKIE = "connect.sid=s%3Aabc123.signature"


# ── Fixtures ─────────────────────────────────────────────────────────────


def mock_login_success(router: respx.MockRouter) -> respx.Route:
    """Register a successful login mock that sets a session cookie."""
    return router.post(LOGIN_PATH).respond(
        200,
        json={"user": {"username": TEST_USERNAME}},
        headers={"Set-Cookie": f"{SESSION_COOKIE}; Path=/; HttpOnly"},
    )


@pytest.fixture
async def mock_router():
    """Provides a started respx mock router scoped to the test base URL."""
    async with respx.mock(base_url=TEST_BASE_URL, assert_all_called=False) as router:
        yield router


@pytest.fixture
async def mock_client(mock_router: respx.MockRouter):
    """
    Provides a DockhandClient connected to a fully mocked Dockhand server.
    Login is pre-mocked to succeed.
    """
    mock_login_success(mock_router)

    client = DockhandClient(TEST_BASE_URL, TEST_USERNAME, TEST_PASSWORD)
    try:
        yield client
    finally:
        await client.close()
