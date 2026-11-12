"""Layer 1: tool boundaries. What can the agent touch, and how is that limited?"""

from __future__ import annotations

import re

from ..model import Evidence, Layer, Severity, Status
from ..repo import FileKind
from .base import NO_TOOLS_MSG, CODE, Outcome, ScanContext, check, find, tiered

L = Layer.TOOLS


@check(
    "TB-01", L, "Tools are an explicit allowlist", Severity.HIGH,
    why="An agent should only see the tools its job needs. Handing it every tool a "
        "library or MCP server exposes turns one bad prompt into access to all of them.",
    look_for="allowed_tools / allowedTools / disallowed_tools (Claude Agent SDK), MCP tool "
             "filters (include_tools, tool_filter), named tool allowlists; weaker: explicit "
             "tools=[...] lists, @tool / @function_tool / server.tool() declarations.",
    full="Tool access is filtered through an allowlist or denylist.",
    partial="Tools are declared explicitly, but nothing filters which ones an agent may call.",
    fix="Give each agent or role an allowlist of tool names and load only those. For MCP, "
        "filter the server's tools rather than exposing all of them.",
)
def tool_allowlist(ctx: ScanContext) -> Outcome:
    if not ctx.has_tools:
        return Outcome(Status.NOT_APPLICABLE, NO_TOOLS_MSG)
    return tiered(
        ctx,
        full=[
            r"\b(allowed_tools|disallowed_tools|allowedTools|disallowedTools)\b\s*[=:]",
            r"\b(tool_allowlist|tool_whitelist|ALLOWED_TOOLS|allowed_tool_names|tool_filter|include_tools|exclude_tools|toolFilter)\b",
            r"\b(allowed|permitted)_?tools?_?(for|by|per)_?(role|agent|user|tier)",
        ],
        partial=[
            r"\btools\s*=\s*\[",
            r"\.bind_tools\(",
            r"^\s*@(tool|function_tool)\b",
            r"\b(server|mcp)\.(tool|registerTool)\(",
            r"\bmcp\.NewTool\(|AddTool\(",
        ],
        full_msg="Tool access goes through an allowlist.",
        partial_msg="Tools are declared explicitly, but no allowlist limits which ones each agent gets.",
        missing_msg="No tool declarations or allowlists found.",
    )


@check(
    "TB-02", L, "Tools carry a risk tier", Severity.CRITICAL,
    why="Approval, logging and budgets all depend on knowing which tools only read and "
        "which change the world. Without tiers, every safety layer has to guess.",
    look_for="risk_level / security_risk / ToolTier / read_only / readOnlyHint / destructiveHint / "
             "requires_confirmation on tool definitions.",
    full="Tools are classified by risk in code (read-only, side-effecting, destructive).",
    partial="Some tools are named as dangerous or side-effecting, without a systematic tier.",
    fix="Add a tier to every tool (read, write, irreversible) and make approvals and "
        "budgets key off it. MCP's readOnlyHint and destructiveHint are a good minimum.",
)
def risk_tiers(ctx: ScanContext) -> Outcome:
    if not ctx.has_tools:
        return Outcome(Status.NOT_APPLICABLE, NO_TOOLS_MSG)
    return tiered(
        ctx,
        full=[
            r"\b(risk_level|risk_tier|tool_tier|tool_tiers|security_risk|SecurityRisk|RiskLevel|ToolTier|ToolRisk|risk_class)\b",
            r"\b(readOnlyHint|destructiveHint|idempotentHint|read_only_hint|destructive_hint)\b",
            r"\b(requires_confirmation|requires_approval|is_destructive|is_read_only)\b",
            r"\b(TIER_(READ|WRITE|CONFIRM|DESTRUCTIVE|DANGER|SAFE|IRREVERSIBLE)\w*|Tier(ReadOnly|Read|Write|Confirm|Destructive|Dangerous|Safe|Irreversible)\w*)\b",
            r"\b(read[-_ ]?only|confirm[-_ ]first|never[-_ ]by[-_ ]voice)\b.{0,40}\btiers?\b",
        ],
        partial=[
            r"\b(dangerous|destructive|sensitive|privileged|side_?effecting)_?(tools?|actions?|operations?|commands?)\b",
            r"\bread_?only\s*[=:]\s*(True|true)",
        ],
        kinds=(FileKind.CODE, FileKind.CONFIG),
        flags=re.I,
        full_msg="Tools are tagged with a risk tier.",
        partial_msg="Dangerous tools are called out, but there is no systematic tier per tool.",
        missing_msg="No risk classification of tools found.",
    )


_EXEC = [
    r"\bsubprocess\.(run|Popen|call|check_call|check_output)\(",
    r"\bos\.(system|popen|exec[lv]p?e?)\(",
    r"\basyncio\.create_subprocess_(exec|shell)\(",
    r"\bchild_process\b|\bexecSync\(|\bspawnSync\(",
    r"\bexec\.Command(Context)?\(",
    r"(?<![\w.])(exec|eval)\(\s*(code|source|script|cmd|command|response|output|result|llm|completion)",
]
# Concrete isolation technology, counted anywhere in production code or config.
_SANDBOX_TECH = [
    r"\b(docker\.from_env|DockerClient|containers\.run|container\.exec_run|exec_create|DockerWorkspace|DockerRuntime|docker_runtime)\b",
    r"\b(e2b_code_interpreter|from\s+e2b\b|modal\.Sandbox|daytona_sdk|Daytona\(|firecracker|gvisor|runsc|nsjail|firejail|bwrap|bubblewrap|seccomp|landlock|wasmtime|pyodide)\b",
]
# The word "sandbox", counted only in the files that execute commands.
_SANDBOX_WORD = [r"\b[Ss]andbox(ed|es|ing)?\b|\bSandbox[A-Z]\w*"]
_RESTRICT = [
    r"\bshlex\.(quote|split)\(",
    r"\bshell\s*=\s*False\b",
    r"\b(allowed_commands|command_allowlist|ALLOWED_COMMANDS|blocked_commands|BLOCKED_COMMANDS|safe_commands)\b",
]


@check(
    "TB-03", L, "Code and shell execution is sandboxed", Severity.CRITICAL,
    why="If an agent can run commands, a prompt injection can too. Isolation decides "
        "whether that is an annoyance or a breach.",
    look_for="subprocess / child_process / exec.Command / eval paths, and alongside them a "
             "sandbox (Docker, E2B, Modal, gVisor, nsjail, seccomp) or at least a command "
             "allowlist and shell=False. N/A when the code never executes commands.",
    full="Execution runs inside a sandbox or container.",
    partial="Commands are restricted (allowlist, shlex, shell=False) but not isolated.",
    fix="Run agent-issued commands in a throwaway container or microVM with no host "
        "credentials and no default network, and keep an allowlist on top.",
)
def exec_sandbox(ctx: ScanContext) -> Outcome:
    exec_hits = find(ctx, _EXEC, CODE)
    tech = find(ctx, _SANDBOX_TECH, (FileKind.CODE, FileKind.CONFIG))
    if not exec_hits and not tech:
        return Outcome(Status.NOT_APPLICABLE, "No command or code execution found in production code.")
    shell_true = [Evidence(e.path, e.line, e.snippet, negative=True)
                  for e in find(ctx, [r"\bshell\s*=\s*True\b", r"\bos\.system\("], CODE)]
    exec_files = {e.path for e in exec_hits}
    sandbox = tech + find(ctx, _SANDBOX_WORD, CODE, paths=exec_files)
    if sandbox:
        return Outcome(Status.PASS, "Execution runs inside a sandbox or container.",
                       tuple(sandbox[:3] + shell_true[:2]))
    restrict = find(ctx, _RESTRICT, CODE)
    if restrict:
        return Outcome(Status.PARTIAL, "Commands are restricted but not isolated in a sandbox.",
                       tuple(restrict[:3] + shell_true[:2] + exec_hits[:1]))
    return Outcome(Status.MISSING, "Commands are executed with no sandbox or allowlist in sight.",
                   tuple(shell_true[:3] + exec_hits[:3]))


@check(
    "TB-04", L, "File access is confined to a workspace", Severity.HIGH,
    why="Agents that read or write files can be steered to ../../.ssh or to overwrite "
        "their own config. A single path check closes most of that.",
    look_for="is_relative_to / commonpath / safe_join / secure_filename / filepath.Rel / "
             "workspace-root checks next to file writes. N/A when nothing writes or deletes files.",
    full="Paths are resolved and checked against an allowed root.",
    partial="Paths are normalised (realpath/abspath), but no root check was found.",
    fix="Resolve every path the agent supplies and reject it unless it sits under the "
        "workspace root. Test it with ../ and symlink cases.",
)
def fs_confinement(ctx: ScanContext) -> Outcome:
    writes = find(ctx, [
        r"\bopen\([^)\n]*['\"][wa]b?\+?['\"]",
        r"\.(write_text|write_bytes|unlink|rmdir)\(",
        r"\b(shutil\.(rmtree|move|copy\w*)|os\.(remove|unlink|rename|makedirs))\(",
        r"\b(fs\.(writeFile|writeFileSync|rm|rmSync|unlink|unlinkSync)|os\.WriteFile|os\.Remove(All)?)\(",
    ], CODE)
    if not writes:
        return Outcome(Status.NOT_APPLICABLE, "No file writes or deletes found in production code.")
    return tiered(
        ctx,
        full=[
            r"\.is_relative_to\(",
            r"\bos\.path\.commonpath\(",
            r"\b(safe_join|secure_filename|filepath\.Rel|filepath\.IsLocal|path_is_within|is_within|is_subpath|within_workspace|ensure_within)\b",
            r"\bpath[_ ]?traversal\b",
            r"\b(workspace|sandbox|allowed)_?(root|dir|directories|paths)\b.{0,60}\b(startswith|is_relative_to|HasPrefix|relative_to)\b",
        ],
        partial=[r"\bos\.path\.(realpath|abspath)\(", r"\bfilepath\.(Clean|Abs)\(", r"\bpath\.resolve\("],
        flags=re.I,
        full_msg="File paths are checked against an allowed root.",
        partial_msg="Paths are normalised, but no check keeps them inside a workspace.",
        missing_msg=f"Files are written or deleted ({len({e.path for e in writes})} file(s)) with no path confinement found.",
    )


_ECOSYSTEMS = {
    # manifest regex: lockfile regex (a lockfile in the same or a parent directory counts,
    # which covers uv, npm, pnpm and yarn workspaces)
    r"(^|/)(pyproject\.toml|setup\.py|setup\.cfg|Pipfile)$": r"(^|/)(uv\.lock|poetry\.lock|Pipfile\.lock|pdm\.lock|requirements[^/]*\.(lock|txt))$",
    r"(^|/)package\.json$": r"(^|/)(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|bun\.lockb?|npm-shrinkwrap\.json)$",
    r"(^|/)go\.mod$": r"(^|/)go\.sum$",
    r"(^|/)Cargo\.toml$": r"(^|/)Cargo\.lock$",
}
_UNPINNED_PKG = re.compile(r"^(@[\w.-]+/)?[\w.-]+(@latest)?$")


def _dir(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


def _covered(manifest_dir: str, lock_dirs: set[str]) -> bool:
    d = manifest_dir
    while True:
        if d in lock_dirs:
            return True
        if not d:
            return False
        d = _dir(d)


def _unpinned_mcp(ctx: ScanContext) -> list[Evidence]:
    out = []
    for path, servers in ctx.mcp_configs:
        f = ctx.index.get(path)
        if f is not None and not f.is_production:
            continue
        for name, cfg in servers.items():
            if not isinstance(cfg, dict):
                continue
            cmd = str(cfg.get("command", ""))
            args = [str(a) for a in cfg.get("args", []) if isinstance(a, (str, int))]
            pkgs = [a for a in args if not a.startswith("-")]
            pkg = pkgs[0] if pkgs else ""
            runner = cmd.rsplit("/", 1)[-1]
            unpinned = False
            if runner in {"npx", "bunx", "pnpx"} and pkg and _UNPINNED_PKG.match(pkg):
                unpinned = True  # npx foo or npx foo@latest
            elif runner in {"uvx", "pipx"} and pkg and not re.search(r"(==|@)\d", pkg):
                unpinned = True
            elif runner in {"docker", "podman"}:
                images = [a for a in pkgs if a != "run" and "=" not in a and ("/" in a or ":" in a)]
                if images:
                    image = images[0]
                    tag = image.rsplit("/", 1)[-1]
                    unpinned = "@sha256:" not in image and (":" not in tag or tag.endswith(":latest"))
            if unpinned:
                out.append(Evidence(path, 1, f"MCP server '{name}': {cmd} {' '.join(args)}"[:140], negative=True))
    return out


def _is_prod_path(path: str) -> bool:
    from ..repo import _EXAMPLE_PARTS, _TEST_PARTS, _TOOLING
    return not (_EXAMPLE_PARTS.search(path) or _TEST_PARTS.search(path) or _TOOLING.search(path))


@check(
    "TB-05", L, "Tool supply chain is pinned", Severity.MEDIUM,
    why="Tools are code the agent runs with your credentials. An unpinned `npx -y some-mcp` "
        "pulls whatever was published five minutes ago.",
    look_for="A lockfile covering every dependency manifest (same or parent directory, so "
             "workspaces count), and MCP server entries pinned to a version or image digest "
             "instead of `npx -y pkg` or `:latest`. Examples and tests are ignored.",
    full="Dependencies are locked and every MCP server is pinned.",
    partial="Some manifests are locked, or MCP servers float while dependencies are locked.",
    fix="Commit lockfiles, pin MCP servers to exact versions (pkg@1.2.3, image@sha256:…) "
        "and update them deliberately.",
)
def supply_chain(ctx: ScanContext) -> Outcome:
    unpinned = _unpinned_mcp(ctx)
    uncovered: list[str] = []
    covered: list[str] = []
    for manifest_rx, lock_rx in _ECOSYSTEMS.items():
        manifests = [p for p in ctx.index.paths(manifest_rx) if _is_prod_path(p)]
        lock_dirs = {_dir(p) for p in ctx.index.paths(lock_rx)}
        for m in manifests:
            (covered if _covered(_dir(m), lock_dirs) else uncovered).append(m)
    if not covered and not uncovered and not unpinned:
        return Outcome(Status.NOT_APPLICABLE, "No dependency manifests or MCP configs found.")
    lock_ev = tuple(Evidence(p, 1, "locked") for p in covered[:2])
    unl_ev = tuple(Evidence(p, 1, "no lockfile covers this manifest", negative=True) for p in uncovered[:3])
    if covered and not uncovered and not unpinned:
        return Outcome(Status.PASS, f"All {len(covered)} dependency manifest(s) are locked"
                       + (" and MCP servers are pinned." if ctx.mcp_configs else "."), lock_ev)
    if covered:
        parts = []
        if uncovered:
            parts.append(f"{len(uncovered)} of {len(covered) + len(uncovered)} manifests have no lockfile")
        if unpinned:
            parts.append(f"{len(unpinned)} MCP server(s) are not pinned")
        return Outcome(Status.PARTIAL, "Locked in places, but " + " and ".join(parts) + ".",
                       tuple(unpinned[:2]) + unl_ev + lock_ev)
    return Outcome(Status.MISSING, "No lockfiles found"
                   + (f", and {len(unpinned)} MCP server(s) float." if unpinned else "."), tuple(unpinned[:3]) + unl_ev)
