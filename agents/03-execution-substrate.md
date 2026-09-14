# 03 — EXECUTION SUBSTRATE

Where each agent actually runs, what the platforms actually do, and what they
do not do.

**All Claude Code facts below were retrieved from Anthropic's own documentation
during this session on 2026-09-14 and are quoted verbatim with their source. All
OpenAI Codex facts are Unverified — the domain was blocked (§4).**

---

## 1. The four places an agent can run

| Substrate | Machine on? | Best for | Verified? |
|---|---|---|---|
| **Claude Code Routine** (cloud) | **No** | Scheduled and event-driven agents. The default | Docs-Verified |
| **GitHub Actions** | No | Deterministic gates, cost-ceilinged vendor calls, CI | Repo-Verified — you already run three |
| **OpenAI Codex** (cloud) | Presumed no | A second independent implementation opinion | **Unverified** |
| **Local node** (HP / ASUS / Mac / Surface) | **Yes** | GPU work, Apple builds, attached devices, data that must not leave | Stated (your fleet pack) |

**Placement rule:** cloud unless the workload has a property only local hardware
provides. Your fleet pack §10.1 already reached this and it is right.

---

## 2. Claude Code Routines — the primary substrate

**What it is** (Docs-Verified, `code.claude.com/docs/en/routines`, retrieved 2026-09-14):

> "A routine is a saved Claude Code configuration: a prompt, one or more
> repositories, and a set of connectors, packaged once and run automatically.
> Routines execute on Anthropic-managed cloud infrastructure... so they keep
> working when your laptop is closed."

**Three trigger types**, and a routine may combine them:

| Trigger | Behavior | Latency |
|---|---|---|
| **Scheduled** | "hourly, daily, weekdays, or weekly", or a one-off at a timestamp | Minutes of stagger |
| **API** | `POST` to a per-routine `/fire` endpoint with a bearer token | Seconds |
| **GitHub** | Pull request and Release events, with filters on author, title, body, base/head branch, labels, draft, merged | Seconds |

**The five constraints that shape the whole design:**

1. **Minimum interval is one hour.** *"The minimum interval is one hour;
   expressions that run more frequently are rejected."* Sub-hour polling is not
   available. Design around it (§3).
2. **There is a daily run cap, plus normal usage limits.** *"routines have a
   daily cap on how many runs can start per account"* and they *"draw down
   subscription usage the same way interactive sessions do."* **Your agents
   compete with your own interactive Claude Code use for the same pool.** Budget
   accordingly; do not schedule ten nightly routines and expect your Tuesday
   session to be unaffected.
3. **No approval prompts during a run.** *"Routines run autonomously as full
   Claude Code cloud sessions: there is no permission-mode picker and no approval
   prompts during a run."* **This is the single most important governance fact on
   this page.** Whatever tools a routine can reach, it will use without asking.
   The tool scope *is* the permission model. See `07-guardrails.md` §1.
4. **All your connectors are included by default.** *"all of your connected MCP
   connectors are included by default. Remove any the routine doesn't need:
   Claude can use every tool from an included connector, including writes,
   without asking for permission during a run."* **The default violates lane
   separation. You must prune on every routine.**
5. **Research preview.** *"Behavior, limits, and the API surface may change."*
   Do not build anything load-bearing that cannot survive this changing.

**Two more facts worth knowing:**

- Branch safety is built in: *"Claude pushes its work to branches prefixed with
  `claude/`, which are always accepted"*, and a push to another branch is
  rejected if the branch is protected, has someone else's open PR, or carries
  someone else's commits. Protect `main`; the platform then enforces §04's
  one-way door for you.
- A green run status is not success: *"A green status in the run list means the
  session started and exited without an infrastructure error. It does not mean
  the task in your prompt succeeded."* STEWARD must read transcripts, not
  statuses.

**Where routines are managed:** `claude.ai/code/routines`, or `/schedule` from the
CLI (`/schedule list`, `/schedule update`, `/schedule run`). API triggers can only
be created on the web — *"The CLI cannot currently create or revoke tokens."*

---

## 3. Designing around the one-hour floor

The floor is not a problem once you stop treating polling as the mechanism.

| Need | Wrong design | Right design |
|---|---|---|
| React to a new email fast | Poll every 2 minutes | Hourly routine. Mail is not a sub-hour medium, and treating it as one is itself the time sink |
| React to a PR instantly | Poll for PRs | **GitHub trigger.** Event-driven, seconds |
| React to an external system | Poll the system | **API trigger.** Have that system `POST` to the routine's `/fire` endpoint |
| Watch a slow feed (SAM.gov) | Poll hourly | **Nightly.** Postings are not sub-day events, and a nightly sweep costs one run instead of twenty-four |
| Genuinely continuous work | Cloud routine | **Local loop on the HP Envy 17**, accepting the wake/power costs in your fleet pack §1.1 |

**The `/fire` endpoint** is the escape hatch that makes anything event-driven
(Docs-Verified, same source):

```bash
curl -X POST https://api.anthropic.com/v1/claude_code/routines/<trigger_id>/fire \
  -H "Authorization: Bearer <routine token>" \
  -H "anthropic-beta: experimental-cc-routine-2026-04-01" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"text": "<run-specific context>"}'
```

Two things to know before wiring this to anything:

- The token is shown once. *"The token is shown once and cannot be retrieved
  later."* Put it in a real secret store, never in a document or a repository.
- **Fire text is untrusted by default, deliberately.** *"The `text` value doesn't
  reach the routine as a bare message. It arrives wrapped in a
  `<routine-fire-payload>` block that labels it as untrusted data and tells
  Claude not to follow instructions inside it unless the routine's own prompt
  says to."* A routine must **opt in** to acting on fire text. That default is
  protecting you — anyone holding the token can send `text`. Opt in narrowly and
  specifically, never with "do what the payload says."

---

## 4. OpenAI Codex — Unverified, and handled by adapter

**What happened.** An attempt to retrieve `developers.openai.com/codex/cloud/`
from this session returned:

```
{"error_type":"EGRESS_BLOCKED","domain":"developers.openai.com",
 "message":"Access to developers.openai.com is blocked by the network egress proxy."}
```

**Therefore, plainly:**

- I could not verify that a model called **"GPT-5.6 Codex"** exists. You named it;
  I am not going to repeat it back as fact. **Unknown — verify at the source.**
- I could not verify Codex's sandbox model, network policy, scheduling
  capability, or `AGENTS.md` handling. All **Unverified**.
- I will not describe Codex's behavior from memory. Recollection of a vendor's
  current product surface is exactly the unverified assertion your
  `adjudication/` engine exists to catch (Repo-Verified, `profiles.example.json`:
  *"Do not write one from memory or from another project."*)

**The design response is an adapter, not a guess.** Every agent in the roster is
specified by *contract* — input, output shape, tool scope, tier — never by vendor.
`prompts/` holds vendor-neutral prompts. To run one on Codex:

1. Read OpenAI's current documentation yourself and fill in
   `agents/prompts/SUBSTRATE-CODEX.md` (stub committed, marked `FILL-IN` in the
   same style as your `profiles.example.json`).
2. Confirm the four properties the design actually depends on: (a) isolated
   execution, (b) a controllable network policy, (c) a scoped repository grant,
   (d) whether it can be triggered on a schedule or by event.
3. If (d) is absent, run Codex agents from a Claude Code routine or a GitHub
   Action that invokes them, rather than abandoning the second opinion.

**Where a second vendor genuinely earns its cost:** BUILDER and REVIEWER. Two
independent implementations of the same issue, or an implementation from one
vendor reviewed by another, is a real independence gain. Everywhere else, a
second vendor is a second thing to maintain.

---

## 5. Agent → substrate map

| Agent | Substrate | Trigger | Node |
|---|---|---|---|
| MAILROOM ×5 | Claude Code Routine | Scheduled hourly | cloud |
| SCOUT | Claude Code Routine | Scheduled nightly | cloud |
| CAPTURE | Claude Code Routine | API `/fire` from the SCOUT queue, or manual | cloud |
| MATRIX | Claude Code Routine + deterministic pre-pass in GitHub Actions | On demand | cloud |
| LIBRARIAN | Claude Code Routine, calling `adjudication/citation_gate.py` | Scheduled weekly | cloud |
| PRIORART | Claude Code Routine | On demand / monthly | cloud |
| BUILDER | Claude Code Routine (GitHub trigger) and/or Codex | `pull_request` / issue label | cloud |
| REVIEWER | Claude Code subagent + GitHub trigger routine | PR opened/synchronized | cloud |
| NIGHTWATCH | **GitHub Actions `workflow_dispatch`** (existing `adjudicate.yml`) | **Manual + typed `SPEND`** | GitHub runner |
| STEWARD | Claude Code Routine | Scheduled weekly | cloud |

**Nothing in the steady state requires a local machine to be awake.** That is the
design goal from `01` §6, and it holds.

### What still belongs on local hardware

| Workload | Node | Why only there |
|---|---|---|
| Embeddings/inference over lane-restricted data | ASUS ProArt 16 (RTX 5070, 8GB VRAM) | Only GPU. **8GB VRAM is the ceiling on model size** (Stated) |
| iOS/macOS builds, TestFlight | MacBook Air 15 M4 | Only Mac. **16GB is the fleet bottleneck** (Stated) |
| Touch/pen QA of the talent app | Surface Pro 8 | Only touchscreen Windows (Stated) |
| Physical device testing | 5 phones, iPad Pro 13, Apple Watch Ultra 2, Pixel Watch 4 | Hardware in hand |
| A genuinely continuous overnight loop | HP Envy 17 (64GB, WSL2) | Only if it must be local. Requires the §1.1 wake procedure |

**Before any unattended local run** (your fleet pack §1.1, Stated/Inference):
`powercfg /a` to record the standby mode; PowerToys Awake; Wi-Fi adapter power
management disabled; Windows Update paused with Active Hours set; Chrome Memory
Saver off. **Running `powercfg /a` and recording the result is an open item in
`10-open-questions.md`.**

### Notification routing — a real constraint from your own fleet pack

The Pixel Watch 4 is **Wi-Fi only, no LTE** (Screenshot-Supported in your pack).
It cannot receive a run-status ping when you are away from both Wi-Fi and your
phone. **Any agent alert that must reach your wrist off-network routes to the
Apple Watch Ultra 2, which is on its own Verizon line, or to a phone directly.**

Only the Verizon line gives independent carrier redundancy — Google Fi rides
T-Mobile towers, so the Pixel 10 Pro XL and the iPhone 17 Pro Max share one
physical network (Stated). For an escalation path that must survive a carrier
outage, the iPhone 16 Pro Max on Verizon is the only independent route.

---

## 6. Routing rule: which substrate for which question

```
Is it mechanical and checkable by code?
  └─ YES → deterministic script / GitHub Action. Do not ask a model.
  └─ NO ↓
Is it a single-pass transformation with a known-good shape?
  └─ YES → one agent, Tier B, sixty-second artifact.
  └─ NO ↓
Is it consequential, contested, AND unresolved by one more hour of your reading?
  └─ NO  → one agent, Tier C, you decide from its evidence.
  └─ YES ↓
        NIGHTWATCH → adjudication/ five-seat run, manual, cost-ceilinged.
```

**The last gate is strict on purpose.** A five-seat run has measured about $5 and
is bounded under $17 per run (Repo-Verified, `adjudicate.yml` input description),
and a full run *"takes on the order of an hour"* (Repo-Verified, `USING.md`).
Spend it on questions where being wrong is expensive and where you are genuinely
uncertain — not on questions where you already know and want reassurance. A
system that adjudicates everything is a system that adjudicates nothing.
