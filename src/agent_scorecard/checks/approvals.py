"""Layer 2: human approval gates. Who says yes before the agent acts?"""

from __future__ import annotations

import re

from ..model import Evidence, Layer, Severity, Status
from .base import NO_TOOLS_MSG, CODE, CODE_AND_CONFIG, Outcome, ScanContext, check, distinct_files, find, near

L = Layer.APPROVALS

# Framework-specific gate signals, grouped so the adapters are easy to extend.
GATE_SIGNALS = {
    "langgraph": [r"(?<!def )(?<![\w.])interrupt\(", r"\binterrupt_(before|after)\s*=", r"\bCommand\(\s*resume\s*="],
    "crewai": [r"\bhuman_input\s*=\s*True\b"],
    "claude_agent_sdk": [r"\b(can_use_tool|canUseTool)\s*[=:]", r"\bPreToolUse\b", r"\bpermission_mode\s*=\s*['\"](default|plan|acceptEdits)['\"]"],
    "openai_agents": [r"\b(needs_approval|needsApproval)\s*[=:]"],
    "generic": [
        r"\b(request|require|await|wait_for|ask_for|pending|get)_(human_)?approvals?\b",
        r"\bapproval_(gate|required|request|requests|status|policy|queue|flow|token)\b",
        r"\b(ApprovalGate|ApprovalRequest|ApprovalPolicy|ApprovalStatus|HumanApproval|PendingApproval)\b",
        r"\b(confirmation_policy|ConfirmationPolicy|confirmation_mode|requires_confirmation|confirm_risky|ConfirmRisky|ask_confirmation|request_confirmation|needs_confirmation|pending_confirmation)\b",
        r"\b(confirm[_-]?first|ConfirmFirst|pending_(approval|confirmation)s?|PendingApprovals?|awaiting_(approval|confirmation))\b",
    ],
}


def gate_evidence(ctx: ScanContext) -> list[Evidence]:
    patterns = [p for pats in GATE_SIGNALS.values() for p in pats]
    return find(ctx, patterns, CODE, langs=None)


# Terminal and browser prompts ask the person at the keyboard, not about an agent's action.
_UI_CONFIRM = re.compile(r"\b(click|typer|Confirm|rich\.prompt\.Confirm)\.(confirm|ask)\(|\bwindow\.confirm\(|(?<![\w.])confirm\(\s*['\"`]")

_APPROVAL_WORDS = [r"\b(approv\w*|confirmation\w*|human_input|interrupt\(|can_use_tool|PreToolUse)"]


@check(
    "AG-01", L, "Side effects wait for human approval", Severity.CRITICAL,
    why="The one control that stops a confused or hijacked agent before it sends, pays, "
        "deletes or deploys. Everything else only tells you afterwards.",
    look_for="LangGraph interrupt() / interrupt_before, CrewAI human_input=True, Claude Agent "
             "SDK can_use_tool or PreToolUse hooks, OpenAI Agents needs_approval, or an "
             "approval request/queue/policy of the project's own.",
    full="A real gate pauses the agent for a human decision on risky actions.",
    partial="Approval or confirmation is mentioned in code, but no blocking gate was found.",
    fix="Put a gate in front of every side-effecting tool tier: the agent proposes, a "
        "human approves the exact action, and only then does it run.",
)
def approval_gate(ctx: ScanContext) -> Outcome:
    if not ctx.has_tools:
        return Outcome(Status.NOT_APPLICABLE, NO_TOOLS_MSG)
    gates = gate_evidence(ctx)
    if gates:
        return Outcome(Status.PASS, f"Approval gates found in {distinct_files(gates)} file(s).", tuple(gates))
    weak = [e for e in find(ctx, [r"\b(approve|approval|approver|confirm)\w*\s*\("], CODE, flags=re.I, paths=ctx.agent_files)
            if not _UI_CONFIRM.search(e.snippet)]
    if weak:
        return Outcome(Status.PARTIAL, "Approval or confirmation calls exist, but no blocking gate was identified.", tuple(weak))
    return Outcome(Status.MISSING, "No human approval step found before agent actions.")


@check(
    "AG-02", L, "Approvals are bound to the exact action", Severity.HIGH,
    why="An approval that says 'yes' without pinning what was approved can be replayed or "
        "swapped for a different payload between the click and the call.",
    look_for="In approval code: a signature or hash of the action (hmac, sha256, digest, "
             "nonce) and an expiry (expires_at, ttl).",
    full="Approvals are signed or hashed over the action and expire.",
    partial="Approvals carry either an integrity check or an expiry, not both.",
    fix="Store the proposed action, sign or hash it with the approval id, give it a short "
        "expiry, and re-check both right before execution.",
)
def approval_binding(ctx: ScanContext) -> Outcome:
    if not ctx.has_tools:
        return Outcome(Status.NOT_APPLICABLE, NO_TOOLS_MSG)
    if not find(ctx, _APPROVAL_WORDS, CODE, flags=re.I):
        return Outcome(Status.MISSING, "No approval flow to bind.")
    integrity = near(ctx, _APPROVAL_WORDS, [r"\b(hmac|HMAC|sha256|SHA256|hexdigest|nonce|signature|sign_payload|compare_digest|ConstantTimeCompare|payload_hash|action_hash)\b"], flags=re.I)
    expiry = near(ctx, _APPROVAL_WORDS, [r"\b(expires_at|expires_in|expiry|expiration|ttl|TTL|valid_until|max_age|timeout_hours)\b"], flags=re.I)
    if integrity and expiry:
        return Outcome(Status.PASS, "Approval code signs or hashes requests and enforces expiry.", tuple(integrity[:3] + expiry[:2]))
    if integrity or expiry:
        which = "an integrity check" if integrity else "an expiry"
        return Outcome(Status.PARTIAL, f"Approval code has {which} but not both.", tuple(integrity + expiry))
    return Outcome(Status.MISSING, "Approvals are not tied to a hash or expiry of the approved action.")


_BYPASS = [
    r"[=:]\s*['\"](bypassPermissions|bypass_permissions)['\"]",
    r"['\"]--dangerously-skip-permissions['\"]|\bdangerouslySkipPermissions\s*[=:]\s*true",
    r"\b(auto_?approve|autoApprove|always_approve|approve_all|skip_approval|skip_confirmation|AUTO_APPROVE)\s*[=:]\s*(True|true|1|['\"](1|true|yes)['\"])",
    r"--yolo\b",
    r"\bconfirmation_mode\s*=\s*False\b",
]
_FAIL_CLOSED = [
    r"\b(deny[_ -]?by[_ -]?default|default[_ -]?deny|fail[_ -]?closed|fail[_ -]?safe|DEFAULT_DENY|DenyAll|deny_all)\b",
    r"\b(deny|reject)\w*\b.{0,40}\b(unknown|unlisted|unclassified)\s+(tools?|actions?)\b",
]
# Timeout or expiry leading to rejection only counts next to approval code.
_TIMEOUT_DENY = [r"\b(timeout|timed[_ ]out|expired|expiry|expires|ttl)\b.{0,60}\b(deny|denied|reject\w*|auto[-_ ]?reject\w*|cancel\w*)\b"]


@check(
    "AG-03", L, "The gate fails closed", Severity.CRITICAL,
    why="Gates break in boring ways: a timeout, a missing tier, an env var left on from a "
        "demo. If the default is 'allow', the gate is decoration.",
    look_for="Anti-patterns in production code: bypassPermissions, auto_approve=True, "
             "--yolo, confirmation_mode=False. Good signs: deny-by-default, reject on timeout "
             "or expiry, unknown tools denied.",
    full="Defaults deny, and nothing in production code switches approvals off.",
    partial="A gate exists and no bypass was found, but its failure default is not visible.",
    fix="Make deny the default on timeout, error and unknown tools. Keep bypass modes out of "
        "production code paths, behind an explicit, logged, test-only flag.",
)
def fail_closed(ctx: ScanContext) -> Outcome:
    if not ctx.has_tools:
        return Outcome(Status.NOT_APPLICABLE, NO_TOOLS_MSG)
    bypass = [Evidence(e.path, e.line, e.snippet, negative=True)
              for e in find(ctx, _BYPASS, CODE_AND_CONFIG)]
    closed = find(ctx, _FAIL_CLOSED, CODE, flags=re.I) + near(ctx, _APPROVAL_WORDS, _TIMEOUT_DENY, flags=re.I)
    gates = gate_evidence(ctx)
    if bypass and (closed or gates):
        return Outcome(Status.PARTIAL, f"Gates exist, but a bypass is set as a value in {distinct_files(bypass)} production file(s).",
                       tuple(bypass[:3] + (closed or gates)[:2]))
    if bypass:
        return Outcome(Status.MISSING, f"Approval bypass switched on in {distinct_files(bypass)} production file(s).", tuple(bypass))
    if closed:
        return Outcome(Status.PASS, "Deny-by-default or reject-on-timeout logic found, and no bypass.", tuple(closed))
    if gates:
        return Outcome(Status.PARTIAL, "A gate exists and nothing bypasses it, but its default on timeout or error is not visible.")
    return Outcome(Status.MISSING, "No gate, so nothing fails closed.")


@check(
    "AG-04", L, "Approval decisions are recorded", Severity.HIGH,
    why="When something goes wrong the first question is 'who approved this, and what did "
        "they see?'. That answer has to exist before the incident.",
    look_for="approved_by / approver_id / decided_by / decision records / an approvals "
             "table, and approved_at or decision timestamps.",
    full="Each decision stores who decided and when.",
    partial="Decisions are stored, but without who made them.",
    fix="Persist every approval and rejection with approver identity, timestamp, the exact "
        "action shown and the outcome.",
)
def approval_record(ctx: ScanContext) -> Outcome:
    if not ctx.has_tools:
        return Outcome(Status.NOT_APPLICABLE, NO_TOOLS_MSG)
    who = find(ctx, [
        r"\b(approved_by|approver|approver_id|approverId|approvedBy|decided_by|decidedBy|reviewer_id|rejected_by)\b",
        r"\b(DecisionRecord|decision_record|approval_log|approvals_log|ApprovalRecord|approval_audit)\b",
    ], CODE_AND_CONFIG)
    if who:
        return Outcome(Status.PASS, f"Approver identity is recorded ({distinct_files(who)} file(s)).", tuple(who))
    when = find(ctx, [r"\b(approved_at|approvedAt|decided_at|decision_at|rejected_at)\b"], CODE_AND_CONFIG)
    if when:
        return Outcome(Status.PARTIAL, "Decision times are stored, but not who decided.", tuple(when))
    return Outcome(Status.MISSING, "No record of approval decisions found.")
