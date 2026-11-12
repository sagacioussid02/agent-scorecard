# Scorecards

Seven agent repositories scored with agent-scorecard 0.1.0 on 2026-11-12. Each row links to the full scorecard with file:line evidence; the commit is the exact tree that was scanned, so anyone can reproduce it with `agent-scorecard scan`.

| Repository | Commit | Score | Grade | Tool | Approval | Audit | Secrets | Budgets | Input | Evals | Critical gaps |
|---|---|---:|:---:|---:|---:|---:|---:|---:|---:|---:|---|
| [sagacioussid02/sutra](sagacioussid02__sutra.md) | `1532657` | 90 | A | 77 | 100 | 83 | 88 | 86 | 100 | 100 | none |
| [OpenHands/software-agent-sdk](OpenHands__software-agent-sdk.md) | `10be259` | 89 | A | 96 | 65 | 83 | 94 | 100 | 100 | 86 | none |
| [sagacioussid02/minions](sagacioussid02__minions.md) | `500da66` | 77 | C* | 54 | 100 | 92 | 62 | 100 | 57 | 71 | TB-02, UI-01 |
| [browser-use/browser-use](browser-use__browser-use.md) | `dfb6a73` | 76 | C* | 73 | 45 | 67 | 88 | 86 | 100 | 71 | TB-02 |
| [langchain-ai/open_deep_research](langchain-ai__open_deep_research.md) | `1b7d2e8` | 51 | D | 33 | 45 | 17 | 62 | 79 | 64 | 57 | TB-02 |
| [sagacioussid02/qxplore](sagacioussid02__qxplore.md) | `867ff63` | 42 | D | 50 | – | 25 | 75 | 50 | 40 | 14 | UI-01 |
| [sagacioussid02/personas](sagacioussid02__personas.md) | `81d7636` | 37 | F | 19 | 25 | 50 | 75 | 29 | 43 | 21 | TB-02, AG-03, BL-01, UI-01 |

\* Grade capped at C because a critical control is missing. – means the layer doesn't apply (no tool calling).

Four of these are the author's own projects (sagacioussid02/*). Scores reflect static signals only: see the Limits section of the main README.
