# Calibration review brief — for ChatGPT Codex

> Paste `REVIEW-BRIEF.md` first (the general rules), then **this file**, then
> `review/bundle-8-calibration.txt`. Ask Codex on its own. Do not show it
> Gemini's answer or vice versa — that is the same blinding rule this tool
> enforces on its own seats, for the same reason.

**Never paste `.env` or `profiles.json`.** The bundles contain no credentials
and the generator refuses to write one that does — verified by planting a
`sk-ant-…` string in `calibrate.py` and confirming the write was refused.

---

## What this module is and why it is dangerous

`calibrate.py` produces `rho` — how much the five seats err *together* — from
**live, paid models**. That number drives one decision: keep paying for five
seats, or cut to three.

A defect here **does not crash**. It produces a plausible number that a
spending decision then rests on. That is the whole review problem. Two
defects of exactly that shape have already been found in this module, both
after it was "working", and both are described below.

---

## What was built

| File | Role |
|---|---|
| `calibrate.py` | The measurement. ~219 statements |
| `test_calibrate.py` | 38 tests |
| `.github/workflows/calibrate.yml` | Manual-only, phone-triggerable run |
| `CALIBRATING.md` | Operator instructions |

### The mechanism

1. `build_items(n, seed)` generates `n` arithmetic statements, half true, half
   false, deterministically from `seed`.
2. All statements go into **one artifact**, shown identically to all five
   seats. One API call per seat, five total.
3. Each seat emits one claim line per statement it judges **correct**. Silence
   means "incorrect" and is recorded as its decision.
4. `ArithmeticGate` recomputes each confirmed expression. **That is the answer
   key** — no human and no model decides truth.
5. `correctness_matrix.build_correctness_matrix` scores
   `X[item][seat] = int(asserted == is_true)` under `SHARED_DETECTION`.
6. `seat_independence.diagnose` returns `rho` and effective seat count.

### The claim line shape, and why it is what it is

```
CLAIM | arithmetic | 463 * 785 = 363455 | 463 * 785 = 363455
```

The statement is repeated in both the warrant and text fields. Two constraints
force this and only this shape:

- **`content_claim_id` hashes (kind, warrant, normalised text).** Five seats
  confirming the same statement must produce the *same* claim id, or the
  matrix sees five one-seat items rather than one five-seat item, every item
  is a singleton, and `rho` is measured over nothing.
- **The relevance guard refuses a warrant that does not bear on the claim
  text.** So the text field cannot be a bare item id.

`text == warrant` is the guard's own explicitly sanctioned case
(`adjudication_orchestrator.py` ~line 507: *"the claim IS the warrant"*).

---

## Two defects already found here — the review should assume there are more

### Defect 1: the silent sample collapse

**First build put the bare item id (`S03`) in the text field.** The relevance
guard saw that `"S03"` does not mention `324` and escalated. Escalated claims
are **excluded from the matrix by design**.

Consequence: every **true** item silently left the sample. The false items
still failed (a FAIL needs no relevance check), so `rho` was computed over
**5 items instead of 17** — from the false items alone. Nothing raised.
Nothing turned red. The only visible trace was a coverage line reading
`5 item(s) x 5 seat(s) ... 12 excluded`.

Found by checking the coverage number rather than the verdict.

Now pinned by three tests: the correct form is ruled true, the broken form
escalates, and `n_excluded_unadjudicated == 0` end to end.

### Defect 2: NaN read as a high correlation

`seat_independence` returns `rho = NaN` when **no seat pair varied** — every
seat scored identically, so there is nothing to correlate. That is the
*absence* of a measurement.

`verdict_line` was a threshold ladder:

```python
if rho <= 0.2:   return "KEEP FIVE SEATS"
if rho <= 0.5:   return "MARGINAL"
return "CUT SEATS"
```

**NaN fails every comparison**, so it fell through to the last branch. Five
perfect, possibly-independent seats produced:

> `CUT SEATS. rho=nan means the seats mostly fail together. You are paying 5
> times for close to one opinion.`

An absent measurement converted into confident, expensive advice, in the
**wrong** direction.

Worse: this was the *most likely* real-world outcome, because the probe was
three-digit addition and current models essentially never get that wrong.

Two fixes: `rho_measured()` is now a `TypeGuard` so the type checker enforces
that no comparison happens on the unmeasured path; and the probe was made
harder — two thirds three-digit **multiplication**, one third six-digit
addition — so real seats have something to actually disagree on.

---

## What I verified, with numbers

- **1,167 tests pass.** `ruff` clean, `mypy --strict` clean across 23 source
  files, `bandit` exit 0, `pip-audit` clean.
- **Coverage 81.92%** against the 80 floor; `calibrate.py` at **99%** (the one
  uncovered line is `if __name__ == "__main__"`).
- **Eleven mutations planted, all eleven caught.** Reverting the claim format;
  declaring `OPEN_ENDED` instead of `SHARED_DETECTION`; swallowing seat
  errors; never flagging unmatched claims; loosening the keep-five threshold
  to 0.9; exiting 0 on an unmeasurable run; making false items wrong by 200;
  making `rho_undefined` ignore NaN; deriving the exit code from `measurable`
  alone; reverting the probe to addition only; making the answer key disagree
  with the gate.
- **Both extremes reproduce.** Seats slipping on different items →
  `rho = -0.133`, 5.00 effective seats, "KEEP FIVE". Seats slipping on the
  same items → `rho = 1.000`, 1.00 effective seat, "CUT SEATS".
- **Every failure path exits non-zero without spending:** missing credentials,
  unfilled settings file, odd item count, unmeasurable run.
- **The answer key is cross-checked against the gate that scores it** —
  `is_true` and `ArithmeticGate` are different code, and the measurement is
  void if they disagree.

---

## What I am NOT confident about — attack these first

These are ordered by how much damage a defect would do. **I have not run this
against a single real model**, so everything below is reasoning, not evidence.

### 1. The effective sample is data-dependent and may be far smaller than `n`

Only claims **at least one seat asserts** become matrix items. A false
statement nobody falls for produces no claim, no item, and contributes
nothing.

So if the seats are good, the matrix collapses toward "the true items only" —
and measuring only *misses* is precisely the flaw the false items were added
to fix. With `--n-items 24` I observed 17 items (mixed demo seats) and **12**
(perfect seats).

**Question for Codex:** is `rho` over ~12 items across 5 seats meaningful at
all? There is **no confidence interval anywhere in this module.** Should
there be, and what would it take to compute one honestly here?

### 2. Probe difficulty is guesswork

I changed the probe from three-digit addition to mostly three-digit
multiplication because I reasoned models slip there. **I have not measured
that.** If it is still too easy, every run returns "NO VERDICT". If it is far
too hard, all five seats fail everything and `rho` goes to 1.0 — reading as
*collapse* when it is really *saturation*.

**I do not currently distinguish saturation from collapse.** That looks like
a real gap. A panel that gets everything wrong together and a panel that
shares a blind spot produce the same `rho = 1.0`.

### 3. `_norm` duplicates the engine's normalisation

`calibrate._norm` does casefold + whitespace collapse to decide whether a
seat's confirmation matches a known item. `content_claim_id` normalises
*similarly but not identically* — it also strips surrounding punctuation.

If they drift, `unmatched_claims` reports wrongly: either false alarms, or —
worse — silence about a seat whose claims genuinely did not collide.
**This is duplicated logic across a module boundary and I am not comfortable
with it.** Is there a public normaliser that should be reused instead?

### 4. Single sample per seat

One call per seat, one shot. Model outputs vary between calls. `rho` from a
single sample per seat has unquantified variance, and re-running with the same
seed will *not* reproduce it (the items are identical; the answers may not
be). Nothing in the module says this.

### 5. Prompt compliance is unmeasured

The instruction says "repeat the statement in both fields, character for
character." Real models may add commentary, reword, or use markdown. I detect
non-matching claims and warn — and that warning biases `rho` **downward**
(more independent-looking, the flattering direction). But if compliance is
poor the whole run is wasted money.

**Is `line_claim_extractor` tolerant enough** of a model that wraps output in
a code fence or adds a preamble?

### 6. Thresholds drive spending and are conventions, not derived

`0.2` and `0.5` come from a discussion, not from an analysis. They are
labelled as conventions in the code, but they still produce "CUT SEATS".

### 7. Known interaction: `temperature` is rejected by current Claude models

`profiles.example.json` templates `"temperature": "{{temperature}}"` in all
five seat blocks. Current Anthropic models (Fable 5, Opus 5, Sonnet 5, and the
4.6/4.7/4.8 family) **removed** `temperature`, `top_p` and `top_k` — sending
them returns HTTP 400. Calibration inherits this path. It fails loudly
(`HTTP 400 from <vendor>`), not silently, but it fails.

The settings checker does not catch it — it only looks for `FILL-IN` markers.

### 8. The workflow uses `eval`

`.github/workflows/calibrate.yml` uses `eval "k=\$K$n"` to index the five key
variables in a loop. The loop values are literals (`1 2 3 4 5`), so I believe
this is safe, but `eval` near credentials deserves a second opinion. Keys are
written with `printf` from the environment rather than passed as arguments
(arguments are visible in a process listing) — check that reasoning too.

### 9. Cost estimation

`HttpSeat.est_input_tokens` defaults to 3000; the real calibration prompt is
roughly 700 tokens. The ledger therefore over-estimates, which is the safe
direction for a ceiling — but confirm the ceiling cannot be *under*-estimated
on this path. Only `--max-cost` (per-run) is exposed; per-stage and per-day
are not.

---

## Specific asks for Codex

1. **Find another way for items to leave the matrix silently.** Escalation is
   one route and it is now pinned. Are there others — a seat error dropping a
   whole pass, a duplicate-claim path, a gate returning `BLOCKED`?
2. **Find a way for two seats confirming the same statement to produce
   different claim ids.** Unicode, whitespace, a trailing period, a
   full-width digit.
3. **Find a way to make the panel look more independent than it is.** That is
   the direction that argues for keeping five paid seats.
4. **Distinguish saturation from collapse** — both give `rho = 1.0`. Propose a
   check.
5. **Attack the answer key.** Can `Item.is_true` ever disagree with what
   `ArithmeticGate` computes? Consider integer overflow bounds, `Fraction`
   coercion, unit-splitting (`_split_unit`), and expressions the AST evaluator
   treats differently than Python would.
6. **Confirm no operator material reaches a vendor on this path.** The quiz is
   generated arithmetic and should carry no artifact text at all.
7. **Name any test that would still pass if the behaviour it names were
   deleted.** Name the test and name the deletion.

A reply saying "this looks solid" is worth nothing. Assume there is a defect
and go find it.
