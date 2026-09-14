# FORGE AGENT SYSTEM

**A design for an agent workforce across Andrew Francisco's four business lanes.**

| | |
|---|---|
| **Version** | 4.0 |
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

**If you only want to run something today, start at [`../START-HERE.md`](../START-HERE.md).**
For where everything stands right now, [`../STATE.md`](../STATE.md).
Otherwise read [`01-operating-model.md`](01-operating-model.md) next.

> **⚠ This repository is PUBLIC** (verified 2026-09-14). Never commit invention
> disclosures, CUI, client or candidate records, third-party personal data, or
> secrets. See [`18-playbook-integration.md`](18-playbook-integration.md) §2.

---

## v2 — what changed, in one paragraph

**v1 routed hard problems to the five-seat paid panel. Your own repository had
already measured that as the wrong call.** `adjudication/one_model.py` records
Stage 0 baselines of **0.968** and **1.000** on your two task classes against a
**0.45** threshold, and the instruction *"DO NOT BUILD THE ENSEMBLE. Build one
model plus gates."* The gates — free, and with errors uncorrelated to the model's
— were always the valuable layer. v2 inverts the hierarchy into a four-tier
cascade that cuts deep-thinking spend by roughly **88%**, promotes the browser
window swarm to the workhorse tier at **zero marginal API cost**, and adds a
Karpathy loop that optimizes the panel itself against the accuracy harness you
already own. Full register: [`13-v2-version-analysis.md`](13-v2-version-analysis.md).

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
| [`11-autoresearch-loops.md`](11-autoresearch-loops.md) | The four Karpathy-style loops. Which lanes can support a real one, which must be hybrids, and why |
| [`12-browser-and-remote-control.md`](12-browser-and-remote-control.md) | Claude driving local Chrome, ChatGPT running remote. **The logged-in-profile risk** |
| [`loops/`](loops/) | **Five** loops — four lanes plus `panel-economics` — with `loop_guard.py`, the fail-closed gate in front of each |
| **[`13-v2-version-analysis.md`](13-v2-version-analysis.md)** | **v1→v2 defect register. Read this first if you read v1** |
| **[`14-panel-economics.md`](14-panel-economics.md)** | **The cost fix. Four-tier cascade, ~88% reduction, arithmetic shown** |
| **[`15-window-swarm.md`](15-window-swarm.md)** | **Five LLMs in Chrome tabs at zero marginal API cost. The workhorse tier** |
| **[`16-agent-roster-v2.md`](16-agent-roster-v2.md)** | **Sixteen agents. ROUTER, ORCHESTRATOR, OPTIMIZER, HARVESTER, SENTINEL, DILIGENCE** |
| **[`17-subscription-economics.md`](17-subscription-economics.md)** | **v2.1. Two Max subscriptions make the two priciest seats free. The constraint becomes rate limits, not dollars** |
| **[`18-playbook-integration.md`](18-playbook-integration.md)** | **v3. Reconciles with your Operating Playbook. Eleven-item defect register, including a privacy incident** |
| **[`cards/`](cards/)** | **21 agent cards. One page per agent — open exactly one** |
| [`mission-template.md`](mission-template.md) | Copy to `mission.md` before any run. Blank limits authorize nothing |
| **[`19-inversion-analysis.md`](19-inversion-analysis.md)** | **v4. How this fails, what plugs each hole, what is still open. The three-rung confidence ladder** |
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
