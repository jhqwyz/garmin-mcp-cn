"""Initialize actual MCP transports and verify discovery and read-only calls."""
import json
import sys
from unittest.mock import Mock
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from starlette.testclient import TestClient
from garmin_mcp.server import create_app
from garmin_mcp.read_only import READ_ONLY_TOOLS


@pytest.mark.asyncio
@pytest.mark.timeout(20)
async def test_stdio_initialization_discovery_and_sleep_query():
    parameters = StdioServerParameters(command=sys.executable, args=["-m", "tests.fake_server"])
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            initialization = await session.initialize()
            assert "Read-only Garmin" in initialization.instructions
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == READ_ONLY_TOOLS
            result = await session.call_tool("get_sleep_summary", {"date": "2026-10-01"})
            assert not result.isError
            assert json.loads(result.content[0].text)["sleep_hours"] == 8
            rejected = await session.call_tool("delete_weigh_ins", {"date": "2026-10-01"})
            assert rejected.isError


def test_streamable_http_discovery_and_read_only_calls():
    mock = Mock()
    mock.get_sleep_data.return_value = {"dailySleepDTO": {"sleepTimeSeconds": 28800}}
    app = create_app(mock)
    headers = {"Accept": "application/json, text/event-stream"}
    with TestClient(app.streamable_http_app(), base_url="http://127.0.0.1:8000") as client:
        initialized = client.post("/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
        })
        assert initialized.status_code == 200
        listed = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        assert listed.status_code == 200
        assert {tool["name"] for tool in listed.json()["result"]["tools"]} == READ_ONLY_TOOLS
        sleep = client.post("/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "get_sleep_summary", "arguments": {"date": "2026-10-01"}},
        })
        payload = sleep.json()["result"]
        assert not payload.get("isError")
        assert json.loads(payload["content"][0]["text"])["sleep_hours"] == 8
        rejected = client.post("/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "delete_weigh_ins", "arguments": {"date": "2026-10-01"}},
        })
        assert rejected.json()["result"]["isError"]
