"""
Image management tools.
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path, truncate_id, strip_nulls


def _compact_image(img: dict) -> dict:
    """Keep only essential fields for token efficiency."""
    return {
        "Id": truncate_id(img.get("Id") or img.get("id")),
        "RepoTags": img.get("RepoTags") or img.get("repoTags") or [],
        "Size": img.get("Size") or img.get("size"),
        "Created": img.get("Created") or img.get("created")
    }


async def list_images(environment_id: int, ctx: Context) -> list:
    """List all Docker images in an environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    images = await client.get("/api/images", params={"env": environment_id})
    if isinstance(images, list):
        return [_compact_image(i) for i in images]
    return images

async def get_image_history(environment_id: int, image_id: str, ctx: Context) -> list:
    """Get history for an image."""
    client = ctx.request_context.lifespan_context["dockhand"]
    data = await client.get(
        f"/api/images/{encode_path(image_id)}/history", 
        params={"env": environment_id}
    )
    return strip_nulls(data)

async def remove_image(environment_id: int, image_id: str, ctx: Context) -> dict:
    """Remove/delete an image from the environment."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(
        f"/api/images/{encode_path(image_id)}", 
        params={"env": environment_id}
    )

async def pull_image(environment_id: int, image: str, ctx: Context) -> dict:
    """
    Pull an image from a registry.
    image: Image name with tag (e.g. nginx:latest)
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(
        "/api/images/pull", 
        json={"image": image}, 
        params={"env": environment_id}
    )

async def tag_image(
    environment_id: int, 
    image_id: str, 
    repo: str, 
    tag: str, 
    ctx: Context
) -> dict:
    """Tag an existing image."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(
        f"/api/images/{encode_path(image_id)}/tag", 
        json={"repo": repo, "tag": tag}, 
        params={"env": environment_id}
    )

def register_image_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_images)
    mcp.add_tool(get_image_history)
    mcp.add_tool(remove_image)
    mcp.add_tool(pull_image)
    mcp.add_tool(tag_image)
