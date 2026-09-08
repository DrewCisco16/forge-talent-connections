# The prompt for ChatGPT Codex

Two versions. **Use A if you can point Codex at the repository** — it can run
the code, and a reviewer that runs things finds what a reader cannot. Use B if
you are pasting text into a chat window.

Before either: **never paste `.env` or `profiles.json`.** They hold your keys.
The bundles contain no credentials and the generator refuses to write one that
does, but those two files are not code and must not leave your machine.

---

## A — Codex with repository access (preferred)

> Copy everything between the lines.

---

You are reviewing a tool called **Elimination Protocol Five**, on branch
`claude/adjudication-test-suite-w27c3h` of `DrewCisco16/forge-talent-connections`.
The code is in `adjudication/`.

**What it does.** It runs one artifact past five different AI models — five
"seats" — one analytical pass at a time, verifies each claim they make with
deterministic code gates, and reports which candidate answers survive. Nothing
is voted on or scored: candidates are only ever *removed*, and only by a gate
that failed.

**The claim the whole design rests on:** when several models agree, the
agreement is worth something *only if* the models fail in different ways. If
they share a blind spot they will agree on a wrong answer and that agreement
will look like confidence. `calibrate.py` is the module that measures which of
those two things is happening. It is the newest code and the most dangerous.

**Read these first, in this order:**
1. `adjudication/REVIEW-BRIEF.md` — what the system is and the review rules
2. `adjudication/CALIBRATION-REVIEW.md` — the calibration module in detail,
   the seventeen defects already found in it, and the nine things its author
   is *not* confident about
3. `adjudication/CALIBRATING.md` — what the operator is told

**Then run it. Do not review it by reading alone.**

```
cd adjudication
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q                     # expect 1230 passing
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/bandit -q -c pyproject.toml -r .
.venv/bin/python calibrate.py --demo              # no network, no cost
.venv/bin/python calibrate.py --demo-collapsed
.venv/bin/python run_adjudication.py --demo
```

**Do NOT run anything that makes a network call.** `calibrate.py --profiles`
and the `calibrate` GitHub workflow spend real money against five vendor APIs.
The `--demo` paths are synthetic and safe.

### What I want from you

**Try to break it. Do not review it.** A reply that says "this looks solid" is
worth nothing. Assume there is a defect and go find it.

The failure mode that matters here is **not a crash**. It is a plausible
number that a spending decision then rests on. Every one of the seventeen
defects already found was of that shape: nothing raised, nothing turned red,
and the run printed a confident figure computed from evidence that had
silently fallen out. Four separate analytical passes each found more of them
in code that was already "done, tested and green" — 2, then 7, then 5, then 3.
**Assume you are the fifth such pass.**

Attack in this order:

1. **Find a way for evidence to leave the measurement silently.** Items that
   never reach the matrix, claims that escalate instead of being ruled on,
   seats excluded or included wrongly, rows that correlate by construction.
   For each: what would the operator see, and would anything look wrong?

2. **Find a fail-open path anywhere in the system.** Any place an error, a
   missing value, a timeout, or a malformed input results in something being
   *accepted* rather than *refused*. This is the highest-value bug class in
   this codebase.

3. **Break the blinding.** Find any route by which a seat could learn another
   seat's answer, a gate verdict, or which passes have run — including
   indirect routes: shared mutable state, ordering effects, error messages,
   anything logged and re-read.

4. **Attack the statistics.** `rho` now carries a bootstrap interval and the
   verdict is decided by the interval rather than the point estimate.
   Construct a panel where that interval is *anticonservative* — where true
   sampling error is wider than the reported 90%. Then attack the
   `_items_to_resolve` estimate, which assumes 1/sqrt(n) scaling.

5. **Attack the answer key.** Can `Item.is_true` ever disagree with what
   `ArithmeticGate` computes for the same expression? Consider integer bounds,
   `Fraction` coercion, unit splitting, Unicode digits, and expressions the
   AST evaluator treats differently from Python.

6. **Name any test that would still pass if the behaviour it names were
   deleted.** Name the test and name the deletion. Several were found that
   way already — one tested a component while the wiring could be removed
   freely; another asserted a property at a size where it could not fail.
   Assume more remain.

7. **Check the thresholds that drive spending.** `0.2`, `0.5`, and a
   saturation cut at `mean_accuracy < 0.6` are conventions the author chose,
   not values derived from anything. Say whether they are defensible.

### How to report

For every finding, give me all five of these. A finding without them is not
actionable and I will not be able to tell a real defect from a guess:

- **File and line.**
- **What breaks** — one sentence.
- **A concrete reproduction** — inputs and the wrong output. Ideally a failing
  test I can paste into `test_calibrate.py` or `test_suite.py`.
- **Which direction the error runs** — does it make the panel look *more*
  independent (flattering, therefore dangerous) or less?
- **Severity**, and say plainly whether it is a real defect, a robustness
  nit, or a matter of taste. Do not inflate.

Then, separately:

- **What you could NOT check**, and why. This matters as much as the findings.
- **Anything in `CALIBRATION-REVIEW.md`'s "what I am NOT confident about"
  section that you think is understated or overstated.**
- Your judgement on one specific question the author flagged: the pass is
  named "Bayesian + MCMC" but what is implemented is Monte Carlo resampling
  plus *conjugate* Bayesian posteriors, with no Markov chain — on the grounds
  that draws are independent and the binomial posterior is closed-form, so a
  sampler would add machinery and no accuracy. Is that the right call?

If you find nothing in a category, say "nothing found in category N" rather
than padding.

---

## B — pasting into a chat window

Paste `REVIEW-BRIEF.md`, then `CALIBRATION-REVIEW.md`, then the prompt above
(dropping the "Then run it" commands and replacing them with *"You cannot run
the code; review by reading, and say clearly which findings you could not
verify"*). Then paste **one bundle per message**.

Generate the bundles first — they are gitignored, so they are not in the repo:

```
cd adjudication && python make_review_bundles.py
```

| Bundle | Covers | Approx. tokens |
|---|---|---|
| `bundle-8-calibration.txt` | **Start here** — calibration, canary | 28,000 |
| `bundle-1-math.txt` | Statistics, run-to-rho join | 11,800 |
| `bundle-2-orchestrator.txt` | Gates, blinding, five passes, stopping | 28,800 |
| `bundle-3-io.txt` | Network, settings, audit log, CLI | 34,900 |
| `bundle-5-verification.txt` | Cost ceilings, DOI, seat conduct | 25,800 |
| `bundle-6-intake.txt` | Intake, domain profiles, console | 38,300 |
| `bundle-7-execution.txt` | Test runner, canary, folder watcher | 10,200 |
| `bundle-4-tests.txt` | Core test suite | 69,400 |
| `bundle-4b-tests.txt` | Subsystem tests | 55,000 |

Each bundle carries its own targeted question at the top — that question is
what to hold the reviewer to for that bundle.

**Ask Codex on its own.** Do not show it Gemini's answer, or Gemini its. That
is the same blinding rule this tool enforces on its own seats, for the same
reason: two reviewers who have seen each other stop being two reviewers.
