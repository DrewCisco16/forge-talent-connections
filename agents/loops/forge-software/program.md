# PROGRAM — FORGE LINK software optimization loop

**Lane:** `FORGE` · **Type:** true optimization · **Node:** ASUS ProArt 16
**Prepend:** `../_LOOP-PREAMBLE.md`

---

## Objective

Lower the composite score on a **bounded target module**. Never "make the app
better" — that is not an objective, it is a wish.

```
TARGET MODULE: <FILL-IN — one module, one directory>
BENCHMARK:     <FILL-IN — the command that produces the numbers>
BASELINE:      <FILL-IN — captured before iteration 1, committed>
```

## Metric — computed entirely by script

```
GATE (not a term): all tests pass.  Any failure → REJECT before scoring.

score = w1·(p95_latency_ms / baseline_p95)
      + w2·(bundle_size_kb  / baseline_bundle)
      + w3·(1 - coverage_of_changed_lines)

Lower is better.  Weights fixed in loop.json, never changed mid-run.
```

**Correctness is a gate, not a term.** You cannot trade correctness for speed.

## What you may change

✅ Implementation inside the target module · algorithms · data structures ·
dead code removal · dependency pruning · memoization · query shape

## What you may never change

❌ **Any test file** — read-only, and a diff touching one is an automatic
rollback and escalation
❌ The metric script · the benchmark harness · `loop.json` · this file
❌ Public API signatures or the contract with other modules
❌ Anything under auth, payments, or PII handling — **escalate instead**
❌ `main` — you work on a branch and you never merge

## The three cheapest ways to cheat this metric (G4)

Written in advance, so you know them when you see them:

1. **Weaken or delete a test** so the correctness gate passes → tests are
   read-only; diff check catches it; automatic escalation
2. **Special-case the benchmark input** so the fast path only fires for it →
   held-out benchmark (G6) uses different inputs the loop never sees
3. **Move work out of the measured window** — defer it to a later call, or to
   startup → total-work check in the harness, not just the windowed measurement

## Held-out check (G6)

A second benchmark with different inputs, run **weekly by a human**, plus an
`adversarial-reviewer` pass over the accumulated diff. **The loop never sees
either.** If held-out and in-loop results diverge, the run is void and the branch
is discarded.

## Stopping

```
MAX_ITERATIONS: <FILL-IN>      MAX_WALL_CLOCK: <FILL-IN>
MAX_SPEND_USD:  <FILL-IN>      STOP EARLY IF: 20 consecutive iterations with no improvement
```

## On finishing

Open a **draft** PR with the accumulated improvements and the full iteration log,
wins and failures both. **Never merge.** A human reads the diff before anything
reaches `main`.
