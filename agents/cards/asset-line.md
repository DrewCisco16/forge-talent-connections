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

**Why this exists, and the arithmetic behind it.** A net worth target of
$1,000,000,000 is not reachable by accumulating earned income at any plausible
rate. Future value of an annual saving `S` compounded at real rate `r` for `n`
years is `S · [(1+r)^n − 1] / r`. At `S = $500,000`, `r = 0.07`, `n = 30`:

```
(1.07^30 − 1) / 0.07  =  (7.6123 − 1) / 0.07  =  94.46
94.46 × $500,000      =  $47,232,000
```

That is roughly **$47M — about 2% of the target**, and it assumes saving half a
million dollars a year for thirty consecutive years. Solving the same expression
for $1B requires `S = 1e9 × 0.07 / 6.6123 = $10,590,000 saved per year`.

**This is arithmetic, not a forecast, and it carries no probability.** What it
establishes is structural: the earned-income path is excluded by the numbers, so
the target is reachable only by owning equity in something that is *valued* —
`f · V ≥ $1e9`, where `f` is Andrew's ownership fraction and `V` the enterprise
value. Every hour therefore either raises `f · V` or it does not. **This card
makes that split visible weekly.** It does not claim the visible split causes the
outcome.

`Evidence label: Empirical Finding` for the arithmetic above (computed here, from
stated inputs, and re-computable). `Assumption` for `r = 0.07` and `S = $500,000`,
which are illustrative placeholders, **not Andrew's figures** — no personal
financial data is held in this repository. `Unknown` for `V` and for any revenue
multiple: those need real comparables, and none has been retrieved.

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
