import pytest
from dockhand_mcp.utils import redact_env_secrets, clean_container_inspect, strip_nulls, filter_labels, truncate_id

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
