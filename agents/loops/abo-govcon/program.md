# PROGRAM — ABO GovCon compliance loop

**Lane:** `ABO` · **Type:** true optimization · **Node:** Surface Pro 8
**Prepend:** `../_LOOP-PREAMBLE.md`

---

> ## ⛔ THIS LOOP DOES NOT RUN YET
>
> A proposal in progress is very plausibly procurement-sensitive. This loop is
> **blocked** until contracts counsel answers the four questions in
> `../../07-guardrails.md` §2 (tracked as `../../10-open-questions.md` A1).
>
> **`loop_guard.py` will refuse this loop while `counsel_cleared` is false in
> `loop.json`.** Do not set that flag to unblock yourself. Set it when counsel has
> answered, in writing, and record the date.
>
> **Professional verification required.**

---

## Objective

Drive **unaddressed requirements to zero** on one proposal response document.

Not persuasiveness. Not win probability. **Coverage.** A technically excellent
proposal thrown out for non-compliance is the most expensive avoidable failure in
this lane, and coverage is the part a machine can check.

## Metric — lower is better, every term mechanical

```
score = 3·(shall_statements_with_no_mapped_response)
      + 2·(section_M_factors_with_no_mapped_response)
      + 2·(section_L_instructions_violated)      # page limits, format, ordering
      + 1·(cross_reference_errors)
```

Every term derives from the **deterministic Pass-1 extraction** in
`../../05-govcon-pipeline.md` §4. `MODEL-ONLY` rows are **never** counted — a
requirement the model invented is not a requirement.

## What you may change

✅ Response text in the proposal document · structure and ordering · cross-
references · formatting to satisfy Section L

## What you may never change

❌ The solicitation, any amendment, or the extracted requirement set
❌ The metric script or `loop.json`
❌ Any past-performance claim, certification, representation, price, or
   personnel commitment — **these are Andrew's to write and certify, full stop**
❌ Anything that would be submitted anywhere. **You never submit** (`07` §6)

## The three cheapest ways to cheat this metric (G4) — this one is the most gameable

1. **Keyword-stuff** so the matcher finds every shall-statement → per-section
   length ceiling + verbatim-quote checks + the G6 sample below
2. **Restate the requirement as the response** ("The offeror shall provide X" →
   "We will provide X") — matches the string, answers nothing → the G6 sample is
   specifically looking for this
3. **Map one paragraph to twenty requirements** so counts fall without content
   → max-requirements-per-response-block cap in the harness

## Held-out check (G6) — mandatory, and the run is void without it

**A human reads a random 10% sample of mapped rows and asks one question of each:
"does this actually respond to the requirement?"**

If the sample fails, **the entire run is void** — not partially credited. The
metric has been demonstrated unreliable for that run, which means every row it
scored is suspect.

## Stopping

```
MAX_ITERATIONS: <FILL-IN>      MAX_WALL_CLOCK: <FILL-IN>
MAX_SPEND_USD:  <FILL-IN>
STOP IMMEDIATELY IF: score reaches 0  (then the G6 sample decides whether it is real)
```

## Standing limits

- **No win probability, Pwin, or expected value.** Ever (`_SHARED-PREAMBLE` §3).
- **Adequacy is not yours to judge.** You report that a row is addressed and
  where. Whether it will win is a human call.
- **Nothing leaves this machine.** No publishing, no posting, no submission.
