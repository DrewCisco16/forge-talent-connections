# Code review request — my own project

I built this tool and I own it. I am asking for an ordinary engineering review:
correctness, robustness, and whether its safety controls actually hold. There
is nothing here to break into and nothing to demonstrate — I am the operator,
and I want to know where my own code is wrong before I trust it with a decision
that matters.

**You do not need any credential, any network access, or any live API call to
do this review.** Everything below can be established by reading the code and
running the offline test suite. `.env` and `profiles.json` hold my live
settings; please do not open, print, or transmit either one. Nothing in the
review requires them.

The review is split into four sessions so each one is a reasonable amount of
reading. Run them separately; each stands alone.

---

## What the tool does

An operator has a hard question with several possible answers. Five language
models from five different vendors answer it independently, none seeing another
model's response. Then code — not a model — checks every claim it can check
mechanically: it recomputes arithmetic, looks up DOIs, confirms quoted text
appears at the page it was attributed to, checks a cited paper is the paper
named, and runs test commands the operator wrote down in advance.

Answers whose claims are shown false get removed. What survives is consolidated
by one of the models and becomes the starting point for the next round. Five
rounds, five analytical frameworks. The result goes back to the operator to
check independently.

The reason it exists: five models agreeing is not evidence, because they can be
wrong in the same way. The tool only claims value if something was ruled out by
machinery rather than agreed on by models.

## The rules it is supposed to follow

Please check the code against these. Where the code and my description
disagree, the code is the fact.

1. **Independence.** No model sees another's answer within a round.
2. **Three outcomes, not two.** Shown false is removed. Not checkable survives
   and is listed as open — it might be true. Only checked-and-held is accepted.
3. **A check that could not run is not a result.** A timeout, a paywall, or a
   rate limit means nothing was learned, and must never be recorded as a
   finding either way.
4. **Agreement is not verification**, and the output must not present one as
   the other.
5. **No invented figures.** Confidence is limited by measured independence, and
   independence that was not measured is not high independence.
6. **Spending limits are checked before a call, never after.**
7. **The record must say why something failed, not only that it did.**

---

# Session 1 — the checking layer

Files: `adjudication_orchestrator.py`, `citation_gate.py`, `quote_gate.py`,
`doi_resolver.py`, `recency_canary.py`, `approved_test_gate.py`

This is the code that decides what is true, so everything else defers to it.

What I want established:

- A check confirms a **warrant** (an equation, a DOI, a quoted string). Does
  anything let a confirmed warrant mark an **unrelated statement** as verified?
  This was previously possible: `2 + 2 = 4` marked both "the launch is safe"
  and "the launch is unsafe" as verified.
- Does every "could not check" path stay separate from "checked and false"? I
  care most about: an unreachable lookup service, a page behind a subscription
  wall that returns HTTP 200, a page larger than the read limit, and a page in a
  non-UTF-8 encoding.
- `approved_test_gate.py` runs shell commands, and it is the only place this
  tool does. It ships with an empty list and only runs exact strings the
  operator wrote down. Is that list validated strictly enough that a malformed
  file cannot widen it? Does the child process get a minimal environment rather
  than inheriting the operator's settings?
- Does anything the tool fetches on a model's suggestion get restricted to
  ordinary public web addresses?

---

# Session 2 — the round engine and the output

Files: `night_loop.py`, `run_adjudication.py`, `audit_log.py`,
`seat_conduct.py`, `closer-system-prompt.md`

What I want established:

- Within a round, can any model's text reach another model's prompt? This is
  the property the whole design rests on.
- One model consolidates at the end of each round. Can it introduce a statement
  no model proposed, and can that statement reach the operator looking checked?
  It previously could: a merged answer reading "Recommendation: liquidate all
  inventory immediately" was reported as an adjudicated result.
- `run_verdict()` decides whether a run gets labelled ADJUDICATED,
  INCONCLUSIVE, or NOT ADJUDICATED. Can a run that removed nothing be labelled
  ADJUDICATED by any path?
- **I would especially like this decision challenged:** unmeasured independence
  currently yields INCONCLUSIVE rather than NOT ADJUDICATED. My reasoning was
  that independence is not measurable at all in this design, so the stricter
  rule would label every possible run the same way and stop carrying
  information. I may have reasoned that wrong.
- Does the durable record on disk say *why* a model failed, not only which one?

---

# Session 3 — spending limits

Files: `cost_ledger.py`, `seat_adapter.py`, `rates.json`

This tool spends the operator's money on API calls, sometimes overnight with
nobody watching. The limit is the only thing standing between a
misconfiguration and an open-ended bill.

What I want established:

- Is the limit checked before **every** dispatch, including each retry?
- A call that fails or times out still reached the vendor and may still be
  billed. Does it consume budget, or only appear in the report?
- The estimate before a call: is it derived from the actual prompt, and does it
  allow for reasoning tokens? A measured example: a request with a 4,096-token
  cap reported 16,748 total tokens.
- Can a limit be set to a value that cannot restrain anything — a non-finite
  number, or a price of zero?
- Per-stage limits are keyed by a round identifier. Is that identifier actually
  set on the live path, or only in tests?
- The daily total is kept in a shared file. What happens when it is unreadable,
  and what happens when two processes write it at once?

---

# Session 4 — the unattended path and the rest

Files: `watcher.py`, `seat_profiles.py`, `console.py`, `intake.py`,
`correctness_matrix.py`, `seat_independence.py`, `.github/workflows/`

`watcher.py` watches a folder and starts a paid run when a file appears, with
nobody present.

What I want established:

- Is the file the tool pays to answer the same file it inspected? It waits for
  the file to stop changing, then moves it before reading — is that enough to
  be sure a half-written file is not paid for?
- Its folders are inbox / processing / done / failed. Can a failed run end up
  back in the inbox and be paid for again?
- If one file fails, does the loop keep going?
- `seat_independence.py` computes what five agreeing models are actually worth.
  `measure_rho` currently returns "not measurable" with a reason rather than a
  number, because a check result says whether a *claim* held and the statistic
  needs whether each *model* was right. Is that reasoning sound, or is there a
  measurement available that I have missed?
- Do the CI steps in `.github/workflows/` actually fail when they should? They
  previously had lists of filenames that stopped covering new code.

---

## Running it

Python 3.11 or newer. No network needed.

```
cd adjudication
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/bandit -q -c pyproject.toml -r .
.venv/bin/python -m pytest --cov --cov-fail-under=80
```

`python3 run_adjudication.py --demo` runs the whole engine against fake models
and costs nothing.

## Known gaps, so you do not have to find them

- `console.py` and `intake.py` are untested — about 480 lines of terminal
  prompting.
- The three citation checks want different warrant formats, so no single format
  satisfies all of them.
- The consolidating model is checked after the fact rather than being limited to
  formatting a list that code produced. I am aware this is the weaker design.

## What I would like back

Findings, most serious first, each with the specific input or state that makes
it go wrong. Please separate what you ran and observed from what you reasoned
about but did not run — I have had reviews where everything was plausible and
none of it had been executed.

If something I have written above is not true of the code, the code is the
fact. If you think the design itself is wrong, that is more useful to me than a
list of small things.
