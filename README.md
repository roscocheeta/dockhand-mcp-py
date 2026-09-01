# Dockhand MCP Server

A Model Context Protocol (MCP) server for [Dockhand](https://dockhand.dev/), enabling LLM agents (like Claude, Cursor, or Antigravity) to manage and monitor your Docker environments, containers, and images.

Written in Python using the `mcp` SDK and FastMCP.

## Features

This server currently implements the core functionality required to manage Dockhand environments:

- **Auth**: Transparently handles Dockhand authentication, session expiry, and concurrent 401 retry guards.
- **System**: Fetch Dockhand server info, host stats, and changelogs.
- **Environments**: List, inspect, create, update, delete, and test Docker environments. Safely strips internal credentials (`hawserToken`, `tlsKey`) from responses.
- **Containers (Read)**: List containers, get stats, fetch logs (tail), read file contents, and run top.
- **Containers (Write)**: Lifecycle controls (start, stop, restart, pause, delete) and configuration (create, update, rename).
- **Images**: List, pull, tag, remove, and view image history.

*(Stacks, Volumes, and Networks are planned for future phases).*

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended for easy execution)

## Configuration

The server requires three environment variables to connect to your Dockhand instance:

```env
DOCKHAND_URL=http://your-dockhand-instance:3866
DOCKHAND_USERNAME=your-username
DOCKHAND_PASSWORD=your-password
```

> **Security Note:** It is highly recommended to create a dedicated Service Account in Dockhand for this MCP server, rather than using your personal admin credentials.

## Usage

### Using with Claude Desktop

Add the following to your `claude_desktop_config.json` (usually located at `%APPDATA%\Claude\claude_desktop_config.json` on Windows or `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "dockhand": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/your-username/Dockhand-MCP-Server-Windows.git", "dockhand-mcp"],
      "env": {
        "DOCKHAND_URL": "http://your-dockhand-instance:3866",
        "DOCKHAND_USERNAME": "your-username",
        "DOCKHAND_PASSWORD": "your-password"
      }
    }
  }
}
```
*(Note: adjust the `--from` path to wherever you publish this repository, or point to a local directory using `--from /path/to/repo`).*

### Using with VSCode / VSCodium (Cline, Roo-Code, etc.)

If you are using an AI coding assistant inside VSCode (such as Cline or Roo-Code), you can add the server to your MCP settings file (usually accessed via the extension's MCP menu, which maps to `mcp_settings.json` or `cline_mcp_settings.json`):

```json
{
  "mcpServers": {
    "dockhand": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/roscocheeta/dockhand-mcp-py.git", "dockhand-mcp"],
      "env": {
        "DOCKHAND_URL": "http://your-dockhand-instance:3866",
        "DOCKHAND_USERNAME": "your-username",
        "DOCKHAND_PASSWORD": "your-password"
      }
    }
  }
}
```

### Using with Antigravity (CLI or Desktop)

Whether you are using the Antigravity Desktop app or running the `agy` CLI in a terminal (like VSCodium), the MCP configuration uses the exact same schema. 

You can configure it globally or per-workspace by adding the following JSON to an `mcp_config.json` file:

**Global Location (Applies everywhere):**
`~/.gemini/config/mcp_config.json`

**Workspace Location (Applies only to a specific project):**
`.agents/mcp_config.json` (Create this file at the root of your project)

```json
{
  "mcpServers": {
    "dockhand": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/roscocheeta/dockhand-mcp-py.git", "dockhand-mcp"],
      "env": {
        "DOCKHAND_URL": "http://your-dockhand-instance:3866",
        "DOCKHAND_USERNAME": "your-username",
        "DOCKHAND_PASSWORD": "your-password"
      }
    }
  }
}
```

### Local Development Usage

## Development & Testing

This project uses `uv` for dependency management.

```bash
# Setup the virtual environment and install dependencies
uv sync --extra dev

# Run the test suite
uv run pytest
```

### Testing Strategy

The test suite is fully hermetic and runs offline—it does not require a live Dockhand instance. We achieve this using:
- **`pytest`** & **`pytest-asyncio`**: For running asynchronous test cases.
- **`respx`**: For intercepting and mocking `httpx` HTTP requests at the network level.

If you are writing new tests (or having an AI write them), use the `mock_router` fixture (defined in `tests/conftest.py`). This fixture intercepts all requests matching the test base URL, allowing you to easily simulate Dockhand backend responses, 401 Unauthorized errors, or network latency without making real HTTP calls.

### Architecture

- **`client.py`**: Wraps `httpx.AsyncClient` with a robust `DockhandAuth` state machine. It guarantees thread-safe login using an `asyncio.Lock` and proactively tracks the ~24h session expiry to prevent 401 floods.
- **`server.py`**: Initializes the `FastMCP` application and manages the client lifecycle. Explicitly routes all Python `logging` to `sys.stderr` to prevent corrupting the MCP JSON-RPC protocol over `stdout`.
- **`tools/`**: Maps cleanly to the Dockhand REST API, utilizing Pydantic types inferred by FastMCP.

## License

MIT
