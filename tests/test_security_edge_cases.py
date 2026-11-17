import pytest
from dockhand_mcp.utils import (
    is_secret_key,
    redact_env_text,
    redact_url_credentials,
    redact_sensitive_dict,
)


class TestSecurityEdgeCases:
    """Corner-case and boundary tests for all security redaction utilities."""

    def test_is_secret_key_types_and_patterns(self):
        # Non-string input
        assert is_secret_key(None) is False
        assert is_secret_key(12345) is False
        assert is_secret_key([]) is False

        # All defined secret patterns
        for key in (
            "PASSWORD", "DB_PASS", "MY_PWD", "SECRET_KEY", "CLIENT_SECRET",
            "API_TOKEN", "ACCESS_TOKEN", "SSH_KEY", "AWS_ACCESS_KEY_ID",
            "AUTH_HEADER", "PRIVATE_KEY", "CREDENTIALS_JSON", "WEBHOOK_SECRET",
        ):
            assert is_secret_key(key) is True
            assert is_secret_key(key.lower()) is True

        # Non-secrets must return False
        for safe_key in (
            "PORT", "DB_PORT", "HOST", "DB_HOST", "DEBUG", "LOG_LEVEL",
            "NODE_ENV", "APP_ENV", "USER", "USERNAME", "TZ", "HOSTNAME",
        ):
            assert is_secret_key(safe_key) is False

    def test_redact_env_text_edge_cases(self):
        # Non-string or empty inputs
        assert redact_env_text(None) is None
        assert redact_env_text("") == ""
        assert redact_env_text(12345) == 12345

        # Empty lines, comments, and mixed casing
        raw = (
            "\n"
            "# Database credentials\n"
            "   # Indented comment\n"
            "DB_HOST=192.168.1.50\n"
            "DB_PORT=5432\n"
            "db_password=unquoted_secret\n"
            "API_KEY=\"quoted_secret_with_equals=xyz\"\n"
            "CUSTOM_SECRET='single_quoted'\n"
            "DEBUG=true\n"
            "\n"
        )
        redacted = redact_env_text(raw)
        assert "# Database credentials" in redacted
        assert "   # Indented comment" in redacted
        assert "DB_HOST=192.168.1.50" in redacted
        assert "DB_PORT=5432" in redacted
        assert "db_password=***REDACTED***" in redacted
        assert "API_KEY=***REDACTED***" in redacted
        assert "CUSTOM_SECRET=***REDACTED***" in redacted
        assert "DEBUG=true" in redacted
        assert "unquoted_secret" not in redacted
        assert "quoted_secret" not in redacted
        assert "single_quoted" not in redacted

        # Export statements
        assert redact_env_text("export AUTH_TOKEN=tok_123") == "export AUTH_TOKEN=***REDACTED***"

        # YAML compose list and dictionary styles
        yaml_env = (
            "services:\n"
            "  web:\n"
            "    environment:\n"
            "      - DB_HOST=postgres\n"
            "      - DB_PASSWORD=my_secret_pw\n"
            "      API_KEY: \"123456\"\n"
            "      JWT_SECRET: super_jwt\n"
            "      APP_PORT: 8080\n"
        )
        redacted_yaml = redact_env_text(yaml_env)
        assert "- DB_HOST=postgres" in redacted_yaml
        assert "- DB_PASSWORD=***REDACTED***" in redacted_yaml
        assert "API_KEY: ***REDACTED***" in redacted_yaml
        assert "JWT_SECRET: ***REDACTED***" in redacted_yaml
        assert "APP_PORT: 8080" in redacted_yaml
        assert "my_secret_pw" not in redacted_yaml
        assert "123456" not in redacted_yaml
        assert "super_jwt" not in redacted_yaml

    def test_redact_url_credentials_edge_cases(self):
        # Non-string or empty inputs
        assert redact_url_credentials(None) is None
        assert redact_url_credentials("") == ""
        assert redact_url_credentials(999) == 999

        # Standard URLs without credentials should remain identical
        assert redact_url_credentials("https://example.com/api/v1") == "https://example.com/api/v1"
        assert redact_url_credentials("http://localhost:8080") == "http://localhost:8080"

        # Basic Auth in URLs
        assert (
            redact_url_credentials("https://admin:SuperSecret123@myhost.net:8443/webhook")
            == "https://admin:***REDACTED***@myhost.net:8443/webhook"
        )

        # Discord Webhooks
        assert (
            redact_url_credentials("https://discord.com/api/webhooks/123456789/abcdefgh-secret-token")
            == "https://discord.com/api/webhooks/123456789/***REDACTED***"
        )
        assert (
            redact_url_credentials("https://discordapp.com/api/webhooks/987654321/xyz-secret")
            == "https://discordapp.com/api/webhooks/987654321/***REDACTED***"
        )

        # Slack Webhooks
        assert (
            redact_url_credentials("https://hooks.slack.com/services/T00000000/B00000000/mock_webhook_token_example")
            == "https://hooks.slack.com/services/T00000000/B00000000/***REDACTED***"
        )

        # Apprise / Notification URIs
        assert redact_url_credentials("discord://123456789/secret_token") == "discord://***REDACTED***"
        assert redact_url_credentials("slack://TokenA/TokenB/TokenC") == "slack://***REDACTED***"
        assert redact_url_credentials("tgram://123456789:ABCDefgh/987654") == "tgram://***REDACTED***"

    def test_redact_sensitive_dict_nested_and_types(self):
        # Primitives pass through safely
        assert redact_sensitive_dict(None) is None
        assert redact_sensitive_dict(123) == 123
        assert redact_sensitive_dict(True) is True
        assert redact_sensitive_dict("hello") == "hello"

        payload = {
            "id": 1,
            "name": "production-stack",
            "status": "active",
            "type": "compose",
            # Direct secret keys
            "webhookSecret": "raw_webhook_sec",
            "clientSecret": "raw_client_sec",
            "bindPassword": "raw_bind_pw",
            "password": "raw_password",
            "token": "raw_token",
            # Nested dictionary with URL credentials
            "config": {
                "serverUrl": "https://vault.corp.internal",
                "webhookUrl": "https://discord.com/api/webhooks/111/secret_token_111",
                "apiKey": "raw_api_key_val",
                "ageKey": "AGE-SECRET-KEY-1...",
            },
            # Dockhand structured envVars shape
            "envVars": [
                {"key": "DB_HOST", "value": "10.0.0.1", "isSecret": False},
                {"key": "DB_PASSWORD", "value": "pg_secret_pw", "isSecret": False},
                {"key": "CUSTOM_VAR", "value": "custom_marked_hidden", "isSecret": True},
            ],
            # Nested list of primitives
            "tags": ["prod", "frontend"],
            # Key-value variables dictionary
            "variables": {
                "PORT": 3000,
                "JWT_SECRET": "jwt_secret_token",
            },
        }

        cleaned = redact_sensitive_dict(payload)

        # Structural metadata preserved
        assert cleaned["id"] == 1
        assert cleaned["name"] == "production-stack"
        assert cleaned["status"] == "active"
        assert cleaned["type"] == "compose"
        assert cleaned["tags"] == ["prod", "frontend"]

        # Secrets masked
        assert cleaned["webhookSecret"] == "***REDACTED***"
        assert cleaned["clientSecret"] == "***REDACTED***"
        assert cleaned["bindPassword"] == "***REDACTED***"
        assert cleaned["password"] == "***REDACTED***"
        assert cleaned["token"] == "***REDACTED***"
        assert cleaned["config"]["serverUrl"] == "https://vault.corp.internal"
        assert cleaned["config"]["webhookUrl"] == "https://discord.com/api/webhooks/111/***REDACTED***"
        assert cleaned["config"]["apiKey"] == "***REDACTED***"
        assert cleaned["config"]["ageKey"] == "***REDACTED***"

        # Structured envVars: DB_HOST preserved, DB_PASSWORD redacted, CUSTOM_VAR (isSecret=True) redacted
        assert cleaned["envVars"][0] == {"key": "DB_HOST", "value": "10.0.0.1", "isSecret": False}
        assert cleaned["envVars"][1] == {"key": "DB_PASSWORD", "value": "***REDACTED***", "isSecret": False}
        assert cleaned["envVars"][2] == {"key": "CUSTOM_VAR", "value": "***REDACTED***", "isSecret": True}

        # Variables map
        assert cleaned["variables"]["PORT"] == 3000
        assert cleaned["variables"]["JWT_SECRET"] == "***REDACTED***"


class TestSecurityHardening:
    """Tests for path traversal, URL scheme validation, redaction edge cases, and tool filtering."""

    def test_encode_path_rejects_dot_segments_and_empty(self):
        import pytest
        from dockhand_mcp.utils import encode_path

        for bad in ("", ".", ".."):
            with pytest.raises(ValueError, match="Invalid path segment"):
                encode_path(bad)
        assert encode_path("my-container") == "my-container"
        assert encode_path("a/b") == "a%2Fb"

    def test_validate_repo_url(self):
        import pytest
        from dockhand_mcp.utils import validate_repo_url

        assert validate_repo_url("https://github.com/org/repo.git") == "https://github.com/org/repo.git"
        assert validate_repo_url("http://git.internal/org/repo.git") == "http://git.internal/org/repo.git"
        assert validate_repo_url("ssh://git@github.com/org/repo.git") == "ssh://git@github.com/org/repo.git"
        assert validate_repo_url("git@github.com:org/repo.git") == "git@github.com:org/repo.git"

        for bad in ("", "file:///etc/passwd", "ext::sh -c id", "fd::3", "ftp://example.com/repo", "not-a-url"):
            with pytest.raises(ValueError):
                validate_repo_url(bad)

    def test_validate_http_url(self):
        import pytest
        from dockhand_mcp.utils import validate_http_url

        assert validate_http_url("https://hooks.slack.com/services/T/B/X") == "https://hooks.slack.com/services/T/B/X"
        for bad in ("", "file:///etc/passwd", "ext::id", "ftp://example.com"):
            with pytest.raises(ValueError):
                validate_http_url(bad, label="webhook_url")

    def test_redact_url_token_userinfo_and_ssh(self):
        assert redact_url_credentials("https://ghp_secret123@github.com/org/repo.git") == "https://***REDACTED***@github.com/org/repo.git"
        assert redact_url_credentials("ssh://git@github.com/org/repo.git") == "ssh://git@github.com/org/repo.git"

    def test_redact_env_text_yaml_block_scalar(self):
        yaml_text = (
            "services:\n"
            "  app:\n"
            "    environment:\n"
            "      DB_PASSWORD: |\n"
            "        super-secret-line-1\n"
            "        super-secret-line-2\n"
            "      APP_PORT: 8080\n"
        )
        redacted = redact_env_text(yaml_text)
        assert "super-secret-line-1" not in redacted
        assert "super-secret-line-2" not in redacted
        assert "APP_PORT: 8080" in redacted

    def test_disable_tools_and_destructive_annotations(self):
        from mcp.server.fastmcp import FastMCP
        from dockhand_mcp.tools import register_all_tools, get_tool_annotations

        mcp = FastMCP("test-disable")
        register_all_tools(mcp, read_only=False, disabled_tools=frozenset({"run_container_exec", "create_user"}))
        tools = mcp._tool_manager._tools
        assert "run_container_exec" not in tools
        assert "create_user" not in tools
        assert "list_containers" in tools

        for tool_name in ("update_stack_env_raw", "rename_container_file", "update_container", "stop_container", "restart_stack"):
            ann = get_tool_annotations(tool_name)
            assert ann.destructiveHint is True, f"{tool_name} should have destructiveHint=True"

    async def test_upload_container_file_rejects_traversal_and_invalid_base64(self, mock_client):
        from unittest.mock import MagicMock
        import pytest
        from dockhand_mcp.tools.containers import upload_container_file

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context = {"dockhand": mock_client}

        for bad_name in ("", ".", "..", "../evil.sh", "sub/evil.sh", "sub\\evil.sh"):
            with pytest.raises(ValueError, match="Invalid upload filename"):
                await upload_container_file(1, "c1", "/tmp", bad_name, "aGVsbG8=", mock_ctx)

        with pytest.raises(ValueError, match="Invalid base64_content"):
            await upload_container_file(1, "c1", "/tmp", "ok.txt", "!!!not-base64!!!", mock_ctx)

    async def test_list_config_sets_redacts_and_create_notification_validates(self, mock_client):
        from unittest.mock import MagicMock
        import pytest
        import respx
        from httpx import Response
        from dockhand_mcp.tools.misc import list_config_sets, create_notification

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context = {"dockhand": mock_client}

        with pytest.raises(ValueError, match="Invalid webhook_url"):
            await create_notification("bad", "file:///etc/passwd", mock_ctx)

        with respx.mock:
            respx.get("http://dockhand.test/api/config-sets").mock(
                return_value=Response(
                    200,
                    json=[{"id": 1, "name": "db", "envVars": [{"key": "DB_PASSWORD", "value": "topsecret", "isSecret": True}]}],
                )
            )
            res = await list_config_sets(mock_ctx)
            assert res[0]["envVars"][0]["value"] == "***REDACTED***"
