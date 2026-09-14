# 19 — INVERSION ANALYSIS

**Method:** it is 2027-09-14. The agent system failed. Write down why — then plug
each hole. Failure modes are enumerated first and favourably; nothing is dismissed
until it has a named plug.

---

## 0. On "raise the confidence level to the maximum"

**I cannot give you a confidence number, and your own `AGENTS.md` is why:**
*"No success percentage, probability, confidence interval or expected value
without a real dataset and a shown calculation."* There is no dataset. A number
here would be the exact failure this system exists to prevent.

**What can be raised is confidence's actual substrate.** Every rule in this
system sits on one of three rungs. Confidence rises by moving rules **up**:

| Rung | What it is | Failure rate |
|---|---|---|
| **3 — Prose** | A rule written in a document | Unknown and unmeasured. Depends entirely on whether a tired human remembers it at 11pm |
| **2 — Test** | A declared acceptance test | Known when run; silent when nobody runs it |
| **1 — Gate** | Code that blocks, fails closed, and is itself tested | Measurable, and it does not depend on anyone remembering |

**The PII incident is the proof.** The rule existed on rung 3 in three separate
places — `AGENTS.md`, the Playbook p.25, the fleet pack's own header — and was
violated anyway. It now sits on rung 1: `scripts/redaction_guard.py`, 35 self-
tests, installed as a pre-commit hook, **and the denial has been live-tested.**

**This document's job is to move as many rules as possible from rung 3 to rung 1.**

---

## 1. The register

Severity: **C** catastrophic (unrecoverable) · **H** high · **M** medium.
Status: 🟢 gated (rung 1) · 🟡 tested (rung 2) · 🔴 prose only (rung 3) · ⬜ open.

### A. Operator failure — the most likely category by a wide margin

| # | How it fails | Sev | Plug | Status |
|---|---|---|---|---|
| **A1** | **It is never started.** 39 documents, 25 cards, five loops, and not one agent has run. This is the single most probable failure mode in the whole register | H | `START-HERE.md` — a ten-line router, one question, one link. **[BRIEFER](cards/briefer.md) is 25 minutes, $0, public sources, no counsel gate.** Plus the §3 kill rule | 🟡 |
| **A2** | Runs twice, then a proposal lands and it dies | H | Value must appear in week 1 or the design is wrong. STEWARD's **review-minutes** number is the early warning | 🟡 |
| **A3** | Six agents started at once; none evaluated | H | **One-at-a-time deployment gate** in `cards/README.md` + [PARKING](cards/parking.md) | 🔴 |
| **A4** | Cannot find the right page at the moment of need | M | `START-HERE.md`; one-page cards; index routes by *task*, not by document number | 🟡 |
| **A5** | **Context lost between sessions.** Nobody knows where things stand | H | `STATE.md` — single source of truth for what is running, what is blocked, what is next | 🟢 |
| **A6** | Bus factor of one. Everything routes through Andrew | M | Cards + `STATE.md` mean someone else could pick it up. **Inherent, not fully closable** | ⬜ |

### B. Truth and integrity — highest severity

| # | How it fails | Sev | Plug | Status |
|---|---|---|---|---|
| **B1** | A fabricated citation reaches the defended dissertation | **C** | `citation_gate.py` + [citation-verifier](../.claude/agents/citation-verifier.md), **fail closed: discarded, never caveated** | 🟢 |
| **B2** | An invented requirement reaches a proposal | **C** | MATRIX two-pass; `MODEL-ONLY` sheet never merged | 🟡 |
| **B3** | **An agent claims it ran a test that it did not run.** `AGENTS.md` forbids it; nothing checks | H | **NEW: [ATTESTOR](cards/attestor.md)** — artifacts must exist on disk with timestamps, or the claim is void | 🟡 |
| **B4** | An evidence label is quietly upgraded across a handoff chain | H | [evidence-auditor](../.claude/agents/evidence-auditor.md), **mandatory on every handoff**, not optional | 🟡 |
| **B5** | An invented number compounds through three documents | H | evidence-auditor; `AGENTS.md` no-number rule | 🟡 |
| **B6** | **Agent quality drifts silently.** Outputs still look good; nobody has ground truth | H | **NEW: [CANARY](cards/canary.md)** — per-agent golden sets re-run monthly, plus **seeded defects so REVIEWER's own blindness is detectable** | 🟡 |
| **B7** | REVIEWER stops finding anything and that reads as good news | M | CANARY seeds a known defect. **Zero findings on a seeded run is an alarm** | 🟡 |

### C. Security and privacy — already failed once

| # | How it fails | Sev | Plug | Status |
|---|---|---|---|---|
| **C1** | **Third-party PII published to a public repo** | **C** | **`scripts/redaction_guard.py` — 35 self-tests, pre-commit hook installed, denial live-tested.** Rung 1 | 🟢 |
| **C2** | A secret is committed | **C** | Same guard: 7 key-shape rules + inline-credential rule | 🟢 |
| **C3** | CUI or a source-selection marking is committed | **C** | Same guard | 🟢 |
| **C4** | An invention disclosure is committed and the patent right dies | **C** | `AGENTS.md` prohibition + [priorart](cards/priorart.md) card. **Not yet gated — no mechanical detector for "this text is an unfiled invention"** | 🔴 |
| **C5** | Browser agent runs in a profile logged into a bank or brokerage | **C** | Per-lane profiles (`12` §3); [SMOKE](cards/smoke.md) tests the boundary before trust | 🟡 |
| **C6** | Prompt injection via an email body or fetched page | H | Untrusted-data rule; **every card carries an unsafe-instruction acceptance test**; CANARY carries an injection corpus | 🟡 |
| **C7** | **Cloudflare Pages serves the repo's documents as a website** | H | **Unverified — pages.dev unreachable from the sandbox.** Awaiting your check | ⬜ |
| **C8** | Data reaches a vendor whose terms permit training on input | H | Route C note; per-vendor terms check | 🔴 |

### D. Economic

| # | How it fails | Sev | Plug | Status |
|---|---|---|---|---|
| **D1** | Spend runs away unattended | H | `cost_ledger.py` checks **before** the call; `loop_guard.py` caps; typed `SPEND` | 🟢 |
| **D2** | **Agents consume the rate limits Andrew needs for his own work** | H | ROUTER's 40% reserved headroom (`17` §4). **Documented, not enforced — no meter exists yet** | 🔴 |
| **D3** | Unnecessary subscriptions bought | M | Break-even rule: 41.7 swarm runs/month (`17` §5) | 🟡 |
| **D4** | A ceiling computed from stale prices bounds nothing | H | `rates.json` staleness window; SENTINEL carries **2026-12-08**; `loop_guard` blocker | 🟢 |

### E. Correctness

| # | How it fails | Sev | Plug | Status |
|---|---|---|---|---|
| **E1** | Loop games its metric (reward hacking) | H | Declared cheat paths + held-out check, both **enforced by `loop_guard.py`** | 🟢 |
| **E2** | Loop runs unbounded and bills all night | H | Pilot mode: 3 variants / 60 min / $0, enforced | 🟢 |
| **E3** | A test is weakened to reach green | H | Immutable paths in `loop.json`, enforced; REVIEWER's weakened-test test | 🟢 |
| **E4** | **No baseline, so "did it help" is unanswerable at day 90** | H | **NEW: [BASELINE](cards/baseline.md)** — starts the two-week capture. Still not started; that is the gap | 🟡 |
| **E5** | A green run status is mistaken for a good run | M | STEWARD reads transcripts, not statuses | 🔴 |

### F. Legal and compliance

| # | How it fails | Sev | Plug | Status |
|---|---|---|---|---|
| **F1** | ABO lane runs on non-public data before counsel answers | **C** | `loop_guard` refuses `counsel_cleared: false`; both cards marked BLOCKED | 🟢 |
| **F2** | **FIU's AI-use policy for doctoral work is violated** | **C** | **NEW OPEN QUESTION A7.** The Playbook flags it (p.23); I never logged it. Nothing in this system has checked what your program actually permits | ⬜ |
| **F3** | AI-prepared content is submitted without required disclosure | H | Open question A2, with counsel | ⬜ |
| **F4** | J4V client data handled against the 1099 agreement | H | Open question A3 | ⬜ |

### G. Systemic

| # | How it fails | Sev | Plug | Status |
|---|---|---|---|---|
| **G1** | **Two sources of truth drift.** `agents/prompts/*.md` and `agents/cards/*.md` now describe the same agents | M | **Precedence declared: the CARD is authoritative; a prompt is a paste-able rendering of it.** Recorded in both indexes | 🟡 |
| **G2** | Vendor behavior changes under a research-preview feature | M | Re-verify dates carried by SENTINEL | 🟡 |
| **G3** | **The system optimizes for looking rigorous rather than producing value** | H | §3 | 🟡 |

---

## 2. What was added to close holes

**Four agents (21 → 25), one gate, two navigation surfaces. Nothing of substance
was removed.**

| Added | Closes | Rung |
|---|---|---|
| **`scripts/redaction_guard.py`** + pre-commit hook | C1, C2, C3 | **1 — gate** |
| **[ATTESTOR](cards/attestor.md)** | B3 — false claims of completed work | 2 |
| **[CANARY](cards/canary.md)** | B6, B7, C6 — silent quality drift, blind reviewer, injection | 2 |
| **[BASELINE](cards/baseline.md)** | E4 — the unanswerable day-90 question | 2 |
| **[REDACTOR](cards/redactor.md)** | C1–C3 outbound, beyond commits | 2 |
| **`START-HERE.md`** | A1, A4 — never started, cannot find the page | 2 |
| **`STATE.md`** | A5 — context lost between sessions | 1 |
| Open question **A7** (FIU AI-use policy) | F2 | — |
| Precedence rule: card > prompt | G1 | 2 |

### The one removal, and why it was needed

**Nothing was deleted.** One thing was *demoted*: `agents/prompts/mailroom.md`,
`scout.md` and `reviewer.md` are no longer authoritative — the cards are. Two
documents describing one agent is a drift hazard, and drift in an agent contract
is how an agent quietly stops doing what you think it does. The prompts remain as
paste-able renderings, now labelled as such.

---

## 3. The kill rule — against G3 and A1

This system can fail by being too good-looking to start. Guard against it
mechanically:

> **If no agent has produced a real artifact you actually used by
> 2026-10-14 — thirty days — then the system is not working, and the correct
> response is to delete every document except `START-HERE.md`,
> `cards/briefer.md`, `AGENTS.md` and the redaction guard, and run only
> BRIEFER until it earns something more.**

Write that date somewhere you will see it. **Documentation that never becomes
action is a cost with no offsetting benefit**, and the honest move at that point
is deletion, not another revision.

---

## 4. Residual risk — what is still open, plainly

These have no plug yet. They are not hidden in a table above.

1. **C7 — Cloudflare Pages.** I could not verify whether the repo's markdown is
   served on the open web. Ten seconds for you; unverifiable from here.
2. **C4 — invention disclosure detection.** No mechanical way to detect "this
   paragraph is an unfiled invention." Prose rule only. **The real plug is a
   separate private repository**, which is a decision, not a gate.
3. **F2 — FIU's AI-use policy.** Unknown. **This is the most serious unlogged gap
   in the system**: an unrecoverable-class risk in your doctoral lane that nobody
   has checked.
4. **D2 — rate-limit headroom.** ROUTER's 40% reserve has no meter behind it.
5. **A6 — bus factor.** Inherent to a one-principal enterprise.
6. **The git history** still carries the PII pending your decision.

---

## 5. Confidence ledger — where each rung sits now

| Rung | Count | Examples |
|---|---|---|
| **1 — gated, fails closed, tested** | 9 | redaction guard · loop_guard (35 + 24 self-tests) · cost ceiling · citation gate · counsel block · immutable paths · rate staleness · STATE.md · pilot caps |
| **2 — declared test, not yet run against reality** | 19 | every card's three acceptance tests; CANARY's golden sets |
| **3 — prose only** | 6 | one-at-a-time deployment · disclosure detection · vendor terms · transcript-not-status · rate headroom · A3 |

**The honest reading:** nine rules can no longer be forgotten. Nineteen are
written down and untested until an agent actually runs. Six still depend on a
person remembering — and each one is named above rather than buried.

**That is what "maximum confidence" can truthfully mean here**: every rule either
blocks, or is written as a test, or is listed as depending on you. None of them
are quietly assumed.
