"""
FastMCP schema, signature, and end-to-end tool dispatch contract tests.

Ensures every registered MCP tool can be validated and invoked through FastMCP's
Pydantic arg_model and tool_manager.call_tool() without phantom *args/**kwargs
or leaked Context parameters.
"""

import inspect
from typing import Any
from unittest.mock import MagicMock

import pytest
import respx
from httpx import Response
from mcp.server.fastmcp import FastMCP

from dockhand_mcp.tools import register_all_tools


def _dummy_value_for_schema(prop_schema: dict[str, Any]) -> Any:
    """Return a minimal valid dummy value for a JSON Schema property."""
    if "anyOf" in prop_schema:
        for branch in prop_schema["anyOf"]:
            if branch.get("type") != "null":
                return _dummy_value_for_schema(branch)
        return None
    t = prop_schema.get("type")
    if t == "string":
        return "test-value"
    if t == "integer":
        return 1
    if t == "number":
        return 1.0
    if t == "boolean":
        return False
    if t == "array":
        return []
    if t == "object":
        return {}
    return "test-value"


class TestMCPToolSchemaContracts:
    """Contract tests across all registered FastMCP tools."""

    def test_all_tool_signatures_and_schemas_are_valid(self):
        mcp = FastMCP("contract-check")
        register_all_tools(mcp, read_only=False, disabled_tools=frozenset())
        tools = mcp._tool_manager._tools
        assert len(tools) == 182

        for name, tool in tools.items():
            # 1. No variadic *args or **kwargs in Python signature
            sig = inspect.signature(tool.fn)
            for param_name, param in sig.parameters.items():
                assert param.kind not in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                ), f"Tool {name!r} has variadic parameter {param_name!r} ({param.kind.name})"

            # 2. No phantom args/kwargs or leaked ctx in generated JSON Schema
            props = tool.parameters.get("properties", {})
            req = tool.parameters.get("required", [])
            for forbidden in ("args", "kwargs", "ctx"):
                assert forbidden not in props, f"Tool {name!r} exposes {forbidden!r} in properties"
                assert forbidden not in req, f"Tool {name!r} requires {forbidden!r} in schema"

            # 3. Non-empty description and valid ToolAnnotations
            assert isinstance(tool.description, str) and tool.description.strip(), (
                f"Tool {name!r} is missing a description"
            )
            assert tool.annotations is not None, f"Tool {name!r} is missing ToolAnnotations"

            # 4. Pydantic arg_model validates minimal required arguments
            minimal_args = {
                req_key: _dummy_value_for_schema(props[req_key])
                for req_key in req
            }
            validated = tool.fn_metadata.arg_model.model_validate(minimal_args)
            assert validated is not None


class TestMCPToolDispatchEndToEnd:
    """End-to-end dispatch tests through FastMCP's tool_manager.call_tool()."""

    @pytest.mark.asyncio
    async def test_dispatch_representative_tools_through_fastmcp(self, mock_client):
        mcp = FastMCP("dispatch-check")
        register_all_tools(mcp, read_only=False, disabled_tools=frozenset())

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context = {"dockhand": mock_client}

        with respx.mock:
            respx.get("http://dockhand.test/api/health").mock(
                return_value=Response(200, json={"status": "ok"})
            )
            respx.get("http://dockhand.test/api/containers?env=1").mock(
                return_value=Response(
                    200,
                    json=[{"id": "c1", "Names": ["/web"], "Image": "nginx", "State": "running", "Status": "Up"}],
                )
            )
            respx.get(respx.patterns.M("http://dockhand.test/api/containers/c1/logs")).mock(
                return_value=Response(200, json={"logs": "hello\n"})
            )
            respx.post("http://dockhand.test/api/containers/c1/update-runtime?env=1").mock(
                return_value=Response(200, json={"success": True, "warnings": []})
            )
            respx.get("http://dockhand.test/api/stacks?env=1").mock(
                return_value=Response(
                    200,
                    json=[{"id": 1, "name": "app", "status": "running", "environmentId": 1}],
                )
            )
            respx.get("http://dockhand.test/api/git/stacks").mock(
                return_value=Response(
                    200,
                    json=[{"id": 33, "stackName": "radarr", "syncStatus": "synced"}],
                )
            )
            respx.post("http://dockhand.test/api/git/stacks/33/sync").mock(
                return_value=Response(200, json={"success": True, "commit": "abc", "updated": False})
            )
            respx.post("http://dockhand.test/api/git/stacks/33/deploy-stream").mock(
                return_value=Response(
                    200,
                    text='data: {"success": true}\n\n',
                    headers={"Content-Type": "text/event-stream"},
                )
            )
            respx.get("http://dockhand.test/api/images?env=1").mock(
                return_value=Response(200, json=[{"Id": "sha256:1234567890ab", "RepoTags": ["nginx:latest"]}])
            )
            respx.get("http://dockhand.test/api/networks?env=1").mock(
                return_value=Response(200, json=[{"Id": "n1", "Name": "bridge", "Driver": "bridge", "Scope": "local"}])
            )
            respx.get("http://dockhand.test/api/volumes?env=1").mock(
                return_value=Response(200, json={"Volumes": [{"Name": "v1", "Driver": "local", "Mountpoint": "/v1"}]})
            )
            respx.put("http://dockhand.test/api/preferences/language").mock(
                return_value=Response(200, json={"language": "ko"})
            )

            health = await mcp._tool_manager.call_tool("health_check", {}, context=mock_ctx)
            assert health == {"status": "ok"}

            containers = await mcp._tool_manager.call_tool(
                "list_containers", {"environment_id": 1, "limit": 10, "offset": 0}, context=mock_ctx
            )
            assert containers["total"] == 1

            logs = await mcp._tool_manager.call_tool(
                "get_container_logs", {"container_id": "c1", "environment_id": 1, "tail": 5}, context=mock_ctx
            )
            assert logs == "hello\n"

            rt = await mcp._tool_manager.call_tool(
                "update_container_runtime", {"container_id": "c1", "environment_id": 1, "memory": "256m"}, context=mock_ctx
            )
            assert rt["success"] is True

            stacks = await mcp._tool_manager.call_tool(
                "list_stacks", {"environment_id": 1, "limit": 5, "offset": 0}, context=mock_ctx
            )
            assert stacks["total"] == 1

            git_sync = await mcp._tool_manager.call_tool(
                "sync_and_deploy_git_stack", {"stack_id": "radarr"}, context=mock_ctx
            )
            assert git_sync["sync"]["success"] is True
            assert git_sync["deploy"]["success"] is True

            imgs = await mcp._tool_manager.call_tool(
                "list_images", {"environment_id": 1, "limit": 5}, context=mock_ctx
            )
            assert imgs["total"] == 1

            nets = await mcp._tool_manager.call_tool(
                "list_networks", {"environment_id": 1, "limit": 5}, context=mock_ctx
            )
            assert nets["total"] == 1

            vols = await mcp._tool_manager.call_tool(
                "list_volumes", {"environment_id": 1, "limit": 5}, context=mock_ctx
            )
            assert vols["total"] == 1

            lang = await mcp._tool_manager.call_tool(
                "set_language_preference", {"language": "ko"}, context=mock_ctx
            )
            assert lang == {"language": "ko"}


class TestRegistrarAndServerEntrypoint:
    """Tests for ToolRegistrar decorator/delegation and server.py helpers."""

    def test_tool_registrar_decorator_and_getattr(self):
        from dockhand_mcp.tools import _AnnotatedToolRegistrar

        mcp = FastMCP("registrar-check")
        registrar = _AnnotatedToolRegistrar(mcp, read_only=False, disabled_tools=frozenset())

        @registrar.tool(name="custom_ping")
        async def ping() -> str:
            """Ping tool."""
            return "pong"

        assert "custom_ping" in mcp._tool_manager._tools
        assert registrar.name == "registrar-check"

    def test_server_get_client_and_main(self, monkeypatch, mock_client):
        from dockhand_mcp import server

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context = {"dockhand": mock_client}
        assert server._get_client(mock_ctx) is mock_client

        called = []
        monkeypatch.setattr(server.mcp, "run", lambda: called.append(True))
        server.main()
        assert called == [True]
