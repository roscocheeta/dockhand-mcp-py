import pytest
import respx
from httpx import Response
from dockhand_mcp.tools.tags import list_tags, create_tag, update_tag, delete_tag

class MockContext:
    def __init__(self, client):
        class LifespanContext:
            def __init__(self, client):
                self.lifespan_context = {"dockhand": client}
        self.request_context = LifespanContext(client)

@pytest.mark.asyncio
async def test_list_tags(mock_client):
    mock_ctx = MockContext(mock_client)
    with respx.mock:
        route = respx.get('http://dockhand.test/api/tags').mock(
            return_value=Response(200, json={'tags': [{'id': 1, 'name': 'test'}]})
        )
        result = await list_tags(ctx=mock_ctx)
        assert route.called
        assert len(result) == 1
        assert result[0]['name'] == 'test'

@pytest.mark.asyncio
async def test_create_tag(mock_client):
    mock_ctx = MockContext(mock_client)
    with respx.mock:
        route = respx.post('http://dockhand.test/api/tags').mock(
            return_value=Response(200, json={'id': 2, 'name': 'new', 'color': 'red', 'icon': 'star'})
        )
        result = await create_tag(name='new', color='red', icon='star', ctx=mock_ctx)
        assert route.called
        assert result['id'] == 2

@pytest.mark.asyncio
async def test_update_tag(mock_client):
    mock_ctx = MockContext(mock_client)
    with respx.mock:
        route = respx.put('http://dockhand.test/api/tags/2').mock(
            return_value=Response(200, json={'success': True})
        )
        result = await update_tag(tag_id=2, color='blue', ctx=mock_ctx)
        assert route.called
        assert result['success'] is True

@pytest.mark.asyncio
async def test_delete_tag(mock_client):
    mock_ctx = MockContext(mock_client)
    with respx.mock:
        route = respx.delete('http://dockhand.test/api/tags/2').mock(
            return_value=Response(200, json={'success': True})
        )
        result = await delete_tag(tag_id=2, ctx=mock_ctx)
        assert route.called
        assert result['success'] is True
