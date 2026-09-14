# GOAL LEDGER

**Andrew writes this. GOALKEEPER reads it and never writes it.**

Empty until filled — and an empty ledger is itself the finding: `FM-33` ranks
first in the failure register precisely because nothing here has been written.

---

## The two invariants

```
1  EVERY GOAL HAS AN OWNER AND ONE NEXT ACTION.
   No owner → it is a wish, not a goal.

2  EVERY AGENT TRACES TO AT LEAST ONE GOAL.
   No goal → trim the agent. It is cost without benefit.
```

## Entry format

```
ID        G-<horizon>-<n>          e.g. G-Q-03
HORIZON   DAY | WEEK | MONTH | QUARTER | YEAR
LANE      ABO | FORGE | J4V | DBA | HOME
GOAL      A falsifiable statement with a date.
          "X will be true by <date>" - not "improve X".
WHY       What it is in service of. One line.
LEADING   The indicator that moves BEFORE the outcome does.
OWNER     Andrew, or a named agent. Never blank.
NEXT      The ONE next action. Never a list.
AGENTS    Which agents advance this, if any. May be "none - human work".
REVIEW    The date this gets looked at again.
STATUS    NOT STARTED | MOVING | STALLED | BLOCKED | DONE | CUT
```

---

## YEAR — 10-year horizon, executed in 90-day sprints

| ID | Lane | Goal (falsifiable, dated) | Owner | Next action | Agents | Status |
|---|---|---|---|---|---|---|
| G-Y-01 | | | | | | |
| G-Y-02 | | | | | | |
| G-Y-03 | | | | | | |

## QUARTER — the current 90-day sprint

**Sprint window:** ____________ to ____________

| ID | Lane | Goal | Owner | Next action | Agents | Status |
|---|---|---|---|---|---|---|
| G-Q-01 | | | | | | |
| G-Q-02 | | | | | | |
| G-Q-03 | | | | | | |

## MONTH

| ID | Lane | Goal | Owner | Next action | Agents | Status |
|---|---|---|---|---|---|---|
| G-M-01 | | | | | | |

## WEEK

| ID | Lane | Goal | Owner | Next action | Agents | Status |
|---|---|---|---|---|---|---|
| G-W-01 | | | | | | |

## DAY — one active goal. Not a list.

```
TODAY'S ONE GOAL:  ______________________________________
THE ONE NEXT ACTION: __________________________________
EVERYTHING ELSE:   parked (agents/cards/parking.md)
```

---

## Orphan checks — GOALKEEPER runs these weekly

**Goals with no owner** — a wish until someone owns it:
```
(none recorded yet)
```

**Agents tracing to no goal** — trim candidates:
```
(cannot be computed until the ledger has entries)
```

---

## What this ledger cannot do

It cannot make you accomplish your goals. **No system can promise that, and one
that claims to is lying.** What it can do is make two specific failures
impossible to have silently:

- a goal nobody owns, discovered at the review that was supposed to catch it
- an agent running that serves nothing

Everything else — the choosing, the weighing, the stewardship — is yours.
