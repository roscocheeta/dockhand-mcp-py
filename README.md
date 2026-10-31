# Dockhand MCP Server

[![CI Tests](https://github.com/roscocheeta/dockhand-mcp-py/actions/workflows/test.yml/badge.svg)](https://github.com/roscocheeta/dockhand-mcp-py/actions/workflows/test.yml)
[![Security & Audit](https://github.com/roscocheeta/dockhand-mcp-py/actions/workflows/security.yml/badge.svg)](https://github.com/roscocheeta/dockhand-mcp-py/actions/workflows/security.yml)
[![GitHub Release](https://img.shields.io/github/v/release/roscocheeta/dockhand-mcp-py?color=blue&logo=github)](https://github.com/roscocheeta/dockhand-mcp-py/releases)
[![Python Versions](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance Model Context Protocol (MCP) server for [Dockhand](https://dockhand.dev/), enabling LLM agents (Claude Desktop, Cursor, Antigravity, Windsurf) to monitor, inspect, and manage Docker environments, containers, compose stacks, and GitOps workflows.

Written in Python using the official `mcp` SDK and FastMCP.

---

## Key Features

- **Agent Ergonomics & Auto-Resolution**:
  - `environment_id` is optional across all tools, auto-resolving to the primary host environment in single-host setups or via `DOCKHAND_DEFAULT_ENV`.
  - Git stacks can be referenced by human-readable names (e.g. `stack_id="radarr"`) without pre-querying numeric stack IDs.
- **Token Efficiency & Compact Inspect Mode**:
  - Compact container listings, truncated 12-char SHA256 IDs, and noisy label suppression.
  - `compact: true` inspect mode for `get_container` and `inspect_container` drops bulky Docker engine internals (graph drivers, layer trees), reducing LLM context window consumption by up to 65%.
- **Atomic GitOps Deployments**:
  - `sync_and_deploy_git_stack` (and `sync_git_stack(deploy=True)`) syncs and deploys in a single round-trip, stripping massive SHA256 digest manifests.
- **Shell Strings in Container Exec**:
  - `run_container_exec` accepts plain shell strings (`cmd: "ps aux | grep nginx"`), automatically executing via `["/bin/sh", "-c", cmd]`.
- **Advanced Log Querying**:
  - `get_container_logs` supports `timestamps: bool = True` and human relative durations or ISO timestamps (`since="1h"` or `since="24h"`).
- **Transparent Authentication**:
  - Supports scoped Bearer API tokens (`DOCKHAND_API_TOKEN`) and session-cookie login (`DOCKHAND_USERNAME` + `DOCKHAND_PASSWORD`) with proactive ~24h session refresh and an `asyncio.Lock` preventing concurrent 401 retry storms.
- **Protocol Safety**:
  - Explicitly routes all Python logging to `sys.stderr` to prevent JSON-RPC transport corruption over stdio.
- **Proactive Security & Guardrails**:
  - Automatically redacts sensitive credentials (`hawserToken`, `tlsKey`, `.env` secrets, passwords, webhook tokens, OIDC/LDAP secrets) from all API responses.
  - Enforces MCP `ToolAnnotations` (`readOnlyHint`, `destructiveHint`) and an optional strict `DOCKHAND_READ_ONLY=true` mode.

---

## Configuration Reference

The server is configured via environment variables:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `DOCKHAND_URL` / `DOCKHAND_BASE_URL` | String | *(Required)* | Base URL of your Dockhand instance (e.g. `http://dockhand.local:3866`). |
| `DOCKHAND_API_TOKEN` | String | *None* | Scoped Bearer API token created in Dockhand (Recommended). |
| `DOCKHAND_USERNAME` | String | *None* | Username for cookie-based session login (alternative to API token). |
| `DOCKHAND_PASSWORD` | String | *None* | Password for cookie-based session login. |
| `DOCKHAND_DEFAULT_ENV` | Integer | *Auto* | Default environment ID override. If omitted, auto-resolves single environment. |
| `DOCKHAND_READ_ONLY` | Boolean | `false` | When `true`, exposes only read-only tools and blocks all POST/PUT/DELETE calls. |
| `DOCKHAND_VERIFY_SSL` | Boolean | `true` | Set to `false` if your homelab uses private self-signed TLS certificates. |
| `DOCKHAND_TIMEOUT` | Float | `60.0` | Request timeout in seconds for standard HTTP endpoints. |
| `DOCKHAND_DISABLE_TOOLS` | String | *None* | Comma-separated list of tool names to hide from the registered catalog. |

---

## Client Setup

### Claude Desktop

Add the following to your `claude_desktop_config.json`:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "dockhand": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/roscocheeta/dockhand-mcp-py.git", "dockhand-mcp"],
      "env": {
        "DOCKHAND_URL": "http://your-dockhand-instance:3866",
        "DOCKHAND_API_TOKEN": "dh_your_api_token_here"
      }
    }
  }
}
```

### Antigravity (IDE & CLI)

Configure globally in `~/.gemini/config/mcp_config.json` or per-workspace in `.agents/mcp_config.json`:

```json
{
  "mcpServers": {
    "dockhand": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/roscocheeta/dockhand-mcp-py.git", "dockhand-mcp"],
      "env": {
        "DOCKHAND_URL": "http://your-dockhand-instance:3866",
        "DOCKHAND_API_TOKEN": "dh_your_api_token_here"
      }
    }
  }
}
```

### Cursor / Windsurf / VS Code

In your extension's MCP settings configuration (`mcp_settings.json`):

```json
{
  "mcpServers": {
    "dockhand": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/roscocheeta/dockhand-mcp-py.git", "dockhand-mcp"],
      "env": {
        "DOCKHAND_URL": "http://your-dockhand-instance:3866",
        "DOCKHAND_API_TOKEN": "dh_your_api_token_here"
      }
    }
  }
}
```

---

## Available Tools (74+ Tools)

### Containers & Scheduled Actions
- **Inspection & State**: `list_containers` (supports `status="running"` filter), `get_container` (with `compact=True`), `inspect_container`, `get_container_stats`, `get_container_top`, `get_container_compose`.
- **Logs & Execution**: `get_container_logs` (supports `tail`, `timestamps=True`, `since="1h"`), `run_container_exec` (accepts shell strings or argument arrays), `exec_container`.
- **File System Operations**: `list_container_files`, `get_container_file_content` (with truncation), `write_container_file_content`, `upload_container_file` (base64 encoded), `create_container_path`, `chown_container_file`, `delete_container_file`, `rename_container_file`.
- **Lifecycle & Updates**: `start_container`, `stop_container`, `restart_container`, `pause_container`, `unpause_container`, `create_container`, `update_container`, `rename_container`, `delete_container`, `check_container_updates`, `get_pending_container_updates`.
- **Scheduled Actions**: `get_container_scheduled_actions`, `set_container_scheduled_actions` (daily start/stop or cron).

### Stacks (Docker Compose)
- **Deployment & Lifecycle**: `list_stacks`, `create_stack`, `deploy_stack`, `start_stack`, `stop_stack`, `restart_stack` (supports `mode="restart"|"ordered"|"recreate"`), `down_stack`, `delete_stack`, `adopt_stack`, `relocate_stack`.
- **Compose & Metrics**: `get_stack_compose`, `update_stack_compose` (supports `pull`, `build`, `force_recreate`), `get_stack_stats`, `get_stack_path_hints`, `get_stack_deploy_history`, `get_stack_deploy_log`.
- **Environment Management**: `get_stack_env`, `get_stack_env_raw`, `update_stack_env`, `update_stack_env_raw`, `remove_stack_env_vars`, `check_stack_env_collisions`, `validate_stack_env`, `get_stack_delete_preview`.

### Git Stacks & GitOps
- **Git Stacks**: `list_git_stacks`, `get_git_stack`, `deploy_git_stack`, `sync_git_stack` (with `deploy=True`), `sync_and_deploy_git_stack`, `create_git_stack`, `update_git_stack`, `delete_git_stack`. *All stack tools accept human names (e.g. `"radarr"`).*
- **Git Repositories & Credentials**: `list_git_repositories`, `create_git_repository`, `update_git_repository`, `delete_git_repository`, `sync_git_repository`, `test_git_repository`, `trigger_git_webhook`, `list_git_credentials`, `create_git_credential`, `update_git_credential`, `delete_git_credential`.

### Environments & System
- **Environments**: `list_environments`, `get_environment`, `create_environment`, `update_environment`, `delete_environment`, `test_environment`, `get_environment_update_check_settings`, `update_environment_update_check_settings`, `get_environment_report`, `get_environment_report_settings`, `update_environment_report_settings`.
- **System & Pruning**: `health_check`, `get_server_info`, `get_host_info`, `get_changelog`, `prune_all`, `prune_containers`, `prune_images`, `prune_networks`, `prune_volumes`.

### Networks, Volumes & Images
- **Networks**: `list_networks`, `get_network`, `inspect_network`, `create_network`, `delete_network`.
- **Volumes**: `list_volumes`, `get_volume`, `inspect_volume`, `create_volume`, `delete_volume`.
- **Images**: `list_images`, `get_image_history`, `remove_image`, `pull_image` (with optional vulnerability scan), `tag_image`, `push_image`.

### Security, Users & Preferences
- **Security & Scans**: `list_vulnerabilities`, `get_vulnerability_count`, `scan_all_vulnerabilities`, `list_image_scans`, `scan_image` (Grype or Trivy).
- **Users, Tokens & Passkeys**: `list_users`, `get_user`, `create_user`, `update_user`, `delete_user`, `list_tokens`, `create_token`, `delete_token`, `list_passkeys`, `delete_passkey`, `list_oidc_providers`, `list_ldap_providers`, `test_oidc_provider`, `test_ldap_provider`.
- **Registries & Secret Providers**: `list_registries`, `get_registry`, `create_registry`, `update_registry`, `delete_registry`, `test_registry`, `list_secret_providers`, `get_secret_provider`, `create_secret_provider`, `update_secret_provider`, `delete_secret_provider` (Psono, SOPS age key).
- **Batch & Preferences**: `execute_batch_operation`, `get_minimum_release_age`, `set_minimum_release_age`, `get_pinned_digest_report`, `set_pinned_digest_report`, `get_language_preference`, `set_language_preference`, `get_preferences`, `set_preferences`, `get_theme_settings`, `update_theme_settings`, `get_sidebar_preferences`, `set_grid_preferences`, `get_environment_order`, `set_environment_order`, `reset_environment_order`, `get_tag_order`, `set_tag_order`, `reset_tag_order`, `list_tags`, `create_tag`, `update_tag`, `delete_tag`, `get_stack_tags`, `set_stack_tags`.

---

## Security Invariants

1. **Zero Secret Leakage**: Passwords, tokens, and private keys (`hawserToken`, `tlsKey`) are automatically stripped before response serialization.
2. **Read-Only Enforcement**: When `DOCKHAND_READ_ONLY=true` is set, all write operations (`create_*`, `update_*`, `delete_*`, `prune_*`) fail-fast before invoking network requests.
3. **Transport Integrity**: All diagnostic logging writes to `sys.stderr`. Standard output (`sys.stdout`) is reserved exclusively for JSON-RPC frame delivery.
4. **Input Sanitization**: Dynamic URL path segments pass through strict URL encoding (`encode_path`) to prevent path traversal or injection.

---

## Development & Testing

This project uses [`uv`](https://docs.astral.sh/uv/) for Python packaging and testing.

```bash
# Clone the repository
git clone https://github.com/roscocheeta/dockhand-mcp-py.git
cd dockhand-mcp-py

# Install dependencies and sync virtual environment
uv sync --extra dev

# Run full test suite with coverage
uv run --no-sync pytest --cov=dockhand_mcp --cov-report=term-missing

# Run security audit on dependencies and SAST
uv tool run pip-audit
uv tool run bandit -r dockhand_mcp -ll

# Verify package build
uv build
```

### Contributing & Guidelines
We welcome contributions! Please review:
- [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines, local development setup, and pull request standards.
- [AGENTS.md](AGENTS.md) for deep architectural invariants, testing hygiene, and release lifecycle specifications.

---

## License

[MIT License](LICENSE)
