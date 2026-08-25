# Re-check request — my own project, before I spend on a live run

You reviewed this at commit `3c22811` and found 5 critical, 19 high and 8
medium defects. I reproduced every one I could and every one was real. Your
executive conclusion was that the tool was not yet safe for a consequential
decision or as a spending boundary, and I agreed with it.

I have changed a lot since. **Before I spend about an hour of real API calls
finding out whether this is useful, I want to know whether the changes hold.**
Please do not take my word for any of it — re-run your own reproductions.

**No credential, no network access, and no live API call is needed.** Everything
below can be established by reading the code and running the offline suite.
`.env` and `profiles.json` hold my live settings; please do not open, print, or
transmit either. Nothing in this review requires them.

Current state: **1009 tests, 82% coverage, ruff / mypy / bandit clean.**

Commits since your review:
```
7ac54f3  connect three controls that were written, tested, and inert
15494e5  plain engineering terms for the safety controls
cad8335  keep the test suite hermetic
8470caa  S1-1, S1-2, S3-5, S4-7
219b3cf  S1-3 to S1-7
f2b5fbc  S2-1, S2-2, S4-2
5791360  S3-1
```

---

## The most important question

**Is the checking layer now sound enough that a five-round paid run would
produce a result I can act on, or would it produce a confident-looking answer
that is not?**

That is the only thing I need settled before running. Everything below is
detail supporting it.

---

## Session A — is a verified warrant now bound to the proposition?

Files: `adjudication_orchestrator.py`, `option_set.py`, `citation_gate.py`,
`quote_gate.py`

This was your S1-1, the critical finding, and it is the one that decides
whether a run is worth doing.

Please re-run your own reproductions:

- Both "The launch is SAFE to proceed, code 4" and "The launch is NOT SAFE to
  proceed, code 4" against the warrant `2 + 2 = 4`.
- The intake path (`gate_candidate_claims`), which you found applied a weaker
  rule than seats were held to.
- A schema-valid JSON warrant beside unrelated prose.
- A page containing "Revenue tripled" offered for "Revenue did not triple".
- `1000000000 = 1000000001`, `9007199254740993 = 9007199254740992`,
  `sqrt(4) = 2`, and `2 ** 1000000000`.
- A citation whose claimed title is the negation of the record's title.
- A resolver record containing `author=[None]`, and one whose `title` is a
  string rather than a list.

My claim: lexical similarity no longer accepts anything. A verified warrant
accepts a claim only when the claim restates that warrant. Citations, schema
validity and located quotes now establish nothing — they rule out fabrication
and stop. Arithmetic compares exactly and refuses what it cannot evaluate
rather than calling it false.

**Please check specifically whether this over-corrected.** If almost everything
now escalates, the tool produces a reading list rather than an answer, and I
would rather know that before paying for one.

## Session B — can the closing model still change the answer?

Files: `night_loop.py`, `option_set.py`

Your S2-1 reproduction was:

```
thinker: CLAIM | arithmetic | 2 + 2 = 5 | Liquidate inventory immediately.
closer:  Liquidate inventory immediately.
```

The claim was refuted and the proposition still reached the packet and seeded
the next round.

I did not write a better detector. Code now holds the option set: round one
parses the closer's list into options with content-addressed ids, later rounds
only remove from it, and removal happens only on a standing FAIL. The text
carried into the next round is assembled from what survived, with the closer's
prose attached as commentary.

Please check: can the closing model still add, remove, reorder into, or
otherwise change membership of that set through prose? Can a removed option
reappear in a later round's prompt by any path?

Also your S2-2: `run_verdict` reported ADJUDICATED from a constructed state
with `failed=1` and a failed closer. Adjudication is now counted from actual
option removals, and reported as two fields — mechanical adjudication and
corroboration confidence — rather than one label.

## Session C — spending

Files: `cost_ledger.py`, `seat_adapter.py`, `rates.json`, `console.py`

I accepted your S3-1 conclusion rather than tuning the multiplier: without a
provider-documented bound for the complete serialised request plus all
billable output, this code cannot offer a hard pre-dispatch ceiling. It no
longer claims to.

What it claims instead: every completed call is reconciled against what the
pre-call check authorised, and a bill more than 5% above it halts the run.

Please check:

- Your three S3-1 triggers: the 1,000,000-character constant body field, the
  `max_tokens=100` under-estimate, and the long-context tier boundary.
- Whether the halt can be bypassed — by a call that reports no usage, by an
  overrun on a different seat, or by any path that reaches transport without
  passing the check.
- S4-7: the guided console paths that ran with no ledger at all.
- S3-5: non-finite and non-positive ceilings.

`max_input_tokens` is null for all five seats in `rates.json`. I did not
invent context limits. The cost report names every unbounded seat on every
run. Please confirm that is actually visible rather than buried.

## Session D — what I know is still open

Stated so you can spend your time elsewhere, and so you can tell me if any of
these is worse than I think — particularly whether any of them can affect a
single interactive run:

- **S3-3**: daily spend accounting is not transactional across processes. Two
  concurrent runs can each be authorised.
- **S4-1, S4-3, S4-4**: the folder watcher can pay for a file a producer is
  still writing, can be defeated by a symlink swapped in after startup, and
  strands its input if the ledger fails to build.
- **S4-5**: pairwise rho cannot justify claims about unanimous agreement.
- **S4-6**: a credential in an endpoint query string can still reach
  `describe()` output.
- **S4-8**: the CI demo step and mypy's explicit file list.
- **S2-4, S2-5**: contamination reasons are conflated, and an exception with an
  empty message produces an empty durable reason.
- **S1-6 remainder**: approved commands get a minimal environment and their
  process tree is killed on timeout, but they are not filesystem- or
  network-isolated.

My reading is that none of D affects a single interactive console run with me
present — no second process, no watcher, no approved commands configured.
**Please tell me if that reading is wrong**, because it is the assumption I am
about to spend real money on.

## Running it

Python 3.11+. No network needed.

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

`python3 run_adjudication.py --demo` exercises the engine on fake models and
costs nothing.

## What I want back

1. **Go or no-go on a paid run**, and if no-go, the single thing to fix first.
2. Findings most serious first, with the input that makes each go wrong.
3. Which of your original findings are closed, which are still open, and which
   I made worse — several of my earlier repairs created the next round's
   defects, so treat these changes as new code.
4. Separate what you executed from what you reasoned about.

If a claim above is not true of the code, the code is the fact.
