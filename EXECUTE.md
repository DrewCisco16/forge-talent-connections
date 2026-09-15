# EXECUTE — the 30 minutes

**This is not analysis. It is a script to follow.** Everything below is
pre-written so the only work left is substitution and typing.

> **Why this file exists.** Seven analytical frameworks now agree on one thing:
> the constraint is not the design, the agent count, or the evidence base. It is
> that `X1` and `X3` are zero. This file closes them.

---

## ⏱ THE TIME RULE — what "ASAP" means here

Andrew set the time bound as **ASAP**. Implemented literally, that is not a time
bound — it is the removal of one, and it makes everything slower. Little's Law:
`WIP = throughput × cycle time`. At fixed throughput, marking everything ASAP
raises WIP, and cycle time rises proportionally. **Everything urgent finishes
later than one thing urgent.**

So ASAP is implemented as the three rules that actually produce speed:

```
1  WIP = 1.      Exactly one goal is MOVING. The rest are parked, not queued.
2  TODAY.        The next action starts today or it is not the next action.
3  HARD STOP.    Every block has an end time written before it starts.
                 At the stop, it stops -- finished or not.
```

**Rule 3 is the one that makes rule 2 survivable.** An open-ended "start today"
is what has kept this file unexecuted; a 20-minute block with a stop time is a
thing a person can actually begin. If the block ends unfinished, that is
information about the estimate, not a failure — record it and start the next one.

`Little's Law is a theorem, not a citation.` `Evidence label: Empirical Finding`
for the observation that this file has gone unexecuted across eight rounds — it
is observable in this repository's own history.

---

## BLOCK 1 — ✅ CLOSED 2026-09-15. `X1 = 1`.

> **Done.** Andrew wrote the Level 0 goal on 2026-09-15: *to become a Christian
> billionaire philanthropist, in U.S. dollars.* Recorded at `G-Y-01`. Verified:
> `python3 scripts/goal_throughput.py` reports `X1 = 1`.
>
> **`X3` is now the only open gate — go to Block 2.** The rest of this block is
> kept for the quarter, month and week rows, which are still empty.

**Open** `agents/analysis/goal-ledger.md`. **Replace** the empty rows.

**One goal closes the gate** — `goal_throughput.py` line 70 is
`x1 = 1 if goals else 0`. The year row is written. **The highest-value remaining
row is the QUARTER**, because a 10-year goal with no 90-day goal under it cannot
stall visibly: nothing is due soon enough to notice.

### The shape each must have

```
"<a thing> will be true by <a date>"     ← falsifiable, dated
NOT "improve X"  ·  NOT "grow Y"  ·  NOT "focus on Z"
```

### Worked examples — replace the content, keep the shape

These are **shapes, not suggestions.** The content must be yours.

```
| G-Y-01 | FORGE | The talent application is in the App Store with 1 paying
                   customer by 2027-06-30 | Andrew | Name the single blocking
                   milestone | BUILDER | NOT STARTED |

| G-Q-01 | ABO   | One compliant proposal is submitted by 2026-12-15 | Andrew |
                   Ask counsel the four questions in agents/07 §2 | none - human |
                   NOT STARTED |

| G-W-01 | DBA   | Chapter 2 draft is with my chair by 2026-09-21 | Andrew |
                   Email my chair to confirm what FIU permits re AI use |
                   none - human | MOVING |
```

**Three rules while you type:**

1. **Every goal gets an owner.** If it is not you and not a named agent, it is a
   wish. Write `Andrew`.
2. **Every goal gets ONE next action.** Not a list. One. Write the first
   physical thing — *open the file*, *send the email*, *make the call*.
3. **At most one goal per lane is `MOVING`.** Little's Law: more concurrent
   goals lengthen every one and finish none faster.

### Verify Block 1

```bash
python3 scripts/goal_throughput.py
```
**Expect:** `X1 = 1` with your goal count. `X3` will still be `0`. That is correct.

---

## BLOCK 2 — 10 minutes, once. Closes `X3`.

A review is not a feeling. It is **six lines written into the ledger**, dated.

**Copy this block to the bottom of the ledger and fill it in:**

```
## REVIEW — 2026-__-__

MOVED THIS PERIOD:    <goal id, and what actually changed>
DID NOT MOVE:         <goal id, and the honest reason - not an excuse>
BLOCKED ON SOMEONE:   <goal id, who, since when>
ONE CHANGE NEXT PERIOD: <exactly one. Everything else stays parked>
NEXT REVIEW:          <date>
REVIEWED BY:          Andrew
```

**On the first review, "DID NOT MOVE: all three, written today" is a correct and
complete answer.** The review exists to establish the cadence, not to report
progress that has not happened yet.

### Verify Block 2

```bash
python3 scripts/goal_throughput.py
```
**Expect the gate to close.** `Y` is no longer structurally zero, and the tool
starts reporting owned goals, WIP, and cap breaches instead of a refusal.

---

## BLOCK 3 — 25 minutes, the same week. First agent.

**Run BRIEFER once.** Card: `agents/cards/briefer.md`.

```
1  Copy agents/mission-template.md to mission.md. Fill it in:
     lane           one of the five
     result         "a one-page brief on <question> with an evidence ledger"
     done means     source links support the important claims
                    no restricted data used
                    the brief fits one page
     time limit     25 minutes        extra spend   $0.00
     route          ONE controller only

2  Pick a real question you would otherwise have researched yourself.
   Public sources only. Up to three.

3  First message, verbatim:
     "Read the project instructions and mission. List the files loaded,
      proposed edits and permissions needed. Make no changes yet."

4  Review once. Then let it produce the brief.
```

**Measure two numbers separately, and do not merge them:**

```
X6  minutes this saved you    ______
X7  minutes you spent reviewing it  ______
NET = X6 - X7 = ______        ← if negative, the artifact is wrong, not you
```

---

## THE FOUR HUMAN ACTS — not agent work, and none of them is long

Each closes an order-1 failure path. None can be delegated.

| # | Act | Time | Closes |
|---|---|---|---|
| 1 | **Email your FIU chair / read the program handbook**: what does the program permit regarding AI use in dissertation research and writing? | 10 min | `FM-06` · RPN 450 · unrecoverable class |
| 2 | **Open one URL**: `https://e8af4871.forge-talent-connections.pages.dev/agents/context/device-fleet.md` — does it render markdown, or 404? | 30 sec | `FM-31` · RPN 384 |
| 3 | **Create a PRIVATE repo** for invention disclosures. Nothing else needed today | 5 min | `FM-04` · order-1 · patent rights |
| 4 | **Read the Just4Veterans 1099 agreement** for data-handling or tooling terms | 15 min | `FM-21` · order-1 |

**Plus two that unblock tooling:** confirm the Mistral seat-3 model id in the
console (2 min), and send contracts counsel the four questions in
`agents/07-guardrails.md` §2.

---

## THE STOP RULE

> **Do not ask for another analysis until Blocks 1 and 2 are done.**
>
> Seven frameworks — inversion, FMEA, FTA, FMEDA-adapted, critical thinking,
> TRIZ, Zero Defects, DMADV, IDOV, CST, Nine Windows — have now returned the
> same answer. An eighth will return it again. **The analysis is not the
> bottleneck and has not been for some time.**

**If Blocks 1 and 2 are not done by 2026-10-14**, the honest conclusion is that
this system does not fit how you actually work. At that point delete everything
except `START-HERE.md`, `agents/cards/briefer.md`, `AGENTS.md` and
`scripts/redaction_guard.py`, and run only BRIEFER.

**That is not a threat. It is the same kill rule that applies to any agent in
this roster that fails to earn its place** — applied to the roster itself.
