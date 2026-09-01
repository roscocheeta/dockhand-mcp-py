"""
Image management tools.
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import encode_path


def register_image_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_images(environment_id: int, ctx: Context) -> list:
        """List all Docker images in an environment."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get("/api/images", params={"env": environment_id})

    @mcp.tool()
    async def get_image_history(environment_id: int, image_id: str, ctx: Context) -> list:
        """Get the history of an image."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.get(
            f"/api/images/{encode_path(image_id)}/history", 
            params={"env": environment_id}
        )

    @mcp.tool()
    async def remove_image(environment_id: int, image_id: str, ctx: Context) -> dict:
        """Remove/delete an image from the environment."""
        client = ctx.request_context.lifespan_context["dockhand"]
        return await client.delete(
            f"/api/images/{encode_path(image_id)}", 
            params={"env": environment_id}
        )

    @mcp.tool()
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

    @mcp.tool()
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
