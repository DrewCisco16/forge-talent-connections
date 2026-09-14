# FORGE AGENT SYSTEM

**A design for an agent workforce across Andrew Francisco's four business lanes.**

| | |
|---|---|
| **Version** | 1.0 |
| **Compiled** | 2026-09-14 |
| **Response tier** | Full (high-stakes, hard to reverse, commits recurring spend and operating habit) |
| **Status** | Design + runnable scaffolding. Nothing in here has been run end-to-end yet. |
| **Confidence** | Medium-High on architecture and Claude Code mechanics (vendor docs retrieved this session). Low on OpenAI Codex specifics and SAM.gov API specifics — both domains were blocked by this session's network egress proxy and are marked Unverified throughout. |

---

## The one thing to read if you read nothing else

**Your binding constraint is not compute. It is your own review capacity.**

You own 144GB of local RAM across four machines, five phones, two watches, a
tablet and four monitors. None of that produces time. Agents produce *output*,
and output you must read is a liability, not an asset — an agent that hands you
twelve pages of research has spent your time, not saved it.

So this system is not organized around "what can an agent do." It is organized
around **what an agent is allowed to hand you, and how long that hand-off is
permitted to cost you.** Every agent in the roster is assigned a Trust Tier that
fixes its review cost before it ever runs. That is the whole design.

Read [`01-operating-model.md`](01-operating-model.md) next.

---

## What is in here

| File | What it settles |
|---|---|
| [`01-operating-model.md`](01-operating-model.md) | First principles, the three Trust Tiers, lane separation, review-cost economics |
| [`02-agent-roster.md`](02-agent-roster.md) | The ten agents. Charter, trigger, inputs, outputs, tier, escalation for each |
| [`03-execution-substrate.md`](03-execution-substrate.md) | Where each agent actually runs. Verified platform facts. **What "24/7" really means** |
| [`04-mailroom-sop.md`](04-mailroom-sop.md) | Email. Classification, drafting, the never-auto-send list, the promotion ladder |
| [`05-govcon-pipeline.md`](05-govcon-pipeline.md) | Opportunity → bid/no-bid → capture → compliance matrix |
| [`06-research-ip-pipeline.md`](06-research-ip-pipeline.md) | DBA literature surveillance and IP/prior-art, both routed into existing gates |
| [`07-guardrails.md`](07-guardrails.md) | Lane separation, CUI boundary, secrets, prompt injection, the kill switch |
| [`08-measurement.md`](08-measurement.md) | How you will know whether this returned time. Instrument first, claim later |
| [`09-rollout-90-day.md`](09-rollout-90-day.md) | One 90-day sprint, three 30-day gates, each with a stop condition |
| [`10-open-questions.md`](10-open-questions.md) | Everything this design needs but does not know. Unresolved by design |
| [`context/`](context/) | Canonical device fleet and principal profile that agents load as context |
| [`prompts/`](prompts/) | Portable, vendor-neutral agent prompts (paste into Codex, a Custom GPT, anywhere) |
| [`../.claude/agents/`](../.claude/agents/) | Runnable Claude Code subagent definitions |

---

## Evidence labels used in this system

This extends the label set already in force in your device fleet context pack.
**No agent may upgrade a label.** An Unknown is a question, never a guess.

| Label | Meaning |
|---|---|
| **Stated** | Andrew stated it directly (resume, fleet pack, or session). Treat as fact. |
| **Docs-Verified** | Retrieved from the vendor's own documentation during this session. URL and date recorded at the point of use. |
| **Repo-Verified** | Read directly out of this repository's source during this session. |
| **Inference** | Derived by reasoning from something labeled above. May be wrong. |
| **Assumption** | A working premise adopted to let the design proceed. Stated so it can be attacked. |
| **Unverified** | A claim that could not be checked because the source was unreachable from this session. **Verify before relying on it.** |
| **Unknown** | No record exists. Ask; do not substitute a plausible value. |

Two whole domains are **Unverified** in this document set:

1. **OpenAI Codex.** `developers.openai.com` returned `EGRESS_BLOCKED` from this
   session's proxy. Every statement about Codex model names, sandbox behavior,
   scheduling, or `AGENTS.md` is therefore unverified. The design routes around
   this with a vendor-neutral adapter — see `03-execution-substrate.md` §4.
   You asked specifically about a "GPT-5.6 Codex" option; **I could not verify
   that any such model exists.** I am not going to assert it does.
2. **SAM.gov / FPDS / USASpending APIs.** `open.gsa.gov` returned
   `EGRESS_BLOCKED`. Endpoint shapes, key requirements and rate limits in
   `05-govcon-pipeline.md` are marked Unverified and carry a verification task.

---

## What this design deliberately does not do

- **It does not promise you a number of hours back.** You have no baseline. §08
  builds the instrument first. A number before the instrument would be invented,
  and inventing it would violate the standard this whole system is built on.
- **It does not let an agent send email on your behalf on day one.** See §04.
- **It does not build a new research engine.** You already have one in
  `adjudication/` — five blinded seats, claim gates, a cost ceiling and a refuse
  path. Hard problems route *into* it. Building a second one would be waste.
- **It does not put CUI or contract-restricted data through vendor cloud agents.**
  That boundary is legal, not technical. See §07. **Professional verification
  required — contracts counsel, not an AI.**
