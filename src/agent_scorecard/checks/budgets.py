"""Layer 5: budgets and limits. What stops a run that will not stop?"""

from __future__ import annotations

import re

from ..model import Layer, Severity, Status
from .base import NO_TOOLS_MSG, CODE, Outcome, ScanContext, check, distinct_files, find, tiered

L = Layer.BUDGETS


@check(
    "BL-01", L, "Agent loops have a step cap", Severity.CRITICAL,
    why="Agents loop: they retry, re-plan and call each other. Without a hard cap, one bad "
        "task becomes thousands of model and tool calls.",
    look_for="recursion_limit (LangGraph), max_iter / max_rpm (CrewAI), max_turns (Claude Agent "
             "SDK, OpenAI Agents), max_steps / max_iterations / max_tool_calls of the project's own. "
             "N/A in a chat-only app with no tool loop.",
    full="Agent runs stop after a bounded number of steps.",
    partial="Only retries are bounded; the agent loop itself is not.",
    fix="Set a step cap on every agent loop, make hitting it a visible failure, and alert on it.",
)
def step_cap(ctx: ScanContext) -> Outcome:
    if not ctx.has_tools:
        return Outcome(Status.NOT_APPLICABLE, NO_TOOLS_MSG)
    return tiered(
        ctx,
        full=[r"\b(recursion_limit|max_iter|max_iterations|max_steps|max_turns|max_rounds|max_tool_calls|max_actions|max_loops|iteration_limit|step_limit|max_agent_steps|maxTurns|maxSteps|maxIterations|MaxSteps|MaxTurns|MaxIterations|max_rpm)\b"],
        partial=[r"\b(max_retries|maxRetries|MaxRetries|retry_limit|max_attempts)\b"],
        kinds=CODE,
        flags=re.I,
        paths=ctx.agent_files,
        full_msg="Agent loops are capped.",
        partial_msg="Retries are bounded, but no cap on agent steps was found.",
        missing_msg="No limit on agent steps or iterations found.",
    )


@check(
    "BL-02", L, "Spend has a budget", Severity.HIGH,
    why="Model spend is the bill nobody sees until month end. A per-run or per-tenant budget "
        "turns a runaway agent into an error instead of an invoice.",
    look_for="max_budget_usd, budget/cost/spend limits, quotas, usage limits, BudgetExceeded; "
             "weaker: cost or token tracking without a limit, or only max_tokens per call.",
    full="Runs or tenants have an enforced cost or token budget.",
    partial="Cost or tokens are tracked, or capped per call, but nothing enforces a budget.",
    fix="Track cost per run and per tenant, stop the run when it crosses a budget, and show "
        "spend next to every run.",
)
def spend_budget(ctx: ScanContext) -> Outcome:
    return tiered(
        ctx,
        full=[r"\b(max_budget\w*|budget_(usd|limit|cap|cents|tokens|exceeded)|cost_(limit|cap|budget)|max_cost\w*|spend(ing)?_(limit|cap)|token_budget|usage_limit|max_total_tokens|BudgetExceeded\w*|daily_(spend|cost|token)_(limit|cap)|quota_exceeded|QuotaExceeded|monthly_(budget|limit))\b"],
        partial=[r"\b(total_cost|cost_usd|costUsd|track_cost|token_usage|tokens_used|usage_metadata|get_openai_callback|max_tokens|maxTokens|accumulated_cost)\b"],
        kinds=CODE,
        flags=re.I,
        paths=ctx.agent_files,
        full_msg="A spend budget is enforced.",
        partial_msg="Spend is tracked or capped per call, but no budget stops a run.",
        missing_msg="No cost or token budget found.",
    )


@check(
    "BL-03", L, "Model and tool calls time out", Severity.HIGH,
    why="A hung tool call holds a worker, a lock and sometimes an approval slot forever. "
        "Timeouts are what make the other limits enforceable.",
    look_for="timeout= arguments, asyncio.wait_for / asyncio.timeout, context.WithTimeout, "
             "AbortSignal.timeout, request_timeout across several files.",
    full="Timeouts are set on calls in several places.",
    partial="A timeout appears in only one place.",
    fix="Give every model call, tool call and external request a timeout, and make the agent "
        "treat a timeout as a failed step.",
)
def timeouts(ctx: ScanContext) -> Outcome:
    hits = find(ctx, [
        r"\b(timeout|request_timeout|read_timeout|connect_timeout)\s*[=:]\s*[\w.(]",
        r"\basyncio\.(wait_for|timeout)\(",
        r"\bcontext\.WithTimeout\(|\bAbortSignal\.timeout\(|\bhttp\.Client\{[^}]*Timeout",
    ], CODE)
    if distinct_files(hits) >= 2:
        return Outcome(Status.PASS, f"Timeouts set in {distinct_files(hits)} file(s).", tuple(hits))
    if hits:
        return Outcome(Status.PARTIAL, "A timeout is set in one file only.", tuple(hits))
    return Outcome(Status.MISSING, "No timeouts on model, tool or network calls found.")

