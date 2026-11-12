import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from agent_scorecard.mcp_server import TOOLS, handle, serve

SRC = str(Path(__file__).parent.parent / "src")


def call(method, params=None, id_=1):
    msg = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        msg["params"] = params
    return handle(msg)


def test_initialize_negotiates_version():
    r = call("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}})
    assert r["result"]["protocolVersion"] == "2025-03-26"
    assert r["result"]["capabilities"] == {"tools": {"listChanged": False}}
    r = call("initialize", {"protocolVersion": "1999-01-01"})
    assert r["result"]["protocolVersion"] == "2025-06-18"


def test_notifications_get_no_response():
    assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_tools_are_listed_and_all_read_only():
    tools = call("tools/list")["result"]["tools"]
    assert {t["name"] for t in tools} == {"scan_repository", "list_checks", "explain_check", "get_rubric"}
    assert all(t["annotations"]["readOnlyHint"] for t in TOOLS)


def test_scan_tool(good_agent):
    r = call("tools/call", {"name": "scan_repository", "arguments": {"path": str(good_agent), "format": "json"}})
    assert r["result"]["isError"] is False
    assert json.loads(r["result"]["content"][0]["text"])["grade"] == "A"


def test_tool_errors_are_results_not_protocol_errors(tmp_path):
    r = call("tools/call", {"name": "scan_repository", "arguments": {"path": str(tmp_path / "nope")}})
    assert r["result"]["isError"] is True
    r = call("tools/call", {"name": "explain_check", "arguments": {"check_id": "XX-1"}})
    assert r["result"]["isError"] is True


def test_protocol_errors():
    assert call("tools/call", {"name": "rm_rf"})["error"]["code"] == -32602
    assert call("resources/list")["error"]["code"] == -32601


def test_serve_over_streams(good_agent):
    lines = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "list_checks", "arguments": {}}},
    ]
    stdin = io.StringIO("\n".join(json.dumps(m) for m in lines) + "\nnot json\n")
    stdout = io.StringIO()
    serve(stdin, stdout)
    out = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert [o.get("id") for o in out] == [1, 2, None]
    assert "AG-01" in out[1]["result"]["content"][0]["text"]
    assert out[2]["error"]["code"] == -32700


def test_official_mcp_client_can_use_the_server(good_agent):
    """Interop check against the official MCP Python SDK, when installed."""
    pytest.importorskip("mcp")
    import asyncio

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def go():
        params = StdioServerParameters(command=sys.executable, args=["-m", "agent_scorecard", "mcp"],
                                       env={"PYTHONPATH": SRC})
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                result = await session.call_tool("scan_repository", {"path": str(good_agent)})
                return [t.name for t in tools.tools], result

    names, result = asyncio.run(asyncio.wait_for(go(), timeout=60))
    assert "scan_repository" in names
    assert "Grade A" in result.content[0].text


def test_cli_entrypoint_runs_mcp():
    proc = subprocess.run([sys.executable, "-m", "agent_scorecard", "mcp"], input='{"jsonrpc":"2.0","id":1,"method":"ping"}\n',
                          capture_output=True, text=True, timeout=30, env={"PYTHONPATH": SRC})
    assert json.loads(proc.stdout)["result"] == {}
