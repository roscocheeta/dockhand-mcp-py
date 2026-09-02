# Dockhand MCP Server - Project Status

*Last Updated: 2026-09-02*

## 🟢 Current State: Production Ready
The Dockhand MCP Server is fully functional, token-efficient, secure, and comprehensively tested. All tools from Phase 1 through Phase 5 have been implemented. 

The `master` branch contains the stable, tested release. Active development happens on `dev`.

### Work Completed (Recent Sessions)
1. **Tier 3 Tools Implemented (Phases 4 & 5):**
   - Registries, Users, Tokens, Audit Logs, Dashboard Metrics, Notifications, Schedules, Templates, Labels, Preferences, Config Sets, Auto-Updates, Image Scanning.
2. **Security Enhancements:**
   - Evaluated credential flow. Added `redact_env_secrets` to inspect endpoints to strip `PASSWORD`, `SECRET`, `TOKEN` keys.
   - Refined `_compact_registry` and `list_git_credentials` to strip passwords regardless of key casing (`TitleCase` vs `lowercase`).
   - Added `SECURITY WARNING` to docstrings of tools that pass passwords in plain text (`create_registry`, `create_user`) so the LLM knows to warn users.
   - Added `DOCKHAND_VERIFY_SSL=false` support for homelabs.
3. **Token Efficiency:**
   - Implemented `strip_nulls` recursively across all large inspect payloads (containers, volumes, networks).
   - Added `max_bytes` (10KB default) to `get_container_file_content`.
   - Added `max_lines` (50 default) to `get_changelog`.
   - Capped `get_container_logs` tail at 500 lines max.
4. **Architecture & Testing:**
   - Wrote a refactoring script that converted all nested `@mcp.tool()` closures into module-level `async def` functions, enabling native unit testing.
   - Achieved 84% coverage on `client.py` and 97% on `utils.py`, covering critical security and auth logic.
   - Added tests for SSE stream parsing and credential stripping.
5. **CI/CD & GitOps:**
   - Configured `.github/workflows/test.yml` to run tests across Windows, Mac, and Ubuntu.
   - Created `.github/workflows/upstream_monitor.yml` to automatically open issues when new upstream Dockhand versions are released.
   - Captured the `dev -> master` workflow directly in `AGENTS.md` so future AI agents follow it.

## 📝 Remaining Enhancements (Backlog)
If we decide to do more work on this project, these are the highest-impact items remaining (tracked in `ENHANCEMENTS.md`):

1. **Add `exec_container` tool** (Medium Effort)
   - Allow the LLM to run bash commands inside containers (highly requested).
2. **Container Filtering** (Medium Effort)
   - Add search parameters to `list_containers` to prevent returning all 50+ containers when the user only wants one.
3. **Batch Operations** (High Effort)
   - Implement `batch_update_containers` or `prune_*` methods for easier cleanup.
4. **PyPI Publishing** (Low Effort)
   - Setup GitHub Actions to publish `dockhand-mcp-py` to PyPI on release tags.

## 🤖 AI Agent Instructions
If you are an AI reading this file at the start of a new session:
- **Rule Check:** You MUST check `AGENTS.md` in the root directory before pushing any code. We only push to `dev`, never `master`.
- **Test Check:** Run `uv run pytest` to ensure you haven't broken the auth or redaction logic.
- **Next Task:** Ask the user if they want to implement an item from the Backlog above, or if they have a specific bug to fix.
