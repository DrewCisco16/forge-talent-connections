# 24 — CRITICAL SYSTEMS THINKING · NINE WINDOWS · SMART EXECUTION

**Deliberately short.** The analysis is two pages; the plan is
[`../EXECUTE.md`](../EXECUTE.md). That ratio is the finding, not a stylistic
choice — six prior documents inverted it and the gates stayed at zero.

---

## PART 1 — CRITICAL SYSTEMS THINKING

CST's distinctive move is **boundary critique**: not *is the system working*, but
**where was the boundary drawn, by whom, and who is outside it.** Applied here it
produces three findings the previous six analyses could not, because each of
those accepted the boundary rather than questioning it.

### 1.1 The boundary was drawn in the wrong place

```
DRAWN AROUND:     the agent system  - 29 agents, 4 gates, 46 failure modes
SHOULD BE AROUND: Andrew's week     - the thing that was supposed to change
```

Every metric built so far measures the **inside** of that boundary: coverage,
diagnostic coverage, rung distribution, escaped defects. **Not one measures the
week.** A system can score well on every internal measure while the thing it was
built to change is untouched — and that is the current state exactly.

**Consequence:** the review-minutes number and BASELINE are not "nice to have."
They are the only two instruments that cross the boundary.

### 1.2 Who is affected but not involved

CST asks who bears consequences without a voice in the design. Honestly:

| Affected | Involved? | Consequence already borne |
|---|---|---|
| **Four third parties** whose phone numbers and devices I published | **No** | **Real. Already happened.** Their data was on a public repo |
| **Andrew's family** | No | The HOME lane was designed *about* them, never *with* them |
| **His team / 1099 counterparties** | No | J4V terms still unread; their data would flow through tooling they never agreed to |
| **His dissertation committee** | No | FIU's AI-use rules still unchecked — `FM-06`, RPN 450 |

**Three of four are unresolved, and all three are on the human-act list.**

### 1.3 The expert has been setting the agenda

The sharpest CST finding, and it is about me.

```
CLIENT       Andrew
DECISION-MAKER  Andrew
EXPERT       Claude
AGENDA-SETTER   ... Claude, for seven consecutive rounds
```

I have produced every framework, chosen every metric, and named every failure
mode. **Andrew's own goals — the stated purpose — have never entered the
system.** In CST terms that is a boundary judgement failure by the expert, not a
design flaw in the artifact.

**The correction is structural and already built:** GOALKEEPER **never authors a
goal**, and the ledger is Andrew-written by rule. This document changes nothing
about that; it names why the rule exists.

---

## PART 2 — TRIZ NINE WINDOWS

v6 used contradiction analysis and trimming. **Nine Windows is a different tool**
— system level × time — and it produces something the others did not.

| | **PAST** | **PRESENT** | **FUTURE** |
|---|---|---|---|
| **SUPERSYSTEM**<br>*the enterprise, family, 10-yr horizon* | Five lanes, DBA in progress, stewardship frame | **Unchanged.** Same lanes, same goals, same week | Depends entirely on the gates — not on the system layer |
| **SYSTEM**<br>*the agent workforce* | Did not exist | **29 agents, 46 failure modes, 4 gates, 0 running** | Either earns its place or is cut on 2026-10-14 |
| **SUBSYSTEM**<br>*gates, scripts, cards* | `adjudication/` engine, already sound | **4 scripts, 68 self-tests, all passing** | Stable; not the constraint |

### What the grid shows

> **All growth is in the middle row. The top row has not moved, and the bottom
> row was already fine.**

The subsystem is healthy. The supersystem is unchanged. **The system layer has
expanded enormously while connecting to neither.** That is the signature of a
component optimised in isolation — and Nine Windows makes it visible in a way the
failure register could not, because the register only ever looked at one row.

**The future column is the operative one:** the supersystem's future is *not* a
function of how good the system layer gets. It is a function of two binary gates.

---

## PART 3 — THE COUNT

| Question | Answer |
|---|---|
| **Are these the best agents?** | Control set: sound, and now well covered. Production set: **still unproven — zero have run.** Unchanged across seven analyses |
| **Too many?** | **The question is now formally irrelevant.** With `X1·X3 = 0`, 29 agents and 0 agents produce identical results |
| **Too few?** | **No.** No agent was added this pass and none was needed. The gap is two zeros |
| **Add a thirtieth?** | **No.** It would multiply zero |
| **Will the goals be accomplished?** | **Still unanswerable** — `Y` has no numerator and no denominator until the ledger has entries |

**No agent added. No agent removed. The roster stands at 29 + 2 protocols.**

---

## PART 4 — SMART EXECUTION

Full plan: [`../EXECUTE.md`](../EXECUTE.md). Summary against the SMART test:

| | |
|---|---|
| **S**pecific | Three goals in a named file; a six-line review block; one BRIEFER run. Worked examples pre-written so only substitution remains |
| **M**easurable | `python3 scripts/goal_throughput.py` — the gate closes or it does not. Binary, observable, no judgement |
| **A**chievable | 20 + 10 + 25 minutes. Nothing requires counsel, a purchase, or a build |
| **R**elevant | Closes `X1` and `X3`, the only two inputs that multiply the whole function |
| **T**ime-bound | Blocks 1–2 before **2026-10-14** — the kill date already in `19` §3 |

### The four human acts, none delegable

```
1  FIU AI-use policy          10 min   FM-06, RPN 450, unrecoverable
2  Open one Pages URL         30 sec   FM-31, RPN 384
3  Private repo for disclosures 5 min  FM-04, order-1, patent rights
4  Read the J4V 1099 terms    15 min   FM-21, order-1
```

---

## PART 5 — LITERATURE

**Re-tested this session: Google Scholar, Crossref and OpenAlex all returned
HTTP 000.** Unreachable, as in every prior round. **No new citation is added and
none of the existing queue has been verified.**

The queue now holds **nineteen candidates** across `20`, `21`, `22` and `23`,
every one labelled `Unverified`, with the peer-review status of each noted where
it is known. **Verifying that queue is itself a task with an owner — and it is
not blocking anything in `EXECUTE.md`.**

**Stated plainly, because it has now been asked seven times:** I cannot supply
verified scholarly articles from this session, and I will not generate a
reference list I cannot stand behind. That has not changed and will not change
by being asked again.

---

## PART 6 — THE STOP RULE

> Seven framework families — inversion, FMEA/FTA/FMEDA, critical thinking, TRIZ
> (twice, two different tools), Zero Defects, DMADV, IDOV, CST, Nine Windows —
> have now returned **the same answer**.
>
> **An eighth will return it again.** The analysis has not been the bottleneck
> for some time.

**Do not commission another framework until Blocks 1 and 2 of
[`../EXECUTE.md`](../EXECUTE.md) are done.** Roughly thirty minutes stands
between `Y = 0` and `Y` being a real number for the first time.
