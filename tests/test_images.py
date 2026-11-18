import json
import pytest
import respx
from httpx import Response
from dockhand_mcp.tools.images import (
    list_images,
    get_image_history,
    remove_image,
    pull_image,
    tag_image,
    push_image,
)


class MockRequestContext:
    def __init__(self, client):
        self.lifespan_context = {"dockhand": client}


class MockContext:
    def __init__(self, client):
        self.request_context = MockRequestContext(client)


@pytest.fixture
def mock_ctx(mock_client):
    return MockContext(mock_client)


@pytest.mark.asyncio
async def test_list_images_and_history(mock_client, mock_ctx):
    mock_images = [
        {
            "Id": "sha256:1234567890abcdef1234567890abcdef",
            "RepoTags": ["nginx:latest"],
            "Size": 142000000,
            "Created": 1700000000,
            "Labels": {"extra": "ignored"},
        }
    ]
    with respx.mock:
        list_route = respx.get("http://dockhand.test/api/images?env=1").mock(
            return_value=Response(200, json=mock_images)
        )
        hist_route = respx.get("http://dockhand.test/api/images/nginx%3Alatest/history?env=1").mock(
            return_value=Response(200, json=[{"Id": "123", "CreatedBy": "/bin/sh", "Comment": None}])
        )

        imgs = await list_images(environment_id=1, ctx=mock_ctx)
        assert list_route.called
        assert len(imgs) == 1
        assert imgs[0]["Id"] == "1234567890ab"
        assert imgs[0]["RepoTags"] == ["nginx:latest"]
        assert "Labels" not in imgs[0]

        hist = await get_image_history(environment_id=1, image_id="nginx:latest", ctx=mock_ctx)
        assert hist_route.called
        assert hist == [{"Id": "123", "CreatedBy": "/bin/sh"}]


@pytest.mark.asyncio
async def test_image_lifecycle_pull_tag_push_remove(mock_client, mock_ctx):
    with respx.mock:
        pull_route = respx.post("http://dockhand.test/api/images/pull?env=1").mock(
            return_value=Response(200, json={"success": True})
        )
        tag_route = respx.post("http://dockhand.test/api/images/sha256%3A123/tag?env=1").mock(
            return_value=Response(200, json={"success": True})
        )
        push_route = respx.post("http://dockhand.test/api/images/push?env=1").mock(
            return_value=Response(200, json={"success": True})
        )
        rm_route = respx.delete("http://dockhand.test/api/images/sha256%3A123?env=1").mock(
            return_value=Response(200, json={"deleted": True})
        )

        pulled = await pull_image(environment_id=1, image="redis:alpine", ctx=mock_ctx, scan_after_pull=True)
        assert pull_route.called
        assert json.loads(pull_route.calls.last.request.content) == {"image": "redis:alpine", "scanAfterPull": True}
        assert pulled["success"] is True

        tagged = await tag_image(environment_id=1, image_id="sha256:123", repo="myrepo/redis", tag="v1", ctx=mock_ctx)
        assert tag_route.called
        assert json.loads(tag_route.calls.last.request.content) == {"repo": "myrepo/redis", "tag": "v1"}
        assert tagged["success"] is True

        pushed = await push_image(
            environment_id=1,
            image_id="sha256:123",
            registry_id=2,
            ctx=mock_ctx,
            image_name="redis",
            new_tag="myrepo/redis:v1",
        )
        assert push_route.called
        assert json.loads(push_route.calls.last.request.content) == {
            "imageId": "sha256:123",
            "registryId": 2,
            "imageName": "redis",
            "newTag": "myrepo/redis:v1",
        }
        assert pushed["success"] is True

        removed = await remove_image(environment_id=1, image_id="sha256:123", ctx=mock_ctx)
        assert rm_route.called
        assert removed["deleted"] is True


@pytest.mark.asyncio
async def test_list_images_search_and_pagination(mock_client, mock_ctx):
    mock_images = [
        {"Id": f"sha256:{i:012x}0000", "RepoTags": [f"app/img-{i}:latest"], "Size": 1000, "Created": 1700000000}
        for i in reversed(range(4))
    ]
    with respx.mock:
        respx.get("http://dockhand.test/api/images?env=1").mock(
            return_value=Response(200, json=mock_images)
        )
        res = await list_images(environment_id=1, ctx=mock_ctx, search="app/img-*", limit=2, offset=1)
        assert res["total"] == 4
        assert res["hasMore"] is True
        assert [i["RepoTags"][0] for i in res["items"]] == ["app/img-1:latest", "app/img-2:latest"]

        # Raw full-ID search (beyond 12-char truncation)
        res_raw_id = await list_images(environment_id=1, ctx=mock_ctx, search="*00020000", limit=5, offset=0)
        assert res_raw_id["total"] == 1
        assert res_raw_id["items"][0]["RepoTags"] == ["app/img-2:latest"]
