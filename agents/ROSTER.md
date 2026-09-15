# THE 32 AGENTS AND 2 PROTOCOLS

Every agent, its name, what it does, **its one goal**, and its status. One entry
each. Full contract for any of them: [`cards/<name>.md`](cards/).

**Legend** — Tier **A** acts alone · **B** decision-ready artifact, ≤60s review ·
**C** evidence only, you decide. Status: 🟢 gated & live · ⚪ specified, ready ·
🔵 specified, needs building · ⛔ blocked.

**Goals.** Each card carries exactly one goal and one measure, and each rolls up
to one of four outcomes:

```
A  time returned            B  nothing irreversible goes wrong
C  no goal stalls unseen    D  work compounds
```

The four roll up to **one goal above them that is not written** — it is yours to
write, and no agent may author it. Full three-level map:
[`analysis/goal-ladder.md`](analysis/goal-ladder.md). The gate that keeps every
card connected to an outcome: `python3 scripts/goal_ladder.py`.

---

## Control and assurance — 8

These do not widen the risk surface. They detect on it. One of them covers all
fourteen production agents at once.

| # | Agent | What it does | Tier | Status |
|---|---|---|---|---|
| 1 | **ROUTER** | Decides which of the four cost tiers answers a question, dispatches it, logs the choice. Defaults *down*, never answers. Holds the usage budget that reserves 40% of your daily allowance for your own work <br> **Goal:** Every question is answered at the cheapest tier that can answer it, and agents never spend the headroom Andrew needs for his own work. *(→ A)* | A | ⚪ |
| 2 | **REVIEWER** | Reads a diff as a hostile reviewer expecting it to be wrong. Reports concrete failure scenarios. Never edits — a checker that fixes acquires an interest in being right <br> **Goal:** No agent-authored change reaches Andrew unreviewed. *(→ B)* | B | ⚪ |
| 3 | **ATTESTOR** | Verifies that work an agent *claims* it did produced a real artifact with a plausible timestamp. A claim without an artifact is void <br> **Goal:** No claim of completed work enters the record without an artifact behind it. *(→ B)* | A | 🔵 |
| 4 | **CANARY** | Monthly: golden sets, a **seeded defect**, and an injection corpus. The seeded defect is the only thing that detects a reviewer gone blind — because a blind reviewer reports clean <br> **Goal:** Catch an agent going bad within one month of it starting. *(→ B)* | B | 🔵 |
| 5 | **REDACTOR** | Blocks any commit carrying phone numbers, account or order identifiers, SSNs, payment cards, private keys, six vendor key shapes, inline credentials, or CUI/FOUO markings <br> **Goal:** Nothing that must never be published reaches this public repository. *(→ B)* | <!-- redaction-guard: allow - policy text naming the markings --> A | 🟢 |
| 6 | **GOALKEEPER** | Holds the goal ledger. Every goal has an owner and one next action; every agent traces to a goal. Emits the daily / weekly / monthly / quarterly / annual line. **Never authors a goal** <br> **Goal:** No goal goes unowned and no agent runs without a goal. *(→ C)* | B | 🔵 |
| 7 | **STEWARD** | Weekly, per lane: approval rate, **review minutes**, material errors, cost and usage drawn, cost per resolved-correct. Reads transcripts, never run statuses <br> **Goal:** Andrew's review minutes fall, week over week. *(→ A)* | B | ⚪ |
| 8 | **SENTINEL** | Watches every dated obligation — response deadlines, **patent bar dates**, committee dates, IRB expiry, key rotation, schedule expiries, the 2026-12-08 rate re-check. Metadata only, never content <br> **Goal:** No dated obligation is ever missed. *(→ B)* | B | ⚪ |

## Production — 14

Each of these imports the same four shared failure modes: false claim, label
drift, invented number, injection. That is why the count above matters.

| # | Agent | What it does | Tier | Status |
|---|---|---|---|---|
| 9 | **BRIEFER** | **Start here.** One sanitized question + up to three approved public sources → a one-page brief with an evidence ledger and named uncertainties. 25 minutes, $0, no counsel gate <br> **Goal:** Replace one research session a week that Andrew would otherwise run himself. *(→ A)* | B | ⚪ |
| 10 | **MAILROOM** ×5 | One instance per mailbox. Classifies every unread thread, drafts replies into the drafts folder, produces a ≤90-second digest. **Has no send tool and never will** <br> **Goal:** Remove the DECIDING from the inbox, not the typing. *(→ A)* | C→B | ⚪ |
| 11 | **SCOUT** | Nightly sweep of federal opportunity sources through seven eligibility gates. Returns only what clears. **An empty queue is a good night.** No Pwin, ever <br> **Goal:** Andrew never learns about a fitting opportunity too late, and never reads about one he cannot bid. *(→ A)* | B | ⚪ |
| 12 | **CAPTURE** | One opportunity at a time: incumbent, award history, competitors, teaming — **leading with the strongest case for NO-BID** <br> **Goal:** No bid proceeds without the case against it having been made at full strength. *(→ B)* | C | ⛔ counsel |
| 13 | **MATRIX** | Parses a solicitation into a requirement matrix with page/¶ provenance. Deterministic extraction first; model-invented rows isolated on a MODEL-ONLY sheet, never merged <br> **Goal:** Zero proposals rejected for non-compliance. *(→ B)* | B | ⛔ counsel |
| 14 | **LIBRARIAN** | Weekly literature sweep for the dissertation. Every item DOI-resolved and matched to the record it claims to be. **Fails closed: discarded, never caveated** <br> **Goal:** No unverified source ever reaches the dissertation. *(→ B)* | B | ⚪ |
| 15 | **TRACKER** | Keeps one live register of dissertation questions: open, supported, contradicted, abandoned — and **what would close each open one** <br> **Goal:** No research question is silently abandoned. *(→ C)* | B | ⚪ |
| 16 | **PRIORART** | Invention disclosure → prior-art packet for counsel. **No patentability opinion, no probability, no public disclosure.** States its coverage gaps <br> **Goal:** Counsel never starts from zero, and never from a search whose gaps are hidden. *(→ B)* | C | ⚪ |
| 17 | **BUILDER** | A specified issue → a **draft** PR with tests. Never merges. Never weakens a test to reach green. Asks rather than guesses on an underspecified issue <br> **Goal:** Andrew stops writing the mechanical 80% of the talent application. *(→ A)* | B | ⚪ |
| 18 | **SYNTH-QA** | Exercises the talent application's flows against **synthetic** fixtures across the device fleet. No real candidate records, ever <br> **Goal:** No user finds a defect that a synthetic fixture could have found first. *(→ B)* | B | ⚪ |
| 19 | **DILIGENCE** | One personal or capital decision → primary-source evidence from .gov sources only, plus **what nobody knows** and the strongest case against. Never recommends, never estimates, never touches an account <br> **Goal:** No capital or family decision is made on a number nobody computed. *(→ B)* | C | ⚪ |
| 20 | **HARVESTER** | After every run, files what is reusable into that lane's library — past-performance narratives, response patterns, verified citations, killed claims and what killed them. **The compounding agent** <br> **Goal:** The next proposal starts from a library, not a blank page. *(→ D)* | B | ⚪ |
| 21 | **ORCHESTRATOR** | Drives the five-window elimination swarm: four thinkers and a closer, the wall at round 1, gates before the merge. **Not the pilot** — your Playbook caps the pilot at two services <br> **Goal:** Where one model is not enough, produce real divergence instead of false agreement. *(→ B)* | B | ⚪ |
| 22 | **NIGHTWATCH** | The paid five-seat panel. Manual, typed `SPEND`, cost-ceilinged. **Demoted to a calibration instrument** by your own Stage 0 finding <br> **Goal:** Tell Andrew whether his five seats are actually independent - and retire itself if they are not. *(→ B)* | C | ⛔ seat 3 |

## Infrastructure — 2

| # | Agent | What it does | Tier | Status |
|---|---|---|---|---|
| 23 | **PARKING** | Captures an idea that is not today's mission in one line and does nothing else with it. Also writes the resume note on every stop <br> **Goal:** No second front is ever opened on a day that already has one. *(→ C)* | A | ⚪ |
| 24 | **OPTIMIZER** | Runs a bounded improvement loop: one change, re-run the fixed evaluation, keep or revert. **Pilot mode: 3 variants, 60 minutes, $0, supervised** <br> **Goal:** Only measured improvements are kept. Noise is never banked. *(→ D)* | B | ⚪ |

## IP prosecution — 5  *(new; the lane had only PRIORART, which searches)*

**Every one of these holds the same boundary: never drafts or amends a claim,
never opines on patentability, never emits a probability, never decides
materiality, never contacts the USPTO, never touches a public repository.**

| # | Agent | What it does | Tier | Status |
|---|---|---|---|---|
| 25 | **ELIGIBILITY-SCOUT** | Flags §101 risk in draft claims — result-language without a mechanism, reads-on-a-human, organising human activity on a generic computer. **The dominant risk for an AI talent application** <br> **Goal:** Zero section 101 rejections that a pre-filing pattern check would have caught. *(→ B)* | C | 🔵 |
| 26 | **SPEC-WARDEN** | Mechanical §112 gate: every claim term supported in the spec, every "the X" with an antecedent, every functional element with a disclosed algorithm. **The fully self-inflicted rejection class** <br> **Goal:** Zero section 112 rejections. This class is entirely self-inflicted, so the target is zero. *(→ B)* | B | 🔵 |
| 27 | **ART-DELTA** | Element-by-element matrix of each claim against the closest art; names the one element no reference discloses — and writes the likeliest §103 combination **against** you <br> **Goal:** Every independent claim has a written delta before it is filed, and the section 103 case against it is already on paper. *(→ B)* | C | 🔵 |
| 28 | **IDS-WARDEN** | Dated inventory for the duty of candor, including negative search results. **Escalates immediately on any public activity older than 12 months** — a statutory bar <br> **Goal:** Zero statutory bars and zero candor surprises. *(→ B)* | C | 🔵 |
| 29 | **INTERVIEW-PREP** | Builds the examiner-interview agenda: the rejection quoted verbatim, where the examiner is right, the distinction, the fallback. **Leaves `[COUNSEL DRAFTS]` for every amendment** <br> **Goal:** Every office action gets an interview agenda before a response is drafted. *(→ A)* | B | 🔵 |

## Summit-serving — 3  *(new 2026-09-15; added when the Level 0 goal was written)*

**The ultimate goal was written on 2026-09-15 and it is three goals in one
sentence** — net worth, deployment, and the means. The roster served the first
only indirectly and the second not at all. These three close that gap. They do
**not** close the seam: no agent produces a billion dollars, and none of these
claims to ([`analysis/goal-ladder.md`](analysis/goal-ladder.md)).

| # | Agent | What it does | Tier | Status |
|---|---|---|---|---|
| 30 | **ASSET-LINE** | Classifies every recorded hour as building an owned asset or renting out time, and reports the ratio weekly. Carries the arithmetic showing earned income cannot reach the target — **$500k/yr at 7% for 30 years is ~$47M, about 2%** <br> **Goal:** Make the asset-versus-time split of Andrew's week a number he sees weekly, instead of an impression he forms yearly. *(→ D)* | B | 🔵 |
| 31 | **CAPTABLE** | Extracts every term that moves Andrew's ownership fraction from any document that creates, transfers or dilutes equity — **before signature, never after**. Never redlines, never opines on whether a term is market <br> **Goal:** No equity leaves Andrew's hands on terms nobody read. *(→ B)* | C | ⛔ counsel |
| 32 | **FIRSTFRUITS** | Records giving as a stated percentage every period, from the first dollar. **A period with no giving is recorded as 0%, never left blank.** Never moves money, never names a target percentage <br> **Goal:** Giving is measured from the first dollar, not deferred to the billionth. *(→ C)* | C | 🔵 |

**Why only three.** The gap was named precisely — nothing served *philanthropist*,
nothing protected the ownership fraction `f`, nothing made the asset-versus-hours
split visible. Three cards close those three holes. **Adding more would be
answering a question nobody asked**, and outcome D stays thin for a reason that
cards cannot fix: compounding happens on the far side of the seam.

## Protocols — 2  *(these are not agents; nothing performs them for you)*

| Protocol | What it is | Card |
|---|---|---|
| **BASELINE** | Fourteen unmodified days of your own time across five categories. **No agent can do this part** — its own card said so, which is what exposed the category error <br> **Goal:** Give day 90 an answer instead of an impression. *(→ C)* | [baseline](cards/baseline.md) |
| **SMOKE** | A five-line checklist proving a browser route hits the right host, profile and page — and that Stop works — before it is trusted <br> **Goal:** No route is trusted before it is tested. *(→ B)* | [smoke](cards/smoke.md) |

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

**One at a time. Measure for a week. Then the next.** Twenty-nine agent cards exist so
each deployment is fast — not so twenty-nine agents run at once
([`20-fmea-fta-fmeda.md`](20-fmea-fta-fmeda.md) §4, FM-27).

## What no agent on this list will ever do

```
send an email to a counterparty    submit anything to a Government portal
file with USPTO                    publish or disclose an unfiled invention
merge to main                      deploy to production
move money or authorize payment    sign or agree to terms
represent size or eligibility      delete data
```
