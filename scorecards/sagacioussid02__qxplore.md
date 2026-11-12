# Agent Safety Scorecard: sagacioussid02/qxplore

**Score: 42/100 · Grade D**

Scanned @ `867ff63` on 2026-11-12 with agent-scorecard 0.1.0 · 228 files · Frameworks: Anthropic API

## Layers

| # | Layer | Score | |
|---|---|---:|---|
| 1 | Tool boundaries | 50 | █████░░░░░ |
| 2 | Human approval gates | n/a | n/a |
| 3 | Audit trail and observability | 25 | ██░░░░░░░░ |
| 4 | Secrets and egress | 75 | ████████░░ |
| 5 | Budgets and limits | 50 | █████░░░░░ |
| 6 | Untrusted input handling | 40 | ████░░░░░░ |
| 7 | Evals, testing and rollback | 14 | █░░░░░░░░░ |

## Critical gaps

- **UI-01 Untrusted content is marked as data.** No handling of untrusted content found. Fix: Wrap every piece of external content in a labelled block, tell the model it is data, never instructions, screen it, and keep tool tiers enforced whatever it says.

## Top fixes

1. **UI-01 Untrusted content is marked as data** (critical): Wrap every piece of external content in a labelled block, tell the model it is data, never instructions, screen it, and keep tool tiers enforced whatever it says.
2. **AU-04 Secrets are redacted from logs and traces** (high): Run every logged payload through a redactor (known keys plus token patterns) and test it with real-looking secrets.
3. **ER-02 Agent behaviour has evals** (high): Keep a small eval set of real tasks (including unsafe ones) and run it on every prompt, tool or model change.
4. **ER-03 Safety controls have their own tests** (high): For every control in this scorecard, add a test that proves it blocks the bad case.
5. **SE-04 Outbound network access is restricted** (high): Route agent HTTP through one client with a domain allowlist, block private and metadata IPs, and deny network by default in sandboxes.

## Checks

| ID | Check | Severity | Result | Finding |
|---|---|---|---|---|
| TB-01 | Tools are an explicit allowlist | high | N/A | No tool calling found: a chat-only model app has no actions to limit or gate. |
| TB-02 | Tools carry a risk tier | critical | N/A | No tool calling found: a chat-only model app has no actions to limit or gate. |
| TB-03 | Code and shell execution is sandboxed | critical | N/A | No command or code execution found in production code. |
| TB-04 | File access is confined to a workspace | high | N/A | No file writes or deletes found in production code. |
| TB-05 | Tool supply chain is pinned | medium | PARTIAL | Locked in places, but 2 of 3 manifests have no lockfile. |
| AG-01 | Side effects wait for human approval | critical | N/A | No tool calling found: a chat-only model app has no actions to limit or gate. |
| AG-02 | Approvals are bound to the exact action | high | N/A | No tool calling found: a chat-only model app has no actions to limit or gate. |
| AG-03 | The gate fails closed | critical | N/A | No tool calling found: a chat-only model app has no actions to limit or gate. |
| AG-04 | Approval decisions are recorded | high | N/A | No tool calling found: a chat-only model app has no actions to limit or gate. |
| AU-01 | Every tool call is logged as a structured event | high | PARTIAL | The app logs, but tool calls are not captured as audit events. |
| AU-02 | Runs are traced end to end | medium | PARTIAL | Runs carry ids, but no tracing backend is wired in. |
| AU-03 | The audit trail is durable and tamper-evident | medium | MISSING | No durable audit storage found. |
| AU-04 | Secrets are redacted from logs and traces | high | MISSING | No redaction of secrets in logs or traces found. |
| SE-01 | No secrets are committed | critical | PASS | No committed secrets detected. |
| SE-02 | Secrets come from the environment or a vault | high | PASS | Secrets are read at runtime and .env is git-ignored. |
| SE-03 | Secret scanning runs before merge | medium | PASS | A secret scanner runs in CI or pre-commit. |
| SE-04 | Outbound network access is restricted | high | MISSING | No outbound network restrictions found. |
| BL-01 | Agent loops have a step cap | critical | N/A | No tool calling found: a chat-only model app has no actions to limit or gate. |
| BL-02 | Spend has a budget | high | PARTIAL | Spend is tracked or capped per call, but no budget stops a run. |
| BL-03 | Model and tool calls time out | high | PARTIAL | A timeout is set in one file only. |
| UI-01 | Untrusted content is marked as data | critical | MISSING | No handling of untrusted content found. |
| UI-02 | Model output is parsed into a schema | high | PASS | Model output is validated against schemas. |
| UI-03 | Tool arguments are validated | high | N/A | No tool calling found: a chat-only model app has no actions to limit or gate. |
| ER-01 | Tests exist and run in CI | high | PARTIAL | 7 test file(s), not run in CI. |
| ER-02 | Agent behaviour has evals | high | MISSING | No evals of agent behaviour found. |
| ER-03 | Safety controls have their own tests | high | MISSING | No tests of safety controls found. |
| ER-04 | The agent can be stopped or rolled back | medium | MISSING | No kill switch, dry-run mode or rollback found. |

## Evidence

**TB-05 Tool supply chain is pinned**

- anti-pattern · `package.json:1` `no lockfile covers this manifest`
- anti-pattern · `backend/package.json:1` `no lockfile covers this manifest`
- `frontend/package.json:1` `locked`

**AU-01 Every tool call is logged as a structured event**

- `backend/main.py:18` `log = logging.getLogger(__name__)`
- `backend/agents/base.py:7` `log = logging.getLogger(__name__)`
- `backend/core/supabase_auth.py:8` `log = logging.getLogger(__name__)`
- `backend/quantum/shor.py:33` `log = logging.getLogger(__name__)`
- `backend/routers/agents.py:28` `log = logging.getLogger(__name__)`

**AU-02 Runs are traced end to end**

- `backend/routers/benchmark.py:245` `run_id = await _save_run(user["sub"], result, settings)`
- `backend/routers/benchmark.py:246` `result.id = run_id`
- `backend/routers/benchmark.py:281` `@router.get("/runs/{run_id}", response_model=BenchmarkResult)`
- `backend/routers/benchmark.py:282` `async def get_run(run_id: str, user: dict = Depends(require_user)):`
- `backend/routers/benchmark.py:290` `params={"id": f"eq.{run_id}", "user_id": f"eq.{user['sub']}", "select": "*"},`

**SE-02 Secrets come from the environment or a vault**

- `backend/src/index.js:7` `const PORT = process.env.PORT || 3000;`
- `backend/src/index.js:17` `windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 15 * 60 * 1000,`
- `backend/src/index.js:18` `max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || 100,`
- `.gitignore:1` `.env ignored`

**SE-03 Secret scanning runs before merge**

- `.gitleaks.toml:4` `title = "Quantumanic Gitleaks Config"`
- `.github/workflows/auto-pr.yml:5` `workflows: ["Secret Scan"]`
- `.github/workflows/auto-pr.yml:19` `# Only run if the secret scan passed and the run originated from this repo (not a fork)`
- `.github/workflows/auto-pr.yml:58` `…f "## Summary\nAuto-generated draft PR from branch \'%s\'.\n\n**Commit:** \'%s\' — %s\n\nPassed secret scan (Gitleaks) before creation.\n" \…`
- `.github/workflows/secret-scan.yml:1` `name: Secret Scan`

**BL-02 Spend has a budget**

- `backend/agents/base.py:13` `def __init__(self, system_prompt: str, max_tokens: int = 1024, temperature: float = 1.0):`
- `backend/agents/base.py:17` `self.max_tokens = max_tokens`
- `backend/agents/base.py:23` `max_tokens=self.max_tokens,`
- `backend/agents/base.py:40` `max_tokens=self.max_tokens,`
- `backend/agents/concept_qa.py:15` `super().__init__(system_prompt=_SYSTEM, max_tokens=1024)`

**BL-03 Model and tool calls time out**

- `backend/core/supabase_auth.py:19` `async with httpx.AsyncClient(timeout=5.0) as client:`

**UI-02 Model output is parsed into a schema**

- `backend/routers/agents.py:48` `ctx = TutorContext.model_validate_json(unquote(context))`
- `backend/routers/agents.py:59` `evt = GameMasterEvent.model_validate_json(unquote(event))`
- `backend/routers/agents.py:75` `req = ConceptQARequest.model_validate_json(unquote(payload))`

**ER-01 Tests exist and run in CI**

- `test_ttt.py:1` `test file`
- `backend/tests/__init__.py:1` `test file`

---

This is a static scan: it reads code and config and never runs them. It finds the presence of controls, not proof that they work. A PASS means the signal is there; a MISSING can be a control the scanner doesn't recognise yet. RUBRIC.md explains every check and how it is scored.
