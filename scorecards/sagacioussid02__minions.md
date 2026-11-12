# Agent Safety Scorecard: sagacioussid02/minions

**Score: 77/100 · Grade C** (capped at C by a missing critical control)

Scanned @ `500da66` on 2026-11-12 with agent-scorecard 0.1.0 · 451 files · Frameworks: LangGraph, CrewAI, LangChain, Anthropic API

## Layers

| # | Layer | Score | |
|---|---|---:|---|
| 1 | Tool boundaries | 54 | █████░░░░░ |
| 2 | Human approval gates | 100 | ██████████ |
| 3 | Audit trail and observability | 92 | █████████░ |
| 4 | Secrets and egress | 62 | ██████░░░░ |
| 5 | Budgets and limits | 100 | ██████████ |
| 6 | Untrusted input handling | 57 | ██████░░░░ |
| 7 | Evals, testing and rollback | 71 | ███████░░░ |

## Critical gaps

- **TB-02 Tools carry a risk tier.** No risk classification of tools found. Fix: Add a tier to every tool (read, write, irreversible) and make approvals and budgets key off it. MCP's readOnlyHint and destructiveHint are a good minimum.
- **UI-01 Untrusted content is marked as data.** No handling of untrusted content found. Fix: Wrap every piece of external content in a labelled block, tell the model it is data, never instructions, screen it, and keep tool tiers enforced whatever it says.

## Top fixes

1. **TB-02 Tools carry a risk tier** (critical): Add a tier to every tool (read, write, irreversible) and make approvals and budgets key off it. MCP's readOnlyHint and destructiveHint are a good minimum.
2. **UI-01 Untrusted content is marked as data** (critical): Wrap every piece of external content in a labelled block, tell the model it is data, never instructions, screen it, and keep tool tiers enforced whatever it says.
3. **ER-02 Agent behaviour has evals** (high): Keep a small eval set of real tasks (including unsafe ones) and run it on every prompt, tool or model change.
4. **SE-04 Outbound network access is restricted** (high): Route agent HTTP through one client with a domain allowlist, block private and metadata IPs, and deny network by default in sandboxes.
5. **TB-04 File access is confined to a workspace** (high): Resolve every path the agent supplies and reject it unless it sits under the workspace root. Test it with ../ and symlink cases.

## Checks

| ID | Check | Severity | Result | Finding |
|---|---|---|---|---|
| TB-01 | Tools are an explicit allowlist | high | PASS | Tool access goes through an allowlist. |
| TB-02 | Tools carry a risk tier | critical | MISSING | No risk classification of tools found. |
| TB-03 | Code and shell execution is sandboxed | critical | PASS | Execution runs inside a sandbox or container. |
| TB-04 | File access is confined to a workspace | high | MISSING | Files are written or deleted (19 file(s)) with no path confinement found. |
| TB-05 | Tool supply chain is pinned | medium | PASS | All 2 dependency manifest(s) are locked. |
| AG-01 | Side effects wait for human approval | critical | PASS | Approval gates found in 10 file(s). |
| AG-02 | Approvals are bound to the exact action | high | PASS | Approval code signs or hashes requests and enforces expiry. |
| AG-03 | The gate fails closed | critical | PASS | Deny-by-default or reject-on-timeout logic found, and no bypass. |
| AG-04 | Approval decisions are recorded | high | PASS | Approver identity is recorded (1 file(s)). |
| AU-01 | Every tool call is logged as a structured event | high | PASS | Tool calls are recorded as audit events. |
| AU-02 | Runs are traced end to end | medium | PASS | A tracing backend is integrated. |
| AU-03 | The audit trail is durable and tamper-evident | medium | PARTIAL | Audit events are persisted, but not tamper-evident. |
| AU-04 | Secrets are redacted from logs and traces | high | PASS | Redaction found in 8 file(s). |
| SE-01 | No secrets are committed | critical | PASS | No committed secrets detected. |
| SE-02 | Secrets come from the environment or a vault | high | PASS | Secrets are read at runtime and .env is git-ignored. |
| SE-03 | Secret scanning runs before merge | medium | MISSING | No secret or security scanning in CI or pre-commit. |
| SE-04 | Outbound network access is restricted | high | MISSING | No outbound network restrictions found. |
| BL-01 | Agent loops have a step cap | critical | PASS | Agent loops are capped. |
| BL-02 | Spend has a budget | high | PASS | A spend budget is enforced. |
| BL-03 | Model and tool calls time out | high | PASS | Timeouts set in 13 file(s). |
| UI-01 | Untrusted content is marked as data | critical | MISSING | No handling of untrusted content found. |
| UI-02 | Model output is parsed into a schema | high | PASS | Model output is validated against schemas. |
| UI-03 | Tool arguments are validated | high | PASS | Tool inputs are validated. |
| ER-01 | Tests exist and run in CI | high | PASS | 81 test files, run in CI. |
| ER-02 | Agent behaviour has evals | high | MISSING | No evals of agent behaviour found. |
| ER-03 | Safety controls have their own tests | high | PASS | 12 test files exercise refusals or attacks. |
| ER-04 | The agent can be stopped or rolled back | medium | PASS | The agent can be switched off or run without side effects. |

## Evidence

**TB-01 Tools are an explicit allowlist**

- `src/minions/agents/base.py:42` `tool_allowlist: list[str] = field(default_factory=list)`

**TB-03 Code and shell execution is sandboxed**

- `src/minions/preflight/runner.py:176` `wrapped = _apply_network_sandbox(command, posture=network, step=step)`
- `src/minions/preflight/runner.py:234` `def _apply_network_sandbox(command: str, *, posture: NetworkPosture, step: str) -> str:`
- `src/minions/preflight/runner.py:254` `"preflight: network sandbox falling back to proxy-blackhole (no 'unshare' available)"`
- anti-pattern · `src/minions/preflight/runner.py:184` `shell=True,`

**TB-05 Tool supply chain is pinned**

- `pyproject.toml:1` `locked`
- `web/package.json:1` `locked`

**AG-01 Side effects wait for human approval**

- `src/minions/approval/graph.py:53` `response = interrupt({"decision_id": state["decision_id"]})`
- `web/lib/crew-dashboard.ts:25` `queue: { needs_approval: number; ready: number; in_progress: number; blocked: number };`
- `web/lib/crew-dashboard.ts:130` `const queue = { needs_approval: 0, ready: 0, in_progress: 0, blocked: 0 };`
- `web/components/sidebar/Sidebar.tsx:187` `["Pending approvals", c.pending_approvals],`
- `web/lib/queries.ts:1740` `) AS pending_approvals,`

**AG-02 Approvals are bound to the exact action**

- `src/minions/approval/tokens.py:16` `import hmac`
- `src/minions/approval/tokens.py:50` `sig = hmac.new(_key(), payload_b64.encode("ascii"), hashlib.sha256).digest()`
- `src/minions/approval/tokens.py:61` `expected = hmac.new(_key(), payload_b64.encode("ascii"), hashlib.sha256).digest()`
- `src/minions/__main__.py:1206` `timeout_hours: float = typer.Option(72.0, "--ttl-hours"),`
- `src/minions/__main__.py:1211` `timed_out = _sweep(store=_store(), notifier=_notifier(), ttl_hours=timeout_hours)`

**AG-03 The gate fails closed**

- `src/minions/__main__.py:1819` `72.0, "--timeout-hours", help="TTL for pending decisions before auto-reject."`
- `src/minions/approval/tokens.py:24` `DEFAULT_TTL_SECONDS = 72 * 60 * 60  # 72 hours, matches the spec's auto-reject window`

**AG-04 Approval decisions are recorded**

- `src/minions/dashboard/app.py:190` `f"{os.getenv('OPERATOR_EMAIL', 'operator@example.com')} — sole human-in-the-loop approver"`

**AU-01 Every tool call is logged as a structured event**

- `src/minions/agents/safety.py:33` `vendor in writing (recorded in the audit log).`
- `src/minions/crews/engineer.py:796` `"in the audit log.\n"`
- `src/minions/dashboard/app.py:548` `placeholder="Why approve / reject? Goes into the audit log.",`
- `src/minions/scheduled/pr_review_loop.py:245` `"to keep the sprint board clean and the audit trail explicit.\n\n"`
- `web/lib/agent-chat/context.ts:64` `vendor in writing (recorded in the audit log).`

**AU-02 Runs are traced end to end**

- `pyproject.toml:15` `"langfuse>=4.5.0",`
- `.github/workflows/_cron-shared.yml:18` `LANGFUSE_PUBLIC_KEY:`
- `.github/workflows/_cron-shared.yml:20` `LANGFUSE_SECRET_KEY:`
- `.github/workflows/_cron-shared.yml:22` `LANGFUSE_HOST:`
- `.github/workflows/_cron-shared.yml:67` `LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}`

**AU-03 The audit trail is durable and tamper-evident**

- `src/minions/__main__.py:78` `help="Inspect per-project LLM cost (read from data/local/cost_log.jsonl).",`
- `src/minions/__main__.py:175` `COST_LOG_PATH = REPO_ROOT / "data" / "local" / "cost_log.jsonl"`
- `src/minions/__main__.py:177` `ACTIVITY_LOG_PATH = REPO_ROOT / "data" / "local" / "activity.jsonl"`
- `src/minions/__main__.py:3388` `cost_path = REPO_ROOT / "data" / "local" / "cost_log.jsonl"`
- `src/minions/__main__.py:3400` `activity_path = REPO_ROOT / "data" / "local" / "activity.jsonl"`

**AU-04 Secrets are redacted from logs and traces**

- `src/minions/working_tree.py:127` `sanitized = [shlex.quote(_redact(a)) for a in cmd]`
- `src/minions/working_tree.py:133` `def _redact(arg: str) -> str:`
- `src/minions/working_tree.py:137` `return f"https://x-access-token:<redacted>@{tail}"`
- `src/minions/agile/pm.py:140` `return _redact(text[:300])`
- `src/minions/agile/pm.py:183` `def _redact(text: str) -> str:`

**SE-02 Secrets come from the environment or a vault**

- `src/minions/__main__.py:163` `override = os.environ.get("MINIONS_DOTENV_OVERRIDE", "").lower() in {"1", "true", "yes"}`
- `src/minions/__main__.py:165` `if override or key not in os.environ:`
- `src/minions/__main__.py:166` `os.environ[key] = value`
- `.gitignore:1` `.env ignored`

**BL-01 Agent loops have a step cap**

- `src/minions/crews/factory.py:60` `max_iter=3,  # cost-discipline cap`

**BL-02 Spend has a budget**

- `src/minions/__main__.py:254` `f"  ✓ procurement: budget ${portfolio.procurement.monthly_budget_usd}/mo, "`
- `src/minions/__main__.py:271` `total_monthly += m.monthly_budget_usd`
- `src/minions/__main__.py:274` `f"weekly ${m.weekly_budget_usd}, monthly ${m.monthly_budget_usd}, "`
- `src/minions/__main__.py:346` `monthly_budget_usd=budget,`
- `src/minions/__main__.py:377` `f"\n[bold]{name}[/bold] (${manifest.monthly_budget_usd}/mo) "`

**BL-03 Model and tool calls time out**

- `src/minions/anthropic_check.py:17` `def auth_check(api_key: str, *, timeout: float = DEFAULT_TIMEOUT) -> tuple[bool, str]:`
- `src/minions/anthropic_check.py:28` `timeout=timeout,`
- `src/minions/crews/discoverer.py:634` `timeout=5,`
- `src/minions/crews/discoverer.py:649` `timeout=5,`
- `src/minions/crews/discoverer.py:665` `timeout=5,`

**UI-02 Model output is parsed into a schema**

- `src/minions/crews/code_auditor.py:226` `output_pydantic=CodeAuditOutput,`
- `src/minions/crews/devils_advocate.py:185` `output_pydantic=DevilsAdvocateCritique,`
- `src/minions/crews/engineer.py:1201` `output_pydantic=EngineerOutput,`
- `src/minions/crews/planning.py:698` `return StructuredSprintPlan.model_validate_json(candidate)`
- `src/minions/crews/portfolio_review.py:375` `task_kwargs["output_pydantic"] = expected_pydantic`

**UI-03 Tool arguments are validated**

- `src/minions/agents/memory_store.py:46` `return AgentMemoryRecord.model_validate(raw) if raw is not None else None`
- `src/minions/agents/memory_store.py:50` `(AgentMemoryRecord.model_validate(raw) for raw in self._load().values()),`
- `src/minions/agents/memory_store.py:85` `record = AgentMemoryRecord.model_validate(raw)`
- `src/minions/agents/memory_store_postgres.py:136` `return AgentMemoryRecord.model_validate(`
- `src/minions/agile/store.py:49` `AgileRitualRecord.model_validate(raw) for raw in self._load()["rituals"].values()`

**ER-01 Tests exist and run in CI**

- `.github/workflows/ci.yml:55` `run: pytest -q`

**ER-03 Safety controls have their own tests**

- `tests/test_budget.py:239` `# Same project, escalated to breach — should fire again.`
- `tests/test_dossier_store_isolation.py:10` `or re-export in ''__init__'' does not bypass the factory.`
- `tests/test_dossier_store_isolation.py:39` `"bypasses make_dossier_store and breaks the env-driven backend swap. "`
- `tests/test_engineer_crew.py:18` `is_forbidden_path,`
- `tests/test_engineer_crew.py:56` `"path,forbidden",`

**ER-04 The agent can be stopped or rolled back**

- `src/minions/__main__.py:358` `"(dry-run) or add [bold]--no-dry-run[/bold] for real planning."`
- `src/minions/__main__.py:395` `dry_run: bool = typer.Option(`
- `src/minions/__main__.py:397` `"--dry-run/--no-dry-run",`
- `src/minions/__main__.py:398` `help="Dry run skips LLM calls and does NOT mutate the repo. Use --no-dry-run to actually open a PR.",`
- `src/minions/__main__.py:424` `if not dry_run:`

---

This is a static scan: it reads code and config and never runs them. It finds the presence of controls, not proof that they work. A PASS means the signal is there; a MISSING can be a control the scanner doesn't recognise yet. RUBRIC.md explains every check and how it is scored.
