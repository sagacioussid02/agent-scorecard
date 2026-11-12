"""Layer 3: audit trail and observability. Can you reconstruct what happened?"""

from __future__ import annotations

import re

from ..model import Layer, Severity, Status
from .base import ANY_TEXT, CODE, CODE_AND_CONFIG, Outcome, ScanContext, check, distinct_files, find, tiered

L = Layer.AUDIT

_AUDIT = [
    r"\baudit[_ ]?(log|logs|trail|event|events|record|records|entry|entries|sink|writer|logger)\b",
    r"\b(AuditLog|AuditEvent|AuditEntry|AuditTrail|AuditRecord|AuditLogger|Auditor)\b",
    r"\b(log_tool_call|tool_call_log|record_tool_call|ToolCallEvent|ToolCallRecord|on_tool_(start|end|error))\b",
    r"\b(ActionEvent|ObservationEvent)\b",
]


@check(
    "AU-01", L, "Every tool call is logged as a structured event", Severity.HIGH,
    why="Agents fail in ways nobody predicted. A structured record of each tool call, its "
        "arguments and its result is the only way to find out what actually happened.",
    look_for="Audit log/event types, tool-call callbacks (on_tool_start/on_tool_end), action "
             "and observation events; weaker: plain application logging.",
    full="Tool calls are written to a dedicated audit or event log.",
    partial="General logging only; tool calls are not recorded as their own events.",
    fix="Emit one structured event per tool call (agent, tool, args digest, result status, "
        "approval id, cost) to an audit sink separate from debug logs.",
)
def tool_call_log(ctx: ScanContext) -> Outcome:
    return tiered(
        ctx,
        full=_AUDIT,
        partial=[r"\b(structlog|logging\.getLogger|getLogger\(|zap\.New|slog\.(New|Info)|pino\(|winston\.)", r"\blogger\.(info|debug)\(.{0,40}\btool"],
        flags=re.I,
        full_msg="Tool calls are recorded as audit events.",
        partial_msg="The app logs, but tool calls are not captured as audit events.",
        missing_msg="No logging of agent actions found.",
    )


@check(
    "AU-02", L, "Runs are traced end to end", Severity.MEDIUM,
    why="A trace ties the prompt, every model call, every tool call and the cost of one run "
        "together, which is what you need to debug and to price the product.",
    look_for="Langfuse, LangSmith, OpenTelemetry, Logfire, Helicone, Arize Phoenix, AgentOps, "
             "Braintrust, Laminar, Weave or Traceloop in code, config or dependencies; weaker: "
             "trace or correlation ids.",
    full="An LLM tracing or OpenTelemetry integration is wired in.",
    partial="Trace or correlation ids exist, but no tracing backend.",
    fix="Wire one tracing backend and propagate a run id through every model and tool call.",
)
def tracing(ctx: ScanContext) -> Outcome:
    return tiered(
        ctx,
        full=[r"\b(langfuse|langsmith|LANGCHAIN_TRACING|LANGSMITH_TRACING|opentelemetry|otel|OTEL_|logfire|helicone|arize|phoenix|agentops|braintrust|laminar|lmnr|traceloop|openllmetry|weave\.init)\b"],
        partial=[r"\b(trace_id|traceId|correlation_id|correlationId|(?<!github\.)run_id|span_id)\b"],
        kinds=ANY_TEXT,
        flags=re.I,
        full_msg="A tracing backend is integrated.",
        partial_msg="Runs carry ids, but no tracing backend is wired in.",
        missing_msg="No tracing found.",
    )


@check(
    "AU-03", L, "The audit trail is durable and tamper-evident", Severity.MEDIUM,
    why="A log the agent (or an attacker using it) can edit is not evidence. Regulated "
        "buyers will ask how you know the record is complete.",
    look_for="append-only storage, hash chaining (prev_hash), object lock / WORM, or "
             "immutability notes; weaker: audit events persisted to a database or file.",
    full="Audit records are append-only or hash-chained.",
    partial="Audit events are persisted, but nothing makes them tamper-evident.",
    fix="Write audit events append-only (separate table with insert-only grants, or object "
        "lock), and chain each record to the previous hash.",
)
def tamper_evident(ctx: ScanContext) -> Outcome:
    strong = find(ctx, [r"\b(append[-_ ]?only|hash[-_ ]?chain\w*|prev(ious)?_hash|tamper[-_ ]?(evident|proof)|immutable[-_ ]audit|object[-_ ]?lock|WORM)\b"], CODE_AND_CONFIG, flags=re.I)
    if strong:
        return Outcome(Status.PASS, "Audit storage is append-only or hash-chained.", tuple(strong))
    audit_files = {e.path for e in find(ctx, _AUDIT, CODE, flags=re.I)}
    persisted = [e for e in find(ctx, [r"(INSERT\s+INTO|insert_one|\binsert\(|\.add\(|\.write\(|put_item|PutObject|\.jsonl|appendFile|O_APPEND|['\"]a['\"]\))"], CODE, flags=re.I)
                 if e.path in audit_files]
    if persisted:
        return Outcome(Status.PARTIAL, "Audit events are persisted, but not tamper-evident.", tuple(persisted))
    return Outcome(Status.MISSING, "No durable audit storage found.")


@check(
    "AU-04", L, "Secrets are redacted from logs and traces", Severity.HIGH,
    why="Agents see tokens in tool arguments and results. Without redaction, the audit log "
        "becomes the easiest place to steal them from.",
    look_for="redact / scrub / mask_secret / SecretStr / REDACTED helpers in logging or "
             "tracing code.",
    full="A redaction step strips secrets before logging or tracing.",
    partial="Secrets are wrapped in secret types, but no redaction of log output was found.",
    fix="Run every logged payload through a redactor (known keys plus token patterns) and "
        "test it with real-looking secrets.",
)
def redaction(ctx: ScanContext) -> Outcome:
    strong = find(ctx, [r"\b(redact\w*|scrub\w*|mask_(secret|secrets|token|key|sensitive)\w*|sanitize_(log|secret|sensitive)\w*|REDACTED|\[redacted\]|filter_sensitive\w*)\b"], CODE, flags=re.I)
    if strong:
        return Outcome(Status.PASS, f"Redaction found in {distinct_files(strong)} file(s).", tuple(strong))
    weak = find(ctx, [r"\b(SecretStr|SecretBytes|SecretValue|Secret\[)\b"], CODE)
    if weak:
        return Outcome(Status.PARTIAL, "Secret types are used, but logs are not explicitly redacted.", tuple(weak))
    return Outcome(Status.MISSING, "No redaction of secrets in logs or traces found.")

