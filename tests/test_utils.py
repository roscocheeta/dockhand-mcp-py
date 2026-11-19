import pytest
from dockhand_mcp.utils import (
    paginate_items,
    parse_memory_bytes,
    parse_since_to_epoch,
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
                "ageKey": "mock_age_key_val_1",
                "age_key": "mock_age_key_val_2",
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


    def test_parse_since_to_epoch(self):
        assert parse_since_to_epoch(None) is None
        assert parse_since_to_epoch("") is None
        assert parse_since_to_epoch("   ") is None
        assert parse_since_to_epoch(1700000000) == 1700000000
        assert parse_since_to_epoch("1700000000") == 1700000000

        # Relative durations with fixed now_epoch = 1000000
        now = 1000000
        assert parse_since_to_epoch("30s", now_epoch=now) == now - 30
        assert parse_since_to_epoch("10m", now_epoch=now) == now - 600
        assert parse_since_to_epoch("1h", now_epoch=now) == now - 3600
        assert parse_since_to_epoch("24h", now_epoch=now) == now - 86400
        assert parse_since_to_epoch("7d", now_epoch=now) == now - 604800
        assert parse_since_to_epoch("2w", now_epoch=now) == now - 1209600

        # ISO 8601 string
        iso_epoch = parse_since_to_epoch("2026-10-31T00:00:00Z")
        assert isinstance(iso_epoch, int)
        assert iso_epoch > 1700000000

        # Invalid formats raise ValueError
        with pytest.raises(ValueError, match="Invalid 'since' value"):
            parse_since_to_epoch("invalid_time")

        with pytest.raises(ValueError, match="Invalid type for 'since'"):
            parse_since_to_epoch(["invalid", "type"])

    def test_paginate_items(self):
        items = [{"id": i} for i in range(5)]
        assert paginate_items(items) == items
        assert paginate_items(items, offset=2) == [{"id": 2}, {"id": 3}, {"id": 4}]

        page1 = paginate_items(items, limit=2, offset=0)
        assert page1 == {
            "items": [{"id": 0}, {"id": 1}],
            "total": 5,
            "limit": 2,
            "offset": 0,
            "hasMore": True,
        }
        page3 = paginate_items(items, limit=2, offset=4)
        assert page3 == {
            "items": [{"id": 4}],
            "total": 5,
            "limit": 2,
            "offset": 4,
            "hasMore": False,
        }

        for bad_offset in (-1, True, "0"):
            with pytest.raises(ValueError, match="Invalid 'offset'"):
                paginate_items(items, limit=2, offset=bad_offset)  # type: ignore[arg-type]

        for bad_limit in (0, -5, True, "2"):
            with pytest.raises(ValueError, match="Invalid 'limit'"):
                paginate_items(items, limit=bad_limit)  # type: ignore[arg-type]

    def test_parse_memory_bytes(self):
        assert parse_memory_bytes(0) == 0
        assert parse_memory_bytes("0") == 0
        assert parse_memory_bytes(1024) == 1024
        assert parse_memory_bytes("512m") == 512 * 1024**2
        assert parse_memory_bytes("512MiB") == 512 * 1024**2
        assert parse_memory_bytes("2g") == 2 * 1024**3
        assert parse_memory_bytes("1.5G") == int(round(1.5 * 1024**3))
        assert parse_memory_bytes("256k") == 256 * 1024
        assert parse_memory_bytes("1tb") == 1024**4
        assert parse_memory_bytes(-1, allow_negative_one=True) == -1
        assert parse_memory_bytes("-1", allow_negative_one=True) == -1
        assert parse_memory_bytes("9007199254740993") == 9007199254740993
        assert parse_memory_bytes("536870912.500000001") == 536870913

        for bad in (-1, -100, True, "", "abc", "512x", "512Mıb", "999999999999999t"):
            with pytest.raises(ValueError, match="Invalid memory value"):
                parse_memory_bytes(bad)  # type: ignore[arg-type]

        for zero_val in (0, "0"):
            with pytest.raises(ValueError, match="Invalid memory value"):
                parse_memory_bytes(zero_val, allow_zero=False)

    def test_utils_remaining_edge_cases(self, monkeypatch):
        from decimal import InvalidOperation
        import dockhand_mcp.utils as utils_mod

        # compact_container_inspect with non-dict input
        assert utils_mod.compact_container_inspect("not-a-dict") == "not-a-dict"  # type: ignore[arg-type]

        # compact_container_inspect preserving non-empty filtered Labels
        inspected = utils_mod.compact_container_inspect(
            {
                "Id": "abcdef1234567890",
                "Name": "/web",
                "Config": {"Image": "nginx", "Labels": {"app": "web", "com.docker.compose.project": "demo"}},
            }
        )
        assert inspected["Config"]["Labels"]["app"] == "web"

        # parse_since_to_epoch with naive ISO-8601 timestamp (no tzinfo -> UTC)
        assert utils_mod.parse_since_to_epoch("2026-10-31T00:00:00") == utils_mod.parse_since_to_epoch(
            "2026-10-31T00:00:00Z"
        )

        # parse_memory_bytes catching InvalidOperation from Decimal
        def _boom(_s):
            raise InvalidOperation("bad decimal")

        monkeypatch.setattr(utils_mod, "Decimal", _boom)
        with pytest.raises(ValueError, match="Invalid memory value"):
            utils_mod.parse_memory_bytes("512m")
