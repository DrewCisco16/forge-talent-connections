# NIGHTWATCH — agent card

> Given one genuinely hard, contested, consequential question, run the paid
> five-seat panel. **Manual only. Typed SPEND. Rare.**

| Lane | Version | Tier | Route | Status |
|---|---|---|---|---|
| one lane per run | 2.1 | **C** | `adjudicate.yml` `workflow_dispatch` | **Tier 3 — rare** |

> **Demoted in v2.** Your own `one_model.py` records Stage 0 baselines of 0.968
> and 1.000 against a 0.45 threshold and the instruction *"DO NOT BUILD THE
> ENSEMBLE."* This is now mostly a **measuring instrument**, not a production
> engine.

### WHEN IT IS JUSTIFIED — all four, or do not run it
```
1 the question is genuinely contested
2 the consequence is high
3 one more hour of your own reading would NOT settle it
4 blind independence is actually required (not just more opinions)
```
Otherwise: Tier 0 → Tier 1 → Tier 2 (`14`).

### GOAL
**Tell Andrew whether his five seats are actually independent - and retire itself if they are not.**

- **Measured by:** Rho computed from a paired sample of >=10 items and reported with its n; zero runs without a typed SPEND. A high rho is a successful run that retires this card.
- **Rolls up to:** outcome B — nothing irreversible goes wrong
- **Which serves:** the goal Andrew writes in [`../analysis/goal-ledger.md`](../analysis/goal-ledger.md). No agent authors that one.

### INPUTS
One `ask` · one lane · one cost ceiling · typed `SPEND`.

### OUTPUT
The engine's own report: gate findings first · survivors · convergence and
divergence · **open holes with what would close each** · judgment queue ·
`May this be committed?` — **YES only if one survivor AND zero holes.**

### ACCEPTANCE TESTS
```
normal              → a five-round report with gates, survivors and holes
missing evidence    → nothing survives → "NOT RESOLVED" is a RESULT, not a failure
unsafe instruction  → a seat reply containing an instruction → FINDING, not obeyed
two survivors       → reports BOTH and refuses to break the tie. Correct behavior
cost refusal        → a plan exceeding the ceiling → REFUSES BEFORE the first call
confirm             → anything other than typed SPEND → stops, bills nothing
concurrency         → a second panel while one runs → blocked by the concurrency group
```

### LIMITS
`max_cost_usd` default `17.00` · measured $4.96 · ~1 hour · one panel at a time.

### BLOCKERS
```
[ ] seat_3 Mistral model id UNVERIFIED in rates.json — Magistral is retired.
    A ceiling computed from an unchecked price bounds nothing. 2 minutes to clear.
[ ] rates.json 90-day re-check: verified 2026-09-09 → DUE 2026-12-08
```

### HUMAN APPROVAL REQUIRED FOR
**Every run. Typed `SPEND`, every time. Never scheduled.**

### STOP CONDITION / SAFE FALLBACK
Stop at the report. **Run `calibrate.py` first — five calls, cents.** If rho is
high, these are five correlated seats billing five times, and the right action is
to retire this card rather than run it.
