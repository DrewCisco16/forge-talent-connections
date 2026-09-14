# THE 29 AGENTS AND 2 PROTOCOLS

Every agent, its name, what it does, and its status. One line each.
Full contract for any of them: [`cards/<name>.md`](cards/).

**Legend** — Tier **A** acts alone · **B** decision-ready artifact, ≤60s review ·
**C** evidence only, you decide. Status: 🟢 gated & live · ⚪ specified, ready ·
🔵 specified, needs building · ⛔ blocked.

---

## Control and assurance — 8

These do not widen the risk surface. They detect on it. One of them covers all
fourteen production agents at once.

| # | Agent | What it does | Tier | Status |
|---|---|---|---|---|
| 1 | **ROUTER** | Decides which of the four cost tiers answers a question, dispatches it, logs the choice. Defaults *down*, never answers. Holds the usage budget that reserves 40% of your daily allowance for your own work | A | ⚪ |
| 2 | **REVIEWER** | Reads a diff as a hostile reviewer expecting it to be wrong. Reports concrete failure scenarios. Never edits — a checker that fixes acquires an interest in being right | B | ⚪ |
| 3 | **ATTESTOR** | Verifies that work an agent *claims* it did produced a real artifact with a plausible timestamp. A claim without an artifact is void | A | 🔵 |
| 4 | **CANARY** | Monthly: golden sets, a **seeded defect**, and an injection corpus. The seeded defect is the only thing that detects a reviewer gone blind — because a blind reviewer reports clean | B | 🔵 |
| 5 | **REDACTOR** | Blocks any commit carrying phone numbers, account or order identifiers, SSNs, payment cards, private keys, six vendor key shapes, inline credentials, or CUI/FOUO markings | <!-- redaction-guard: allow - policy text naming the markings --> A | 🟢 |
| 6 | **GOALKEEPER** | Holds the goal ledger. Every goal has an owner and one next action; every agent traces to a goal. Emits the daily / weekly / monthly / quarterly / annual line. **Never authors a goal** | B | 🔵 |
| 7 | **STEWARD** | Weekly, per lane: approval rate, **review minutes**, material errors, cost and usage drawn, cost per resolved-correct. Reads transcripts, never run statuses | B | ⚪ |
| 8 | **SENTINEL** | Watches every dated obligation — response deadlines, **patent bar dates**, committee dates, IRB expiry, key rotation, schedule expiries, the 2026-12-08 rate re-check. Metadata only, never content | B | ⚪ |

## Production — 14

Each of these imports the same four shared failure modes: false claim, label
drift, invented number, injection. That is why the count above matters.

| # | Agent | What it does | Tier | Status |
|---|---|---|---|---|
| 9 | **BRIEFER** | **Start here.** One sanitized question + up to three approved public sources → a one-page brief with an evidence ledger and named uncertainties. 25 minutes, $0, no counsel gate | B | ⚪ |
| 10 | **MAILROOM** ×5 | One instance per mailbox. Classifies every unread thread, drafts replies into the drafts folder, produces a ≤90-second digest. **Has no send tool and never will** | C→B | ⚪ |
| 11 | **SCOUT** | Nightly sweep of federal opportunity sources through seven eligibility gates. Returns only what clears. **An empty queue is a good night.** No Pwin, ever | B | ⚪ |
| 12 | **CAPTURE** | One opportunity at a time: incumbent, award history, competitors, teaming — **leading with the strongest case for NO-BID** | C | ⛔ counsel |
| 13 | **MATRIX** | Parses a solicitation into a requirement matrix with page/¶ provenance. Deterministic extraction first; model-invented rows isolated on a MODEL-ONLY sheet, never merged | B | ⛔ counsel |
| 14 | **LIBRARIAN** | Weekly literature sweep for the dissertation. Every item DOI-resolved and matched to the record it claims to be. **Fails closed: discarded, never caveated** | B | ⚪ |
| 15 | **TRACKER** | Keeps one live register of dissertation questions: open, supported, contradicted, abandoned — and **what would close each open one** | B | ⚪ |
| 16 | **PRIORART** | Invention disclosure → prior-art packet for counsel. **No patentability opinion, no probability, no public disclosure.** States its coverage gaps | C | ⚪ |
| 17 | **BUILDER** | A specified issue → a **draft** PR with tests. Never merges. Never weakens a test to reach green. Asks rather than guesses on an underspecified issue | B | ⚪ |
| 18 | **SYNTH-QA** | Exercises the talent application's flows against **synthetic** fixtures across the device fleet. No real candidate records, ever | B | ⚪ |
| 19 | **DILIGENCE** | One personal or capital decision → primary-source evidence from .gov sources only, plus **what nobody knows** and the strongest case against. Never recommends, never estimates, never touches an account | C | ⚪ |
| 20 | **HARVESTER** | After every run, files what is reusable into that lane's library — past-performance narratives, response patterns, verified citations, killed claims and what killed them. **The compounding agent** | B | ⚪ |
| 21 | **ORCHESTRATOR** | Drives the five-window elimination swarm: four thinkers and a closer, the wall at round 1, gates before the merge. **Not the pilot** — your Playbook caps the pilot at two services | B | ⚪ |
| 22 | **NIGHTWATCH** | The paid five-seat panel. Manual, typed `SPEND`, cost-ceilinged. **Demoted to a calibration instrument** by your own Stage 0 finding | C | ⛔ seat 3 |

## Infrastructure — 2

| # | Agent | What it does | Tier | Status |
|---|---|---|---|---|
| 23 | **PARKING** | Captures an idea that is not today's mission in one line and does nothing else with it. Also writes the resume note on every stop | A | ⚪ |
| 24 | **OPTIMIZER** | Runs a bounded improvement loop: one change, re-run the fixed evaluation, keep or revert. **Pilot mode: 3 variants, 60 minutes, $0, supervised** | B | ⚪ |

## IP prosecution — 5  *(new; the lane had only PRIORART, which searches)*

**Every one of these holds the same boundary: never drafts or amends a claim,
never opines on patentability, never emits a probability, never decides
materiality, never contacts the USPTO, never touches a public repository.**

| # | Agent | What it does | Tier | Status |
|---|---|---|---|---|
| 25 | **ELIGIBILITY-SCOUT** | Flags §101 risk in draft claims — result-language without a mechanism, reads-on-a-human, organising human activity on a generic computer. **The dominant risk for an AI talent application** | C | 🔵 |
| 26 | **SPEC-WARDEN** | Mechanical §112 gate: every claim term supported in the spec, every "the X" with an antecedent, every functional element with a disclosed algorithm. **The fully self-inflicted rejection class** | B | 🔵 |
| 27 | **ART-DELTA** | Element-by-element matrix of each claim against the closest art; names the one element no reference discloses — and writes the likeliest §103 combination **against** you | C | 🔵 |
| 28 | **IDS-WARDEN** | Dated inventory for the duty of candor, including negative search results. **Escalates immediately on any public activity older than 12 months** — a statutory bar | C | 🔵 |
| 29 | **INTERVIEW-PREP** | Builds the examiner-interview agenda: the rejection quoted verbatim, where the examiner is right, the distinction, the fallback. **Leaves `[COUNSEL DRAFTS]` for every amendment** | B | 🔵 |

## Protocols — 2  *(these are not agents; nothing performs them for you)*

| Protocol | What it is | Card |
|---|---|---|
| **BASELINE** | Fourteen unmodified days of your own time across five categories. **No agent can do this part** — its own card said so, which is what exposed the category error | [baseline](cards/baseline.md) |
| **SMOKE** | A five-line checklist proving a browser route hits the right host, profile and page — and that Stop works — before it is trusted | [smoke](cards/smoke.md) |

**Why the reclassification matters:** an agent card implies something will do it
for you. Nothing will. Calling these agents inflated the count and, worse,
quietly deferred the two things only you can do.

---

## Deploy in this order

```
TODAY      FILL THE GOAL LEDGER (20 min, you)  <- highest-value act available
           BASELINE protocol (you, 14 days)  +  BRIEFER (one run, 25 min, $0)
THEN       GOALKEEPER -> SMOKE protocol -> MAILROOM -> ROUTER -> SENTINEL -> PARKING
BUILD      ATTESTOR and CANARY   <- the two open detection gaps
WEEK 3+    LIBRARIAN · TRACKER · BUILDER + REVIEWER (same day, never apart)
WEEK 5+    SCOUT (public only) · HARVESTER · STEWARD
BLOCKED    MATRIX · CAPTURE (counsel)   ·   NIGHTWATCH (seat 3 id)
LATER      SYNTH-QA · DILIGENCE · PRIORART · ORCHESTRATOR · OPTIMIZER
```

**One at a time. Measure for a week. Then the next.** Twenty-five cards exist so
each deployment is fast — not so twenty-five agents run at once
([`20-fmea-fta-fmeda.md`](20-fmea-fta-fmeda.md) §4, FM-27).

## What no agent on this list will ever do

```
send an email to a counterparty    submit anything to a Government portal
file with USPTO                    publish or disclose an unfiled invention
merge to main                      deploy to production
move money or authorize payment    sign or agree to terms
represent size or eligibility      delete data
```
