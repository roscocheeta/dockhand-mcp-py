# Dockhand MCP Server Enhancements

This document tracks planned enhancements, future phases, and outstanding technical debt.

## 1. Publishing & Distribution
- [ ] **Rename Package:** Rename the PyPI package to `dockhand-mcp-py` to clarify it is the Python implementation.
- [ ] **Publish to PyPI:** Publish the package so it can be installed seamlessly via `uvx dockhand-mcp-py` without needing the local source code.
- [ ] **Automate Releases:** Set up GitHub Actions to automatically publish releases to PyPI when a new tag is pushed.

## 2. API Coverage (Phase 5 Completion)
- [ ] Some minor endpoints may require deeper testing.
- [ ] Add unit tests for `misc.py` (Tier 3 endpoints).

## 3. Tool Optimization
- [ ] Continue monitoring token efficiency across large Dockhand environments.
- [ ] Potentially add pagination parameters (`limit`, `offset`) to `list_containers` and `list_images` if environment sizes exceed context windows despite truncation.
