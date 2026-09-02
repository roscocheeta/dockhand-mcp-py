---
trigger: always_on
description: Project branching strategy and automated testing requirements
---

# Dockhand MCP Server - Project Guidelines

## Git Branching Strategy
- This project follows a `dev` -> `master` workflow.
- **NEVER** push directly to the `master` branch.
- All active development, bug fixes, and new features must be committed to the `dev` branch.
- The `master` branch should only be updated via Pull Requests (PRs) from `dev`, once all tests pass.

## Automated Testing & CI
- A GitHub Actions workflow (`.github/workflows/test.yml`) is configured to run automatically on every push to `dev` and `master`.
- The CI pipeline runs the test suite across Windows, macOS, and Ubuntu against Python 3.11, 3.12, and 3.13.
- Tests must pass in the CI pipeline before a PR can be merged into `master`.
- All new tools or features must include `pytest` test coverage, utilizing `respx` to mock the Dockhand API where necessary.

## Security
- Be aware that write-operations (e.g., `create_registry`, `create_user`) will pass passwords in plain text, making them visible in chat transcripts.
- Ensure that `strip_nulls()` and appropriate credential masking functions are used when returning large API payloads (like `inspect_container`) to prevent context window bloat and credential leaks.
