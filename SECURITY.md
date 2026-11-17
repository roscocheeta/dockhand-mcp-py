# Security Policy

## Supported Versions

Security updates are applied to the latest minor release on the `master` branch:

| Version | Supported          |
| :------ | :----------------- |
| 0.7.x   | :white_check_mark: |
| < 0.7   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability in `dockhand-mcp-py`, please report it privately using GitHub's **Private Vulnerability Reporting** feature on the repository's **Security** tab (`Security -> Advisories -> Report a vulnerability`).

Please include:
- A clear description of the vulnerability and its potential impact.
- Steps to reproduce or a proof-of-concept.
- Any affected configuration (e.g., auth mode, environment variables, MCP client).

You can expect an initial acknowledgment within 72 hours and updates as we investigate and prepare a fix.

## Security Design & Invariants

For details on how `dockhand-mcp-py` handles credentials, response redaction, read-only enforcement, and stdio transport isolation, see the **Architectural & Security Invariants** section in [AGENTS.md](AGENTS.md).
