"""
Image management tools.
"""

import fnmatch
from typing import Any
from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path, paginate_items, truncate_id, strip_nulls


def _compact_image(img: dict) -> dict:
    """Keep only essential fields for token efficiency."""
    return {
        "Id": truncate_id(img.get("Id") or img.get("id")),
        "RepoTags": img.get("RepoTags") or img.get("repoTags") or [],
        "Size": img.get("Size") or img.get("size"),
        "Created": img.get("Created") or img.get("created")
    }


async def list_images(
    environment_id: int | None = None,
    ctx: Context = None,
    search: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list | dict:
    """List all Docker images in an environment.

    Args:
        environment_id: Environment ID (optional, auto-resolves to default).
        ctx: FastMCP Context.
        search: Optional repo-tag or ID wildcard filter ('*' and '?'), e.g. 'nginx*'.
        limit: Optional maximum number of items to return (returns pagination envelope when set).
        offset: Zero-based starting offset for pagination (default 0).
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    images = await client.get("/api/images", params={"env": await client.resolve_environment_id(environment_id)})
    if isinstance(images, list):
        ordered = sorted(
            images,
            key=lambda i: (-(i.get("Created") or i.get("created") or 0), str(i.get("Id") or i.get("id") or "")),
        )
        if search:
            pat = search.strip().lower()
            ordered = [
                i for i in ordered
                if fnmatch.fnmatchcase(str(i.get("Id") or i.get("id") or "").lower(), pat)
                or fnmatch.fnmatchcase(str(truncate_id(i.get("Id") or i.get("id")) or "").lower(), pat)
                or any(fnmatch.fnmatchcase(str(tag).lower(), pat) for tag in (i.get("RepoTags") or i.get("repoTags") or []))
            ]
        items = [_compact_image(i) for i in ordered]
        return paginate_items(items, limit=limit, offset=offset)
    return images

async def get_image_history(image_id: str, ctx: Context = None, environment_id: int | None = None) -> list:
    if isinstance(image_id, int):
        environment_id, image_id, ctx = image_id, str(ctx), environment_id
    """Get history for an image."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/images/{encode_path(image_id)}/history", 
        params={"env": await client.resolve_environment_id(environment_id)}
    )
    return strip_nulls(data)

async def remove_image(image_id: str, ctx: Context = None, environment_id: int | None = None) -> dict:
    if isinstance(image_id, int):
        environment_id, image_id, ctx = image_id, str(ctx), environment_id
    """Remove/delete an image from the environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(
        f"/api/images/{encode_path(image_id)}", 
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def pull_image(
    image: str,
    ctx: Context = None,
    environment_id: int | None = None,
    scan_after_pull: bool = False,
) -> dict:
    if isinstance(image, int):
        environment_id, image, ctx = image, str(ctx), environment_id
    """
    Pull an image from a registry.
    image: Image name with tag (e.g. nginx:latest)
    scan_after_pull: Whether to scan the image for vulnerabilities after pulling.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {"image": image}
    if scan_after_pull:
        body["scanAfterPull"] = True
        
    return await client.post(
        "/api/images/pull", 
        json=body, 
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def tag_image(
    image_id: str,
    repo: str,
    tag: str,
    ctx: Context = None,
    environment_id: int | None = None,
) -> dict:
    if isinstance(image_id, int):
        environment_id, image_id, repo, tag, ctx = image_id, str(repo), tag, ctx, environment_id
    """Tag an existing image."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(
        f"/api/images/{encode_path(image_id)}/tag", 
        json={"repo": repo, "tag": tag}, 
        params={"env": await client.resolve_environment_id(environment_id)}
    )

async def push_image(
    image_id: str,
    registry_id: int,
    ctx: Context = None,
    environment_id: int | None = None,
    image_name: str | None = None,
    new_tag: str | None = None,
) -> dict:
    if isinstance(image_id, int):
        environment_id, image_id, registry_id, ctx = image_id, str(registry_id), ctx, environment_id
    """Push an image to a registry.
    
    Args:
        image_id: The ID of the image to push (e.g. sha256 or name).
        registry_id: ID of the configured registry in Dockhand.
        ctx: FastMCP Context.
        environment_id: Environment ID (optional; defaults to active environment).
        image_name: Optional original image name.
        new_tag: Custom tag for the pushed image (e.g. username/myapp:v1.0).
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {
        "imageId": image_id,
        "registryId": registry_id
    }
    if image_name:
        body["imageName"] = image_name
    if new_tag:
        body["newTag"] = new_tag
        
    return await client.post(
        "/api/images/push", 
        json=body, 
        params={"env": await client.resolve_environment_id(environment_id)}
    )

def register_image_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_images)
    mcp.add_tool(get_image_history)
    mcp.add_tool(remove_image)
    mcp.add_tool(pull_image)
    mcp.add_tool(tag_image)
    mcp.add_tool(push_image)
