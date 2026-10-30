"""
Utility functions for the Dockhand MCP server.
"""

import re
import time
from datetime import datetime, timezone
from urllib.parse import quote
from typing import Any


def encode_path(value: str) -> str:
    """
    URI-encode a path parameter value.

    Container IDs, stack names, and other identifiers can contain characters
    that are not safe in URL path segments (e.g. '/', '+', spaces).
    """
    return quote(str(value), safe="")


def truncate_id(id_str: str | None) -> str | None:
    """Truncate a Docker SHA256 ID to 12 characters."""
    if not id_str:
        return id_str
    # If it has a sha256: prefix, remove it before truncating
    if id_str.startswith("sha256:"):
        id_str = id_str[7:]
    return id_str[:12] if len(id_str) > 12 else id_str


def strip_nulls(data: Any) -> Any:
    """Recursively remove None values and empty lists/dicts to save tokens."""
    if isinstance(data, dict):
        return {
            k: strip_nulls(v)
            for k, v in data.items()
            if v is not None and v != [] and v != {}
        }
    elif isinstance(data, list):
        return [strip_nulls(v) for v in data if v is not None and v != [] and v != {}]
    return data


def filter_labels(labels: dict | None) -> dict | None:
    """Strip verbose Docker Compose and Build labels."""
    if not labels:
        return labels
    prefixes_to_strip = ("org.opencontainers.", "com.docker.", "net.nr-ops.", "com.docker.compose.")
    return {
        k: v for k, v in labels.items()
        if not k.startswith(prefixes_to_strip)
    }


# Patterns that indicate a secret value in environment variable keys
_SECRET_KEY_PATTERNS = (
    "PASSWORD", "SECRET", "TOKEN", "KEY", "API_KEY", "APIKEY",
    "PRIVATE", "CREDENTIAL", "AUTH", "PASS", "PWD",
)

# Dict field names (lowercased) that should never be treated as secret values
_NON_SECRET_DICT_KEYS = {
    "key", "name", "id", "type", "authtype", "auth_type", "authenabled",
    "auth_enabled", "tokenprefix", "token_prefix", "injectedsecretkeys",
    "secretproviderid", "secret_provider_id", "haspassword", "hassshkey",
    "hastlskey", "hashawsertoken", "hascredentials", "iskey", "is_secret",
    "issecret",
}

# Patterns that indicate a sensitive dictionary field name (lowercased)
_SENSITIVE_DICT_FIELD_PATTERNS = (
    "password", "secret", "token", "privatekey", "private_key",
    "sshkey", "ssh_key", "tlskey", "tls_key", "passphrase",
    "apikey", "api_key", "credential", "clientsecret", "client_secret",
    "bindpassword", "bind_password", "webhooksecret", "webhook_secret",
    "hawsertoken", "hawser_token", "agekey", "age_key",
)


def is_secret_key(key: str) -> bool:
    """Return True if an environment variable key matches known secret patterns."""
    if not key or not isinstance(key, str):
        return False
    key_upper = key.strip().upper()
    return any(pattern in key_upper for pattern in _SECRET_KEY_PATTERNS)


def redact_env_secrets(env_list: list | None) -> list | None:
    """
    Redact values of environment variables whose keys match secret patterns.
    
    Docker stores env vars as ["KEY=VALUE", ...] strings.
    Returns the list with sensitive values replaced by "***REDACTED***".
    """
    if not env_list or not isinstance(env_list, list):
        return env_list
    
    redacted = []
    for entry in env_list:
        if not isinstance(entry, str) or "=" not in entry:
            redacted.append(entry)
            continue
        key, _, _ = entry.partition("=")
        if is_secret_key(key):
            redacted.append(f"{key}=***REDACTED***")
        else:
            redacted.append(entry)
    return redacted


_ENV_LINE_RE = re.compile(
    r"^(\s*(?:-\s*)?(?:export\s+)?)([\"']?)([A-Za-z_][A-Za-z0-9_]*)(\s*=\s*)(.*)$"
)
_YAML_KV_LINE_RE = re.compile(
    r"^(\s+)([A-Za-z_][A-Za-z0-9_]*)(\s*:\s*)(\S.*)$"
)


def redact_env_text(raw_text: str | None) -> str | None:
    """
    Redact values of secret keys in raw .env content or Docker Compose YAML text.

    Preserves comments, blank lines, indentation, and non-secret values while
    replacing secret values with '***REDACTED***'.
    """
    if not raw_text or not isinstance(raw_text, str):
        return raw_text

    out_lines: list[str] = []
    for line in raw_text.splitlines(keepends=True):
        ending = ""
        body = line
        if body.endswith("\r\n"):
            ending = "\r\n"
            body = body[:-2]
        elif body.endswith("\n"):
            ending = "\n"
            body = body[:-1]

        stripped = body.lstrip()
        if not stripped or stripped.startswith("#"):
            out_lines.append(line)
            continue

        m_env = _ENV_LINE_RE.match(body)
        if m_env:
            prefix, open_q, key, sep, val = m_env.groups()
            if is_secret_key(key):
                close_q = open_q if open_q and val.endswith(open_q) else ""
                out_lines.append(f"{prefix}{open_q}{key}{sep}***REDACTED***{close_q}{ending}")
                continue

        m_yaml = _YAML_KV_LINE_RE.match(body)
        if m_yaml:
            indent, key, sep, val = m_yaml.groups()
            if is_secret_key(key) and not val.startswith(("{", "[")):
                out_lines.append(f"{indent}{key}{sep}***REDACTED***{ending}")
                continue

        out_lines.append(line)

    return "".join(out_lines)


_URL_USERPASS_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*://[^/:@\s]+:)([^@\s]+)(@.*)$")
_WEBHOOK_PATH_RE = re.compile(
    r"(https?://[^/\s]+/(?:api/webhooks/\d+|services/[^/\s]+/[^/\s]+)/)([^\s/?#]+)",
    re.IGNORECASE,
)


def redact_url_credentials(url: str) -> str:
    """Redact credentials or tokens embedded in a URL or Apprise URI."""
    if not isinstance(url, str) or "://" not in url:
        return url

    # Redact scheme://user:pass@host
    m_up = _URL_USERPASS_RE.match(url)
    if m_up:
        url = f"{m_up.group(1)}***REDACTED***{m_up.group(3)}"

    # Redact Discord / Slack webhook token segments in HTTP(S) URLs
    url = _WEBHOOK_PATH_RE.sub(r"\1***REDACTED***", url)

    # Non-HTTP Apprise schemes (e.g. discord://id/token, slack://a/b/c, tgram://bot/chat)
    scheme, _, rest = url.partition("://")
    if scheme.lower() not in ("http", "https", "ws", "wss", "tcp", "unix") and rest:
        return f"{scheme}://***REDACTED***"

    return url


def redact_sensitive_dict(data: Any) -> Any:
    """
    Recursively redact sensitive fields in dicts/lists returned by Dockhand APIs.

    Handles:
    - Structured env var lists (`variables` / `envVars`: `[{'key': ..., 'value': ..., 'isSecret': ...}]`)
    - Dict fields whose names indicate secrets (`webhookSecret`, `clientSecret`, `bindPassword`, etc.)
    - Embedded credentials in notification/webhook URLs (`urls`, `webhookUrl`)
    """
    if isinstance(data, list):
        return [redact_sensitive_dict(item) for item in data]

    if not isinstance(data, dict):
        return data

    # Check if this dict itself is a {key, value} env variable entry
    if "key" in data and "value" in data and isinstance(data.get("key"), str):
        copied = dict(data)
        if copied.get("isSecret") is True or is_secret_key(copied["key"]):
            if copied.get("value") not in (None, "", "***", "***REDACTED***"):
                copied["value"] = "***REDACTED***"
        return copied

    result: dict[str, Any] = {}
    for k, v in data.items():
        k_lower = str(k).lower()

        if isinstance(v, (dict, list)):
            if k_lower in ("urls", "webhook_urls", "webhookurls") and isinstance(v, list):
                result[k] = [redact_url_credentials(u) if isinstance(u, str) else redact_sensitive_dict(u) for u in v]
            else:
                result[k] = redact_sensitive_dict(v)
            continue

        if isinstance(v, str):
            if k_lower in ("url", "webhookurl", "webhook_url") and "://" in v:
                result[k] = redact_url_credentials(v)
                continue

            if (
                k_lower not in _NON_SECRET_DICT_KEYS
                and any(pat in k_lower for pat in _SENSITIVE_DICT_FIELD_PATTERNS)
                and v not in ("", "***", "***REDACTED***", "********")
            ):
                result[k] = "***REDACTED***"
                continue

        result[k] = v

    return result


def clean_container_inspect(c: dict) -> dict:
    """Deeply clean a container inspect payload for get_container and inspect_container."""
    c = strip_nulls(c)
    if isinstance(c, dict):
        if "Id" in c:
            c["Id"] = truncate_id(c["Id"])
        elif "id" in c:
            c["id"] = truncate_id(c["id"])
            
        if "Image" in c and isinstance(c["Image"], str) and c["Image"].startswith("sha256:"):
            c["Image"] = truncate_id(c["Image"])
        elif "image" in c and isinstance(c["image"], str) and c["image"].startswith("sha256:"):
            c["image"] = truncate_id(c["image"])
            
        # Clean labels in Config
        if "Config" in c and isinstance(c["Config"], dict):
            if "Labels" in c["Config"]:
                c["Config"]["Labels"] = filter_labels(c["Config"]["Labels"])
            if "Env" in c["Config"]:
                c["Config"]["Env"] = redact_env_secrets(c["Config"]["Env"])
        elif "config" in c and isinstance(c["config"], dict):
            if "labels" in c["config"]:
                c["config"]["labels"] = filter_labels(c["config"]["labels"])
            if "env" in c["config"]:
                c["config"]["env"] = redact_env_secrets(c["config"]["env"])
    return c

def compact_container_inspect(c: dict) -> dict:
    """Extract essential runtime info, omitting bulky Docker engine internals to save tokens."""
    if not isinstance(c, dict):
        return c

    c = clean_container_inspect(c)
    res: dict[str, Any] = {
        "Id": truncate_id(c.get("Id") or c.get("id")),
        "Name": (c.get("Name") or c.get("name") or "").lstrip("/"),
        "Image": truncate_id(c.get("Image") or c.get("image")),
        "Created": c.get("Created") or c.get("created"),
        "State": c.get("State") or c.get("state"),
        "Status": c.get("Status") or c.get("status"),
        "RestartCount": c.get("RestartCount") or c.get("restartCount"),
    }

    cfg = c.get("Config") or c.get("config") or {}
    if isinstance(cfg, dict):
        res["Config"] = {
            "Image": cfg.get("Image") or cfg.get("image"),
            "Env": redact_env_secrets(cfg.get("Env") or cfg.get("env")),
            "Cmd": cfg.get("Cmd") or cfg.get("cmd"),
            "WorkingDir": cfg.get("WorkingDir") or cfg.get("workingDir"),
        }
        labels = filter_labels(cfg.get("Labels") or cfg.get("labels"))
        if labels:
            res["Config"]["Labels"] = labels

    hc = c.get("HostConfig") or c.get("hostConfig") or {}
    if isinstance(hc, dict):
        res["HostConfig"] = {
            "RestartPolicy": hc.get("RestartPolicy") or hc.get("restartPolicy"),
            "PortBindings": hc.get("PortBindings") or hc.get("portBindings"),
            "AutoRemove": hc.get("AutoRemove") or hc.get("autoRemove"),
        }

    mounts = c.get("Mounts") or c.get("mounts")
    if isinstance(mounts, list):
        res["Mounts"] = [
            {
                "Type": m.get("Type") or m.get("type"),
                "Source": m.get("Source") or m.get("source"),
                "Destination": m.get("Destination") or m.get("destination"),
                "Mode": m.get("Mode") or m.get("mode"),
                "RW": m.get("RW") or m.get("rw"),
            }
            for m in mounts
            if isinstance(m, dict)
        ]

    ns = c.get("NetworkSettings") or c.get("networkSettings") or {}
    if isinstance(ns, dict):
        nets = ns.get("Networks") or ns.get("networks") or {}
        res["NetworkSettings"] = {
            "Ports": ns.get("Ports") or ns.get("ports"),
            "Networks": {
                net_name: {
                    "IPAddress": net_info.get("IPAddress") or net_info.get("ipAddress"),
                    "Gateway": net_info.get("Gateway") or net_info.get("gateway"),
                    "Aliases": net_info.get("Aliases") or net_info.get("aliases"),
                }
                for net_name, net_info in nets.items()
                if isinstance(net_info, dict)
            },
        }

    return strip_nulls(res)


_DURATION_RE = re.compile(r"^(\d+)\s*([smhdw])$", re.IGNORECASE)
_DURATION_MULTIPLIERS = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
    "w": 604800,
}


def parse_since_to_epoch(since: str | int | None, now_epoch: int | None = None) -> int | None:
    """
    Parse a 'since' filter value into an integer Unix epoch timestamp (seconds).

    Dockhand's log endpoint forwards 'since' to Go's strconv.ParseInt, requiring
    an integer epoch timestamp. Passing relative durations like '1h' directly to
    Dockhand causes an HTTP 500.

    Supports:
    - None -> None
    - int (e.g. 1714400000) -> 1714400000
    - Numeric string (e.g. '1714400000') -> 1714400000
    - Relative duration (e.g. '30s', '10m', '1h', '24h', '7d', '2w') -> calculated epoch from now
    - ISO 8601 timestamp (e.g. '2026-10-31T00:00:00Z') -> parsed epoch seconds
    """
    if since is None:
        return None
    if isinstance(since, int):
        return since
    if not isinstance(since, str):
        raise ValueError(f"Invalid type for 'since': expected str or int, got {type(since).__name__}")

    s = since.strip()
    if not s:
        return None

    if s.isdigit():
        return int(s)

    m = _DURATION_RE.match(s)
    if m:
        val = int(m.group(1))
        unit = m.group(2).lower()
        multiplier = _DURATION_MULTIPLIERS[unit]
        base_now = int(time.time()) if now_epoch is None else now_epoch
        return base_now - (val * multiplier)

    try:
        iso_str = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except (ValueError, TypeError):
        pass

    raise ValueError(
        f"Invalid 'since' value '{since}'. Expected an integer Unix epoch (e.g. 1714400000), "
        "a relative duration (e.g. '30m', '1h', '24h', '7d'), or an ISO 8601 timestamp."
    )
