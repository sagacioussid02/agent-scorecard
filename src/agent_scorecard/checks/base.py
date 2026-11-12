"""Check registry and the small toolkit every check is written with.

A check is a function decorated with :func:`check`. The decorator holds the
rubric text (why it matters, what to look for, how credit is given, how to
fix), so the rubric document and the scanner can never disagree:
``agent-scorecard rubric`` renders RUBRIC.md straight from this registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Callable, Iterable

from .. import frameworks as fw
from ..model import CheckResult, CheckSpec, Evidence, Layer, Severity, Status
from ..repo import FileKind, RepoIndex

CODE = (FileKind.CODE,)
CODE_AND_CONFIG = (FileKind.CODE, FileKind.CONFIG)
ANY_TEXT = (FileKind.CODE, FileKind.CONFIG, FileKind.CI)
MAX_EVIDENCE = 5
AGENT_VOCAB = (
    r"\b(llm|LLM|agents?|Agent\w*|anthropic|Anthropic|openai|OpenAI|bedrock|Bedrock|completions?|"
    r"chat_model|ChatModel|tool_calls?|tool_use|toolUse|langgraph|crewai|messages\.create|invoke_model|"
    r"converse|generateText|streamText|prompt|Prompt)\b"
)


TOOL_USE = (
    r"\btools\s*=\s*\[|\bbind_tools\(|^\s*@(tool|function_tool)\b|\btool_use\b|\btool_calls?\b|\btoolUse\b|"
    r"\btoolConfig\b|\bfunction_call\b|['\"]type['\"]\s*:\s*['\"]function['\"]|\b(server|mcp)\.(tool|registerTool)\(|\bAddTool\("
)
NO_TOOLS_MSG = "No tool calling found: a chat-only model app has no actions to limit or gate."


@dataclass
class ScanContext:
    index: RepoIndex

    @cached_property
    def frameworks(self) -> list[str]:
        return fw.detect(self.index)

    @cached_property
    def framework_keys(self) -> set[str]:
        return fw.keys(self.index)

    @cached_property
    def mcp_configs(self) -> list[tuple[str, dict]]:
        return fw.mcp_config_files(self.index)

    @cached_property
    def agent_files(self) -> set[str]:
        """Production code files that talk to a model or define agent behaviour.

        Used to keep generic words (max_steps, budget, confirm) from counting
        when they appear in code that has nothing to do with the agent.
        """
        return self.index.files_matching(AGENT_VOCAB, CODE)

    @cached_property
    def has_tools(self) -> bool:
        """Does the agent call tools at all? A chat-only app has nothing to gate."""
        if self.framework_keys & {"langgraph", "crewai", "claude_agent_sdk", "openai_agents", "autogen", "mcp"}:
            return True
        return bool(self.index.grep(TOOL_USE, (FileKind.CODE,), limit=1))

    def uses(self, key: str) -> bool:
        return key in self.framework_keys


@dataclass(frozen=True)
class Outcome:
    """What a check function returns; the registry adds the spec."""

    status: Status
    summary: str
    evidence: tuple[Evidence, ...] = ()


CheckFn = Callable[[ScanContext], Outcome]


@dataclass
class RegisteredCheck:
    spec: CheckSpec
    fn: CheckFn

    def run(self, ctx: ScanContext) -> CheckResult:
        out = self.fn(ctx)
        return CheckResult(self.spec, out.status, out.summary, tuple(out.evidence[:MAX_EVIDENCE]))


@dataclass
class Registry:
    checks: dict[str, RegisteredCheck] = field(default_factory=dict)

    def add(self, spec: CheckSpec, fn: CheckFn) -> None:
        if spec.id in self.checks:
            raise ValueError(f"duplicate check id {spec.id}")
        self.checks[spec.id] = RegisteredCheck(spec, fn)

    def ordered(self) -> list[RegisteredCheck]:
        layer_order = {layer: i for i, layer in enumerate(Layer)}
        return sorted(self.checks.values(), key=lambda c: (layer_order[c.spec.layer], c.spec.id))

    def get(self, check_id: str) -> RegisteredCheck | None:
        return self.checks.get(check_id.upper())


REGISTRY = Registry()


def check(
    id: str,
    layer: Layer,
    title: str,
    severity: Severity,
    *,
    why: str,
    look_for: str,
    full: str,
    partial: str,
    fix: str,
) -> Callable[[CheckFn], CheckFn]:
    spec = CheckSpec(id, layer, title, severity, why, look_for, full, partial, fix)

    def deco(fn: CheckFn) -> CheckFn:
        REGISTRY.add(spec, fn)
        return fn

    return deco


# ---------------------------------------------------------------------------
# Helpers that keep individual checks short and readable.
# ---------------------------------------------------------------------------

def find(ctx: ScanContext, patterns: Iterable[str], kinds=CODE, **kw) -> list[Evidence]:
    """Search several regexes and return de-duplicated evidence in order."""
    seen: set[tuple[str, int]] = set()
    out: list[Evidence] = []
    for p in patterns:
        for ev in ctx.index.grep(p, kinds, **kw):
            key = (ev.path, ev.line)
            if key not in seen:
                seen.add(key)
                out.append(ev)
    return out


def near(
    ctx: ScanContext,
    anchors: Iterable[str],
    targets: Iterable[str],
    *,
    window: int = 25,
    kinds=CODE,
    flags: int = 0,
) -> list[Evidence]:
    """Target matches within ``window`` lines of an anchor match in the same file.

    This is how a check tells "an HMAC used to sign approvals" apart from "an
    HMAC used somewhere in the same 3,000-line server file".
    """
    anchor_lines: dict[str, list[int]] = {}
    for e in find(ctx, anchors, kinds, flags=flags, code_only=False, limit=500):
        anchor_lines.setdefault(e.path, []).append(e.line)
    if not anchor_lines:
        return []
    hits = find(ctx, targets, kinds, flags=flags, paths=set(anchor_lines), limit=500)
    return [e for e in hits if any(abs(e.line - a) <= window for a in anchor_lines[e.path])]


def distinct_files(evidence: Iterable[Evidence]) -> int:
    return len({e.path for e in evidence})


def tiered(
    ctx: ScanContext,
    *,
    full: Iterable[str],
    partial: Iterable[str] = (),
    kinds=CODE,
    full_msg: str,
    partial_msg: str,
    missing_msg: str,
    min_full_files: int = 1,
    flags: int = 0,
    paths: set[str] | None = None,
) -> Outcome:
    """The common shape: strong signals earn PASS, weaker ones PARTIAL."""
    strong = find(ctx, full, kinds, flags=flags, paths=paths)
    if strong and distinct_files(strong) >= min_full_files:
        return Outcome(Status.PASS, full_msg, tuple(strong))
    weak = strong + find(ctx, partial, kinds, flags=flags, paths=paths)
    if weak:
        return Outcome(Status.PARTIAL, partial_msg, tuple(weak))
    return Outcome(Status.MISSING, missing_msg)

