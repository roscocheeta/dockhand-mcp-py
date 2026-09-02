"""
Utility functions for the Dockhand MCP server.
"""

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

def clean_container_inspect(c: dict) -> dict:
    """Deeply clean a container inspect payload for get_container."""
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
        if "Config" in c and isinstance(c["Config"], dict) and "Labels" in c["Config"]:
            c["Config"]["Labels"] = filter_labels(c["Config"]["Labels"])
        elif "config" in c and isinstance(c["config"], dict) and "labels" in c["config"]:
            c["config"]["labels"] = filter_labels(c["config"]["labels"])
    return c
