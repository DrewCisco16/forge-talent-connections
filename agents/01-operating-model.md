# 01 — OPERATING MODEL

The architecture, from first principles. Everything else in this system is a
consequence of this file.

---

## 1. The problem, stated correctly

**Your stated goal:** "these AI agents need to get me my time back."

That goal is not served by adding agent capacity. It is served by removing
**decisions and reading** from your day. Those are different problems, and
optimizing the first makes the second worse.

Consider what actually consumes a day across your four lanes (Stated, from your
resume and fleet pack):

| Consumer of time | Lane | Character |
|---|---|---|
| Email triage and reply | all four | High volume, low stakes each, no batching |
| Solicitation scanning and bid/no-bid | ABO / Just4Veterans | High volume in, tiny fraction relevant |
| Compliance matrix construction | ABO | Mechanical, high-consequence if wrong |
| Literature surveillance and citation hygiene | DBA | Mechanical, fraud risk if wrong |
| Prior-art scanning | FORGE LINK IP | Mechanical, legally consequential |
| Code review and build babysitting | FORGE LINK | Mechanical, catchable by machine |
| Reconciling what happened across all of it | you only | Irreducible |

Six of those seven are **filtering and mechanical transformation**. One is
judgment. An agent workforce is worth building exactly to the extent that it
consumes the six without enlarging the seventh.

**The failure mode to design against:** ten agents each produce a competent
two-page brief every morning. You now have twenty pages of competent reading
before 9am and less time than you had before. *The agents worked. The system
failed.* This is the most common outcome of agent deployments and it is the one
this design is organized to prevent.

---

## 2. First principle: review cost is the unit of account

> **An agent's value is its output's decision value minus the time you spend
> reviewing it. An agent whose output you must read carefully is a tax until
> proven otherwise.**

So every agent gets a **Trust Tier** assigned *before* it runs, and the tier
fixes its permitted review cost. Tiers are earned by measured performance, never
granted by intent.

### The three Trust Tiers

| Tier | Name | Agent may | Your review cost | Reversibility requirement |
|---|---|---|---|---|
| **A** | **Autonomous** | Act without telling you. Appears only in the weekly ledger. | **Zero.** You do not read it. | Fully reversible, bounded blast radius, nothing leaves your control |
| **B** | **Draft-and-hold** | Produce a decision-ready artifact and stop. | **≤60 seconds** to approve, reject, or send back. One screen. | May be outward-facing, but nothing is committed until you act |
| **C** | **Adjudicated** | Assemble evidence and options. Never decide. | Minutes to hours, deliberately. | Irreversible, capital-committing, legally binding, or reputational |

**Tier B is the whole game.** A Tier B artifact that takes four minutes to review
is a failed Tier B artifact — it has been mis-specified and must be either
narrowed until it fits in sixty seconds or promoted to Tier C honestly.

### The sixty-second test

A Tier B artifact must fit this shape, on one screen, always in this order:

```
RECOMMENDATION:  <one line — the action, not a summary of considerations>
CONFIDENCE:      High | Medium | Low  + the one reason
BASIS:           <=3 bullets, each carrying its evidence label
WOULD CHANGE MY MIND: <the one fact that would flip this>
ACTION:          [ APPROVE ]  [ REJECT ]  [ SEND BACK: ____ ]
```

If an agent cannot fill `RECOMMENDATION` in one line, it does not have a Tier B
output. It has Tier C evidence and must say so.

### The promotion ladder

No agent starts at Tier A. Tiers are earned against a measured record:

```
Tier C  ──30 outputs, zero material errors──▶  Tier B
Tier B  ──50 approvals, ≥95% approved unedited, zero outward-facing errors──▶  Tier A
                              (for that narrow category only)
```

Promotion is **per category, never per agent.** MAILROOM may reach Tier A for
"decline a recruiter cold-email" while remaining Tier C forever for "reply to a
contracting officer." Demotion is immediate and automatic on any material error;
see `08-measurement.md` §4.

---

## 3. Second principle: the human is the only cross-lane node

Your fleet pack already fixes this (§10.3.6, Stated): *"GovCon, software company,
DBA, and personal administration are separate lanes. Agents must not cross-use
information between lanes without explicit authorization."*

This design implements that literally.

| Lane | Entity | Data character | Isolation |
|---|---|---|---|
| **ABO** | Alpha Beta Omega Enterprises LLC / ABO Solutions | Government contracting. May touch CUI, procurement-sensitive, competitor-sensitive | Hardest boundary. See `07-guardrails.md` §2 |
| **FORGE** | FORGE LINK LLC | Product, source, IP, invention disclosures | Patent-sensitive. Public disclosure destroys rights |
| **J4V** | Just4Veterans Enterprises (1099 BD) | Another party's pipeline and teaming data | **Not your data.** Contractual duties you did not write |
| **DBA** | FIU doctoral program | Dissertation, literature, data | Academic integrity. Fabrication is career-ending |
| **HOME** | Personal / family stewardship | Financial, medical, family | Never enters a work lane |

**Implementation, not aspiration:**

1. **One workspace per lane.** Separate repository or separate directory root,
   separate Claude Code environment, separate routine set.
2. **No agent is granted connectors from two lanes.** A routine's connector list
   is its lane boundary. (Docs-Verified: routines include *all* your connected
   connectors by default and Claude "can use every tool from an included
   connector, including writes, without asking for permission during a run" —
   `code.claude.com/docs/en/routines`, retrieved 2026-09-14. **You must remove
   the ones that do not belong to the lane. The default is wrong for you.**)
3. **No cross-lane agent exists in this roster.** Not even a "chief of staff."
   The temptation is real and the answer is no: an agent with read access to all
   five lanes is a single point of compliance failure across a government
   contract, a patent filing, a doctoral committee, and your family's finances.
4. **You are the integration layer.** The weekly STEWARD ledger (§02, agent 10)
   is produced *per lane* and you read the five side by side. That reconciliation
   is judgment work and it stays yours.

**Cost of this rule, stated honestly:** you lose the convenience of asking one
agent "what's on my plate." That convenience is worth less than the boundary.

---

## 4. Third principle: one-way doors require a human hand

Classify every agent action by reversibility before granting it:

| Door | Examples | Rule |
|---|---|---|
| **Two-way** (reversible in minutes, no witness) | Label an email, open a draft PR, write a file to a scratch branch, build a research brief, tag a solicitation | **Tier A eligible** |
| **Two-way with a witness** (reversible, but someone saw it) | Post a comment, reply on an internal thread, push to a shared branch | Tier B minimum |
| **One-way** (irreversible or outward-facing to a counterparty) | Send email to a contracting officer, submit anything to SAM.gov, file with USPTO, commit to `main`, transfer money, sign, publish, disclose an invention | **Human hand on every one. No exceptions, no promotion ladder, permanently Tier C.** |

The one-way list is not a starting posture that relaxes with confidence. A
patent right destroyed by premature public disclosure does not come back because
the agent had a good track record.

---

## 5. Fourth principle: separate the proposer from the checker

Your `adjudication/` engine already encodes this and the reasoning is sound
(Repo-Verified, `adjudication/night_loop.py` docstring): *"THE CHECK RUNS BEFORE
THE CLOSER, ALWAYS. If the closer merges first and the gates run second, a false
claim is already woven into the working answer... The ordering is the whole
reason this is safe to run unattended."*

Generalize it to the whole workforce:

1. **No agent verifies its own output.** Verification goes to a different agent
   in a different context window. (Docs-Verified: *"Each subagent starts with a
   fresh, isolated context window. It doesn't see your conversation history"* —
   `code.claude.com/docs/en/sub-agents`, retrieved 2026-09-14. That isolation is
   what makes the check independent rather than theatrical.)
2. **Mechanical checks run before model judgment.** A DOI either resolves or it
   does not. A shall-statement either has a matrix row or it does not. A test
   either passes or it does not. Run the deterministic gate first; never ask a
   model to assess what code can decide.
3. **Model output is data, never instruction.** Also already yours
   (Repo-Verified, same file): *"Every piece of prior model text fed into a later
   prompt is wrapped in delimiters and preceded by a line saying so. An
   instruction found inside a reply is recorded as a finding, never obeyed."*
   This extends to *every* external input an agent ingests — email bodies,
   solicitation PDFs, web pages, PR comments. See `07-guardrails.md` §4.

---

## 6. Fifth principle: cloud-first placement

Your fleet pack already reached this conclusion (§10.1, Stated) and it is
correct: *"Any 24/7 agent that can run in a vendor cloud should run there, not on
local hardware."*

Confirmed for the Claude side (Docs-Verified, `code.claude.com/docs/en/routines`,
retrieved 2026-09-14): *"Routines execute on Anthropic-managed cloud
infrastructure... so they keep working when your laptop is closed."*

The corollary is the useful part: **local hardware earns a workload only when it
has something the cloud does not.**

| Local node | What only it can do | Therefore it gets |
|---|---|---|
| ASUS ProArt 16 (RTX 5070, 8GB VRAM) | CUDA, local inference on data that must not leave the premises | Any embedding/inference over lane-restricted data |
| MacBook Air 15 M4 (16GB) | Apple platform builds, Xcode, TestFlight | Apple release work only. **16GB is the fleet bottleneck — do not stack Docker + Xcode + Android Studio + terminals** |
| Surface Pro 8 | Touch, pen, Thunderbolt 4 | Touch/pen QA of the talent app |
| HP Envy 17 (64GB, WSL2) | Long unattended local loops with real bash, physical device attachment | The overnight loop *only if* it must be local; otherwise cloud |
| Five phones, iPad, two watches | Physical device testing | Nothing scheduled. These are hands-on targets |

Everything else goes to a vendor cloud. Your laptops are then free to be
*laptops* instead of servers you are afraid to close.

---

## 7. What "24 hours a day" actually means

You asked for agents working twenty-four hours a day. Here is the honest shape of
that, because the marketing shape is wrong and planning against it will fail.

| What you may have imagined | What is actually available |
|---|---|
| Agents thinking continuously all night | **Event-driven bursts plus scheduled runs.** Nothing "thinks" between runs |
| Poll every minute for new work | **Minimum schedule interval is one hour.** (Docs-Verified: *"The minimum interval is one hour; expressions that run more frequently are rejected"* — `code.claude.com/docs/en/routines`, retrieved 2026-09-14) |
| Unlimited runs | **A daily cap on runs per account, plus normal subscription usage limits.** Both draw from the same pool as your interactive work (Docs-Verified, same source) |
| Instant reaction to anything | Instant only where a real event exists: a GitHub event, or an HTTP POST to a routine's `/fire` endpoint (Docs-Verified, same source) |

**So the true 24/7 pattern is:**

```
EVENT-DRIVEN  ── GitHub events, API /fire from a webhook ──▶ seconds
HOURLY        ── the fastest recurring cadence available  ──▶ ≤1 hour latency
NIGHTLY       ── the heavy work, while you sleep          ──▶ ready by morning
WEEKLY        ── the ledger and the reconciliation        ──▶ your Monday
```

That is genuinely enough for every workload in your roster. Nothing you do needs
sub-hour autonomous latency. What you actually need is that **the work is done
before you get to it**, and nightly delivers that.

**The one real "continuous" option** is a local loop on the HP Envy 17, which
your own fleet pack documents the cost of (§1.1, Stated/Inference): Modern
Standby must be defeated, Wi-Fi power management disabled, Windows Update paused,
Chrome Memory Saver off — and the machine is audible under load. Use it for the
NIGHTWATCH adjudication runs where it earns its keep, not as the default host.

---

## 8. The resulting shape

```
                         ┌──────────────────────────┐
                         │   ANDREW  (only cross-   │
                         │   lane node; one-way     │
                         │   doors; Tier C calls)   │
                         └────────────┬─────────────┘
        ┌───────────┬──────────┬──────┴──────┬──────────────┐
        ▼           ▼          ▼             ▼              ▼
     ┌──────┐   ┌──────┐   ┌──────┐      ┌──────┐       ┌──────┐
     │ ABO  │   │FORGE │   │ J4V  │      │ DBA  │       │ HOME │
     │GovCon│   │ LINK │   │  BD  │      │ FIU  │       │Family│
     └──┬───┘   └──┬───┘   └──┬───┘      └──┬───┘       └──┬───┘
        │          │          │             │              │
   ┌────┴────┐ ┌───┴────┐ ┌───┴───┐    ┌────┴────┐    ┌────┴────┐
   │MAILROOM │ │MAILROOM│ │MAILROOM│   │MAILROOM │    │MAILROOM │
   │SCOUT    │ │BUILDER │ │SCOUT   │   │LIBRARIAN│    │ (only)  │
   │CAPTURE  │ │REVIEWER│ │        │   │         │    │         │
   │MATRIX   │ │PRIORART│ │        │   │         │    │         │
   └────┬────┘ └───┬────┘ └───┬───┘    └────┬────┘    └────┬────┘
        └──────────┴──────────┴─────┬───────┴──────────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │  NIGHTWATCH → adjudication/   │
                    │  five blinded seats, claim    │
                    │  gates, cost ceiling, refuse  │
                    │  path.  Hard problems only.   │
                    └───────────────┬───────────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │  STEWARD — per-lane weekly     │
                    │  ledger: what ran, what it     │
                    │  cost, what it got wrong       │
                    └───────────────────────────────┘
```

MAILROOM appears five times because there are five mailbox lanes and **they do
not share an agent instance.** Same prompt, five isolated deployments, five
connector scopes. That is the price of §3 and it is worth paying.
