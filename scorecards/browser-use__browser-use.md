# Agent Safety Scorecard: browser-use/browser-use

**Score: 76/100 · Grade C** (capped at C by a missing critical control)

Scanned @ `dfb6a73` on 2026-11-12 with agent-scorecard 0.1.0 · 124 files · Frameworks: MCP (server or client), Anthropic API, OpenAI API

## Layers

| # | Layer | Score | |
|---|---|---:|---|
| 1 | Tool boundaries | 73 | ███████░░░ |
| 2 | Human approval gates | 45 | ████░░░░░░ |
| 3 | Audit trail and observability | 67 | ███████░░░ |
| 4 | Secrets and egress | 88 | █████████░ |
| 5 | Budgets and limits | 86 | █████████░ |
| 6 | Untrusted input handling | 100 | ██████████ |
| 7 | Evals, testing and rollback | 71 | ███████░░░ |

## Critical gaps

- **TB-02 Tools carry a risk tier.** No risk classification of tools found. Fix: Add a tier to every tool (read, write, irreversible) and make approvals and budgets key off it. MCP's readOnlyHint and destructiveHint are a good minimum.

## Top fixes

1. **TB-02 Tools carry a risk tier** (critical): Add a tier to every tool (read, write, irreversible) and make approvals and budgets key off it. MCP's readOnlyHint and destructiveHint are a good minimum.
2. **AG-02 Approvals are bound to the exact action** (high): Store the proposed action, sign or hash it with the approval id, give it a short expiry, and re-check both right before execution.
3. **AG-04 Approval decisions are recorded** (high): Persist every approval and rejection with approver identity, timestamp, the exact action shown and the outcome.
4. **AG-01 Side effects wait for human approval** (critical): Put a gate in front of every side-effecting tool tier: the agent proposes, a human approves the exact action, and only then does it run.
5. **AU-03 The audit trail is durable and tamper-evident** (medium): Write audit events append-only (separate table with insert-only grants, or object lock), and chain each record to the previous hash.

## Checks

| ID | Check | Severity | Result | Finding |
|---|---|---|---|---|
| TB-01 | Tools are an explicit allowlist | high | PASS | Tool access goes through an allowlist. |
| TB-02 | Tools carry a risk tier | critical | MISSING | No risk classification of tools found. |
| TB-03 | Code and shell execution is sandboxed | critical | PASS | Execution runs inside a sandbox or container. |
| TB-04 | File access is confined to a workspace | high | PASS | File paths are checked against an allowed root. |
| TB-05 | Tool supply chain is pinned | medium | PASS | All 1 dependency manifest(s) are locked. |
| AG-01 | Side effects wait for human approval | critical | PARTIAL | Approval or confirmation calls exist, but no blocking gate was identified. |
| AG-02 | Approvals are bound to the exact action | high | MISSING | Approvals are not tied to a hash or expiry of the approved action. |
| AG-03 | The gate fails closed | critical | PASS | Deny-by-default or reject-on-timeout logic found, and no bypass. |
| AG-04 | Approval decisions are recorded | high | MISSING | No record of approval decisions found. |
| AU-01 | Every tool call is logged as a structured event | high | PARTIAL | The app logs, but tool calls are not captured as audit events. |
| AU-02 | Runs are traced end to end | medium | PASS | A tracing backend is integrated. |
| AU-03 | The audit trail is durable and tamper-evident | medium | MISSING | No durable audit storage found. |
| AU-04 | Secrets are redacted from logs and traces | high | PASS | Redaction found in 4 file(s). |
| SE-01 | No secrets are committed | critical | PASS | No committed secrets detected. |
| SE-02 | Secrets come from the environment or a vault | high | PASS | Secrets are read at runtime and .env is git-ignored. |
| SE-03 | Secret scanning runs before merge | medium | MISSING | No secret or security scanning in CI or pre-commit. |
| SE-04 | Outbound network access is restricted | high | PASS | Outbound destinations are restricted. |
| BL-01 | Agent loops have a step cap | critical | PASS | Agent loops are capped. |
| BL-02 | Spend has a budget | high | PARTIAL | Spend is tracked or capped per call, but no budget stops a run. |
| BL-03 | Model and tool calls time out | high | PASS | Timeouts set in 13 file(s). |
| UI-01 | Untrusted content is marked as data | critical | PASS | Untrusted content is labelled or screened. |
| UI-02 | Model output is parsed into a schema | high | PASS | Model output is validated against schemas. |
| UI-03 | Tool arguments are validated | high | PASS | Tool inputs are validated. |
| ER-01 | Tests exist and run in CI | high | PASS | 23 test files, run in CI. |
| ER-02 | Agent behaviour has evals | high | PARTIAL | Golden or judge-based tests exist, but no eval suite. |
| ER-03 | Safety controls have their own tests | high | PASS | 7 test files exercise refusals or attacks. |
| ER-04 | The agent can be stopped or rolled back | medium | MISSING | No kill switch, dry-run mode or rollback found. |

## Evidence

**TB-01 Tools are an explicit allowlist**

- `browser_use/llm/__init__.py:126` `return OpenAIModelProfile(openai_chat_supports_allowed_tools=False, openai_supports_strict_tool_definition=False)`

**TB-03 Code and shell execution is sandboxed**

- `browser_use/browser/local.py:357` `args.append('--no-sandbox')  # Chrome refuses to start as root with the sandbox; containers usually lack it`
- `browser_use/browser/local.py:431` `except RuntimeError as e:  # Linux without user namespaces or a setuid sandbox helper (some CI runners, VMs)`
- `browser_use/browser/local.py:432` `if 'No usable sandbox' not in str(e) or '--no-sandbox' in args:`

**TB-04 File access is confined to a workspace**

- `browser_use/auth.py:40` `if failed.is_relative_to(base) or base.is_relative_to(failed):`
- `browser_use/browser/local.py:460` `lock = '' if self.user_data_dir.is_relative_to(self.tmp) else f' is another Chrome using {self.user_data_dir}?'`

**TB-05 Tool supply chain is pinned**

- `pyproject.toml:1` `locked`

**AG-01 Side effects wait for human approval**

- `browser_use/cli.py:539` `def run_mac_approve(argv: list[str]) -> int:`

**AG-03 The gate fails closed**

- `browser_use/repl/worker.py:869` `except Exception:  # unknown recipient: scoped secrets fail closed below`
- `browser_use/mcp/cli_mcp.py:582` `if not errors and result is not None and result.is_error:  # no exception: rejected arguments, an unknown tool`

**AU-01 Every tool call is logged as a structured event**

- `browser_use/domains.py:40` `logger = logging.getLogger(__name__)`
- `browser_use/legacy.py:25` `"each step logs one INFO line to logging.getLogger('browser_use'); add a logging.Handler to stream progress, and "`
- `browser_use/legacy.py:250` `"logging.getLogger('browser_use') and BROWSER_USE_LOGGING_LEVEL=debug|info|warning|error.",`
- `browser_use/logging_config.py:24` `logger = logging.getLogger('browser_use')`
- `browser_use/logging_config.py:37` `"to logging.getLogger('browser_use') instead."`

**AU-02 Runs are traced end to end**

- `browser_use/legacy.py:38` `"Pydantic AI's OpenTelemetry tracing: pydantic_ai.Agent.instrument_all() (or logfire.instrument_pydantic_ai()) "`

**AU-04 Secrets are redacted from logs and traces**

- `browser_use/cli.py:38` `def _scrub_harness_telemetry() -> None:`
- `browser_use/cli.py:51` `if not getattr(enabled, '__bu_scrubbed__', False):`
- `browser_use/cli.py:56` `is_enabled.__bu_scrubbed__ = True  # type: ignore[attr-defined]`
- `browser_use/cli.py:58` `if not getattr(telemetry._install_id, '__bu_scrubbed__', False):`
- `browser_use/cli.py:66` `install_id.__bu_scrubbed__ = True  # type: ignore[attr-defined]`

**SE-02 Secrets come from the environment or a vault**

- `browser_use/__init__.py:11` `os.environ.setdefault('PYDANTIC_AI_NO_BANNER', '1')  # a library should not print an ad on every run`
- `browser_use/__init__.py:13` `if os.environ.get('BROWSER_USE_SETUP_LOGGING', 'true').lower() != 'false':`
- `browser_use/auth.py:34` `if failed is None or not (raw := os.environ.get(name)):`
- `.gitignore:1` `.env ignored`

**SE-04 Outbound network access is restricted**

- `browser_use/cli.py:170` `options = {k: profile[k] for k in ('allowed_domains', 'prohibited_domains') if profile.get(k)}`
- `browser_use/cli.py:171` `if domains := os.environ.pop('BROWSER_USE_ALLOWED_DOMAINS', '').strip():  # Browser() raises on the variable itself`
- `browser_use/cli.py:172` `options['allowed_domains'] = [d.strip() for d in domains.split(',') if d.strip()]`
- `browser_use/cli.py:198` `DomainRules.of(options.get('allowed_domains'), options.get('prohibited_domains'))  # a bad pattern: here, not mid-protocol`
- `browser_use/domains.py:206` `rules = cls(_patterns(allowed, 'allowed_domains'), _patterns(prohibited, 'prohibited_domains'), bool(block_ips))`

**BL-01 Agent loops have a step cap**

- `browser_use/agent/loop.py:123` `max_steps: int = 1000`
- `browser_use/agent/loop.py:135` `budget_hit: str | None = None  # max_steps | timeout | browser_gone: what forced the delivery-only turn`
- `browser_use/agent/loop.py:268` `if ctx.run_step > s.max_steps:`
- `browser_use/agent/loop.py:426` `if ctx.run_step >= s.max_steps:  # 0.x: the last step is the forced done`
- `browser_use/agent/loop.py:427` `s.budget_hit = 'max_steps'`

**BL-02 Spend has a budget**

- `browser_use/legacy.py:32` `_USAGE = 'result.usage (tokens) and result.cost_usd.'`
- `browser_use/agent/loop.py:973` `settings['max_tokens'] = 12_000`
- `browser_use/agent/loop.py:1112` `'max_tokens': 32_768,`
- `browser_use/agent/loop.py:1133` `else:  # other providers: unified thinking (dropped where the profile has none), the provider's own max_tokens`
- `browser_use/agent/service.py:101` `'calculate_cost': 'result.cost_usd is computed whenever the price is known.',`

**BL-03 Model and tool calls time out**

- `browser_use/ax.py:334` `_response_timeout=5,`
- `browser_use/ax.py:395` `timeout=CDP_TIMEOUT_MS,`
- `browser_use/cli.py:596` `with opener.open(f'http://{ws.split("/")[2]}/json/version', timeout=1) as r:`
- `browser_use/cli.py:684` `lock = admin._spawn_lock(OWN_CHROMIUM, timeout=90.0)  # concurrent cold calls: one launches the Chromium`
- `browser_use/domains.py:350` `self._ws = connect(self.ws_url, max_size=None, open_timeout=GUARD_START_S, close_timeout=1, ssl=tls)`

**UI-01 Untrusted content is marked as data**

- `browser_use/agent/service.py:86` `'you can read. Put task files in the workspace (workspace=...); run untrusted tasks in a container or VM.',`

**UI-02 Model output is parsed into a schema**

- `browser_use/legacy.py:19` `'await pydantic_ai.Agent(llm.pydantic_model()).run(prompt) (output_type=YourModel for structured output).'`
- `browser_use/agent/loop.py:25` `from pydantic import Field, TypeAdapter, ValidationError`
- `browser_use/agent/loop.py:304` `def _outputs(output_type: Any) -> list[Any]:`
- `browser_use/agent/loop.py:305` `adapter = TypeAdapter(output_type)`
- `browser_use/agent/loop.py:330` `if output_type is str:`

**UI-03 Tool arguments are validated**

- `browser_use/cli.py:227` `input_schema={'type': 'object', 'properties': {'code': {'type': 'string'}}, 'required': ['code']},`
- `browser_use/mcp/cli_mcp.py:457` `input_schema={`
- `browser_use/mcp/cli_mcp.py:468` `input_schema={`
- `browser_use/mcp/cli_mcp.py:487` `input_schema={`

**ER-01 Tests exist and run in CI**

- `.github/workflows/claude.yml:56` `…the whole test file at the end to make sure no other tests in that file started failing due to your changes: 'uv run pytest/ci/test_....py'.…`
- `.github/workflows/claude.yml:71` `"Bash(uv run pytest:*)",`
- `.github/workflows/claude.yml:92` `Bash(uv run pytest:*)`

**ER-02 Agent behaviour has evals**

- `tests/ci/test_compat.py:40` `'judge_llm',  # judge`
- `tests/ci/test_compat.py:1109` `for served in ('gemini-2.5-pro-made-up-snapshot-9', None):`

**ER-03 Safety controls have their own tests**

- `tests/ci/test_browser.py:224` `raise urllib.error.HTTPError(url, 401, 'Unauthorized', {}, io.BytesIO(body))  # type: ignore[arg-type]`
- `tests/ci/test_domains.py:48` `def test_userinfo_cannot_bypass_the_allowlist():`
- `tests/ci/test_domains.py:50` `assert not ok('https://example.com:password@malicious.com', a)`
- `tests/ci/test_domains.py:51` `assert not ok('https://example.com@malicious.com', a)`
- `tests/ci/test_domains.py:52` `assert not ok('https://example.com%20@malicious.com', a)`

---

This is a static scan: it reads code and config and never runs them. It finds the presence of controls, not proof that they work. A PASS means the signal is there; a MISSING can be a control the scanner doesn't recognise yet. RUBRIC.md explains every check and how it is scored.
