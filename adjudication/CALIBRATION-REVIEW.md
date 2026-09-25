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
spending decision then rests on. That is the whole review problem.
**Seventeen** defects of exactly that shape have already been found in this
module, every one of them after it was "working, tested and green", and all
seventeen are described below with how they were reproduced.

---

## What was built

| File | Role |
|---|---|
| `calibrate.py` | The measurement. ~540 statements |
| `test_calibrate.py` | 128 tests |
| `.github/workflows/calibrate.yml` | Manual-only, phone-triggerable run |
| `CALIBRATING.md` | Operator instructions |

### The mechanism

1. `build_items(n, seed)` generates `n` arithmetic statements, half true, half
   false, deterministically from `seed`.
2. All statements go into **one artifact**, shown identically to all five
   seats. One API call per seat, five total.
3. Each seat emits one claim line per statement it judges **correct**. Silence
   means "incorrect" and is recorded as its decision — but a seat that emits
   NOTHING at all, or that raised, is excluded rather than scored, because
   that is an absence and not a judgement.
   `calibration_extractor` snaps each line's wording onto the canonical item
   so spelling differences cannot split one item into several.
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

## Seventeen defects already found here — the review should assume there are more

Two were found before the module shipped. Seven more came out of an
**Inversion Analysis** — assume it is wrong, enumerate how. Five more came out
of a **Critical Systems Thinking + TRIZ** pass, asking what the measurement
excludes and whose perspective it privileges. Three more came out of a
**Bayesian** pass, asking what the numbers' uncertainty actually is. Every one
was verified by running it, not by reading it.

That four successive passes each found defects in a module already "done,
tested and green" — 2, then 7, then 5, then 3 — is the most useful thing to
know about it. Assume a fifth pass would find more, and that you are that
pass.

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

### Defects 3-9: found by the Inversion Analysis pass

Each was reproduced before it was fixed.

**3. One flaky seat voided the entire run.** `correctness_matrix._errored_passes`
drops every claim first adjudicated in a pass where ANY seat raised. That is
right for a five-pass run — an errored seat's silence in one pass is
uninterpretable — and catastrophic for a one-pass calibration, because no
other pass carries the items. Measured: one errored seat out of five gave a
**zero-item matrix**, `measurable=False`, and a wasted paid run. Worse, the
report *claimed* "rho is computed over the seats that answered", which was
simply false — nothing was computed. Excluded seats are now dropped from the
panel and the run measures the rest; the report states how many seats the
number actually describes.

**4. An empty reply was scored as "every statement is false".** A refusal, a
safety filter, or an empty body behind a 200 all arrive as `""`. That produced
a decisive all-false row rather than an absence, putting a fabricated opinion
into the correlation. Zero usable claims is now an exclusion.

**5. Formatting variance manufactured disagreement.** `content_claim_id` hashes
the warrant verbatim, so `463*785 = 363455` and `463 * 785 = 363455` produce
**different claim ids** — verified. The two spellings became two one-seat
items, each seat scored as having MISSED the other's, so a purely typographic
difference made the panel look *more independent than it is*. The flattering
direction.

**6. A bullet or bold marker made the line vanish.** Measured against
`line_claim_extractor`: `- CLAIM | ...` and `**CLAIM** | ...` both yield **zero
claims**, silently, and the seat then looks like it judged everything false.
Code fences, blockquotes and preambles were already tolerated; these two were
not.

**7. A thousands separator escalated the item.** `363,455` is the same number,
but the gate cannot parse it and rules INAPPLICABLE — which drops the item from
the matrix without a word. Same silent-shrinkage class as defect 1.

Fixes 5-7 are one mechanism: `calibration_extractor` strips leading decoration
and snaps a seat's wording onto the canonical item expression, so every
plausible spelling collides on one id. It normalises **spelling only** — a
statement outside the item set is never snapped, so the extractor cannot
repair a seat's arithmetic.

**8. Saturation was indistinguishable from collapse.** Both give `rho = 1.0`
and they mean opposite things: seats sharing a blind spot score *well* and fail
together on a few items; seats drowning in too hard a probe fail nearly
everything, which also correlates perfectly but says nothing about
independence. Verified: two synthetic panels, both `rho = 1.000`, mean accuracy
**91%** vs **17%**. The first now reads CUT SEATS, the second refuses a verdict.

**9. "Cut seats" was unactionable.** The operator was told to drop two of five
and given nothing to choose by. Per-seat accuracy and confirmation counts are
now reported, read off the same X the correlation uses. The confirmation count
also exposes truncation — a seat cut off mid-reply and a seat that judged the
rest false are identical from the text alone.

Plus one hardening with no observed failure: item operand pairs are now
guaranteed unique. Two items sharing a left-hand side would collapse into one
claim id, scoring fewer items than reported, and if one were true and the other
false that id would carry two contradictory answer-key entries. Measured: no
collision below n=1000, which is exactly why it is enforced rather than
assumed.

---

## What I verified, with numbers

- **1,230 tests pass.** `ruff` clean, `mypy --strict` clean across 23 source
  files, `bandit` exit 0, `pip-audit` clean.
- **Coverage 82.81%** against the 80 floor; `calibrate.py` at **98%** (the one
  uncovered line is `if __name__ == "__main__"`).
- **Thirty-two mutations planted, all thirty-two caught** — and FIVE of
  them survived on the first attempt, which is the useful part:
  removing the snapping extractor changed no test (every format test called
  the extractor directly; none asserted the wiring); the uniqueness guard was
  untestable at n=24 because collisions do not occur below n=1000; the
  discriminating-rho threshold could be deleted freely because the panel it
  was tested on returned NaN either way; and the truth-alternation rule is
  genuinely EQUIVALENT at three bands, so it had to be exercised at four.
  Each test was rewritten until the mutation failed it.
- **One factual error in my own comments, caught by mutation.** I had written
  that alternating truth by index "would have pinned band 0 to true every
  time". Enumeration says otherwise: at three bands it balances, because three
  is odd. It collapses at four. The comment is corrected and the test now
  asserts the rule at four bands rather than restating a false claim. Reverting the claim format;
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

Ordered by how much damage a defect would do. **I have still not run this
against a single real model**, so everything below is reasoning, not evidence.
Three items from the first version of this brief were closed by the Inversion
pass and are gone; what remains is what remains.

### 1. The interval's own assumptions are unchecked

There is an interval now, but a bootstrap over items assumes items are
exchangeable draws from a population. They are not quite: they are generated
in balanced bands with fixed polarity, so resampling with replacement can
produce a draw whose band or true/false balance differs from the design. I
believe that is conservative — it widens rather than narrows — but I have not
proved it, and a stratified resample within bands would be the stricter
construction. Is the unstratified version defensible here?

### 2. The band boundaries are guesses

Easy is two-digit addition, medium three-digit multiplication, hard
four-by-three-digit multiplication. Those were chosen by reasoning about where
models slip, and **not one of them has been checked against a real model**.
If all three bands land above or below the panel's ability the span buys
nothing, and I would not know until a live run.

### 3. I invented the saturation threshold

`mean_accuracy < 0.6 and rho > 0.5` decides between "CUT SEATS" and "PROBE
SATURATED". **0.6 is a number I chose**, not one I derived. It is doing real
work: it is the only thing standing between a saturated probe and a
recommendation to retire paid seats. Both this and the `0.2` / `0.5` rho
thresholds drive spending and are conventions, not analysis.

### 4. Single sample per seat

One call per seat, one shot. Model outputs vary between calls. `rho` from a
single sample has unquantified variance, and re-running with the same seed
gives identical *questions* but not identical *answers*. Nothing in the module
says this.

### 5. Snapping could in principle over-reach

`calibration_extractor` rewrites a seat's wording to the canonical item when
the canonical key matches. Keys drop whitespace, commas and underscores, then
casefold. I believe no two distinct statements in a set can share a key —
operand pairs are unique and the full expression including both operands must
match — but **this is the one place the module edits what a seat said**, and it
deserves a hostile read. Can you construct two item expressions, or a seat
utterance and an item, that collide on `_canonical_key` while asserting
different propositions?

### 6. Truncation is reported, not detected

A seat cut off mid-reply and a seat that judged the rest false are identical
from the content. The confirmation count exposes the difference to a human
reading the table; nothing detects it automatically. `HttpSeat` raises on
`stop_reason == max_tokens` **only when the text is empty** — a partial reply
passes through silently.

### 7. The preflight gate is a heuristic

`preflight_settings` refuses to start when a settings block sends
`temperature`, `top_p` or `top_k` to an endpoint whose URL contains
"anthropic". Both halves are heuristics: the substring match will miss a
gateway or proxy URL that fronts the same models, and it assumes every
Anthropic-hosted endpoint rejects those keys. Attack both directions — a
configuration it wrongly blocks, and one it wrongly allows through.

### 8. The workflow uses `eval`

`.github/workflows/calibrate.yml` uses `eval "k=\$K$n"` to index the five key
variables in a loop. The loop values are literals (`1 2 3 4 5`), so I believe
this is safe, but `eval` near credentials deserves a second opinion. Keys are
written with `printf` from the environment rather than passed as arguments
(arguments are visible in a process listing) — check that reasoning too.

### 9. Cost estimation

`HttpSeat.est_input_tokens` defaults to 3000; the real calibration prompt is
roughly 700 tokens. The ledger therefore over-estimates, which is the safe
direction for a ceiling — but confirm it cannot *under*-estimate on this path.
Only `--max-cost` (per-run) is exposed; per-stage and per-day are not.

---

## Defects 10-14: found by the Critical Systems Thinking + TRIZ pass

Run after the Inversion pass, asking different questions: what does this
measurement include and exclude, whose perspective does its framing privilege,
and which of its constraints are real contradictions versus false ones.

**10. A shared MISS left no trace — the most dangerous blind spot was
invisible.** `build_correctness_matrix` builds rows from the verdicts, and a
statement nobody proposed is never gated and never becomes a row. So when all
five seats FAILED TO SPOT the same true statement — everyone missing a real
defect, which is precisely what this tool exists to detect — the item vanished
from the measurement entirely. Measured: five seats all missing three true
items gave a **9-row matrix and rho = NaN**; the visible half of the identical
behaviour, all five wrongly asserting three false statements, gave 15 rows and
rho = 1.0. The same panel pathology, one half measured and one half erased.
Fixed by seeding every item into the pass so all get adjudicated; the seat
credited with a claim is read from the RESPONSES, so seeding attributes
nothing to anyone. This also closes the "effective sample is data-dependent"
uncertainty from the previous brief: the matrix is now always `n` rows.

**11. Zero-variance ITEMS inflate the headline rho.** `seat_independence`
guards against a zero-variance SEAT (a constant column) but not a
zero-variance ITEM (a constant row). A difficulty band every seat fails enters
the correlation as perfect agreement, by construction. Measured: a panel that
was genuinely independent on the band that discriminated it — each seat
slipping on a different medium item — scored **rho 0.871 and was told to CUT
SEATS**, because hard items nobody got right counted as instances of failing
together. Now reported as two readings side by side, with no single verdict
when they imply different decisions. Both are legitimate answers to different
questions and collapsing them is what produced the wrong recommendation.

**12. The probe was a compromise where it should have been a span.** One
difficulty can only be wrong in one of two directions and cannot tell you
which — too easy gives NaN, too hard gives a false collapse. Items now span
easy / medium / hard and the report shows accuracy per band, so the panel's
ability level is visible rather than inferred. This is the TRIZ move:
separation instead of trade-off.

**13. "Cheap versus statistically stable" was a false contradiction.** The
default was 24 items because more felt more expensive. Measured: 24 items is
179 prompt tokens, 120 items is 811 — and all of it is still **five calls**.
Items were priced as though they were calls. Default raised to 60.

**14. The report spoke to only one of its two readers.** Every line was framed
for the budget-holder: how many seats to pay for next time. That framing hides
the other reader entirely — whoever relies on an answer this panel has already
produced. A high rho does not only bear on future spending; it says
convergence in COMPLETED runs was worth less than it looked, and nothing else
in the system will ever tell them. The report now says so when rho is high.

Plus one preventive gate, on Zero-Defects grounds — the module detected
problems well and prevented none. `preflight_settings` reads the settings file
and refuses to start when it finds something that would only be discovered by
paying for it: currently sampling parameters sent to an Anthropic endpoint,
which current Claude models reject with HTTP 400. That was open uncertainty #7
in the previous brief; it is now caught before any call is made.

---

## Defects 15-17: found by the Bayesian pass

**15. `rho` was a point estimate driving a spending decision.** No interval
anywhere, while `seat_independence`'s own reading line already said "a small
number of items makes rho unstable regardless of its value" and nothing acted
on it. There is now a 90% interval from resampling items, and **the interval
decides the verdict, not the point estimate**: when it straddles a threshold
the run refuses a recommendation and estimates how many more items would
settle it.

**16. The first estimate of "how many more items" was arithmetically right and
useless.** For rho=0.190 against a 0.2 edge it returned **12,618 items** —
which reads as a plan and is not one. When the estimate sits essentially on
the threshold, the true value may BE the threshold and no sample size resolves
it. Capped at ten times the default; above that it says so plainly instead.

**17. The Beta quantile was wrong, and closed forms caught it.** The per-seat
posterior needed an incomplete-beta inverse, and scipy is not a dependency, so
it is hand-rolled. The first version used a generic Lentz loop returning
`f - 1`, which drops a leading term this particular continued fraction does
not carry. **Beta(1,1) is exactly Uniform(0,1), and it returned a 5th
percentile of 0.0528 instead of 0.0500.** Now the Numerical Recipes recurrence,
checked against four closed forms.

**On the name.** The pass is "Bayesian + MCMC" and what is implemented is
Monte Carlo resampling plus **conjugate** Bayesian posteriors. There is no
Markov chain, and there should not be: draws here are independent and the
binomial posterior has a closed form, so a sampler with burn-in and
convergence diagnostics would add machinery and no accuracy. Calling it MCMC
would overstate what was done. Challenge that judgement if you disagree.

---

## Specific asks for Codex

1. **Find another way for items to leave the matrix silently.** Escalation is
   one route and it is now pinned. Are there others — a seat error dropping a
   whole pass, a duplicate-claim path, a gate returning `BLOCKED`?
2. **Find a way for two seats confirming the same statement to produce
   different claim ids**, now that `calibration_extractor` snaps wording.
   Unicode digits, a full-width asterisk, a minus sign that is not
   HYPHEN-MINUS, an expression split across two lines, `x` for `*`.
   Then the inverse: make the snapper collapse two DIFFERENT propositions
   onto one item.
3. **Find a way to make the panel look more independent than it is.** That is
   the direction that argues for keeping five paid seats.
4. **Attack the interval.** It is a bootstrap over items, unstratified.
   Construct a panel where it is anticonservative — where the true sampling
   error is wider than the reported 90% interval. Then attack the
   `_items_to_resolve` estimate, which assumes 1/sqrt(n) scaling.
5. **Break the saturation guard.** It now distinguishes the two, but on a
   threshold I invented (`mean_accuracy < 0.6`). Construct a panel that is
   genuinely collapsed yet scores below it, or genuinely saturated yet above.
6. **Attack the answer key.** Can `Item.is_true` ever disagree with what
   `ArithmeticGate` computes? Consider integer overflow bounds, `Fraction`
   coercion, unit-splitting (`_split_unit`), and expressions the AST evaluator
   treats differently than Python would.
7. **Confirm no operator material reaches a vendor on this path.** The quiz is
   generated arithmetic and should carry no artifact text at all.
8. **Name any test that would still pass if the behaviour it names were
   deleted.** Name the test and name the deletion. Two were found that way
   here — one that tested a component while the wiring could be removed
   freely, and one whose property could not fail at the size it ran at — so
   assume more remain.
9. **Attack seat exclusion.** A seat is now dropped when it raises or returns
   nothing usable. Find an input where a seat that DID answer gets excluded,
   or where a seat that answered nothing usable still reaches the matrix.

A reply saying "this looks solid" is worth nothing. Assume there is a defect
and go find it.
