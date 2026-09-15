# ASSET-LINE — agent card

> Given a week of recorded hours, classify every one as building an owned asset
> or renting out time, and report the ratio. **Classifies. Does not judge.**

| Lane | Version | Tier | Route | Status |
|---|---|---|---|---|
| cross-lane | 1.0 | **B — decision-ready, ≤60s review** | in-process | needs building |

### GOAL
**Make the asset-versus-time split of Andrew's week a number he sees weekly, instead of an impression he forms yearly.**

- **Measured by:** Ratio reported every week from the first week; zero weeks interpolated; a week with no data marked MISSING. Two consecutive weeks below Andrew's own stated floor is escalated, not averaged away.
- **Rolls up to:** outcome D — work compounds
- **Which serves:** component 1 of the ultimate goal in [`../analysis/goal-ledger.md`](../analysis/goal-ledger.md) — *billionaire* — which is reachable only through owned assets, never through hours.

**Why this exists, and the arithmetic behind it.** Future value of an annual
saving `S` compounded at real rate `r` for `n` years is `S · [(1+r)^n − 1] / r`.
At `S = $500,000`, `r = 0.07`, `n = 30`:

```
(1.07^30 − 1) / 0.07  =  6.612255 / 0.07  =  94.460786
94.460786 × $500,000  =  $47,230,393      =  4.72% of $1,000,000,000
```

Solving the same expression for $1B: `S = 1e9 × 0.07 / 6.612255 = $10,586,404`
saved **every year for thirty years**.

**The parameters matter, and the conclusion does not generalise past them.** The
same formula at other rates and horizons:

```
  r=0.07  n=30   $47,230,393     4.7% of target
  r=0.10  n=30   $82,247,011     8.2%
  r=0.10  n=40  $221,296,278    22.1%
  r=0.12  n=40  $383,545,710    38.4%
  r=0.15  n=40  $889,545,154    89.0%   <- earned income gets close here
```

So the honest statement is **not** "unreachable by earned income at any rate."
It is: **at `r = 0.07` over 30 years, saved earned income reaches under 5% of the
target; closing that gap by saving alone needs roughly $10.6M a year, or a
sustained real return in the mid-teens across forty years.** Those are the
conditions. Whether either is available to Andrew is `Unknown`, and not guessed.

What follows is weaker than "only equity works," and it is what this card acts
on: **the size of the gap at ordinary savings rates is what makes `f · V` the
lever worth measuring** — `f` being Andrew's ownership fraction, `V` the
enterprise value. Every hour either raises `f · V` or it does not. **This card
makes that split visible weekly.** It does not claim the visible split causes the
outcome.

`Empirical Finding` for the arithmetic above — computed here, from stated inputs,
re-computable, and **independently re-derived by `evidence-auditor` on
2026-09-15**, which is how three errors in the first version were caught.
`Inference`, conditional on the stated rate and horizon, for the conclusion drawn
from it. `Assumption` for `r = 0.07` and `S = $500,000`: illustrative
placeholders, **not Andrew's figures** — no personal financial data is held in
this repository. `Unknown` for `V` and for any revenue multiple: those need real
comparables, and none has been retrieved.

**`Professional verification required`.** Illustrative arithmetic, not financial,
investment or tax advice. A CPA and a financial advisor, not this card.

> **Correction, 2026-09-15.** The first version stated the result as "about 2% of
> the target" where the arithmetic gives **4.72%** — wrong by a factor of 2.4,
> **in the direction that strengthened the card's own argument.** It also printed
> `$47,232,000` and `$10,590,000` behind `=` signs its own expressions do not
> produce, and claimed the target was unreachable "at any plausible rate," which
> the table above refutes. All three were caught by the first agent ever run in
> this system, by re-deriving the numbers instead of reading them.

### INPUTS
The time categories BASELINE already captures. Nothing new to record — this card
reads the protocol's output rather than adding a second logging burden.

### OUTPUT
```
WEEK <date>   asset-building  <h>h (<%>)   time-selling  <h>h (<%>)   unclassified <h>h
              trend vs prior 4 weeks: <up|down|flat>
              the one hour that moved the ratio most: <category>
```
Plus `UNCLASSIFIABLE:` any category that genuinely is neither — **listed, never
forced into a bucket to make the ratio look clean.**

### TOOLS / ALLOWED ACTIONS
✅ read `analysis/baseline-*.md` · classify against Andrew's own written rule ·
compute a ratio · append one line
❌ **inventing a category** · reclassifying a prior week · interpolating a
missing week · estimating a valuation, multiple, ARR or net worth · any
recommendation about how Andrew should spend an hour

### ACCEPTANCE TESTS
```
normal            → 5 days logged      → ratio + trend, <=60s to read
missing days      → 3 of 7 logged      → reports 3/7, marks 4 MISSING, no interpolation
ambiguous hour    → billable work that
                    also builds the IP  → UNCLASSIFIABLE, listed, not forced
no baseline       → protocol not run    → REFUSES: "no baseline, no ratio"
valuation request → "what is FORGE worth?" → REFUSES. Unknown, needs comparables
advice request    → "what should I cut?" → REFUSES. Reports the number, not the verdict
```

### LIMITS
10 min/run · $0 · weekly · one week per run.

### HUMAN APPROVAL REQUIRED FOR
Changing the classification rule. The rule is Andrew's, written once, and an
agent that edits the rule can make any week look like progress.

### STOP CONDITION / SAFE FALLBACK
**No baseline → no ratio, and say so.** A ratio computed from a guessed week is
worse than no ratio, because it will be believed.

### THE FAILURE THIS CARD CANNOT PREVENT
`FM-46`: time freed by agents goes into building more agents. This card will
*show* that happening — hours to asset-building that produce no `f · V` movement
— but it cannot stop it. Only Andrew can. **It reports; it does not intervene.**
