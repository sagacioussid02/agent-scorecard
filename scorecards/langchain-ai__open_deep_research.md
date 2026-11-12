# Agent Safety Scorecard: langchain-ai/open_deep_research

**Score: 51/100 · Grade D**

Scanned @ `1b7d2e8` on 2026-11-12 with agent-scorecard 0.1.0 · 38 files · Frameworks: LangGraph, LangChain, MCP (server or client), OpenAI API, AWS Bedrock

## Layers

| # | Layer | Score | |
|---|---|---:|---|
| 1 | Tool boundaries | 33 | ███░░░░░░░ |
| 2 | Human approval gates | 45 | ████░░░░░░ |
| 3 | Audit trail and observability | 17 | ██░░░░░░░░ |
| 4 | Secrets and egress | 62 | ██████░░░░ |
| 5 | Budgets and limits | 79 | ████████░░ |
| 6 | Untrusted input handling | 64 | ██████░░░░ |
| 7 | Evals, testing and rollback | 57 | ██████░░░░ |

## Critical gaps

- **TB-02 Tools carry a risk tier.** No risk classification of tools found. Fix: Add a tier to every tool (read, write, irreversible) and make approvals and budgets key off it. MCP's readOnlyHint and destructiveHint are a good minimum.

## Top fixes

1. **TB-02 Tools carry a risk tier** (critical): Add a tier to every tool (read, write, irreversible) and make approvals and budgets key off it. MCP's readOnlyHint and destructiveHint are a good minimum.
2. **AG-02 Approvals are bound to the exact action** (high): Store the proposed action, sign or hash it with the approval id, give it a short expiry, and re-check both right before execution.
3. **AG-04 Approval decisions are recorded** (high): Persist every approval and rejection with approver identity, timestamp, the exact action shown and the outcome.
4. **AU-01 Every tool call is logged as a structured event** (high): Emit one structured event per tool call (agent, tool, args digest, result status, approval id, cost) to an audit sink separate from debug logs.
5. **AU-04 Secrets are redacted from logs and traces** (high): Run every logged payload through a redactor (known keys plus token patterns) and test it with real-looking secrets.

## Checks

| ID | Check | Severity | Result | Finding |
|---|---|---|---|---|
| TB-01 | Tools are an explicit allowlist | high | PARTIAL | Tools are declared explicitly, but no allowlist limits which ones each agent gets. |
| TB-02 | Tools carry a risk tier | critical | MISSING | No risk classification of tools found. |
| TB-03 | Code and shell execution is sandboxed | critical | N/A | No command or code execution found in production code. |
| TB-04 | File access is confined to a workspace | high | N/A | No file writes or deletes found in production code. |
| TB-05 | Tool supply chain is pinned | medium | PASS | All 1 dependency manifest(s) are locked. |
| AG-01 | Side effects wait for human approval | critical | PASS | Approval gates found in 1 file(s). |
| AG-02 | Approvals are bound to the exact action | high | MISSING | Approvals are not tied to a hash or expiry of the approved action. |
| AG-03 | The gate fails closed | critical | PARTIAL | A gate exists and nothing bypasses it, but its default on timeout or error is not visible. |
| AG-04 | Approval decisions are recorded | high | MISSING | No record of approval decisions found. |
| AU-01 | Every tool call is logged as a structured event | high | MISSING | No logging of agent actions found. |
| AU-02 | Runs are traced end to end | medium | PASS | A tracing backend is integrated. |
| AU-03 | The audit trail is durable and tamper-evident | medium | MISSING | No durable audit storage found. |
| AU-04 | Secrets are redacted from logs and traces | high | MISSING | No redaction of secrets in logs or traces found. |
| SE-01 | No secrets are committed | critical | PASS | No committed secrets detected. |
| SE-02 | Secrets come from the environment or a vault | high | PASS | Secrets are read at runtime and .env is git-ignored. |
| SE-03 | Secret scanning runs before merge | medium | MISSING | No secret or security scanning in CI or pre-commit. |
| SE-04 | Outbound network access is restricted | high | MISSING | No outbound network restrictions found. |
| BL-01 | Agent loops have a step cap | critical | PARTIAL | Retries are bounded, but no cap on agent steps was found. |
| BL-02 | Spend has a budget | high | PASS | A spend budget is enforced. |
| BL-03 | Model and tool calls time out | high | PASS | Timeouts set in 2 file(s). |
| UI-01 | Untrusted content is marked as data | critical | PARTIAL | Content is delimited or injection is acknowledged, but external content is not labelled untrusted. |
| UI-02 | Model output is parsed into a schema | high | PASS | Model output is validated against schemas. |
| UI-03 | Tool arguments are validated | high | PARTIAL | Tools are typed, but their inputs are not validated beyond types. |
| ER-01 | Tests exist and run in CI | high | PASS | 9 test files, run in CI. |
| ER-02 | Agent behaviour has evals | high | PASS | An eval suite exists. |
| ER-03 | Safety controls have their own tests | high | MISSING | No tests of safety controls found. |
| ER-04 | The agent can be stopped or rolled back | medium | MISSING | No kill switch, dry-run mode or rollback found. |

## Evidence

**TB-01 Tools are an explicit allowlist**

- `src/legacy/multi_agent.py:165` `tools = [tool(Sections), tool(Introduction), tool(Conclusion), tool(FinishReport)]`
- `src/legacy/multi_agent.py:179` `tools = [tool(Section), tool(FinishResearch)]`
- `src/open_deep_research/deep_researcher.py:202` `lead_researcher_tools = [ConductResearch, ResearchComplete, think_tool]`
- `src/open_deep_research/utils.py:507` `configured_tools = []`
- `src/open_deep_research/utils.py:579` `tools = [tool(ResearchComplete), think_tool]`

**TB-05 Tool supply chain is pinned**

- `pyproject.toml:1` `locked`

**AG-01 Side effects wait for human approval**

- `src/legacy/graph.py:175` `feedback = interrupt(interrupt_message)`

**AU-02 Runs are traced end to end**

- `.env.example:5` `LANGSMITH_API_KEY=`
- `.env.example:6` `LANGSMITH_PROJECT=`
- `.env.example:7` `LANGSMITH_TRACING=`
- `pyproject.toml:39` `"langsmith>=0.3.37",`
- `src/legacy/utils.py:39` `from langsmith import traceable`

**SE-02 Secrets come from the environment or a vault**

- `src/legacy/configuration.py:63` `f.name: os.environ.get(f.name.upper(), configurable.get(f.name))`
- `src/legacy/configuration.py:99` `f.name: os.environ.get(f.name.upper(), configurable.get(f.name))`
- `src/legacy/utils.py:234` `if not all(var in os.environ for var in ["AZURE_AI_SEARCH_ENDPOINT", "AZURE_AI_SEARCH_INDEX_NAME", "AZURE_AI_SEARCH_API_KEY"]):`
- `.gitignore:1` `.env ignored`

**BL-01 Agent loops have a step cap**

- `src/legacy/utils.py:1263` `max_retries = 3`
- `src/legacy/utils.py:1268` `while retry_count <= max_retries:`
- `src/legacy/utils.py:1276` `print(f"Retry {retry_count}/{max_retries} for query '{query}' after {delay:.2f}s delay")`
- `src/legacy/utils.py:1310` `print(f"DuckDuckGo search error: {str(e)}. Retrying {retry_count}/{max_retries}")`
- `src/legacy/utils.py:1415` `max_retries=configurable.max_structured_output_retries,`

**BL-02 Spend has a budget**

- `src/legacy/graph.py:124` `thinking={"type": "enabled", "budget_tokens": 16_000})`
- `src/legacy/graph.py:333` `thinking={"type": "enabled", "budget_tokens": 16_000}).with_structured_output(Feedback)`

**BL-03 Model and tool calls time out**

- `src/legacy/utils.py:1128` `async with session.get(url, headers=headers, timeout=10) as response:`
- `src/legacy/utils.py:1208` `async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:`
- `src/open_deep_research/utils.py:195` `timeout=60.0  # 60 second timeout for summarization`
- `src/open_deep_research/utils.py:193` `summary = await asyncio.wait_for(`

**UI-01 Untrusted content is marked as data**

- `src/legacy/prompts.py:41` `<Context>`
- `src/legacy/prompts.py:44` `</Context>`

**UI-02 Model output is parsed into a schema**

- `src/legacy/graph.py:86` `structured_llm = writer_model.with_structured_output(Queries)`
- `src/legacy/graph.py:133` `structured_llm = planner_llm.with_structured_output(Sections)`
- `src/legacy/graph.py:221` `structured_llm = writer_model.with_structured_output(Queries)`
- `src/legacy/graph.py:333` `thinking={"type": "enabled", "budget_tokens": 16_000}).with_structured_output(Feedback)`
- `src/legacy/graph.py:336` `model_provider=planner_provider, model_kwargs=planner_model_kwargs).with_structured_output(Feedback)`

**UI-03 Tool arguments are validated**

- `src/legacy/utils.py:1246` ``
- `src/legacy/utils.py:1362` ``
- `src/legacy/utils.py:1454` ``
- `src/open_deep_research/utils.py:43` `@tool(description=TAVILY_SEARCH_DESCRIPTION)`
- `src/open_deep_research/utils.py:218` ``

**ER-01 Tests exist and run in CI**

- `.github/workflows/claude-code-review.yml:72` `# allowed_tools: "Bash(npm run test),Bash(npm run lint),Bash(npm run typecheck)"`
- `.github/workflows/claude.yml:53` `# allowed_tools: "Bash(npm install),Bash(npm run build),Bash(npm run test:*),Bash(npm run lint:*)"`

**ER-02 Agent behaviour has evals**

- `tests/pairwise_evaluation.py:2` `from langsmith.evaluation import evaluate_comparative`
- `tests/run_evaluate.py:64` `return await client.aevaluate(`
- `tests/supervisor_parallel_evaluation.py:51` `return await client.aevaluate(`

---

This is a static scan: it reads code and config and never runs them. It finds the presence of controls, not proof that they work. A PASS means the signal is there; a MISSING can be a control the scanner doesn't recognise yet. RUBRIC.md explains every check and how it is scored.
