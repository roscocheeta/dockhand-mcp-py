from typing import Any
from mcp.server.fastmcp import Context
from dockhand_mcp.utils import encode_path

async def list_tags(ctx: Context = None) -> list:
    """List all tags in the global catalog."""
    client = ctx.request_context.lifespan_context['dockhand']
    data = await client.get('/api/tags')
    return data.get('tags', [])

async def create_tag(name: str, color: str, icon: str | None = None, ctx: Context = None) -> dict:
    """Create a tag in the global catalog (requires admin privileges)."""
    client = ctx.request_context.lifespan_context['dockhand']
    payload = {'name': name, 'color': color}
    if icon is not None:
        payload['icon'] = icon
    return await client.post('/api/tags', json=payload)

async def update_tag(tag_id: int, name: str | None = None, color: str | None = None, icon: str | None = None, ctx: Context = None) -> dict:
    """Update a tag in the global catalog (requires admin privileges)."""
    client = ctx.request_context.lifespan_context['dockhand']
    payload = {}
    if name is not None:
        payload['name'] = name
    if color is not None:
        payload['color'] = color
    if icon is not None:
        payload['icon'] = icon
    return await client.put(f'/api/tags/{encode_path(str(tag_id))}', json=payload)

async def delete_tag(tag_id: int, ctx: Context = None) -> dict:
    """Delete a tag from the global catalog (requires admin privileges)."""
    client = ctx.request_context.lifespan_context['dockhand']
    return await client.delete(f'/api/tags/{encode_path(str(tag_id))}')

async def get_stack_tags(name: str, ctx: Context = None, environment_id: int | None = None) -> list[int]:
    if isinstance(name, int):
        environment_id, name, ctx = name, str(ctx), environment_id
    """Get the tag IDs assigned to a stack."""
    client = ctx.request_context.lifespan_context['dockhand']
    data = await client.get(
        f'/api/stacks/{encode_path(name)}/tags', 
        params={'env': await client.resolve_environment_id(environment_id)}
    )
    return data.get('tagIds', [])

async def set_stack_tags(name: str, tag_ids: list[int] = None, ctx: Context = None, environment_id: int | None = None) -> list[int]:
    if isinstance(name, int):
        environment_id, name, tag_ids, ctx = name, str(tag_ids), ctx, environment_id
    """Replace the tag IDs assigned to a stack."""
    client = ctx.request_context.lifespan_context['dockhand']
    data = await client.put(
        f'/api/stacks/{encode_path(name)}/tags',
        json={'tagIds': tag_ids or []},
        params={'env': await client.resolve_environment_id(environment_id)}
    )
    return data.get('tagIds', [])

def register_tag_tools(mcp) -> None:
    mcp.add_tool(list_tags)
    mcp.add_tool(create_tag)
    mcp.add_tool(update_tag)
    mcp.add_tool(delete_tag)
    mcp.add_tool(get_stack_tags)
    mcp.add_tool(set_stack_tags)
