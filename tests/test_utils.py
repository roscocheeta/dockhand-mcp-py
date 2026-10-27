import pytest
from dockhand_mcp.utils import (
    redact_env_secrets,
    is_secret_key,
    redact_env_text,
    redact_url_credentials,
    redact_sensitive_dict,
    clean_container_inspect,
    strip_nulls,
    filter_labels,
    truncate_id,
)

class TestUtils:
    def test_truncate_id(self):
        assert truncate_id(None) is None
        assert truncate_id("12345") == "12345"
        assert truncate_id("sha256:abc123def456ghi789jkl") == "abc123def456"
        assert truncate_id("abc123def456ghi789jkl") == "abc123def456"

    def test_strip_nulls(self):
        data = {
            "a": 1,
            "b": None,
            "c": [],
            "d": {},
            "e": {"nested_none": None, "nested_val": 2},
            "f": [1, None, 2, []]
        }
        cleaned = strip_nulls(data)
        assert cleaned == {
            "a": 1,
            "e": {"nested_val": 2},
            "f": [1, 2]
        }

    def test_filter_labels(self):
        assert filter_labels(None) is None
        assert filter_labels({}) == {}
        labels = {
            "org.opencontainers.image.version": "1.0",
            "com.docker.compose.project": "dockhand",
            "net.nr-ops.monitor": "true",
            "my.custom.label": "keep_this",
            "app.name": "nginx"
        }
        filtered = filter_labels(labels)
        assert filtered == {
            "my.custom.label": "keep_this",
            "app.name": "nginx"
        }

    def test_redact_env_secrets(self):
        assert redact_env_secrets(None) is None
        assert redact_env_secrets("not-a-list") == "not-a-list"
        env = [
            "DB_HOST=127.0.0.1",
            "DB_PASSWORD=supersecret",
            "API_KEY=12345",
            "NOT_A_SECRET=safe_value",
            "my_token=abcde",
            "SOMETHING_ELSE" # no equals sign
        ]
        redacted = redact_env_secrets(env)
        assert redacted == [
            "DB_HOST=127.0.0.1",
            "DB_PASSWORD=***REDACTED***",
            "API_KEY=***REDACTED***",
            "NOT_A_SECRET=***REDACTED***",
            "my_token=***REDACTED***",
            "SOMETHING_ELSE"
        ]

    def test_clean_container_inspect_titlecase(self):
        inspect = {
            "Id": "abc123def456ghi789jkl",
            "Image": "sha256:111222333444",
            "Config": {
                "Env": [
                    "AWS_SECRET_ACCESS_KEY=my_secret"
                ],
                "Labels": {
                    "com.docker.compose.service": "web",
                    "safe": "yes"
                }
            }
        }
        cleaned = clean_container_inspect(inspect)
        assert cleaned["Id"] == "abc123def456"
        assert cleaned["Image"] == "111222333444"
        assert cleaned["Config"]["Env"][0] == "AWS_SECRET_ACCESS_KEY=***REDACTED***"
        assert cleaned["Config"]["Labels"] == {"safe": "yes"}

    def test_clean_container_inspect_lowercase(self):
        inspect = {
            "id": "abc123def456ghi789jkl",
            "image": "sha256:111222333444",
            "config": {
                "env": [
                    "AWS_SECRET_ACCESS_KEY=my_secret"
                ],
                "labels": {
                    "com.docker.compose.service": "web",
                    "safe": "yes"
                }
            }
        }
        cleaned = clean_container_inspect(inspect)
        assert cleaned["id"] == "abc123def456"
        assert cleaned["image"] == "111222333444"
        assert cleaned["config"]["env"][0] == "AWS_SECRET_ACCESS_KEY=***REDACTED***"
        assert cleaned["config"]["labels"] == {"safe": "yes"}

    def test_is_secret_key(self):
        assert is_secret_key("DB_PASSWORD") is True
        assert is_secret_key("api_key") is True
        assert is_secret_key("WEBHOOK_SECRET") is True
        assert is_secret_key("auth_token") is True
        assert is_secret_key("DB_HOST") is False
        assert is_secret_key("PORT") is False

    def test_redact_env_text_dotenv_and_yaml(self):
        dotenv_text = (
            "# Comment line\n"
            "DB_HOST=postgres\n"
            "DB_PASSWORD=supersecret\n"
            "export API_TOKEN=xyz123\n"
        )
        redacted_dotenv = redact_env_text(dotenv_text)
        assert "# Comment line" in redacted_dotenv
        assert "DB_HOST=postgres" in redacted_dotenv
        assert "DB_PASSWORD=***REDACTED***" in redacted_dotenv
        assert "export API_TOKEN=***REDACTED***" in redacted_dotenv
        assert "supersecret" not in redacted_dotenv
        assert "xyz123" not in redacted_dotenv

        yaml_text = (
            "services:\n"
            "  app:\n"
            "    image: myapp:latest\n"
            "    environment:\n"
            "      - DB_HOST=postgres\n"
            "      - DB_PASSWORD=my_secret_pw\n"
            "      API_KEY: \"123456\"\n"
            "      APP_PORT: 8080\n"
        )
        redacted_yaml = redact_env_text(yaml_text)
        assert "- DB_HOST=postgres" in redacted_yaml
        assert "- DB_PASSWORD=***REDACTED***" in redacted_yaml
        assert "API_KEY: ***REDACTED***" in redacted_yaml
        assert "APP_PORT: 8080" in redacted_yaml
        assert "my_secret_pw" not in redacted_yaml
        assert "123456" not in redacted_yaml

    def test_redact_env_text_crlf(self):
        crlf_text = "DB_HOST=postgres\r\nDB_PASSWORD=supersecret\r\n"
        redacted = redact_env_text(crlf_text)
        assert redacted == "DB_HOST=postgres\r\nDB_PASSWORD=***REDACTED***\r\n"

    def test_redact_url_credentials(self):
        assert redact_url_credentials("https://user:s3cr3t@example.com/hook") == "https://user:***REDACTED***@example.com/hook"
        assert redact_url_credentials("https://discord.com/api/webhooks/12345/abcdefg") == "https://discord.com/api/webhooks/12345/***REDACTED***"
        assert redact_url_credentials("https://hooks.slack.com/services/T000/B000/XXXX") == "https://hooks.slack.com/services/T000/B000/***REDACTED***"
        assert redact_url_credentials("discord://12345/secret_tok") == "discord://***REDACTED***"
        assert redact_url_credentials("https://example.com/public/status") == "https://example.com/public/status"

    def test_redact_sensitive_dict(self):
        payload = {
            "id": 1,
            "name": "my-stack",
            "webhookSecret": "wh_sec_123",
            "config": {
                "serverUrl": "https://vault.example.com",
                "secretKey": "vault_key_abc",
                "webhookUrl": "https://discord.com/api/webhooks/999/secret_hook_token",
                "ageKey": "AGE-SECRET-KEY-1PQ...",
                "age_key": "AGE-SECRET-KEY-2PQ...",
            },
            "envVars": [
                {"key": "DB_HOST", "value": "localhost", "isSecret": False},
                {"key": "DB_PASSWORD", "value": "pw123", "isSecret": False},
                {"key": "CUSTOM_VAR", "value": "hidden_val", "isSecret": True},
            ],
            "variables": {
                "PORT": "8080",
                "JWT_SECRET": "jwt_super_secret",
            },
        }
        cleaned = redact_sensitive_dict(payload)
        assert cleaned["id"] == 1
        assert cleaned["name"] == "my-stack"
        assert cleaned["webhookSecret"] == "***REDACTED***"
        assert cleaned["config"]["serverUrl"] == "https://vault.example.com"
        assert cleaned["config"]["secretKey"] == "***REDACTED***"
        assert cleaned["config"]["webhookUrl"] == "https://discord.com/api/webhooks/999/***REDACTED***"
        assert cleaned["config"]["ageKey"] == "***REDACTED***"
        assert cleaned["config"]["age_key"] == "***REDACTED***"
        # Check envVars items: key names preserved, secret values redacted
        assert cleaned["envVars"][0] == {"key": "DB_HOST", "value": "localhost", "isSecret": False}
        assert cleaned["envVars"][1] == {"key": "DB_PASSWORD", "value": "***REDACTED***", "isSecret": False}
        assert cleaned["envVars"][2] == {"key": "CUSTOM_VAR", "value": "***REDACTED***", "isSecret": True}
        assert cleaned["variables"]["PORT"] == "8080"
        assert cleaned["variables"]["JWT_SECRET"] == "***REDACTED***"
