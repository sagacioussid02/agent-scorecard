# Agent Safety Review

**A fixed-price, senior review of how safely your AI agent is built, delivered in five business days.**

The free scanner tells you which safety signals are in your code. The review tells you whether they actually hold up, what an attacker or a bad prompt could make your agent do, and the shortest path to fixing it.

## Who it's for

Teams shipping an agent that takes real actions (sends email, writes to a database, runs code, spends money, touches customer data) and who need to answer "is this safe to put in front of customers?" for a launch, an enterprise deal, a security questionnaire or their own peace of mind.

Works with the Claude Agent SDK, LangGraph, CrewAI, OpenAI Agents SDK, AutoGen, LangChain, MCP servers, and agents built straight on the Anthropic, OpenAI or Bedrock APIs.

## Two options

| | **Scorecard Review** | **Full Review** |
|---|---|---|
| Price | **$1,500** fixed | **$3,000** fixed |
| Scope | One agent, one repo | One agent and its tools, MCP servers and deployment config |
| Annotated scorecard against the 27-check rubric, every finding checked by hand | ✓ | ✓ |
| Top 10 fixes, ranked by risk and effort, with code-level guidance | ✓ | ✓ |
| Threat model: what the agent can touch, who can steer it, what goes wrong | | ✓ |
| Data-flow review of secrets, customer data and untrusted input | | ✓ |
| Prompt-injection walkthrough against your real tools | | ✓ |
| 60-minute call to go through findings with your team | | ✓ |
| Re-score after you ship fixes (within 30 days) | | ✓ |
| Turnaround | 5 business days | 5 business days |

## How it works

1. **Day 0.** A 20-minute intro call, or just email. You grant read access to the repo (or send a tarball). NDA on request.
2. **Days 1 to 4.** I run the scanner, then read the code: tool definitions, approval paths, logging, secrets handling, limits, and how untrusted content reaches the model.
3. **Day 5.** You get a written report (Markdown and PDF) and, for the Full Review, the walkthrough call.

No production access is needed. I only read code; nothing is executed against your systems.

## What you get, concretely

- A score and grade per layer, with the evidence (`file:line`) behind each finding.
- A list of the gaps that matter most for *your* agent, not a generic checklist.
- For each gap: why it matters, what an incident would look like, and the fix, sized in hours.
- A short summary you can hand to a customer's security reviewer.

## Who's doing it

I'm Sidd, a senior engineer who builds production agent systems. I wrote `agent-scorecard`, the open-source scanner behind this review, and I've scored seven public agent repos with it, including my own.

## Terms

- Fixed price, invoiced half up front and half on delivery.
- If the report doesn't give you at least five fixes worth making, you don't pay the second half.
- Your code stays private: reviewed on my machine, deleted 30 days after delivery, never used to train anything.

**To book:** [siddharthuncc@gmail.com](mailto:siddharthuncc@gmail.com?subject=Agent%20Safety%20Review)
