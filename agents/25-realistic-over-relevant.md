# 25 — REALISTIC BEATS RELEVANT, AND WHY THE SUMMIT IS THE REASON

**Question asked (2026-09-15):** *which is stronger for making sure the AI agents
will be successful — Relevant or Realistic?* And: *Time-Bound is ASAP.*

**Answer: Realistic. Not marginally — categorically, and specifically because of
the goal that was written at Level 0 the same day.**

---

## 1. The short version

```
RELEVANT    "does this serve the goal above it?"      -> a ROUTING test
REALISTIC   "can this actually be done, by whom,
             with what, by when?"                      -> a FEASIBILITY test
```

Four reasons Realistic is the stronger of the two **in this system, right now**:

| # | Reason | Label |
|---|---|---|
| 1 | Relevant is already enforced by a gate. Realistic is enforced by nothing | `Repo-Verified` |
| 2 | A $1B summit destroys Relevant's discriminating power | `Evidence-Based Inference` |
| 3 | The observed failure here is feasibility, not relevance | `Repo-Verified` |
| 4 | Realistic is the only letter of SMART that can return *no* | `Evidence-Based Inference` |

---

## 2. Relevant is already gated. Realistic is not.

`scripts/goal_ladder.py --gate` runs in the pre-commit hook and **blocks a commit**
if any card traces to no outcome. That is Relevance, mechanically enforced: all 34
cards are connected, and a disconnected one cannot be committed.

Nothing anywhere in this repository asks whether an agent can actually be made to
work. Every card carries acceptance tests — **and not one of those tests has run.**

```
RELEVANT    rung 1  gate, blocks, tested, denial live-tested
REALISTIC   rung 0  no check of any kind exists
```

**Adding strength to the letter that is already enforced buys nothing.** The
marginal return is entirely on the unguarded one. `Repo-Verified.`

## 3. The summit makes Relevant nearly useless as a filter

This is the reason that is specific to Andrew, and it is not obvious.

Relevance discriminates in proportion to how *narrow* the goal above it is. Under
a narrow goal — *file one patent by March* — most activities fail the relevance
test, and it does real work.

**Under "become a billionaire," almost nothing fails it.** Any commercial
activity, any skill, any relationship, any tool can be argued to ladder into a
$1B outcome, because a goal that large has no edges. A test that everything
passes is not a test; it is a rubber stamp that feels like governance.

```
narrow goal  ->  Relevance rejects a lot   ->  the filter does work
$1B goal     ->  Relevance rejects ~nothing ->  the filter approaches a tautology
```

So the very act of writing an enormous Level 0 goal — which was the right thing to
do, and which closed `X1` — **structurally weakened the R that means Relevant.**
That is not an argument against the goal. It is an argument that the *other* R now
has to carry the load. `Evidence-Based Inference` — reasoned from the structure of
the test, not from a study.

## 4. The failure actually observed here is feasibility

Not a hypothetical. This repository's own record:

```
agents specified ............ 32      agents that have run ......... 0
cards with acceptance tests . 34      acceptance tests executed .... 0
EXECUTE.md ("the 30 minutes") open across eight consecutive rounds
```

Every one of those 34 cards is relevant. **Relevance was never the problem.** The
problem is that nothing has been demonstrated to work, and a plan whose every step
is relevant and none of which is feasible produces exactly this: a growing,
well-connected, entirely inert system. `Repo-Verified` — `STATE.md`, and
`scripts/goal_ladder.py`.

## 5. Realistic is the only letter with the power to refuse

```
SPECIFIC     always satisfiable -- you can always write more precisely
MEASURABLE   always satisfiable -- you can always name a metric
ATTAINABLE   collapses into Realistic, or into wishful thinking
RELEVANT     under a $1B goal, satisfiable by almost anything  (section 3)
REALISTIC    CAN RETURN NO, and is the only one that can
```

A gate that cannot say no is not a gate. **Realistic is the only letter of SMART
with a refusal in it**, and this entire system is built on the principle that the
useful controls are the ones that block rather than advise.

---

## 6. What changes because of this answer

**The Realistic test, as a rule, before any agent is deployed:**

```
R1  HAS IT RUN ONCE?          A card that has never executed is a hypothesis.
                              Its status is 🔵 or ⚪, never "ready".
R2  WHAT DOES IT COST ANDREW  Review minutes per run, estimated before, measured
    TO REVIEW ITS OUTPUT?     after. Above the estimate twice -> demote a tier.
R3  WHAT IS ITS BLOCKER?      Named, or the card does not deploy. "None" is an
                              answer only if someone checked.
R4  CAN IT BE RUN TODAY,      If it needs counsel, a credential, a policy answer
    IN ONE SITTING?           or a purchase -> it is BLOCKED, not "ready".
```

**R4 already reclassifies cards that are currently marked ready.** That is the
test doing its job: `⛔` is a Realistic verdict, and this system has been treating
"specified" as though it were "feasible."

### The relationship between the two, stated once

Relevant and Realistic are not competitors; they fail in opposite directions:

```
relevant but not realistic  ->  a well-aimed plan that never executes   <- HERE
realistic but not relevant  ->  efficient progress in the wrong direction
```

**Both are failures. Only one of them is this project's.** Relevance is kept — it
is gated and costs nothing to keep. Realistic is the one being added, because it
is the one that is missing. *Andrew's standing instruction: add on, do not take
away.*

---

## 7. Time-Bound = ASAP, implemented honestly

**"ASAP" is not a time bound. It is the absence of one**, and applied to
everything it makes everything slower. Little's Law — `WIP = throughput × cycle
time` — is a theorem: at fixed throughput, raising the number of concurrently
active items raises the time each one takes. It does not raise how many finish.

```
everything ASAP  ->  WIP rises  ->  cycle time rises  ->  nothing lands sooner
```

The implementation that genuinely produces *as soon as possible*:

```
1  WIP = 1       exactly one goal MOVING; the rest parked, not queued
2  TODAY         the next action starts today, or it is not the next action
3  HARD STOP     an end time written before the block starts
```

**Rule 3 is what makes rule 2 survivable.** An open-ended "start now" is precisely
what has left `EXECUTE.md` unexecuted for eight rounds; a 20-minute block with a
stop time is something a person can actually begin. Recorded in `EXECUTE.md` as
THE TIME RULE, and already enforced in part by PARKING (`no second front`) and by
the ledger's DAY section (`one active goal, not a list`).

---

## 8. What this document does not claim

- **No probability** that Realistic-gating makes the agents succeed. No dataset,
  no experiment, no number. `Unverified.`
- **No citation.** Sections 3, 5 and 6 are reasoned from structure, and every
  scholarly index remains egress-blocked from this session. They are labelled
  `Evidence-Based Inference`, and they stand or fall on the argument, not on an
  authority that was never retrieved.
- **No claim that this is the standard SMART reading.** Conventional SMART
  usually resolves R as *Relevant* (or *Achievable*). This document argues the
  opposite for this system, for the four stated reasons, and the reasons are the
  whole of the case.
