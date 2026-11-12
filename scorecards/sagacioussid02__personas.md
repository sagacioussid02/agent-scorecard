# Agent Safety Scorecard: sagacioussid02/personas

**Score: 37/100 · Grade F**

Scanned @ `81d7636` on 2026-11-12 with agent-scorecard 0.1.0 · 158 files · Frameworks: OpenAI API, AWS Bedrock

## Layers

| # | Layer | Score | |
|---|---|---:|---|
| 1 | Tool boundaries | 19 | ██░░░░░░░░ |
| 2 | Human approval gates | 25 | ██░░░░░░░░ |
| 3 | Audit trail and observability | 50 | █████░░░░░ |
| 4 | Secrets and egress | 75 | ████████░░ |
| 5 | Budgets and limits | 29 | ███░░░░░░░ |
| 6 | Untrusted input handling | 43 | ████░░░░░░ |
| 7 | Evals, testing and rollback | 21 | ██░░░░░░░░ |

## Critical gaps

- **TB-02 Tools carry a risk tier.** No risk classification of tools found. Fix: Add a tier to every tool (read, write, irreversible) and make approvals and budgets key off it. MCP's readOnlyHint and destructiveHint are a good minimum.
- **AG-03 The gate fails closed.** No gate, so nothing fails closed. Fix: Make deny the default on timeout, error and unknown tools. Keep bypass modes out of production code paths, behind an explicit, logged, test-only flag.
- **BL-01 Agent loops have a step cap.** No limit on agent steps or iterations found. Fix: Set a step cap on every agent loop, make hitting it a visible failure, and alert on it.
- **UI-01 Untrusted content is marked as data.** No handling of untrusted content found. Fix: Wrap every piece of external content in a labelled block, tell the model it is data, never instructions, screen it, and keep tool tiers enforced whatever it says.

## Top fixes

1. **AG-03 The gate fails closed** (critical): Make deny the default on timeout, error and unknown tools. Keep bypass modes out of production code paths, behind an explicit, logged, test-only flag.
2. **BL-01 Agent loops have a step cap** (critical): Set a step cap on every agent loop, make hitting it a visible failure, and alert on it.
3. **TB-02 Tools carry a risk tier** (critical): Add a tier to every tool (read, write, irreversible) and make approvals and budgets key off it. MCP's readOnlyHint and destructiveHint are a good minimum.
4. **UI-01 Untrusted content is marked as data** (critical): Wrap every piece of external content in a labelled block, tell the model it is data, never instructions, screen it, and keep tool tiers enforced whatever it says.
5. **AG-02 Approvals are bound to the exact action** (high): Store the proposed action, sign or hash it with the approval id, give it a short expiry, and re-check both right before execution.

## Checks

| ID | Check | Severity | Result | Finding |
|---|---|---|---|---|
| TB-01 | Tools are an explicit allowlist | high | MISSING | No tool declarations or allowlists found. |
| TB-02 | Tools carry a risk tier | critical | MISSING | No risk classification of tools found. |
| TB-03 | Code and shell execution is sandboxed | critical | N/A | No command or code execution found in production code. |
| TB-04 | File access is confined to a workspace | high | PARTIAL | Paths are normalised, but no check keeps them inside a workspace. |
| TB-05 | Tool supply chain is pinned | medium | PARTIAL | Locked in places, but 1 of 4 manifests have no lockfile. |
| AG-01 | Side effects wait for human approval | critical | PARTIAL | Approval or confirmation calls exist, but no blocking gate was identified. |
| AG-02 | Approvals are bound to the exact action | high | MISSING | Approvals are not tied to a hash or expiry of the approved action. |
| AG-03 | The gate fails closed | critical | MISSING | No gate, so nothing fails closed. |
| AG-04 | Approval decisions are recorded | high | PARTIAL | Decision times are stored, but not who decided. |
| AU-01 | Every tool call is logged as a structured event | high | PARTIAL | The app logs, but tool calls are not captured as audit events. |
| AU-02 | Runs are traced end to end | medium | MISSING | No tracing found. |
| AU-03 | The audit trail is durable and tamper-evident | medium | MISSING | No durable audit storage found. |
| AU-04 | Secrets are redacted from logs and traces | high | PASS | Redaction found in 1 file(s). |
| SE-01 | No secrets are committed | critical | PASS | No committed secrets detected. |
| SE-02 | Secrets come from the environment or a vault | high | PASS | Secrets are read at runtime and .env is git-ignored. |
| SE-03 | Secret scanning runs before merge | medium | PASS | A secret scanner runs in CI or pre-commit. |
| SE-04 | Outbound network access is restricted | high | MISSING | No outbound network restrictions found. |
| BL-01 | Agent loops have a step cap | critical | MISSING | No limit on agent steps or iterations found. |
| BL-02 | Spend has a budget | high | PARTIAL | Spend is tracked or capped per call, but no budget stops a run. |
| BL-03 | Model and tool calls time out | high | PARTIAL | A timeout is set in one file only. |
| UI-01 | Untrusted content is marked as data | critical | MISSING | No handling of untrusted content found. |
| UI-02 | Model output is parsed into a schema | high | PARTIAL | Output is parsed as JSON, without schema validation. |
| UI-03 | Tool arguments are validated | high | PASS | Tool inputs are validated. |
| ER-01 | Tests exist and run in CI | high | PARTIAL | 1 test file(s), not run in CI. |
| ER-02 | Agent behaviour has evals | high | MISSING | No evals of agent behaviour found. |
| ER-03 | Safety controls have their own tests | high | MISSING | No tests of safety controls found. |
| ER-04 | The agent can be stopped or rolled back | medium | PARTIAL | State can be rolled back, but there is no switch to stop the agent. |

## Evidence

**TB-04 File access is confined to a workspace**

- `backend/server.py:913` `path = os.path.realpath(os.path.join(TWINS_DIR, f"{twin_id}.json"))`
- `backend/server.py:914` `if not path.startswith(os.path.realpath(TWINS_DIR) + os.sep):`
- `backend/server.py:1090` `sessions_dir = os.path.realpath(os.path.join(MEMORY_DIR, "sessions"))`
- `backend/server.py:1091` `file_path = os.path.realpath(os.path.join(sessions_dir, f"{session_id}.json"))`
- `backend/server.py:1098` `memory_dir_real = os.path.realpath(MEMORY_DIR)`

**TB-05 Tool supply chain is pinned**

- anti-pattern · `pyproject.toml:1` `no lockfile covers this manifest`
- `backend/pyproject.toml:1` `locked`
- `package.json:1` `locked`

**AG-01 Side effects wait for human approval**

- `backend/context.py:106` `…message is appended after your reply to confirm (or not) whether that actually happened — if you also make that claim, it duplicates or cont…`
- `backend/server.py:1880` `async def approve_public_persona(twin_id: str, _admin_email: str = Depends(get_current_admin_email)):`

**AG-04 Approval decisions are recorded**

- `backend/server.py:1894` `_small_object_put(FEATURED_S3_PREFIX, FEATURED_DIR, f"{twin_id}.json", {"twin_id": twin_id, "approved_at": datetime.now().isoformat()})`

**AU-01 Every tool call is logged as a structured event**

- `backend/personality_agent.py:12` `logger = logging.getLogger(__name__)`

**AU-04 Secrets are redacted from logs and traces**

- `backend/context.py:22` `def _redact_pii(text: str) -> str:`
- `backend/context.py:24` `text = _EMAIL_RE.sub('[email redacted]', text)`
- `backend/context.py:25` `text = _PHONE_RE.sub('[phone redacted]', text)`
- `backend/context.py:293` `sections.append(f"**LinkedIn Profile:**\n{_redact_pii(linkedin)}")`

**SE-02 Secrets come from the environment or a vault**

- `backend/server.py:66` `origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")`
- `backend/server.py:78` `region_name=os.getenv("DEFAULT_AWS_REGION", "us-east-1")`
- `backend/server.py:82` `BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "global.amazon.nova-2-lite-v1:0")`
- `.gitignore:1` `.env ignored`

**SE-03 Secret scanning runs before merge**

- `.github/workflows/secrets-scan.yml:12` `gitleaks:`
- `.github/workflows/secrets-scan.yml:13` `name: Gitleaks — detect exposed secrets`
- `.github/workflows/secrets-scan.yml:18` `fetch-depth: 0  # full history required for Gitleaks PR range scan`
- `.github/workflows/secrets-scan.yml:20` `- name: Run Gitleaks`
- `.github/workflows/secrets-scan.yml:21` `uses: gitleaks/gitleaks-action@v2`

**BL-02 Spend has a budget**

- `backend/personality_agent.py:104` `"maxTokens": 1000,`
- `backend/server.py:392` `inferenceConfig={"maxTokens": 120, "temperature": 0},`
- `backend/server.py:479` `inferenceConfig={"maxTokens": 40, "temperature": 0},`
- `backend/server.py:1512` `"maxTokens": 500,`
- `backend/server.py:1594` `inferenceConfig={"maxTokens": 1500, "temperature": 0.2},`

**BL-03 Model and tool calls time out**

- `backend/server.py:598` `timeout=8.0,`
- `backend/server.py:672` `async with httpx.AsyncClient(timeout=5.0) as client:`
- `backend/server.py:1864` `timeout=5.0,`
- `backend/server.py:596` `await asyncio.wait_for(`
- `backend/server.py:1850` `await asyncio.wait_for(`

**UI-02 Model output is parsed into a schema**

- `backend/server.py:626` `data = json.loads(f.read_text())`
- `backend/server.py:849` `candidate = json.loads(text[start:end + 1])`
- `backend/server.py:881` `return json.loads(text[start:i + 1])`
- `backend/server.py:889` `return json.loads(response["Body"].read().decode("utf-8"))`
- `backend/server.py:1076` `return json.loads(response["Body"].read().decode("utf-8"))`

**UI-03 Tool arguments are validated**

- `backend/server.py:2945` `validated = OnboardResponse.model_validate(data)`
- `backend/server.py:4323` `validated = ResumeResponse.model_validate(data)`
- `backend/server.py:2324` `question: str = Field(..., min_length=1, max_length=500)`
- `backend/server.py:2325` `wrong_response: str = Field(..., min_length=1, max_length=500)`
- `backend/server.py:2326` `correction: str = Field(..., min_length=1, max_length=500)`

**ER-01 Tests exist and run in CI**

- `__tests__/package-json.test.js:1` `test file`

**ER-04 The agent can be stopped or rolled back**

- `backend/server.py:3505` `_append_model_version(twin_data, current_model, trigger="pre-rollback")`
- `backend/server.py:3508` `_append_model_version(twin_data, restored, trigger=f"rollback_to_v{version}")`
- `backend/server.py:3880` `@app.patch("/twin/{twin_id}/personality/rollback")`
- `backend/server.py:3881` `async def rollback_personality_model(`
- `backend/personalities/archetypes.json:27` `"Observability, rollback plans, and owned complexity",`

---

This is a static scan: it reads code and config and never runs them. It finds the presence of controls, not proof that they work. A PASS means the signal is there; a MISSING can be a control the scanner doesn't recognise yet. RUBRIC.md explains every check and how it is scored.
