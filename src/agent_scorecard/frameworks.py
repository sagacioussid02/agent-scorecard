"""Detect which agent frameworks a repository uses.

Detection looks at dependency manifests and imports. The result does two
things: it is printed on the scorecard, and checks use it to switch on
framework-specific signals (for example LangGraph's ``interrupt()`` counts
as an approval gate, CrewAI's ``human_input=True`` does too).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .repo import FileKind, RepoIndex


@dataclass(frozen=True)
class Framework:
    key: str
    name: str
    manifest_pattern: str  # searched in dependency manifests
    import_pattern: str  # searched in code


FRAMEWORKS: tuple[Framework, ...] = (
    Framework(
        "claude_agent_sdk", "Claude Agent SDK",
        r"claude[-_]agent[-_]sdk|@anthropic-ai/claude-agent-sdk|claude[-_]code[-_]sdk|@anthropic-ai/claude-code",
        r"from\s+claude_agent_sdk\b|import\s+claude_agent_sdk\b|from\s+claude_code_sdk\b|['\"]@anthropic-ai/claude-(agent-sdk|code)['\"]",
    ),
    Framework(
        "langgraph", "LangGraph",
        r"\blanggraph\b|@langchain/langgraph",
        r"from\s+langgraph[\.\s]|import\s+langgraph\b|['\"]@langchain/langgraph",
    ),
    Framework(
        "crewai", "CrewAI",
        r"\bcrewai\b",
        r"from\s+crewai[\.\s]|import\s+crewai\b",
    ),
    Framework(
        "openai_agents", "OpenAI Agents SDK",
        r"openai-agents|@openai/agents",
        r"from\s+agents\s+import\s+.*\bAgent\b|['\"]@openai/agents['\"]",
    ),
    Framework(
        "autogen", "AutoGen",
        r"autogen-agentchat|pyautogen|\bag2\b",
        r"from\s+autogen(_agentchat)?[\.\s]|import\s+autogen\b",
    ),
    Framework(
        "langchain", "LangChain",
        r"\blangchain\b|@langchain/core",
        r"from\s+langchain(_core|_community|_openai|_anthropic)?[\.\s]|['\"]@langchain/core",
    ),
    Framework(
        "mcp", "MCP (server or client)",
        r"(^|[\s\"'])mcp([<>=~\[\s\"']|$)|@modelcontextprotocol/sdk|github\.com/mark3labs/mcp-go|modelcontextprotocol/go-sdk|fastmcp",
        r"from\s+mcp[\.\s]|from\s+fastmcp\b|['\"]@modelcontextprotocol/sdk|mark3labs/mcp-go|modelcontextprotocol/go-sdk",
    ),
    # Direct model APIs: no agent framework, but the code still drives a model.
    Framework(
        "anthropic_api", "Anthropic API",
        r"(^|[\s\"'])anthropic([<>=~\[\s\"']|$)|@anthropic-ai/sdk|anthropics/anthropic-sdk-go",
        r"^\s*(from\s+anthropic\b|import\s+anthropic\b)|['\"]@anthropic-ai/sdk['\"]|anthropic-sdk-go",
    ),
    Framework(
        "openai_api", "OpenAI API",
        r"(^|[\s\"'])openai([<>=~\[\s\"']|$)|github\.com/openai/openai-go|sashabaranov/go-openai",
        r"^\s*(from\s+openai\b|import\s+openai\b)|from\s+['\"]openai['\"]|require\(['\"]openai['\"]\)|openai/openai-go|go-openai",
    ),
    Framework(
        "bedrock", "AWS Bedrock",
        r"@aws-sdk/client-bedrock|langchain-aws",
        r"['\"]bedrock-runtime['\"]|BedrockRuntimeClient|ChatBedrock",
    ),
    Framework(
        "vercel_ai", "Vercel AI SDK",
        r"(^|[\s\"'])ai(['\"]\s*:)|@ai-sdk/",
        r"['\"]@ai-sdk/|from\s+['\"]ai['\"]",
    ),
)

_MANIFEST = re.compile(r"(^|/)(pyproject\.toml|requirements[^/]*\.txt|setup\.py|setup\.cfg|package\.json|go\.mod|Pipfile)$", re.I)
MCP_CONFIG_NAMES = re.compile(r"(^|/)(\.mcp\.json|mcp\.json|mcp_config\.json|claude_desktop_config\.json|\.cursor/mcp\.json|\.vscode/mcp\.json)$", re.I)


def detect(index: RepoIndex) -> list[str]:
    """Return framework display names in a stable order."""
    manifests = [f for f in index.files if _MANIFEST.search(f.path)]
    found: list[str] = []
    for fw in FRAMEWORKS:
        rx_m = re.compile(fw.manifest_pattern, re.I | re.M)
        rx_i = re.compile(fw.import_pattern, re.M)
        if any(rx_m.search(m.text) for m in manifests) or any(
            rx_i.search(f.text) for f in index.select((FileKind.CODE,), production_only=False)
        ):
            found.append(fw.name)
    if mcp_config_files(index) and "MCP (server or client)" not in found:
        found.append("MCP config")
    return found


def keys(index: RepoIndex) -> set[str]:
    names = set(detect(index))
    out = {fw.key for fw in FRAMEWORKS if fw.name in names}
    if "MCP config" in names:
        out.add("mcp")
    return out


def mcp_config_files(index: RepoIndex) -> list[tuple[str, dict]]:
    """MCP client configs ({"mcpServers": {...}}) found anywhere in the repo."""
    out: list[tuple[str, dict]] = []
    for f in index.files:
        if f.lang != "json":
            continue
        if not MCP_CONFIG_NAMES.search(f.path) and '"mcpServers"' not in f.text and '"servers"' not in f.text:
            continue
        try:
            data = json.loads(f.text)
        except (ValueError, RecursionError):
            continue
        if not isinstance(data, dict):
            continue
        servers = data.get("mcpServers")
        if servers is None and MCP_CONFIG_NAMES.search(f.path):
            servers = data.get("servers")
        if isinstance(servers, dict) and servers:
            out.append((f.path, servers))
    return out
