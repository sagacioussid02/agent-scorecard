"""Layer 7: evals, testing and rollback. How do you know a change is safe to ship?"""

from __future__ import annotations

import re

from ..model import Evidence, Layer, Severity, Status
from ..repo import FileKind
from .base import CODE, CODE_AND_CONFIG, Outcome, ScanContext, check, distinct_files, find, tiered

L = Layer.EVALS

_TEST_RUN = r"\b(pytest|go test|npm (run )?test|pnpm (run )?test|yarn test|jest|vitest|make test|tox|nox|unittest|cargo test|bun test)\b"


@check(
    "ER-01", L, "Tests exist and run in CI", Severity.HIGH,
    why="An agent's safety layers are code. Untested code drifts, and a gate that silently "
        "stopped gating is worse than no gate.",
    look_for="Test files, and a CI workflow that runs them.",
    full="A test suite runs in CI.",
    partial="Tests exist but CI doesn't run them, or CI exists without tests.",
    fix="Run the test suite on every pull request and block merges on failure.",
)
def tests_in_ci(ctx: ScanContext) -> Outcome:
    tests = [f for f in ctx.index.files if f.is_test and f.kind == FileKind.CODE]
    ci_runs = ctx.index.grep(_TEST_RUN, (FileKind.CI,), production_only=False)
    if len(tests) >= 3 and ci_runs:
        return Outcome(Status.PASS, f"{len(tests)} test files, run in CI.", tuple(ci_runs[:3]))
    if tests or ci_runs:
        what = f"{len(tests)} test file(s)" + (", run in CI" if ci_runs else ", not run in CI")
        return Outcome(Status.PARTIAL, what + ".", tuple(ci_runs[:2] + [Evidence(t.path, 1, "test file") for t in tests[:2]]))
    return Outcome(Status.MISSING, "No tests found.")


@check(
    "ER-02", L, "Agent behaviour has evals", Severity.HIGH,
    why="Unit tests check code; evals check behaviour. A prompt or model change can pass "
        "every unit test and still make the agent worse or less safe.",
    look_for="An evals/ or benchmarks/ directory, eval frameworks (promptfoo, deepeval, ragas, "
             "Inspect, LangSmith evaluate, Braintrust, OpenAI evals), datasets of cases; "
             "weaker: golden files, LLM-as-judge helpers.",
    full="Agent behaviour is measured against an eval set.",
    partial="Golden files or LLM-judge helpers exist, but no eval suite.",
    fix="Keep a small eval set of real tasks (including unsafe ones) and run it on every "
        "prompt, tool or model change.",
)
def evals(ctx: ScanContext) -> Outcome:
    eval_dirs = [f for f in ctx.index.files if re.search(r"(^|/)(evals?|evaluations?|agent_?benchmarks?)/", f.path, re.I)
                 and f.kind in (FileKind.CODE, FileKind.CONFIG)]
    frameworks = find(ctx, [r"\b(promptfoo|deepeval|ragas|inspect_ai|openai\.evals|braintrust|langsmith\.evaluation|from langsmith import .*evaluate|aevaluate\(|EvalCase|eval_dataset)\b"],
                      CODE_AND_CONFIG + (FileKind.CI,), production_only=False)
    if eval_dirs or frameworks:
        ev = frameworks[:3] + [Evidence(f.path, 1, "eval file") for f in eval_dirs[:2]]
        return Outcome(Status.PASS, "An eval suite exists.", tuple(ev))
    weak = find(ctx, [r"\b(golden|llm[-_ ]?as[-_ ]?(a[-_ ]?)?judge|judge_\w+|rubric|snapshot)\b"], CODE, tests_only=True, flags=re.I)
    judged_tasks = [e for e in weak if re.search(r"eval", e.path.rsplit("/", 1)[-1], re.I) and "judge" in e.snippet.lower()]
    if judged_tasks:
        return Outcome(Status.PASS, "Agent tasks are scored by an LLM judge.", tuple(judged_tasks))
    if weak:
        return Outcome(Status.PARTIAL, "Golden or judge-based tests exist, but no eval suite.", tuple(weak))
    return Outcome(Status.MISSING, "No evals of agent behaviour found.")


@check(
    "ER-03", L, "Safety controls have their own tests", Severity.HIGH,
    why="The tests that matter most are the ones where the agent should be stopped: the "
        "denied approval, the injected instruction, the path that escapes the workspace.",
    look_for="Tests about prompt injection, jailbreaks, denied or expired approvals, "
             "forbidden tools, unauthorised access, path traversal, budget exhaustion.",
    full="Three or more test files exercise refusals and attacks.",
    partial="One or two test files do.",
    fix="For every control in this scorecard, add a test that proves it blocks the bad case.",
)
def safety_tests(ctx: ScanContext) -> Outcome:
    # Letter boundaries, not \b, so test names like test_prompt_injection_blocked match.
    lb, rb = r"(?<![A-Za-z])", r"(?![A-Za-z])"
    hits = find(ctx, [
        lb + r"(prompt[-_ ]?injection|injection|jailbreak|red[-_ ]?team|adversarial|malicious|untrusted|unauthori[sz]ed|forbidden|bypass\w*|escalat\w*|traversal|exfiltrat\w*|budget[-_ ]?exceeded|ssrf)" + rb,
        lb + r"(approval|approve|confirm\w*)[\w ]{0,40}(denied|rejected|expired|declined)" + rb
        + "|" + lb + r"(denied|rejected|expired|declined)[\w ]{0,40}(approval|confirm\w*)",
        lb + r"(blocked|refuse[sd]?|not allowed|disallowed)[\w ]{0,30}(tool|command|domain|path|action)s?" + rb,
    ], (FileKind.CODE,), tests_only=True, flags=re.I, limit=300, code_only=False)
    n = distinct_files(hits)
    if n >= 3:
        return Outcome(Status.PASS, f"{n} test files exercise refusals or attacks.", tuple(hits))
    if n:
        return Outcome(Status.PARTIAL, f"{n} test file(s) exercise refusals or attacks.", tuple(hits))
    return Outcome(Status.MISSING, "No tests of safety controls found.")


@check(
    "ER-04", L, "The agent can be stopped or rolled back", Severity.MEDIUM,
    why="When an agent misbehaves in production you need to turn it off in seconds, or run "
        "it without side effects, without a deploy.",
    look_for="Kill switches, feature flags, dry-run / simulation / shadow modes, circuit "
             "breakers, emergency stop; weaker: rollback, undo or checkpoints.",
    full="A kill switch, flag or dry-run mode can disable or defang the agent.",
    partial="Actions can be rolled back or replayed from checkpoints, but not switched off.",
    fix="Add a runtime kill switch per agent and per tool tier, and a dry-run mode that "
        "records actions instead of executing them.",
)
def kill_switch(ctx: ScanContext) -> Outcome:
    return tiered(
        ctx,
        full=[r"\b(kill[-_ ]?switch|feature[-_ ]?flags?|dry[-_ ]?run|DRY_RUN|dryRun|simulation[-_ ]?mode|simulate_only|shadow[-_ ]?mode|circuit[-_ ]?breaker|emergency[-_ ]?stop|AGENT_ENABLED|agents?_enabled|pause_agent|disable_agent)\b"],
        partial=[r"\b(rollback|roll_back|undo|revert|checkpointer|MemorySaver|PostgresSaver|SqliteSaver|time[-_ ]?travel)\b"],
        kinds=CODE_AND_CONFIG,
        flags=re.I,
        full_msg="The agent can be switched off or run without side effects.",
        partial_msg="State can be rolled back, but there is no switch to stop the agent.",
        missing_msg="No kill switch, dry-run mode or rollback found.",
    )

