# Agent Safety Scorecard

[![CI](https://github.com/sagacioussid02/agent-scorecard/actions/workflows/ci.yml/badge.svg)](https://github.com/sagacioussid02/agent-scorecard/actions/workflows/ci.yml) [![PyPI](https://img.shields.io/pypi/v/agent-scorecard)](https://pypi.org/project/agent-scorecard/)

**How safely is your AI agent built?** `agent-scorecard` reads an agent codebase and scores it 0 to 100 against 27 checks across the seven layers that keep production agents out of trouble: tool boundaries, human approval gates, audit trail, secrets and egress, budgets, untrusted input, and evals.

```console
$ agent-scorecard scan ./my-agent        # example output
# Agent Safety Scorecard: my-agent

**Score: 77/100 · Grade C** (capped at C by a missing critical control)

| # | Layer                          | Score |            |
|---|--------------------------------|------:|------------|
| 1 | Tool boundaries                |    54 | █████░░░░░ |
| 2 | Human approval gates           |   100 | ██████████ |
| 3 | Audit trail and observability  |    92 | █████████░ |
| 4 | Secrets and egress             |    62 | ██████░░░░ |
| 5 | Budgets and limits             |   100 | ██████████ |
| 6 | Untrusted input handling       |    57 | ██████░░░░ |
| 7 | Evals, testing and rollback    |    71 | ███████░░░ |

## Critical gaps
- **UI-01 Untrusted content is marked as data.** No handling of untrusted content found. ...
```

Every finding links to `file:line` evidence, and every gap comes with the fix.

- **Framework-aware.** Understands the Claude Agent SDK, LangGraph, CrewAI, OpenAI Agents SDK, AutoGen, LangChain, MCP servers and MCP client configs, and agents built straight on the Anthropic, OpenAI or Bedrock APIs, in Python, TypeScript and Go.
- **Runs as a CLI or an MCP server.** Ask your coding agent to score the repo it's working in.
- **Safe to point at anything.** It only reads. It never imports, executes or installs code from the target, never follows symlinks, and makes no network calls.
- **Zero runtime dependencies.** Standard library only, so its own supply chain is trivial to audit.

## Install

```console
$ pipx install agent-scorecard            # or: pip install agent-scorecard
$ agent-scorecard --version
```

Or run from a checkout with `uv run agent-scorecard ...` or `PYTHONPATH=src python -m agent_scorecard ...`.

## Use

```console
$ agent-scorecard scan PATH                     # Markdown scorecard to stdout
$ agent-scorecard scan PATH --format json       # machine-readable, for dashboards
$ agent-scorecard scan PATH --out SCORECARD.md  # write to a file
$ agent-scorecard scan PATH --fail-under 70     # exit 1 below 70: use it as a CI gate
$ agent-scorecard scan PATH --only AG-01,AG-03  # run a subset of checks
$ agent-scorecard explain AG-03                 # why a check matters and how to fix it
$ agent-scorecard rubric                        # the full rubric as Markdown
```

### In CI

```yaml
# .github/workflows/agent-scorecard.yml
on: [pull_request]
jobs:
  scorecard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pipx run agent-scorecard scan . --fail-under 70 --out scorecard.md
      - run: cat scorecard.md >> "$GITHUB_STEP_SUMMARY"
        if: always()
```

### As an MCP server

```json
{
  "mcpServers": {
    "agent-scorecard": { "command": "agent-scorecard", "args": ["mcp"] }
  }
}
```

Tools: `scan_repository(path, format?, checks?)`, `list_checks()`, `explain_check(check_id)`, `get_rubric()`. All are annotated read-only. The server speaks MCP over stdio (protocol versions 2024-11-05 through 2025-06-18) and is tested against the official MCP Python client.

## What it checks

27 checks, 7 layers. [RUBRIC.md](https://github.com/sagacioussid02/agent-scorecard/blob/main/RUBRIC.md) has the full text of each: why it matters, what the scanner looks for, what earns full and partial credit, and how to fix it.

| Layer | Checks |
|---|---|
| 1. Tool boundaries | allowlisted tools · risk tiers per tool · sandboxed execution · workspace-confined file access · pinned tool supply chain |
| 2. Human approval gates | approval before side effects · approvals bound to the exact action · fail-closed defaults · recorded decisions |
| 3. Audit trail and observability | structured tool-call events · end-to-end tracing · tamper-evident storage · secret redaction |
| 4. Secrets and egress | no committed secrets · runtime secret loading · secret scanning in CI · outbound allowlists |
| 5. Budgets and limits | step caps · spend budgets · timeouts |
| 6. Untrusted input handling | untrusted content labelled as data · schema-validated model output · validated tool arguments |
| 7. Evals, testing and rollback | tests in CI · behaviour evals · safety tests · kill switch or dry-run |

### Scoring

Each check is **PASS** (2 points), **PARTIAL** (1) or **MISSING** (0), weighted by severity (critical ×3, high ×2, medium ×1). Checks that can't apply are **N/A** and left out: sandboxing when nothing executes commands, or the approval layer in a chat-only app that never calls tools. A layer's score is its share of possible points; the overall score is the plain average of the layers, because a perfect audit trail doesn't make up for having no approval gate. Grades run A (85+) to F (under 40), and **any missing critical control caps the grade at C**.

## Scorecards

[scorecards/](https://github.com/sagacioussid02/agent-scorecard/tree/main/scorecards) holds scorecards for seven real agent repositories, with commit hashes so anyone can reproduce them.

## How it works

```
repo on disk ──► RepoIndex ──► ScanContext ──► 27 checks ──► Scorecard ──► Markdown / JSON / MCP
                 (walk, classify,  (frameworks,   (registry,      (weighted
                  mask comments)    tool use,      evidence)       layers, cap)
                                    agent files)
```

- `repo.py` walks the tree once (skipping vendored and generated directories, symlinks, binaries and files over 512 KB), classifies each file as code, config, CI or docs, and flags tests, examples and developer tooling so they don't count as production controls. Comments and docstrings are masked: a comment saying "we fail closed" is not a control. Prompts in triple-quoted strings are kept, because that is where untrusted-data labels live.
- `frameworks.py` detects frameworks from manifests and imports. Checks use it, along with "does this code call tools at all?" and "which files talk to a model?", to decide what applies and to keep generic words such as `max_steps` from counting outside agent code.
- `checks/` holds one module per layer. Each check is a small function registered with its rubric text, so the scanner and [RUBRIC.md](https://github.com/sagacioussid02/agent-scorecard/blob/main/RUBRIC.md) can't drift: RUBRIC.md is generated from the registry, and a test fails if it is out of date.
- Signals that only mean something together are matched by proximity. An HMAC counts toward "approvals are bound to the action" only within a few lines of approval code, not anywhere in the same 3,000-line file.
- Anti-patterns (`bypassPermissions`, `shell=True`, committed keys, unpinned `npx -y` MCP servers) are reported as negative evidence. Secret values are redacted in every report.

## Limits

This is a static scan. It shows whether a control is present, not that it works, and it reads names and structure, not intent. A PASS means the signal is there; a MISSING can be a control written in a way the scanner doesn't recognise yet. The useful output is the list of gaps to look at, not the number. Large repos take a few seconds (about 18 s for 2,000 files).

For a review that goes past signals (threat model, data flows, tested controls, a fix plan), see the [paid review](https://sagacioussid02.github.io/agent-scorecard/#review).

## Development

```console
$ uv run --with pytest pytest          # or: python -m pytest
$ PYTHONPATH=src python -m agent_scorecard rubric --out RUBRIC.md   # after changing a check
```

Add a check by writing a function in the right `checks/<layer>.py` with the `@check(...)` decorator, then add PASS and MISSING cases to `tests/test_checks.py` (a test enforces both) and regenerate RUBRIC.md.

## License

MIT
