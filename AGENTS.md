---
trigger: always_on
description: Modern engineering guidelines, branching lifecycle, quality gates, security invariants, and release recipes.
---

# Dockhand MCP Server - Engineering & Agent Guidelines

*A comprehensive blueprint for human and AI contributors to maintain release integrity, proactive security, pragmatic test hygiene, and agent ergonomics.*

---

## 1. Branching Strategy & The Dual-Branch Release Lifecycle

This repository strictly follows the **Dual-Branch Release Lifecycle** (`dev` -> `master`):

```mermaid
gitGraph
   commit id: "Initial"
   branch dev
   checkout dev
   commit id: "feat: core"
   branch feat/feature-x
   checkout feat/feature-x
   commit id: "feature work"
   checkout dev
   merge feat/feature-x id: "squash-merge PR #1"
   branch chore/prepare-release
   checkout chore/prepare-release
   commit id: "bump version & changelog"
   checkout dev
   merge chore/prepare-release id: "squash-merge release PR"
   checkout master
   merge dev id: "Release vX.Y.Z" tag: "vX.Y.Z"
   checkout dev
   merge master id: "sync: -s ours"
```

### Core Rules
1. **Protected Release Branch (`master`)**:
   - Represents strictly released, production-ready software.
   - **NEVER** push directly to `master` under any circumstances.
   - **`master` is NOT an echo branch**: Do NOT open or merge PRs to `master` for intermediate chores, docs, or feature branches. `master` is updated **ONLY** via a formal Release PR from `dev` when cutting a versioned release (`vX.Y.Z`).
2. **Integration Trunk (`dev`)**:
   - All active development, bug fixes, refactoring, chores, and documentation originate from and target `dev`.
   - Working branches must use standard prefixes: `feat/*`, `fix/*`, `docs/*`, `chore/*`.
   - Work accumulates on `dev` across multiple PRs until a release milestone is reached.
3. **Hard Quality Gate on `dev` Pull Requests**:
   - Every PR into `dev` must pass all CI/CD matrix tests, security audits (Gitleaks, pip-audit, Bandit SAST), and local quality gates.
   - **NEVER merge into `dev` while checks are in-progress or failing**: You must watch checks with `gh pr checks <PR> --watch` and verify all jobs report green (`exit code 0`) before merging.
   - PRs into `dev` are squash-merged to preserve a clean, atomic linear commit history.
4. **Strict Release Promotion (`dev` -> `master`)**:
   - Only when preparing a formal release (`vX.Y.Z`), open a single Release PR from `dev` to `master`.
   - The Release PR must independently pass all CI checks before merging via a standard merge commit (`gh pr merge <PR> --merge`).
5. **Mandatory Post-Release Reconcile (`ours` merge strategy)**:
   - When a release PR merges `dev` into `master`, Git's common-ancestor calculation breaks due to squash or merge commit diffs, leading to ghost conflicts on future release PRs.
   - **Mandatory Action**: Immediately after tagging `master`, checkout `dev` and merge `master` using the `ours` strategy:
     ```bash
     git checkout dev
     git merge -s ours origin/master -m "chore: sync master into dev post-vX.Y.Z release"
     git push origin dev
     ```

---

## 2. Quality Gates & Local Verification

Before submitting any Pull Request or committing changes, run the following verification steps:

| Step | Command | Standard |
| :--- | :--- | :--- |
| **Test Suite & Coverage** | `uv run --no-sync pytest --cov=dockhand_mcp --cov-report=term-missing` | 100% pass rate; maintain >90% line coverage across all modules. |
| **Dependency Security Audit** | `uv export --locked --no-dev --no-hashes --no-emit-project -o req.txt && uv tool run pip-audit -r req.txt` | Zero known vulnerabilities (moderate+ severity). |
| **Static Application Security (SAST)** | `uv tool run bandit -r dockhand_mcp -ll` | Zero medium or high severity security findings. |
| **Build & Packaging Verification** | `uv build` | Successfully builds `.tar.gz` sdist and `.whl` wheel without hatchling errors. |
| **Syntax & Type Validation** | `uv run --no-sync python -m py_compile dockhand_mcp/**/*.py` | Zero syntax or indentation errors. |
| **Local AI Review (Optional/Pre-PR)** | `coderabbit review --agent --base dev` | Address any critical or major findings before pushing/opening PRs. |

> [!IMPORTANT]
> **Windows Lock Contention**: When running the MCP server locally (e.g. in Claude Desktop or background daemon), `.venv\Scripts\dockhand-mcp.exe` may be file-locked. Always pass `--no-sync` (`uv run --no-sync pytest`) to execute python commands without attempting to rewrite active executable binaries.

---

## 3. Architectural & Security Invariants

All code, tool implementations, and refactors must uphold these non-negotiable invariants:

### 1. Protocol Safety (JSON-RPC Transport)
- MCP communication over stdio relies on pristine JSON-RPC formatting on `sys.stdout`.
- **NEVER** write raw `print()` statements or unformatted logs to `sys.stdout`.
- All logging must be routed exclusively to `sys.stderr` via Python's standard `logging` library.

### 2. In-Memory Credential Lifecycle
- Scoped Bearer API tokens (`DOCKHAND_API_TOKEN`) and session credentials (`DOCKHAND_USERNAME` / `DOCKHAND_PASSWORD`) must be stored strictly in-memory within `DockhandAuth`.
- **NEVER** persist credentials, session cookies, or tokens to temporary files, configuration caches, or disk.

### 3. Response Sanitization & Token Economy
- Large API responses (such as `inspect_container` or compose files) can consume 20,000+ LLM tokens and leak sensitive configuration.
- **Redaction**: All container environment variables, stack `.env` contents, secret provider fields, and host credentials (`hawserToken`, `tlsKey`) must pass through `redact_env_text()`, `clean_env_list()`, or `redact_sensitive_dict()`.
- **Compact Modes**: Tools such as `get_container(compact=True)` and `inspect_container(compact=True)` must drop bulky engine internals (graph drivers, image layer lists, bridge options) while preserving essential runtime health, state, ports, mounts, networks, and restart policy.
- **Truncation**: IDs must be truncated to 12 characters (`truncate_id()`) and null values removed (`strip_nulls()`).

### 4. Tool Annotations & Guardrails
- FastMCP tool registration must include appropriate MCP annotations:
  - `readOnlyHint: True` on non-destructive queries (`list_*`, `get_*`, `inspect_*`).
  - `destructiveHint: True` on state-altering or irreversible operations (`delete_*`, `prune_*`, `down_stack`).
- Strict Read-Only Mode (`DOCKHAND_READ_ONLY=true`) must immediately reject state-mutating requests before network transmission.

### 5. Input Validation & Taint Tracking
- **URL Path Sanitization**: Path parameters (`container_id`, `stack_name`, `image_id`) must pass through `encode_path()` (`urllib.parse.quote(safe="")`) to prevent path traversal or route injection.
- **Protocol Whitelisting**: External repository URLs and base URLs must use `http` or `https` schemes only.
- **Command Injection Prevention**: In `run_container_exec`, shell strings must be executed safely via `["/bin/sh", "-c", cmd]`, preserving explicit list execution when an array is provided.

### 6. Environment & Resource Auto-Resolution
- LLMs frequently manage single-host homelabs where passing `environment_id: int` on every tool call creates context bloat.
- All tools must mark `environment_id: int | None = None` as optional, automatically resolving via `DockhandClient.resolve_environment_id()`:
  1. Respects `DOCKHAND_DEFAULT_ENV` environment variable override if present.
  2. Auto-resolves and caches the ID if only one environment exists or if an environment is marked default (`isDefault=True`).
  3. Raises a clear disambiguation error if multiple environments exist without a default.
- Git stack tools (`get_git_stack`, `sync_git_stack`, `deploy_git_stack`, `delete_git_stack`, etc.) must accept `stack_id: int | str` and automatically resolve human-readable stack names (e.g. `"radarr"`) via `resolve_git_stack_id()`.

---

## 4. Testing Protocols & Hygiene

- **Upstream Mocking**: Never rely on a live Dockhand instance during automated testing. All HTTP interactions must be mocked using `respx.mock` and `httpx.Response`.
- **SSE Stream Testing**: Server-Sent Events endpoints (`/deploy-stream`, `/check-updates`) must be tested with `Content-Type: text/event-stream` and valid `data: {...}\n\n` payloads to verify `post_sse` and `_parse_sse_response`.
- **Backward-Compatible Parameter Swapping**: When modifying tool parameter orders or adding optional defaults, maintain legacy positional argument compatibility using type checks (`isinstance(first_arg, int)` or `_normalize_container_args`).
- **Clean Teardown**: Close any active HTTP clients or mock transports in test fixtures to avoid leaking connections or unclosed event loops across pytest runs.

---

## 5. Release Recipe

When preparing and publishing a new release:

1. **Create Chore Branch**:
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b chore/prepare-release-vX.Y.Z
   ```
2. **Version & Documentation Bump**:
   - Update `version = "X.Y.Z"` in `pyproject.toml` and `uv.lock`, and update the `description` example and `placeholder` under `id: version` in `.github/ISSUE_TEMPLATE/bug_report.yml` (leaving the upstream Dockhand version field unchanged).
   - Update `README.md` features, tool tables, and roadmap.
3. **Execute Local Quality Gates**:
   ```bash
   uv run --no-sync pytest --cov=dockhand_mcp --cov-report=term-missing
   uv tool run pip-audit
   uv tool run bandit -r dockhand_mcp -ll
   uv build
   ```
4. **Commit & Pull Request into `dev`**:
   - Commit changes: `git commit -m "chore: prepare release vX.Y.Z"`.
   - Push branch and open PR targeting `dev`: `gh pr create --base dev ...`.
   - Wait for all CI checks (Ubuntu, Windows, Gitleaks, pip-audit, Bandit SAST) to pass.
   - Squash-merge into `dev`.
5. **Release Pull Request into `master`**:
   - Checkout updated `dev`: `git checkout dev && git pull origin dev`.
   - Open release PR targeting `master`: `gh pr create --base master --head dev --title "Release vX.Y.Z: ..."`.
   - Wait for all CI matrix checks to pass.
   - Merge into `master` using standard merge commit: `gh pr merge <PR_NUMBER> --merge`.
6. **Tag & Publish Release**:
   - Checkout `master` and pull: `git checkout master && git pull origin master`.
   - Create and push signed tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.
   - Create GitHub release: `gh release create vX.Y.Z --title "vX.Y.Z - Summary" --notes-file release_notes.md`.
7. **Post-Release Reconcile**:
   - Sync `master` back into `dev` to ensure clean git graph ancestry:
     ```bash
     git checkout dev
     git merge -s ours origin/master -m "chore: sync master into dev post-vX.Y.Z release"
     git push origin dev
     ```
