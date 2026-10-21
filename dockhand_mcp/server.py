"""
Dockhand MCP Server — FastMCP entry point.

Uses stdio transport for integration with Antigravity-CLI.
All logging goes to stderr to avoid corrupting the JSON-RPC stream on stdout.
"""

import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP, Context

from .client import DockhandClient, DockhandAPIError, DockhandAuthError

# ── Logging — stderr only ────────────────────────────────────────────────
# Stdio transport: stdout is the MCP JSON-RPC channel.
# ANY stray output to stdout will corrupt the protocol.
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dockhand_mcp")


# ── Configuration ────────────────────────────────────────────────────────

def _get_config() -> dict[str, Any]:
    """Read required configuration from environment variables."""
    url = os.environ.get("DOCKHAND_URL", "").strip()
    api_token = os.environ.get("DOCKHAND_API_TOKEN", "").strip()
    username = os.environ.get("DOCKHAND_USERNAME", "").strip()
    password = os.environ.get("DOCKHAND_PASSWORD", "")
    verify_ssl = os.environ.get("DOCKHAND_VERIFY_SSL", "true").lower() not in ("false", "0", "no")
    read_only = os.environ.get("DOCKHAND_READ_ONLY", "false").lower() in ("true", "1", "yes")

    missing = []
    if not url:
        missing.append("DOCKHAND_URL")
    if not api_token:
        if not username:
            missing.append("DOCKHAND_USERNAME (or DOCKHAND_API_TOKEN)")
        if not password:
            missing.append("DOCKHAND_PASSWORD (or DOCKHAND_API_TOKEN)")

    if missing:
        logger.error(
            "Missing required environment variables: %s", ", ".join(missing)
        )
        sys.exit(1)

    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        logger.error(
            "Invalid DOCKHAND_URL '%s': must start with http:// or https:// and include a host.",
            url,
        )
        sys.exit(1)

    if not verify_ssl:
        logger.warning(
            "SSL certificate verification is DISABLED (DOCKHAND_VERIFY_SSL=false). "
            "Connections to %s are vulnerable to MITM attacks.",
            url,
        )

    return {
        "url": url,
        "username": username,
        "password": password,
        "api_token": api_token,
        "verify_ssl": verify_ssl,
        "read_only": read_only,
    }


# ── Lifespan — client lifecycle management ───────────────────────────────

@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """
    Manage the DockhandClient lifecycle.

    The client is created on server startup and properly closed on shutdown.
    The yielded dict is accessible in tools via:
        ctx.request_context.lifespan_context["dockhand"]
    """
    config = _get_config()
    client = DockhandClient(
        base_url=config["url"],
        username=config["username"],
        password=config["password"],
        verify_ssl=config["verify_ssl"],
        api_token=config["api_token"],
        read_only=config["read_only"],
    )
    logger.info(
        "Dockhand MCP server starting — target: %s (SSL verify: %s, read-only: %s, auth: %s)",
        config["url"],
        config["verify_ssl"],
        config["read_only"],
        "api_token" if config["api_token"] else "cookie_login",
    )
    try:
        yield {"dockhand": client}
    finally:
        logger.info("Shutting down — closing Dockhand client")
        await client.close()


# ── FastMCP server ───────────────────────────────────────────────────────

mcp = FastMCP(
    "dockhand-mcp",
    lifespan=lifespan,
)


def _get_client(ctx: Context) -> DockhandClient:
    """Extract the DockhandClient from the request context."""
    return ctx.request_context.lifespan_context["dockhand"]


# ── Error handling helper ────────────────────────────────────────────────

def _format_error(exc: Exception) -> str:
    """Format an exception into a user-friendly error message."""
    if isinstance(exc, DockhandAPIError):
        return (
            f"Dockhand API Error (HTTP {exc.status_code}) "
            f"on {exc.method} {exc.path}: {exc.detail}"
        )
    if isinstance(exc, DockhandAuthError):
        return f"Dockhand Authentication Error: {exc}"
    return f"Unexpected error: {exc}"


from .tools import register_all_tools

# ── Tools ────────────────────────────────────────────────────────────────

register_all_tools(mcp)

# ── Entry point ──────────────────────────────────────────────────────────

def main() -> None:
    """Entry point for the dockhand-mcp console script."""
    mcp.run()


if __name__ == "__main__":
    main()
