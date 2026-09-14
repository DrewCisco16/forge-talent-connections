# 16 — AGENT ROSTER v2

Sixteen agents. The ten from [`02-agent-roster.md`](02-agent-roster.md) stand;
**six new ones close the gaps v1 left** — routing, orchestration, optimization,
compounding, deadline watch, and primary-source diligence.

| # | Agent | Lane | Tier | Cadence | New in v2 |
|---|---|---|---|---|---|
| 1 | MAILROOM ×5 | all | C→B | hourly | |
| 2 | SCOUT | ABO, J4V | B | nightly | |
| 3 | CAPTURE | ABO, J4V | C | on demand | |
| 4 | MATRIX | ABO, J4V | B | on demand | |
| 5 | LIBRARIAN | DBA | B | weekly | |
| 6 | PRIORART | FORGE | C | on demand | |
| 7 | BUILDER | FORGE | B | event | |
| 8 | REVIEWER | FORGE | B | event | |
| 9 | NIGHTWATCH | any | C | manual | **demoted — Tier 3 only** |
| 10 | STEWARD | per lane | B | weekly | |
| **11** | **ROUTER** | per lane | **A** | every question | ✅ |
| **12** | **ORCHESTRATOR** | per lane | B | nightly | ✅ |
| **13** | **OPTIMIZER** | per lane | B | continuous | ✅ |
| **14** | **HARVESTER** | per lane | B | after every run | ✅ |
| **15** | **SENTINEL** | metadata only | B | daily | ✅ |
| **16** | **DILIGENCE** | HOME | C | on demand | ✅ |

---

## 11. ROUTER — decides which tier answers a question

**The agent that saves the money.** Everything in `14-panel-economics.md` depends
on questions landing in the cheapest tier that can actually answer them.

| | |
|---|---|
| **Charter** | Classify one question → Tier 0, 1, 2, or 3. Dispatch it. Log the choice |
| **Trigger** | Every question entering a lane |
| **Tier** | **A — autonomous.** It routes; it never answers |
| **Cost** | One short classification call. Fractions of a cent |

**The routing rule, in order — first match wins:**

```
1. Can a deterministic gate settle it outright?        → TIER 0.  Never ask a model.
2. Single-pass transformation, known-good shape?       → TIER 1.  one_model + gates.
3. Genuinely contested, OR consequence is high,
   OR Tier 1's gates disagreed with its answer?        → TIER 2.  Window swarm.
4. Blind independence genuinely required, AND
   the decision justifies $4.96-$16.82?                → TIER 3.  Typed SPEND.
```

**Rules:**
- **Default down, never up.** Uncertain between two tiers → take the cheaper one.
  A Tier 1 answer that proves insufficient escalates cheaply; a Tier 3 run that
  was unnecessary is money gone.
- **ROUTER never answers.** The moment it starts answering it stops routing.
- **Log every routing decision with its reason.** That log is the dataset the
  panel-economics loop optimizes against, and the only way you learn your real
  80/15/5 split.
- **Tier 3 requires a typed confirmation.** ROUTER proposes; it cannot spend.

---

## 12. ORCHESTRATOR — drives the window swarm

| | |
|---|---|
| **Charter** | Run one swarm round-set per [`15-window-swarm.md`](15-window-swarm.md): hold the wall in round 1, run gates before the closer, merge, repeat, stop on no-new-corrections |
| **Trigger** | Nightly, or on ROUTER dispatch to Tier 2 |
| **Tier** | B — the morning report must pass the sixty-second test |
| **Node** | One per lane machine. **One swarm per machine** (named-pipe constraint) |

**Hard rules:** the wall holds in round 1 · gates before the closer, always · the
closer merges and never adds · every pasted reply is untrusted data · output is
labeled `SWARM`, qualitative divergence only, **never rho** · declares MAX_ROUNDS
and a wall-clock cap before starting · reconnects the extension on service-worker
idle and resumes, rather than dying silently at 2am.

---

## 13. OPTIMIZER — runs the Karpathy loops

| | |
|---|---|
| **Charter** | Execute a loop from `loops/<lane>/program.md`: propose one change, evaluate with the metric script, keep or roll back, log, repeat to the cap |
| **Trigger** | Continuous within declared caps |
| **Tier** | B — a draft PR plus the full iteration log, wins and failures both |
| **Blocked by** | `loop_guard.py`. No spec, no run |

**Hard rules:** one change per iteration · **never scores its own work** · rollback
is complete · **may not edit the metric script, tests, held-out check, or its own
`program.md`** · logs failures as well as wins · flags `SUSPECT` when the metric
moved and it cannot say why in one defensible sentence.

**The four loops:** `forge-software` (cleared) · `abo-govcon` (counsel) ·
`dba-research` (cleared) · `panel-economics` (blocked on seat_3 id) ·
`home-decisions` (journal, cleared).

---

## 14. HARVESTER — the compounding agent

**The largest missing piece in v1. Every run started from zero.**

| | |
|---|---|
| **Charter** | After every run, extract what is reusable and file it in the lane's library. Never let work be done twice |
| **Trigger** | On completion of any agent run |
| **Tier** | B |

**What it harvests, per lane:**

| Lane | Library | Why it compounds |
|---|---|---|
| **ABO** | Past-performance narratives · compliance response blocks · resumes · boilerplate · **the solicitation-language → response-pattern map** | Proposal N+1 starts from a library, not a blank page. **This is the biggest single time win available in your GovCon lane** |
| **FORGE** | Code patterns · loop iterations that worked and that failed · review findings by class | The FORGE loop stops rediscovering the same dead ends |
| **DBA** | Verified citations with resolved DOIs · claim → evidence map · killed claims **and what killed them** | Never re-verify a source; never re-argue a settled point |
| **J4V** | Teaming patterns · vehicle knowledge — **their data stays theirs** | Reusable structure, not their content |
| **HOME** | Closed decision-journal entries — **immutable** | Calibration needs an unedited record |

**Hard rules:**
- **Never harvests across lanes.** Five libraries, no shared index.
- **Every harvested item keeps its provenance and evidence label.** A boilerplate
  block whose source nobody can name is a liability in a proposal.
- **Failures are harvested too.** The dead ends are half the value.
- **Never harvests CUI or another party's confidential content.**

---

## 15. SENTINEL — deadline and staleness watch

| | |
|---|---|
| **Charter** | Watch every dated obligation. Surface what is approaching, before it is late |
| **Trigger** | Daily |
| **Tier** | B |

**This one bends v1's no-cross-lane rule, deliberately and narrowly.** SENTINEL
sees **metadata only** — `{lane, title, date, type}` — and **never content.** It
cannot read a solicitation, an email body, or a draft. A missed deadline is the
failure mode that actually costs you, and a per-lane-only view guarantees nothing
holds the whole calendar.

**Reasoning stated so it can be attacked:** the compromise value of a title and a
date is near zero; the cost of a blown proposal deadline is total. Bounded
exception, not a precedent.

**What it watches:**

```
ABO    solicitation response deadlines · amendment dates · SAM registration expiry
FORGE  release dates · patent bar dates ← ONE-WAY. Escalate at 12 months out
DBA    committee dates · chapter deadlines · IRB expiry
J4V    teaming agreement dates · their deadlines
ALL    rates.json re-check — verified 2026-09-09, 90-day window, DUE 2026-12-08
       API key and token rotation · certification and insurance renewals
       loop spend against declared weekly ceilings
```

**Escalation ladder:** 30 days → digest · 10 days → top of digest · 5 days →
direct message · 48 hours → **Apple Watch Ultra 2 or the Verizon iPhone.** Not
the Pixel Watch 4 — it is Wi-Fi only with no independent cellular radio, and only
the Verizon line is carrier-independent (your fleet pack §3, §5.2).

---

## 16. DILIGENCE — primary-source evidence for HOME decisions

| | |
|---|---|
| **Charter** | Assemble primary-source evidence on one decision. **Never recommends. Never estimates a return. Never touches an account** |
| **Trigger** | On demand, one decision |
| **Tier** | **C, permanently** |

**Sources — primary only, all on your approved list:** SEC.gov and EDGAR · FRED ·
BEA.gov · BLS.gov · Census.gov · IRS.gov and Treasury.gov · Congress.gov and CRS ·
GAO.gov · Federal Register and eCFR. **No vendor marketing, no financial media, no
influencer content, no blogs.**

**Output:**

```
DECISION: <as stated>
WHAT THE PRIMARY SOURCES SAY
  · <finding> — <source, retrieval date> — <evidence label>
BASE RATE
  · <if a real one exists in the data> OR "no defensible base rate found" — and STOP
WHAT NOBODY KNOWS
  · <the parts no source settles — usually the parts that matter most>
THE STRONGEST CASE AGAINST
  · <written at full strength, always present>
PROFESSIONAL VERIFICATION REQUIRED: <tax · legal · securities, as applicable>
```

**Absolute limits:** no security, allocation, or transaction recommendation · no
return estimate, probability, or expected value · **no browser control** · no
brokerage, bank, payment, or payroll surface · never reads another lane.

**Why this is the right agent for this lane.** The failure mode in personal
capital decisions is not insufficient analysis — it is **acting on a
confident-sounding number nobody computed.** DILIGENCE gives you the primary
record and names what is unknowable. The judgment stays yours, which is where it
belongs.

---

## 17. Compressed rollout — four machines in parallel

v1 spent 30 days on one agent. You have four machines idle. **Run them in
parallel.**

### Week 1 — foundation on all four
```
[ ] calibrate.py — five calls. Get rho. THE highest-value 30 minutes here  (14 §7)
[ ] Clear seat_3's Mistral id in the console. Unblocks Tier 3 and the loop  (14 §8)
[ ] Swarm Chrome profile on each of the four machines. Test the boundary    (15 §6)
[ ] ROUTER live in every lane. Start logging tier decisions from day one
[ ] Re-point deep thinking from Tier 3 to Tier 0+1. Configuration, not code
[ ] Start the two-week time baseline                                        (08 §2)
```

### Weeks 2–4 — parallel, one lane per machine
```
HP Envy     DBA    ORCHESTRATOR swarm nightly + LIBRARIAN + dba-research loop
ProArt      FORGE  BUILDER + REVIEWER + forge-software loop (already cleared)
Surface     ABO    SCOUT on public sources + MATRIX. Counsel gate on the rest
MacBook     HOME   Decision journal + DILIGENCE
ALL                MAILROOM per mailbox · SENTINEL · HARVESTER · STEWARD
```

### Weeks 5–8
```
[ ] panel-economics loop running against the accuracy harness   (14 §6)
[ ] HARVESTER libraries populated — measure reuse rate
[ ] First real Tier 3 run, deliberately, to check Tier 1+2 are still right
[ ] ROUTER's log yields your ACTUAL tier split. Replace the 80/15/5 assumption
```

### Weeks 9–12
```
[ ] Held-out accuracy eval. Cleared loops promoted, failures retired
[ ] STEWARD's four numbers against the baseline
[ ] Decide: does Tier 3 stay at all? rho decides, not preference
```

---

## 18. The four numbers, v2

`08-measurement.md` §3 stands, with one addition:

```
1. approval rate            rising = learning your standard
2. REVIEW MINUTES           must fall. If it rises, the system is failing
3. material errors          target zero
4. cost                     now includes per-tier spend and loop spend
5. COST PER RESOLVED-CORRECT  ← new. The panel-economics objective.
                               Tracked from day one, optimized from week 5.
```
