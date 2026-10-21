import pytest
import respx
from httpx import Response
from dockhand_mcp.client import DockhandClient, DockhandAPIError
from dockhand_mcp.tools.containers import (
    run_container_exec,
    get_container_file_content,
    get_container_logs,
    list_containers,
    create_container,
    update_container,
    create_container_path,
    write_container_file_content,
    upload_container_file,
)
from dockhand_mcp.tools.stacks import get_stack_deploy_log
from dockhand_mcp.tools.system import get_changelog
from dockhand_mcp.tools.environments import (
    get_environment_report,
    update_environment_update_check_settings,
    update_environment_report_settings,
)
from dockhand_mcp.tools.users import update_user


class MockRequestContext:
    def __init__(self, client):
        self.lifespan_context = {"dockhand": client}


class MockContext:
    def __init__(self, client):
        self.request_context = MockRequestContext(client)


@pytest.fixture
def mock_ctx(mock_client):
    return MockContext(mock_client)


class TestLimitsAndValidation:
    """Verifies output truncation limits, DoS safeguards, and input validation."""

    @pytest.mark.asyncio
    async def test_run_container_exec_limits_and_params(self, mock_client, mock_ctx):
        with respx.mock:
            route = respx.post("http://dockhand.test/api/containers/c1/exec/run?envId=1").mock(
                return_value=Response(
                    200,
                    json={
                        "exitCode": 0,
                        "stdout": "A" * 20000,
                        "stderr": "B" * 20000,
                    },
                )
            )

            # Test truncation with custom max_bytes
            res = await run_container_exec(
                environment_id=1,
                container_id="c1",
                cmd=["ls", "-la"],
                ctx=mock_ctx,
                user="deploy",
                working_dir="/var/app",
                max_bytes=50,
            )
            assert "[TRUNCATED AT 50 BYTES]" in res["stdout"]
            assert "[TRUNCATED AT 50 BYTES]" in res["stderr"]

            # Test execution without truncation when within limit
            res_no_trunc = await run_container_exec(
                environment_id=1,
                container_id="c1",
                cmd=["ls"],
                ctx=mock_ctx,
                max_bytes=50000,
            )
            assert "[TRUNCATED" not in res_no_trunc["stdout"]
            assert len(res_no_trunc["stdout"]) == 20000

    @pytest.mark.asyncio
    async def test_get_stack_deploy_log_limits(self, mock_client, mock_ctx):
        with respx.mock:
            long_log = "step log line\n" * 1500  # ~21KB
            respx.get("http://dockhand.test/api/stacks/my-stack/deploys/101/log?env=1").mock(
                return_value=Response(200, json={"log": long_log})
            )

            res = await get_stack_deploy_log(1, "my-stack", 101, mock_ctx, max_bytes=100)
            assert isinstance(res, dict)
            assert "[TRUNCATED AT 100 BYTES]" in res["log"]

            # Test with string response from API
            respx.get("http://dockhand.test/api/stacks/string-stack/deploys/102/log?env=1").mock(
                return_value=Response(200, text=long_log)
            )
            res_str = await get_stack_deploy_log(1, "string-stack", 102, mock_ctx, max_bytes=80)
            assert isinstance(res_str, str)
            assert "[TRUNCATED AT 80 BYTES]" in res_str

    @pytest.mark.asyncio
    async def test_get_container_file_content_limits(self, mock_client, mock_ctx):
        with respx.mock:
            respx.get("http://dockhand.test/api/containers/c1/files/content?env=1&path=%2Fvar%2Flog%2Fapp.log").mock(
                return_value=Response(200, text="X" * 15000)
            )

            res = await get_container_file_content(
                environment_id=1,
                container_id="c1",
                path="/var/log/app.log",
                ctx=mock_ctx,
                max_bytes=200,
            )
            assert "[...truncated at 200 bytes" in res

            # Content within max_bytes should not be truncated
            respx.get("http://dockhand.test/api/containers/c1/files/content?env=1&path=%2Fshort.txt").mock(
                return_value=Response(200, text="short content")
            )
            res_short = await get_container_file_content(
                environment_id=1,
                container_id="c1",
                path="/short.txt",
                ctx=mock_ctx,
                max_bytes=200,
            )
            assert res_short == "short content"

    @pytest.mark.asyncio
    async def test_get_container_logs_tail_cap(self, mock_client, mock_ctx):
        with respx.mock:
            route = respx.get("http://dockhand.test/api/containers/c1/logs?env=1&tail=500").mock(
                return_value=Response(200, text="sample log output")
            )
            # Requesting 5000 lines should be capped to 500 lines to protect context window
            res = await get_container_logs(1, "c1", mock_ctx, tail=5000)
            assert route.called
            assert res == "sample log output"

    @pytest.mark.asyncio
    async def test_get_changelog_line_cap(self, mock_client, mock_ctx):
        with respx.mock:
            # 60 lines of changelog
            dummy_changelog = "\n".join([f"- v1.0.{i} release notes" for i in range(60)])
            respx.get("http://dockhand.test/api/changelog").mock(
                return_value=Response(200, text=dummy_changelog)
            )
            res = await get_changelog(mock_ctx)
            assert "[...truncated at 50 lines. Use max_lines parameter to see more.]" in res
            # Check only first 50 lines are kept
            assert "- v1.0.49 release notes" in res
            assert "- v1.0.55 release notes" not in res

    @pytest.mark.asyncio
    async def test_create_container_all_options(self, mock_client, mock_ctx):
        import json
        with respx.mock:
            route = respx.post("http://dockhand.test/api/containers?env=1").mock(
                return_value=Response(200, json={"id": "new_c", "name": "custom_c"})
            )
            res = await create_container(
                environment_id=1,
                name="custom_c",
                image="postgres:16",
                ctx=mock_ctx,
                start_after_create=True,
                env=["POSTGRES_DB=mydb"],
                ports={"5432/tcp": [{"HostPort": "5432"}]},
                volumes=["/data:/var/lib/postgresql/data"],
                restart_policy="unless-stopped",
                network_mode="bridge",
                labels={"service": "db"},
            )
            assert route.called
            payload = json.loads(route.calls.last.request.content)
            assert payload["name"] == "custom_c"
            assert payload["image"] == "postgres:16"
            assert payload["startAfterCreate"] is True
            assert payload["Env"] == ["POSTGRES_DB=mydb"]
            assert payload["Labels"] == {"service": "db"}
            assert payload["HostConfig"]["PortBindings"] == {"5432/tcp": [{"HostPort": "5432"}]}
            assert payload["HostConfig"]["Binds"] == ["/data:/var/lib/postgresql/data"]
            assert payload["HostConfig"]["RestartPolicy"] == {"Name": "unless-stopped"}
            assert payload["HostConfig"]["NetworkMode"] == "bridge"
            assert res["id"] == "new_c"

    @pytest.mark.asyncio
    async def test_update_container_all_options(self, mock_client, mock_ctx):
        import json
        with respx.mock:
            route = respx.post("http://dockhand.test/api/containers/c1/update?env=1").mock(
                return_value=Response(200, json={"id": "c1", "updated": True})
            )
            res = await update_container(
                environment_id=1,
                container_id="c1",
                ctx=mock_ctx,
                image="redis:7-alpine",
                name="redis_updated",
                cmd=["redis-server", "--appendonly", "yes"],
                env=["MAXMEMORY=256mb"],
                restart_policy="always",
                network_mode="host",
                repull_image=True,
                start_after_update=False,
            )
            assert route.called
            payload = json.loads(route.calls.last.request.content)
            assert payload["image"] == "redis:7-alpine"
            assert payload["name"] == "redis_updated"
            assert payload["cmd"] == ["redis-server", "--appendonly", "yes"]
            assert payload["env"] == ["MAXMEMORY=256mb"]
            assert payload["restartPolicy"] == "always"
            assert payload["networkMode"] == "host"
            assert payload["repullImage"] is True
            assert payload["startAfterUpdate"] is False
            assert res["updated"] is True

    @pytest.mark.asyncio
    async def test_list_containers_non_list_response(self, mock_client, mock_ctx):
        with respx.mock:
            respx.get("http://dockhand.test/api/containers?env=1").mock(
                return_value=Response(200, json={"error": "environment unreachable"})
            )
            res = await list_containers(1, mock_ctx)
            assert res == {"error": "environment unreachable"}

    @pytest.mark.asyncio
    async def test_write_container_file_content_and_create_path(self, mock_client, mock_ctx):
        import json
        with respx.mock:
            # write_container_file_content
            put_route = respx.put("http://dockhand.test/api/containers/c1/files/content?env=1&path=%2Fetc%2Ftest.conf").mock(
                return_value=Response(200, json={"success": True})
            )
            res = await write_container_file_content(
                environment_id=1,
                container_id="c1",
                path="/etc/test.conf",
                content="hello world",
                ctx=mock_ctx,
            )
            assert put_route.called
            put_payload = json.loads(put_route.calls.last.request.content)
            assert put_payload["content"] == "hello world"
            assert res["success"] is True

            # create_container_path with owner
            post_route = respx.post("http://dockhand.test/api/containers/c1/files/create?env=1").mock(
                return_value=Response(200, json={"created": True})
            )
            res2 = await create_container_path(
                environment_id=1,
                container_id="c1",
                path="/etc/test.d",
                type="directory",
                ctx=mock_ctx,
                owner="1000:1000",
            )
            assert post_route.called
            post_payload = json.loads(post_route.calls.last.request.content)
            assert post_payload["path"] == "/etc/test.d"
            assert post_payload["type"] == "directory"
            assert post_payload["owner"] == "1000:1000"
            assert res2["created"] is True

    @pytest.mark.asyncio
    async def test_upload_container_file_valid_and_invalid(self, mock_client, mock_ctx):
        import base64
        import json
        with respx.mock:
            # Valid upload with owner
            upload_route = respx.post("http://dockhand.test/api/containers/c1/files/upload?env=1&path=%2Fopt").mock(
                return_value=Response(200, json={"uploaded": True})
            )
            valid_b64 = base64.b64encode(b"my binary payload").decode("ascii")
            res = await upload_container_file(
                environment_id=1,
                container_id="c1",
                directory="/opt",
                filename="binary.bin",
                base64_content=valid_b64,
                ctx=mock_ctx,
                owner="deploy:deploy",
            )
            assert upload_route.called
            assert res["uploaded"] is True

            # Invalid base64
            with pytest.raises(ValueError, match="Invalid base64_content"):
                await upload_container_file(
                    environment_id=1,
                    container_id="c1",
                    directory="/opt",
                    filename="bad.bin",
                    base64_content="!!!NOT_VALID_BASE64@@@",
                    ctx=mock_ctx,
                )

    @pytest.mark.asyncio
    async def test_environment_reporting_and_update_check_settings(self, mock_client, mock_ctx):
        import json
        with respx.mock:
            # get_environment_report
            rep_route = respx.get("http://dockhand.test/api/environments/report?format=csv&env=2").mock(
                return_value=Response(200, text="header1,header2\nval1,val2")
            )
            rep_res = await get_environment_report(
                ctx=mock_ctx,
                environment_id=2,
                format="csv",
            )
            assert rep_route.called
            assert "header1,header2" in rep_res

            # update_environment_update_check_settings
            upd_route = respx.post("http://dockhand.test/api/environments/2/update-check").mock(
                return_value=Response(200, json={"status": "updated"})
            )
            upd_res = await update_environment_update_check_settings(
                environment_id=2,
                ctx=mock_ctx,
                enabled=True,
                cron="0 3 * * *",
                auto_update=True,
                vulnerability_criteria="critical_only",
                minimum_release_age_hours=24,
                minimum_release_age_override=True,
            )
            assert upd_route.called
            upd_payload = json.loads(upd_route.calls.last.request.content)
            assert upd_payload["enabled"] is True
            assert upd_payload["cron"] == "0 3 * * *"
            assert upd_payload["autoUpdate"] is True
            assert upd_payload["vulnerabilityCriteria"] == "critical_only"
            assert upd_payload["minimumReleaseAgeHours"] == 24
            assert upd_payload["minimumReleaseAgeOverride"] is True

            # update_environment_report_settings
            rep_settings_route = respx.post("http://dockhand.test/api/environments/2/report").mock(
                return_value=Response(200, json={"status": "saved"})
            )
            rep_settings_res = await update_environment_report_settings(
                environment_id=2,
                ctx=mock_ctx,
                enabled=True,
                cron="0 8 * * 1",
                format="pdf",
                notification_id=42,
            )
            assert rep_settings_route.called
            rep_settings_payload = json.loads(rep_settings_route.calls.last.request.content)
            assert rep_settings_payload["enabled"] is True
            assert rep_settings_payload["format"] == "pdf"
            assert rep_settings_payload["notificationId"] == 42

    @pytest.mark.asyncio
    async def test_update_user_with_password_and_role(self, mock_client, mock_ctx):
        import json
        with respx.mock:
            route = respx.put("http://dockhand.test/api/users/5").mock(
                return_value=Response(200, json={"id": 5, "updated": True})
            )
            res = await update_user(5, mock_ctx, password="new_password_123", role="admin")
            assert route.called
            payload = json.loads(route.calls.last.request.content)
            assert payload["password"] == "new_password_123"
            assert payload["role"] == "admin"
