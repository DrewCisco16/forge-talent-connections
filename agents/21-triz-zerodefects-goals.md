# 21 — CRITICAL THINKING · TRIZ · ZERO DEFECTS

**Question:** are these the best agents, is the count right, and will the daily,
weekly, monthly and yearly goals actually be accomplished?

**The finding that outranks everything else in this document:** the system has
never seen your goals. Every prior version optimised the *integrity of the agent
system*; none of it was connected to what you are trying to achieve. That gap is
now `FM-33` in the register and it computes to **RPN 504 — first place, above
the FIU policy risk and above the PII exposure.**

---

## PART 1 — CRITICAL THINKING: the assumption audit

Not a framework recital. The load-bearing assumptions of everything built so far,
stated so they can be attacked, with what would falsify each.

| # | Assumption | Evidence for it | What would falsify it | Verdict |
|---|---|---|---|---|
| **A1** | The binding constraint is your review capacity | Reasoning only. **No measurement** | BASELINE showing MAIL+SCAN+MECHANICAL is a small share of your week | **UNTESTED.** Whole design rests on it |
| **A2** | You want time back | You said so, twice | Your behaviour: six sessions spent *building* the system, none running it | **CONTESTED — see below** |
| **A3** | 25 agent contracts will be used | None. Zero have run | Day 30 with nothing deployed | **UNTESTED** |
| **A4** | Agents can do GovCon capture work usefully | None | The first CAPTURE brief being unusable | **UNTESTED**, and blocked by counsel anyway |
| **A5** | The five lanes are genuinely separable | ABO and J4V both do federal BD | One opportunity that both lanes legitimately touch | **PROBABLY FALSE at the edges** |
| **A6** | Written goals exist to serve | **None.** Never supplied, never asked for | This document | **FALSE. This is FM-33** |
| **A7** | Specification transfers to execution | None | 40 documents, 0 agents running | **UNTESTED, and the record so far is against it** |

### A2 deserves being said plainly

You have asked six times for more analysis, more agents, more frameworks. You
have not once reported running one. **That is not a criticism — it is the single
most diagnostic fact available about this system, and ignoring it would be the
unfair thing to do.**

Two readings, and they demand opposite responses:

1. **You want the system complete before you trust it with real work.** Then the
   right move is to stop adding and start the two build items.
2. **Building is more rewarding than running, and the analysis has become the
   deliverable.** Then every further document makes the problem worse.

I cannot tell which from here. **`FM-24` — never started — still carries the
highest occurrence rank in the register (O = 9), and nothing in this document
changes that.** The kill date of 2026-10-14 exists for exactly this.

---

## PART 2 — TRIZ

### 2.1 The contradiction, stated properly

TRIZ starts by refusing the compromise. The technical contradiction here:

```
IMPROVING FEATURE   coverage - how much of the work gets done without you
WORSENING FEATURE   reliability and your attention - every agent adds review
                    burden and widens a shared failure surface

The compromise everyone reaches for: "pick the right number of agents."
TRIZ says: do not pick a number. Remove the contradiction.
```

**Separation principles applied — the contradiction dissolves on three axes:**

| Separate in | Applied here | Already built? |
|---|---|---|
| **Time** | Specify many, deploy one at a time. Coverage accrues without concurrent burden | Yes — one-at-a-time rule |
| **Condition** | Agents act alone only where reversible; Trust Tiers set that condition per category | Yes — Tiers A/B/C |
| **Space** | One lane per machine, one controller per browser. Failures cannot cross | Yes — per-lane machines |

**So the agent-count question was the wrong question.** With separation in place,
the count is not what trades against reliability. **The number of agents running
*concurrently and unreviewed* is.** That number is currently one, by rule.

### 2.2 Ideal Final Result — and this is the valuable part

> **IFR: the function is delivered, the goal is achieved, and the agent does not
> exist.**

TRIZ's most useful move is **trimming**: remove the component and ask whether the
function survives. Applied honestly to the roster:

| Agent | Function | Can the function survive without it? | Trim verdict |
|---|---|---|---|
| **MAILROOM ×5** | Remove decision load from five inboxes | **Partly — by removing the mail.** Unsubscribe, filters, one published route in, fewer addresses. **The ideal inbox agent is a smaller inbox** | **Trim the HOME instance. Attack volume first** |
| **SCOUT** | Notice relevant solicitations | Possibly — a saved search with native email alerts, if the source offers them | **Check before building.** An alert beats an agent |
| **SENTINEL** | Never miss a dated obligation | Largely — a calendar with reminders does this | **Keep only for cross-lane dates a calendar cannot hold.** Narrow it |
| **BASELINE** | Capture 14 days of time data | **It already has no agent.** Its own card says "no agent can do this part" | **RECLASSIFY — this is a protocol, not an agent** |
| **SMOKE** | Prove a browser route before trusting it | It is a five-line checklist run once per route | **RECLASSIFY — protocol, not an agent** |
| **PARKING** | Keep a stray idea from opening a second front | A notes app does this | **Keep** — near-zero cost, and it enforces the one-at-a-time rule |
| **NIGHTWATCH** | Adjudicate genuinely hard questions | Your own Stage 0 says one model plus gates suffices | **Already trimmed to a calibration instrument** |
| **ORCHESTRATOR** | Corroboration across model families | Tier 1b — Opus 5 + GPT-5.6 Sol, both subscription-funded — gives two-vendor corroboration at $0 | **Defer further.** The swarm is a workaround for a weakness that no longer exists |

**Two reclassifications, not deletions.** Calling BASELINE and SMOKE "agents"
was a category error, and a harmful one: **an agent card implies something will
do it for you.** Nothing will. They are protocols you execute.

### 2.3 The trim that matters most

> **The ideal MAILROOM is not a better inbox agent. It is less inbound mail.**

Automating triage on five inboxes accepts the volume as fixed. TRIZ says attack
the volume: unsubscribe aggressively, consolidate where lanes permit, publish one
route in, and stop being cc'd. **An hour spent on that plausibly beats the
MAILROOM deployment**, costs nothing, adds no failure surface, and needs no
review.

Same logic on SCOUT: before building an agent to watch a feed, check whether the
feed will email you.

**This is what TRIZ produces that FMEA and FTA cannot: not a safer agent, but the
question of whether the agent should exist.**

### 2.4 Inventive principles already embodied

Named because they were arrived at by reasoning, and it is worth knowing the
pattern has a name:

| Principle | Where it already appears |
|---|---|
| **10 — Preliminary action** | The pre-commit hook acts *before* the commit, not after the publication |
| **11 — Beforehand cushioning** | Held-out sets and declared cheat paths, written before the loop runs |
| **22 — Blessing in disguise** | CANARY turns the system's own failure modes into its test corpus |
| **23 — Feedback** | STEWARD's review-minutes number; the ROUTER tier log |
| **24 — Intermediary** | ROUTER sits between question and engine so neither has to know the other |
| **25 — Self-service** | `loop_guard` and `redaction_guard` carry their own self-tests |
| **2 — Taking out** | The sixty-second artifact removes the *reviewing*, not the output |

---

## PART 3 — ZERO DEFECTS, correctly applied

### 3.1 The standard has to be restated for a stochastic generator

Crosby's four absolutes: quality is **conformance to requirements**; the system is
**prevention, not appraisal**; the standard is **Zero Defects**; the measure is
the **Price of Nonconformance**.

**Zero Defects cannot mean zero defects out of an LLM.** The generator is
stochastic. Any plan that depends on the model never erring is not a quality
plan, it is a wish, and it will fail silently.

> **The correct standard here is ZERO ESCAPED DEFECTS (ZED): zero defects
> reaching an irreversible act.**
>
> A defect caught by a gate is not a quality failure. **It is the system
> working.** Only an escape counts.

That is both achievable and measurable, which "zero defects" is not.

### 3.2 Conformance to requirements

Crosby's first absolute needs written requirements. **The 25 acceptance-test sets
are the requirements** — normal, missing evidence, unsafe instruction, plus the
ten-test suite for research and browser agents. An agent without declared tests
cannot conform to anything, which is why the rule is: **no tests, no run.**

### 3.3 Prevention over appraisal — the current ratio

From the register, computed:

```
rung 1  PREVENTION (a gate blocks)     10 / 36   27.8%
rung 2  APPRAISAL  (a test would find) 20 / 36   55.6%
rung 3  NEITHER    (human memory)       6 / 36   16.7%
```

**Crosby's argument is that appraisal is the expensive way to get quality.** The
work is to move rung 2 → rung 1. The two named build items, ATTESTOR and CANARY,
are exactly that move.

### 3.4 The escape ledger — start it at 1, not 0

**One defect has escaped to date.** Recording it honestly is the whole point of
the measure:

| # | Escape | Reached | Caught by | PONC — price of nonconformance |
|---|---|---|---|---|
| **E-01** | Third-party PII committed to a public repository | An irreversible act: publication | Andrew's own Playbook, read *after* the commit | A redaction commit · a guard built from scratch · a history-remediation decision still open · residual exposure pending the Pages check · **and the trust cost of an agent system whose first act was the thing it was built to prevent** |

**ZED count since E-01: 0.** The guard has since blocked four attempted
commits — three of them mine. **Those are not defects. Those are the system
working.**

### 3.5 The ZED metric, added to STEWARD

```
ESCAPES THIS PERIOD ................ target 0, and 0 is achievable
GATE BLOCKS THIS PERIOD ............ expected > 0. A zero here is suspicious,
                                     not reassuring - it usually means the gate
                                     stopped running, not that nothing tried
PREVENTION RATIO ................... rung1 / total. Must rise
PONC ENTRIES OPEN .................. each escape carries its cost until closed
```

**A period with zero gate blocks and zero escapes is not a clean period. It is an
unverified one.** Check that the gate ran.

---

## PART 4 — WILL THE GOALS BE ACCOMPLISHED?

### 4.1 The honest answer first

**No system can promise you will accomplish all your goals, and one that claims
to is lying to you.** I will not make that claim.

What a system *can* do is make two specific failures impossible to have silently:

```
1  a goal nobody owns - discovered at the review that was meant to catch it
2  an agent running that advances nothing
```

Both are now structural, via the two ledger invariants.

### 4.2 What was missing, and why it ranked first

Until this document, **not one of the 25 agents traced to a goal.** They traced
to *failure modes*. That is a system built to avoid loss, not to achieve
anything — and it is why `FM-33` computes to RPN 504 and takes first place.

### 4.3 The mechanism now in place

| Cadence | What GOALKEEPER emits | Time cost |
|---|---|---|
| **Daily** | The ONE next action on the one active goal. Nothing else | ≤2 min |
| **Weekly** | Advanced / stalled / blocked · orphan goals · orphan agents | ≤10 min |
| **Monthly** | What moved, what did not, the honest reason | ≤20 min |
| **Quarterly** | The 90-day sprint close — your stated operating cadence | ≤45 min |
| **Annual** | Did the year hold; what next year inherits | — |

**GOALKEEPER never authors a goal.** It records, tracks, and flags orphans. Your
goals are weighed against a ten-year horizon, family, and a biblical frame — that
weighing is not delegable, and an agent has no standing to attempt it.

### 4.4 The first entry is empty, and that is the finding

[`analysis/goal-ledger.md`](analysis/goal-ledger.md) is a template with no goals
in it, because **none have ever been supplied.** Six sessions of system design
have proceeded without a single written goal to serve.

**Filling that file is worth more than any further agent.**

---

## PART 5 — THE COUNT

### 5.1 What changed

```
BEFORE   25 agents
         - BASELINE    reclassified: PROTOCOL (no agent performs it)
         - SMOKE       reclassified: PROTOCOL (a checklist, run once per route)
         + GOALKEEPER  new: closes FM-33, the highest-ranked mode in the register
         = 24 AGENTS + 2 PROTOCOLS
```

### 5.2 Verdict

| Question | Answer |
|---|---|
| **Best agents?** | **The control set is sound. The production set is unproven** — zero have run, so "best" is an untested claim and A3 stays open |
| **Too many?** | **No, to specify. Yes, to run.** With TRIZ separation in place, the trade is not against the count but against how many run **concurrently and unreviewed** — currently one, by rule |
| **Too few?** | **Was.** GOALKEEPER was missing and it ranked first once written down. I looked for a 26th beyond it and found none that closes an open cut set |
| **Trim further?** | **Attack volume before adding coverage.** Less mail beats a better mail agent; a native alert beats SCOUT; a calendar beats most of SENTINEL |
| **Will the goals be accomplished?** | **Unanswerable, and it will stay unanswerable while the goal ledger is empty.** That file is now the highest-value thing you can spend twenty minutes on |

---

## PART 6 — VERIFICATION QUEUE (additions)

**Every scholarly host remains blocked from this session** — Crossref, PubMed,
arXiv, SAGE, NeurIPS, OpenAlex, Semantic Scholar, Europe PMC, DOAJ all returned
`EGRESS_BLOCKED` or HTTP 000. **No citation in this document is verified, and
none is presented as such.**

Run these through `.claude/agents/citation-verifier.md` before any of it informs
a decision or enters a document.

| # | Candidate | What the snippet claimed | Relevance | Label |
|---|---|---|---|---|
| **L4** | Locke & Latham (2002), *"Building a practically useful theory of goal setting and task motivation: A 35-year odyssey"*, **American Psychologist**; PMID 12237980 | 35 years of research; **400+ laboratory and field studies**; specific and difficult goals outperform "do your best" | **Directly supports the falsifiable, dated goal format in the ledger** | **Unverified — snippet only** |
| **L5** | *"Optimized but Unowned: How AI-Authored Goals Undermine the Motivation They Are Meant to Drive"*, arXiv:2605.12344 | AI-authored goals reduce the motivation they aim to create | **The reason GOALKEEPER never authors a goal** | **Unverified — title and framing only** |
| **L6** | *"AI-Assisted Goal Setting Improves Goal Progress Through Social Accountability"*, arXiv:2603.17887 | AI assistance improves goal progress via accountability | **Points the opposite way to L5.** A live tension, not a settled question | **Unverified** |
| **L7** | *"A review of TRIZ, and its benefits and challenges in practice"*, ScienceDirect (S0166497212001356) <!-- redaction-guard: allow - publisher article identifier, not an account number --> | TRIZ spread to 35+ countries; practical issues make application challenging | Tempers TRIZ claims | **Unverified** |
| **L8** | ASEE PEER, *"The effectiveness of TRIZ from the perspective of comprehensive benefits of technological innovation"* | **300+ engineers surveyed**, regression analysis; stronger economic and IP benefits than social | Empirical TRIZ evidence | **Unverified** |

**L5 and L6 disagree.** That disagreement is itself the useful finding: whether
AI involvement in goal-setting helps or harms is contested. **Design against the
harm and take the benefit only where it does not require authorship** — which is
exactly GOALKEEPER's hard rule.

**What I could not do:** supply the empirical scholarly base you asked for. The
network in this session does not permit retrieval, and five honestly labelled
candidates beat twenty citations I cannot stand behind.
