# PROGRAM — panel economics optimization loop

**Lane:** any (operates on the adjudication engine itself) · **Type:** true
optimization · **Node:** HP Envy 17
**Prepend:** `../_LOOP-PREAMBLE.md`

---

## Objective

**Lower `cost_per_resolved_correct` without resolving fewer questions or getting
more of them wrong.**

```
objective  = total_cost / resolved_correct_count          (lower is better)

HARD CONSTRAINTS — violations reject the change before it is scored:
  resolved_correct_rate  must NOT fall below the recorded baseline
  not_resolved_rate      must NOT rise above the recorded baseline
```

**The second constraint is load-bearing.** Without it the cheapest possible
"improvement" is a panel that resolves nothing — a run that answers no questions
has an excellent cost per answer. See §Cheat paths.

---

## Why this loop can exist when most cannot

`adjudication/accuracy.py` is already a `val_bpb`. It plants questions with known
answers and returns three outcomes — **RESOLVED CORRECT / RESOLVED WRONG /
NOT RESOLVED** — and `cost_ledger.py` records actual spend per call from
vendor-reported token counts. **Objective and cost are both already
instrumented.** Nothing needs inventing, which is why this is a real loop and not
a wish.

---

## The search space

```
tier_default            TIER 0 | TIER 1 | TIER 2 | TIER 3
tier1_seat              grok-4.6 | mistral | gemini | gpt-5.6-sol | claude-opus-5
panel_seats             which subset, when TIER 3 is used at all
round_count             3 | 4 | 5
early_stop_threshold    the convergence yield at which rounds stop
max_tokens_per_seat     current caps carry 2.0x-7.0x headroom over measurement
prompt_caching          on | off   (cache reads are 0.1x input on seat_5)
gate_order              cheapest-and-most-refuting first
router_thresholds       where ROUTER sends a question
```

**Start from the five changes in `../../14-panel-economics.md` §5.** Early stop and
dropping the two priciest seats are together roughly a 4× reduction and need no
new code. Do not let the loop wander before those are in.

---

## The two-speed metric — G2 and G6 together

A full accuracy eval is 30 five-round runs: **$148.80–$504.60 and hours.** Far too
expensive per iteration. So the metric splits, which is what the Measurability
Gate prescribes anyway:

### Per iteration — cheap, seconds to minutes
```
rho                   calibrate.py — FIVE CALLS TOTAL, not five runs
convergence_yield     convergence.py — verified corrections per round
gate_refutation_count how much work the free layer did
total_cost            cost_ledger.py — actuals, not estimates
smoke_correct         a fixed 6-question subset with known answers
```

### Held out — expensive, rare, **and the loop never sees it**
```
full accuracy.py on the 30-question set
  cadence: once per 20 iterations, and once at the end
  cost:    $148.80 - $504.60, gated by ACCURACY_CONFIRM=yes
  authority: if held-out and per-iteration disagree, HELD-OUT WINS
             and every iteration since the last held-out run is void
```

**The loop may not read, reference, or reason about the held-out set.** That is
G6, and without it §Cheat paths wins.

---

## What you may change

✅ Panel configuration · seat selection · round count · early-stop threshold ·
token caps · caching · gate ordering · ROUTER thresholds

## What you may never change

❌ **`accuracy.py`, the question sets, or anything under `eval/`** — changing the
   measuring instrument to improve the measurement is the purest form of the
   failure this guard exists to catch
❌ `cost_ledger.py` or `rates.json` — **a ceiling computed from numbers the loop
   edited bounds nothing**
❌ The gates themselves (`citation_gate` · `quote_gate` · `predicate` ·
   `doi_resolver`) — you may reorder them, never weaken them
❌ `adjudication/` test files
❌ This file or `loop.json`

---

## Cheat paths, named in advance (G4)

| # | The cheap path | Defence |
|---|---|---|
| 1 | **Resolve fewer questions.** A panel that answers nothing has a superb cost per answer | `not_resolved_rate` is a **hard constraint, not a term.** A run that raises it is rejected before its cost is computed |
| 2 | **Overfit the 6-question smoke set.** Tune until the smoke passes and nothing else does | The 30-question held-out set, which the loop never sees. Divergence voids every iteration since the last held-out run |
| 3 | **Weaken a gate** so more claims survive and more questions "resolve" | Gates are immutable. Reorder yes, weaken no. A diff touching gate logic is an automatic rollback **and an escalation** |
| 4 | **Lower `max_tokens` until answers truncate.** Cost falls; so does quality, invisibly | Truncation is detected and counted as `RESOLVED WRONG`, never as a saving. `test_truncation.py` already exists |

---

## Stopping

```
MAX_ITERATIONS:  60          MAX_WALL_CLOCK:  12h
MAX_SPEND_USD:   60          ← includes held-out evals. Ceiling checked BEFORE each call
STOP EARLY IF:   15 consecutive iterations with no improvement
STOP IMMEDIATELY IF: a held-out eval disagrees with the per-iteration proxy
```

---

## The question this loop may answer, and you should be ready for it

**It may conclude that Tier 3 should not exist.**

If `rho` is high, five seats are five correlated opinions billing five times.
`one_model.py` already records the Stage 0 verdict on your two task classes —
baselines of 0.968 and 1.000 against a 0.45 threshold, and *"DO NOT BUILD THE
ENSEMBLE."* `accuracy.py` records SOP 7.1: *"overall mean multi-agent improvement
across six benchmarks was 0.0%."*

**If the loop reaches the same conclusion from live data, take it.** Retiring
Tier 3 is a successful outcome of this loop, not a failure of it. The engine was
built to find out; letting it find out and then ignoring the answer would waste
everything spent building it.
