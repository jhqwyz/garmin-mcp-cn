"""Verify the externally exposed server is read-only, not only annotated so."""
from unittest.mock import Mock
import json
import pytest
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from garmin_mcp import server
from garmin_mcp.read_only import READ_ONLY_TOOLS


@pytest.mark.asyncio
async def test_only_reviewed_read_tools_are_exposed():
    app = server.create_app(Mock())
    tools = await app.list_tools()
    assert {tool.name for tool in tools} == READ_ONLY_TOOLS
    assert len(tools) == 79
    assert all(tool.annotations.readOnlyHint and not tool.annotations.destructiveHint for tool in tools)
    with pytest.raises(ToolError):
        await app.call_tool("delete_weigh_ins", {"date": "2026-10-01"})


@pytest.mark.asyncio
async def test_unreviewed_get_tool_is_not_exposed():
    app = FastMCP("test")
    registrar = server.ReadOnlyRegistrar(app)
    @registrar.tool()
    async def get_unreviewed_data() -> str:
        return "unreviewed"
    assert not await app.list_tools()


def test_server_resumes_china_session(monkeypatch):
    monkeypatch.setenv("GARMIN_IS_CN", "true")
    client = Mock(spec=["login"])
    constructor = Mock(return_value=client)
    monkeypatch.setattr(server, "Garmin", constructor)
    assert server.init_api(token_path="/test/native") is client
    assert constructor.call_args.kwargs["is_cn"] is True
    client.login.assert_called_once_with("/test/native")


@pytest.mark.asyncio
async def test_stress_summary_counts_zero_and_excludes_missing_values():
    client = Mock()
    client.get_stress_data.return_value = {
        "calendarDate": "2026-10-01",
        "stressValuesArray": [[1, 0], [2, 0], [3, 50], [4, 100], [5, -1], [6, None]],
    }
    result = await server.create_app(client).call_tool("get_stress_summary", {"date": "2026-10-01"})
    data = json.loads(result[0].text)
    assert data["rest_percent"] == 50
    assert data["low_stress_percent"] == 25
    assert data["high_stress_percent"] == 25
    assert data["data_points_count"] == 4


@pytest.mark.asyncio
async def test_sleep_without_stage_metrics_keeps_available_data():
    client = Mock()
    client.get_sleep_data.return_value = {"dailySleepDTO": {"sleepTimeSeconds": 28800}}
    result = await server.create_app(client).call_tool("get_sleep_summary", {"date": "2026-10-01"})
    data = json.loads(result[0].text)
    assert data["date"] == "2026-10-01"
    assert data["sleep_hours"] == 8
    assert "deep_sleep_percent" not in data
