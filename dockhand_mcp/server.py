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

def _get_config() -> dict[str, str]:
    """Read required configuration from environment variables."""
    url = os.environ.get("DOCKHAND_URL", "")
    username = os.environ.get("DOCKHAND_USERNAME", "")
    password = os.environ.get("DOCKHAND_PASSWORD", "")

    missing = []
    if not url:
        missing.append("DOCKHAND_URL")
    if not username:
        missing.append("DOCKHAND_USERNAME")
    if not password:
        missing.append("DOCKHAND_PASSWORD")

    if missing:
        logger.error(
            "Missing required environment variables: %s", ", ".join(missing)
        )
        sys.exit(1)

    return {"url": url, "username": username, "password": password}


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
    )
    logger.info("Dockhand MCP server starting — target: %s", config["url"])
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
