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
            redact_url_credentials("https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX")
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
