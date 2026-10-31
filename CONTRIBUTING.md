# Contributing to Dockhand MCP Server

Thank you for your interest in contributing to the **Dockhand MCP Server**! Whether you are a human developer, an open-source contributor, or an AI pair programmer, this guide details our development workflow, engineering standards, quality gates, and security invariants.

---

## 1. Branching Strategy & Lifecycle

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
   merge feat/feature-x id: "squash-merge PR"
   checkout master
   merge dev id: "Release vX.Y.Z"
   checkout dev
   merge master id: "sync: -s ours"
```

### Core Rules
- **Integration Trunk (`dev`)**: All active development, bug fixes, refactoring, and documentation originate from and target `dev`. **All pull requests must target `dev`**.
- **Protected Release Branch (`master`)**: Represents strictly released, production software. Direct pushes and direct PRs from forks into `master` are rejected.
- **Working Branch Prefixes**:
  - `feat/*`: New MCP tools, API endpoints, or ergonomic features
  - `fix/*`: Bug fixes or error handling corrections
  - `docs/*`: Documentation, README, or guideline improvements
  - `chore/*`: Dependency updates, CI/CD tweaks, release preparation

---

## 2. Local Development Setup

### Prerequisites
- **Python**: Version `3.11` or newer (`3.12` recommended).
- **Package Manager**: [uv](https://docs.astral.sh/uv/) is strongly recommended for fast, deterministic virtual environments.
- *Note*: Node.js is **not** required.

### Getting Started

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/<your-username>/dockhand-mcp-py.git
   cd dockhand-mcp-py
   ```

2. **Check out the `dev` branch**:
   ```bash
   git checkout dev
   ```

3. **Create a working branch**:
   ```bash
   git checkout -b feat/my-new-feature
   ```

4. **Install dependencies in a virtual environment**:
   ```bash
   uv sync --extra dev
   ```

5. **Run the MCP server locally**:
   ```bash
   # Using environment variables for Dockhand API connection
   export DOCKHAND_URL="http://localhost:3866"
   export DOCKHAND_API_TOKEN="your-dockhand-bearer-token"
   uv run dockhand-mcp
   ```

---

## 3. Local Quality Gates (Mandatory Verification)

Before opening a pull request or submitting changes, ensure your branch passes all local quality gates:

| Verification Gate | Command | Passing Standard |
| :--- | :--- | :--- |
| **Unit Tests & Coverage** | `uv run --no-sync pytest --cov=dockhand_mcp --cov-report=term-missing` | 100% pass rate; maintain >90% line coverage across all modules. |
| **Dependency Security Audit** | `uv tool run pip-audit` | Zero known vulnerabilities (moderate+ severity). |
| **Static Application Security (SAST)** | `uv tool run bandit -r dockhand_mcp -ll` | Zero medium or high severity security findings. |
| **Build & Packaging Verification** | `uv build` | Successfully builds `.tar.gz` sdist and `.whl` wheel without hatchling errors. |
| **Syntax Validation** | `uv run --no-sync python -m py_compile dockhand_mcp/**/*.py` | Zero syntax or indentation errors. |

> [!TIP]
> **Windows Lock Contention**: If running the MCP server locally in a background client (such as Claude Desktop), `.venv\Scripts\dockhand-mcp.exe` may be file-locked by the OS. Always pass `--no-sync` when running pytest (`uv run --no-sync pytest`).

---

## 4. Architectural & Security Invariants

All tool implementations and refactors must strictly uphold these architectural rules:

### 1. Protocol Safety (Stdio Transport)
- MCP communication over stdio relies on pristine JSON-RPC formatting on `sys.stdout`.
- **Never** write raw `print()` statements or unformatted logs to `sys.stdout`.
- All logging must be routed exclusively to `sys.stderr` via Python's standard `logging` library.

### 2. In-Memory Credential Lifecycle
- Scoped Bearer API tokens (`DOCKHAND_API_TOKEN`) and session credentials (`DOCKHAND_USERNAME` / `DOCKHAND_PASSWORD`) must be stored strictly in-memory within `DockhandAuth`.
- **Never** persist credentials, session cookies, or tokens to temporary files or disk.

### 3. Response Sanitization & Token Economy
- Large API responses (such as container inspection payloads and compose files) can quickly exhaust LLM context windows.
- **Redaction**: Pass all container environment variables, stack `.env` contents, and secret provider fields through `redact_env_text()`, `clean_env_list()`, or `redact_sensitive_dict()`.
- **Compact Modes**: Tools like `get_container(compact=True)` and `inspect_container(compact=True)` drop bulky Docker internals (graph drivers, image layer lists) while preserving runtime health, state, ports, mounts, and networks.
- **Truncation**: Truncate IDs to 12 characters via `truncate_id()` and remove empty null values with `strip_nulls()`.

### 4. Tool Annotations & Guardrails
- FastMCP tool registration must include appropriate MCP annotations:
  - `readOnlyHint: True` on non-destructive queries (`list_*`, `get_*`, `inspect_*`).
  - `destructiveHint: True` on state-altering or irreversible operations (`delete_*`, `prune_*`, `down_stack`).
- Strict Read-Only Mode (`DOCKHAND_READ_ONLY=true`) must immediately reject state-mutating requests before network transmission.

### 5. Input Validation & Path Sanitization
- Path parameters (`container_id`, `stack_name`, `image_id`) must pass through `encode_path()` (`urllib.parse.quote(safe="")`) to prevent path traversal.
- External URLs must use `http` or `https` schemes only.
- In `run_container_exec`, execute shell strings safely via `["/bin/sh", "-c", cmd]`.

---

## 5. Testing Protocols

- **Upstream Mocking**: Never make live network requests to a remote Dockhand instance during automated testing. All HTTP and SSE interactions must be mocked using `respx.mock` and `httpx.Response`.
- **SSE Stream Testing**: Server-Sent Events endpoints (`/deploy-stream`, `/check-updates`) must be tested with `Content-Type: text/event-stream` and valid `data: {...}\n\n` payloads.
- **Backward-Compatible Parameter Swapping**: When modifying tool parameter orders or adding optional defaults, maintain legacy positional argument compatibility using normalization helpers (`_normalize_container_args`, `_normalize_stack_args`).

---

## 6. Pull Request Checklist

When submitting a pull request to `dev`:

- [ ] Target branch is set to `dev` (not `master`).
- [ ] PR title follows [Conventional Commits](https://www.conventionalcommits.org/) (e.g. `feat: add container pause action`, `fix: handle null network gateways`).
- [ ] Unit tests are added or updated in `tests/` covering new behavior or bug fixes.
- [ ] Code coverage remains above 90%.
- [ ] All local quality gates pass (`pytest`, `pip-audit`, `bandit`, `uv build`).
- [ ] No secrets, private IPs, or credentials are committed.
- [ ] Documentation (`README.md` or docstrings) is updated if adding or modifying MCP tools.

---

## 7. AI & Pair-Programming Guidelines

If you are using an AI coding assistant (Antigravity, Cursor, Windsurf, Claude Code):
- Refer to [`AGENTS.md`](AGENTS.md) for deep architectural invariants, error patterns, and machine-readable execution rules.
- Maintain documentation integrity: do not delete or rewrite existing docstrings or comments unrelated to your changes.
- Ensure all tests run with `--no-sync` to avoid binary lock contention on Windows environments.
