# Dockhand MCP Server Enhancements

This document tracks planned enhancements, future phases, and outstanding technical debt.

## 1. Publishing & Distribution
- [x] **Rename Package:** Renamed package to `dockhand-mcp-py` in `pyproject.toml`.
- [ ] **Publish to PyPI:** Publish the package so it can be installed seamlessly via `uvx dockhand-mcp-py` without needing local source code.
- [ ] **Automate Releases:** Set up GitHub Actions to automatically publish releases to PyPI when a new tag is pushed.

## 2. API Coverage & Testing
- [x] Add unit tests for core auth, client, containers, environments, registries, git_stacks, and stacks tools.
- [ ] Add unit tests for `misc.py`, `users.py`, `audit.py`, `dashboard.py`.

## 3. Tool Optimization
- [x] Compact list responses, truncate IDs (12 chars), and filter noisy Docker labels.
- [x] Redact env secrets (`PASSWORD`, `SECRET`, `KEY`, `TOKEN`) from container inspect calls.
- [ ] Potentially add pagination parameters (`limit`, `offset`) to `list_containers` and `list_images` if environment sizes exceed context windows despite truncation.

## 4. Missing Tools from Node.js Reference (Audit Gap Analysis)

An audit comparison between `dockhand-mcp-py` (Python) and the reference Node.js implementation (`scratch/mcp-dockhand`) identified **74 matching core tools**, **12 Python-exclusive tools**, and additional granular tools available in the Node.js implementation.

### High Priority / High Utility Enhancements
- [x] **System & Docker Pruning Tools (`prune_*`):**
  - `prune_all`, `prune_containers`, `prune_images`, `prune_networks`, `prune_volumes`
- [x] **Advanced Container File Operations:**
  - `upload_container_file`, `write_container_file_content`, `delete_container_file`, `rename_container_file`
- [x] **Advanced Stack Environment Management:**
  - `update_stack_env` (Structured env merge/replace with DB secret support)
  - `remove_stack_env_vars` (Selective key removal from .env/DB)
  - `check_stack_env_collisions`, `validate_stack_env`
  - `get_stack_delete_preview`
  - `adopt_stack`, `relocate_stack`

### Medium Priority Enhancements
- [x] **Vulnerability & Security Scanning:**
  - `list_vulnerabilities`, `get_vulnerability_count`, `scan_all_vulnerabilities`
  - `list_image_scans`
- [x] **Git Repository & Credential Management:**
  - `create_git_stack`, `update_git_stack`, `delete_git_stack`
  - `create_git_credential`, `update_git_credential`, `delete_git_credential`
  - `create_git_repository`, `update_git_repository`, `delete_git_repository`
  - `sync_git_repository`, `test_git_repository`, `trigger_git_webhook`

### Low Priority / Granular Tools (Optional)
- [x] **Single Resource Getters:** `get_network`, `get_volume`, `get_registry`, `get_user`, `get_notification`, `get_secret_provider`
- [x] **Granular Settings/Preferences:** `get_theme_settings`, `update_theme_settings`, `get_sidebar_preferences`, `set_grid_preferences`
- [x] **SSO / Enterprise Auth:** `list_oidc_providers`, `list_ldap_providers`, `test_oidc_provider`, `test_ldap_provider`

### Future Feature Considerations
- [x] **Container Exec Mode (run_container_exec):** While Dockhand v1.0.48 added a WebSocket-based attach terminal, v1.0.49 introduced a true REST-based one-shot container exec API. This completely resolves the WebSocket limitation and allows the MCP server to easily execute commands inside containers and synchronously return stdout, stderr, and exitCode.

### Dockhand v1.0.51 Enhancements
- [x] **Tag Catalog Management:** Added tools to list, create, update, and delete global catalog tags (colors and icons) via /api/tags.
- [x] **UI Custom Ordering:** Added tools to read and write custom sort orders for Environments and Tags via /api/preferences/*-order.

