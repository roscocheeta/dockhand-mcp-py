# Dockhand MCP Server

A Model Context Protocol (MCP) server for [Dockhand](https://dockhand.dev/), enabling LLM agents (like Claude, Cursor, or Antigravity) to manage and monitor your Docker environments, containers, and images.

Written in Python using the `mcp` SDK and FastMCP.

## Features

- **Transparent Auth**: Handles Dockhand authentication, tracking the ~24h session expiry, and uses an `asyncio.Lock` to prevent concurrent 401 retry floods.
- **Protocol Safe**: Explicitly routes all Python logging to `sys.stderr` to prevent JSON-RPC transport corruption.
- **Secure**: Automatically strips sensitive internal credentials (`hawserToken`, `tlsKey`) from API responses before passing them to the LLM context.

## Available Tools

The server exposes the following tools to the LLM agent:

### System & Health
- `health_check`: Check connectivity to the Dockhand instance.
- `get_server_info`: Fetch Dockhand system/version information.
- `get_host_info`: Fetch OS and host hardware information.
- `get_changelog`: Get the Dockhand release changelog.
- `prune_all`, `prune_containers`, `prune_images`, `prune_networks`, `prune_volumes`: System pruning tools.

### Environments
- `list_environments`: List all Docker hosts managed by Dockhand.
- `get_environment`: Get details for a specific environment (automatically strips `tlsKey` and `hawserToken` for security).
- `create_environment`, `update_environment`, `delete_environment`: Manage environment configurations.
- `test_environment`: Validate connectivity to an environment.

### Containers
- **Read**: `list_containers`, `get_container`, `inspect_container`, `get_container_stats`, `get_container_top`
- **Logs & Files**: `get_container_logs` (tail stdout/stderr), `list_container_files`, `get_container_file_content`, `upload_container_file`, `write_container_file_content`, `delete_container_file`, `rename_container_file`, `chown_container_file`, `create_container_path`
- **Write**: `create_container`, `update_container`, `rename_container`, `delete_container` (with force flag)
- **Lifecycle & Exec**: `start_container`, `stop_container`, `restart_container`, `pause_container`, `unpause_container`, `exec_container`, `run_container_exec`

### Stacks (Docker Compose)
- `list_stacks`, `create_stack`, `get_stack_compose`, `update_stack_compose`
- `get_stack_env`, `get_stack_env_raw`, `update_stack_env`, `update_stack_env_raw`, `remove_stack_env_vars`, `check_stack_env_collisions`, `validate_stack_env`
- `deploy_stack`, `start_stack`, `stop_stack`, `restart_stack`, `down_stack`, `delete_stack`, `get_stack_delete_preview`
- `adopt_stack`, `relocate_stack`, `get_stack_deploy_history`, `get_stack_deploy_log`

### Git Stacks
- `list_git_stacks`, `get_git_stack`, `deploy_git_stack`, `sync_git_stack`, `create_git_stack`, `update_git_stack`, `delete_git_stack`
- `list_git_credentials`, `create_git_credential`, `update_git_credential`, `delete_git_credential`
- `list_git_repositories`, `create_git_repository`, `update_git_repository`, `delete_git_repository`, `sync_git_repository`, `test_git_repository`, `trigger_git_webhook`

### Networks & Volumes
- `list_networks`, `inspect_network`, `delete_network`
- `list_volumes`, `inspect_volume`, `delete_volume`

### Tags
- `list_tags`, `create_tag`, `update_tag`, `delete_tag`

### Administration & Security
- **Users/Auth:** `list_users`, `get_user`, `create_user`, `update_user`, `delete_user`, `list_tokens`, `create_token`, `delete_token`, `list_oidc_providers`, `list_ldap_providers`, `test_oidc_provider`, `test_ldap_provider`
- **Registries:** `list_registries`, `get_registry`, `create_registry`, `update_registry`, `delete_registry`, `test_registry`
- **Audit/Stats:** `get_audit_log`, `get_audit_users`, `get_dashboard`, `get_activity`

### Automation & Misc
- **Schedules & Updates:** `list_schedules`, `create_schedule`, `get_auto_update`, `set_auto_update`
- **Backups:** `delete_snapshots`
- **Alerts & Scans:** `list_notifications`, `get_notification`, `create_notification`, `list_vulnerabilities`, `get_vulnerability_count`, `scan_all_vulnerabilities`, `list_image_scans`, `scan_image`
- **Config:** `list_templates`, `list_labels`, `list_secret_providers`, `get_secret_provider`, `list_config_sets`, `get_preferences`, `set_preferences`, `get_theme_settings`, `update_theme_settings`, `get_sidebar_preferences`, `set_grid_preferences`, `get_environment_order`, `set_environment_order`, `reset_environment_order`, `get_tag_order`, `set_tag_order`, `reset_tag_order`

## Security & Privacy Note

This MCP server acts as a bridge between the AI model and your Dockhand instance. The AI model **must** be provided with the arguments required to execute tools. 

> [!WARNING]
> Tools such as `create_registry`, `create_user`, and `update_user` accept passwords as parameters. If you ask the AI to create a registry or user, it will need to know the password, which means the password will appear in your chat history and the server logs. 
> 
> **Best Practice:** Only use these tools for throwaway or development credentials. For production systems, you should create users and registries directly through the Dockhand web UI.

To protect your data during read operations, the server automatically masks or strips known secrets (like passwords, SSH keys, API tokens, and sensitive environment variables) from API responses before passing them to the AI context.

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

Optional configuration:
```env
# Set to 'false' if your homelab uses self-signed certificates
DOCKHAND_VERIFY_SSL=true
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
