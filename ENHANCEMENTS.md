# Dockhand MCP Server Enhancements

This document tracks planned enhancements, future phases, and outstanding technical debt.

## 1. Publishing & Distribution
- [x] **Rename Package:** Renamed package to `dockhand-mcp-py` in `pyproject.toml`.
- [ ] **Publish to PyPI:** Publish the package so it can be installed seamlessly via `uvx dockhand-mcp-py` without needing local source code.
- [ ] **Automate Releases:** Set up GitHub Actions to automatically publish releases to PyPI when a new tag is pushed.

## 2. API Coverage & Testing
- [x] Add unit tests for core auth, client, containers, environments, registries, git_stacks, and stacks tools.
- [x] Add unit tests for `misc.py`, `users.py`, `audit.py`, `dashboard.py`.

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

### Dockhand v1.0.52 - v1.0.54 Enhancements
- [x] **Per-Stack Resource Totals & Health:** Added `get_stack_stats` (`/api/stack-stats`), `get_stack_path_hints` (`/api/stacks/path-hints`), and enriched `list_stacks` with stack `Health`, `LabelTags`, and update/cooldown/pinned-digest counters.
- [x] **Stack Redeploy & Tagging:** Enhanced `restart_stack` with `mode` (`restart` | `ordered` | `recreate`), `update_stack_compose` with `pull` / `build` / `force_recreate` options, and added `get_stack_tags` / `set_stack_tags`.
- [x] **Minimum Image Release Age:** Added global `get_minimum_release_age` / `set_minimum_release_age` (`/api/settings/minimum-release-age`) and per-environment update check & cooldown settings (`get_environment_update_check_settings`, `update_environment_update_check_settings`).
- [x] **Container Updates & Compose Export:** Added `get_container_compose`, `check_container_updates`, `get_pending_container_updates` (exposing moved pinned digests and release age cooldowns), and updated `list_containers` to surface `dockhand.name`, `dockhand.tags`, and `health`.
- [x] **Secret Providers (Psono & CRUD):** Added `create_secret_provider`, `update_secret_provider`, and `delete_secret_provider` supporting Psono and other external secret providers.
- [x] **Batch Operations, Passkeys & Environment Reports:** Added `execute_batch_operation` (`/api/batch`), `list_passkeys` / `delete_passkey` (`/api/profile/passkeys`), and environment state report tools (`get_environment_report`, `get_environment_report_settings`, `update_environment_report_settings`).

### Dockhand v1.0.55 Enhancements
- [x] **Scheduled Container Actions:** Added `get_container_scheduled_actions` and `set_container_scheduled_actions` (`/api/scheduled-actions/{containerName}`) for start/stop on schedule (HH:MM or cron).
- [x] **SOPS (age) Secret Provider:** Supported SOPS age key decryption (`sops` provider type) with automatic `ageKey` / `age_key` sensitive redaction.
- [x] **Interface Language Preference:** Added `get_language_preference` and `set_language_preference` (`/api/preferences/language`).
- [x] **Pinned Digest Report Configuration:** Added `get_pinned_digest_report` and `set_pinned_digest_report` (`/api/settings/pinned-digest-report`).


### Agent Ergonomics & Performance (Phase 1)
- [x] **Git Stack Field Mapping & Compact Sync:** Fixed `_compact_git_stack` to properly map `stackName`, `repository.url`, `syncStatus`, and `composePath`. Added `_compact_sync_result` to strip massive SHA256 digest manifests and compose dumps.
- [x] **Atomic GitOps Deployments (`sync_and_deploy_git_stack`):** Added `deploy=True` support to `sync_git_stack` and dedicated convenience tool `sync_and_deploy_git_stack` to eliminate LLM round-trips.
- [x] **Shell Strings in `run_container_exec`:** Accepted `cmd: str | list[str]` with automatic normalization of shell strings to `["/bin/sh", "-c", cmd]`.
- [x] **Enhanced Log Querying in `get_container_logs`:** Added `timestamps: bool = False` and duration/ISO/epoch `since` parameter with client-side normalization to integer Unix epoch seconds.
- [x] **Batch Operations Schema Documentation & String Normalization:** Added full entity type documentation to `execute_batch_operation` and support for passing plain string lists (e.g. `items: ["radarr", "sonarr"]`).
### Agent Ergonomics & Performance (Phase 2 - v0.5.0)
- [x] **Client-Side Default `environment_id` Auto-Resolution:** `environment_id: int | None = None` is now optional across all tools (containers, stacks, git stacks, images, networks, volumes, security, tags). Automatically resolves to the default/active environment in single-host setups or via `DOCKHAND_DEFAULT_ENV` environment variable, avoiding throwaway `list_environments` calls. Disambiguates with helpful guidance if multiple environments exist without a default.
- [x] **Git Stack Lookups by Human-Readable Name:** Tools like `get_git_stack`, `sync_git_stack`, `deploy_git_stack`, `delete_git_stack`, `update_git_stack` now accept `stack_id: int | str`. Passing a human name (e.g. `"radarr"`) automatically resolves to its integer stack ID, eliminating the need to pre-query `list_git_stacks`.
- [x] **Token Economy & Compact Container Inspect Mode:** Added `compact: bool = False` to `get_container` and `inspect_container`. When enabled, drops bulky Docker engine internals (graph drivers, image layers, network endpoint options) while preserving essential state, health, port bindings, mounts, networks, restart policy, and secret-redacted environment variables. Reduces context footprint by up to 65%.
- [x] **Container State Filtering:** Added optional `status: str | None = None` filter to `list_containers` (e.g. `status="running"` or `status="exited"`).
