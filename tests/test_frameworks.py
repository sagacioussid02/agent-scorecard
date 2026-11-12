import pytest

from agent_scorecard.frameworks import detect, mcp_config_files
from agent_scorecard.repo import RepoIndex


@pytest.mark.parametrize("files,name", [
    ({"a.py": "from claude_agent_sdk import query"}, "Claude Agent SDK"),
    ({"a.ts": "import { query } from '@anthropic-ai/claude-agent-sdk'"}, "Claude Agent SDK"),
    ({"pyproject.toml": "dependencies = ['langgraph>=0.6']"}, "LangGraph"),
    ({"a.ts": "import { StateGraph } from '@langchain/langgraph'"}, "LangGraph"),
    ({"a.py": "from crewai import Agent, Crew"}, "CrewAI"),
    ({"requirements.txt": "crewai==0.80"}, "CrewAI"),
    ({"a.py": "from agents import Agent, Runner"}, "OpenAI Agents SDK"),
    ({"a.py": "from mcp.server.fastmcp import FastMCP"}, "MCP (server or client)"),
    ({"go.mod": "require github.com/mark3labs/mcp-go v0.30.0"}, "MCP (server or client)"),
    ({".mcp.json": '{"mcpServers": {"x": {"command": "uvx", "args": ["x==1"]}}}'}, "MCP config"),
    ({"a.py": "import anthropic"}, "Anthropic API"),
    ({"a.py": "from openai import OpenAI"}, "OpenAI API"),
])
def test_detects(files, name):
    assert name in detect(RepoIndex.from_mapping(files))


def test_provider_name_in_a_string_is_not_a_dependency():
    assert "OpenAI API" not in detect(RepoIndex.from_mapping({"a.py": "PROVIDERS = ['openai', 'anthropic']"}))


def test_mcp_config_parsing_tolerates_junk():
    idx = RepoIndex.from_mapping({
        ".mcp.json": "{not json",
        "mcp.json": '{"mcpServers": []}',
        ".vscode/mcp.json": '{"servers": {"a": {"command": "npx", "args": ["a@1.0.0"]}}}',
        "config/app.json": '{"mcpServers": {"b": {"command": "uvx", "args": ["b==2"]}}}',
    })
    paths = [p for p, _ in mcp_config_files(idx)]
    assert paths == [".vscode/mcp.json", "config/app.json"]
