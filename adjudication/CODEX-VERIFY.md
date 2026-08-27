# Re-check request — my own project, before I authorise a paid run

You have reviewed this three times and returned NO-GO each time. Every finding
reproduced. Two of them were things I had already reported to my operator as
fixed, and one of those failed for a reason worth stating plainly, because it
says more about how I work than about the code: I wrote a constant and its
call site in one script, the script asserted on the second edit and died
before writing anything, the constant landed, the call site did not, and I
reported it done without re-reading the file.

**Assume I have introduced new defects.** This round changed claim acceptance,
elimination, option parsing, merging, the cost planner, the daily spend
ledger, and two exception hierarchies.

## What you do not need

No credential, no network, no live API call. The suite is hermetic and builds
its own fixtures.

`.env` and `profiles.json` hold my live settings. **Please do not open, print,
or transmit either one.** Nothing here requires them.

## Current state

- **1168 tests passing, 81% coverage**
- `ruff check .`, `mypy` (23 source files), `bandit -c pyproject.toml -r .` clean
- Head `1aeac92` on branch `claude/adjudication-test-suite-w27c3h`

```
1aeac92  say estimate where it is an estimate
2925816  the test suite was spending the operator's daily budget
4f03532  two watchers cannot both spend the same daily budget
2dd7f92  an unmetered seat should take saying so
9b34226  the spend controls said more than they enforced
694c365  price every reply, and stop the quote cascade removing answers
d52d1b8  two seats proposing one answer are two advocates for it
35dcc18  a challenger supplies the numbers, never the reasoning
903b2b7  delete the lexical rule instead of repairing it again
```

```
cd adjudication
uv venv && uv pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

## What the tool is

Five models from five vendors answer one hard question independently. Each is
asked to state, for each answer it proposes, a quantity that decides it: the
figure, the formula that produces it, and the numbers going into that formula.
Code recomputes. An answer whose own arithmetic does not produce its own
figure is eliminated. This repeats over five analytical rounds, and whatever
survives is reported alongside an explicit statement of what was never checked.

The commitment: **fail closed on the conclusion, never on the candidate.**

---

## 1. Free-prose acceptance (your critical #1)

You executed, through both `run_pass()` and `gate_candidate_claims()`:

    warrant "2 + 2 = 4"  claim "The launch is 4 and safe to proceed"     PASS
    warrant "2 + 2 = 4"  claim "The launch is 4 and unsafe to proceed"   PASS

The ~250-line lexical warrant-to-proposition rule is **deleted** — content
words, linking verbs, positional assertion splitting, leading tokens. Deleted
rather than disabled, because kept around it reads like a working control and
answers confidently and wrongly.

A gate now reports `WARRANT_HELD`, which is your `WARRANT HELD, PROPOSITION
OPEN`. It renders as those words in the packet and in the closer's input, not
as a status token a reader could mistake for a ruling, and it is routed out of
the section that lists rulings.

**One case still reaches PASS, and I want you to attack it rather than confirm
it.** When the claim's TEXT is itself an assertion the gate can rule on, the
text is fed to that gate as its own warrant. `2 + 2 = 4` parses and holds, so
the claim is verified. `The launch is 4 and safe to proceed` is not an
arithmetic assertion, does not parse, and no prose can make it parse. My
argument is that this is not a lexical rule: the evaluator decides, and the
evaluator has no opinion about launches. If that reasoning is wrong, I would
rather drop the exception than keep it.

## 2. The challenge supplied the reasoning (your critical #2)

You executed:

    PREDICATE | annual launch accidents | = | 4 accidents
    CHALLENGE | <that id> | 2 + 3

and it removed the option. You were right that I had moved the binding defect
rather than fixing it — taken the power from whoever wrote the sentence and
handed it to whoever wrote the expression.

An option now declares its **formula and its inputs** with the figure, fixed
when it is proposed. **What removes it is its own formula with its own inputs
failing to produce its own figure.** That needs nothing from any other seat and
cannot be steered by one.

A challenge may change the **inputs** and nothing else, and **it removes
nothing**. It records that two seats put different numbers into the same
formula and get different answers, and says nobody has established which are
right. An option with no formula cannot be recomputed and is never removed; it
survives, reported untested.

This is close to your prescription, with one deliberate difference: you asked
for challenges with independently obtained inputs, and I could not see how to
establish "independently obtained" mechanically, so challenges do not
eliminate at all. **Please tell me whether that is the right call or an
over-correction.**

## 3, 4, 6 — things lost in silence

Every proposer of an identical answer is retained, and the same figure reached
a different way becomes an alternate route: the figure stands if any route
holds. It had been order-dependent — reversing the seats reversed the outcome,
which means seat names were deciding answers.

An absorbed option whose keeper is refuted now stands on its own; it had
appeared nowhere while the run reported it as the survivor.

Commitment ids include the subject, so `fatalities = 0 people` and
`cost = 0 people` are two commitments.

`Do nothing.` is eleven characters and the floor was twelve. `$12.27`, `95%`,
`2.5 hours/day` and `1e3 dollars` produced no commitment at all. A seat
quoting the contract's own example CHALLENGE line — fenced or indented — had
it executed. A fifth commitment was truncated silently; it is refused now, and
the refusal falls on that option alone rather than the round.

## 5, 7 — protocol and durable output

Both prompts were rewritten. The trusted required-output block asks for
CHALLENGE and no longer claims CLAIM removes anything.

`apply_quote_cascade` no longer eliminates, and no longer bypasses the single
removal function. The finding is not softened: the claim loses its stated
basis, the conduct ledger records the fabrication against the seat, and the
report prints `EVIDENCE WITHDRAWN FROM SURVIVING ANSWERS` — a section that did
not exist, over a collection that was gathered and never printed anywhere.

Option state is recorded before the closer runs. Rulings accumulate across
rounds. `status.md` carries the rulings themselves, not just counts. The
refuted-claim caveat is no longer suppressed by any removal anywhere.

## 8, 9, 10 — confidence and cost

`trustworthy` is connected, and additionally requires the surviving answer to
have had every commitment settled. It states explicitly that it is **not** a
claim the answer is correct — you wrote that measured independence gives a
corroboration ceiling, not evidence the survivor is right, and I have tried to
make the code say only the narrower thing.

The merging seat is charged for its own reply. My corrected estimates match
yours: **$12.68 at the floor, $16.79 as configured.** The ask now enters the
plan. A seat with no configured price refuses the plan rather than being
costed at zero.

`CeilingOverrun` is a `CeilingReached`. The 5% tolerance no longer covers a
crossed run ceiling. `--max-cost` is no longer described as hard, anywhere.

The daily file is written under an exclusive lock, and each dispatch claims
its estimate **before** the call, so two watchers cannot both spend the same
budget. Unmeasured calls persist as their reservation rather than as zero.
`ledger=None` and an omitted ledger are both refused; `UNMETERED` must be
written down.

## What I found after your review, which you did not ask about

**The test suite was writing to the operator's real daily spend ledger.** A
CLI test passing `--max-cost` built a ledger on the default day-state path and
persisted to it, so every test run added fabricated spend to
`.spend-by-day.json` — which had reached **$121 against no paid run that day**.
With a daily ceiling configured, that refuses a real run for a budget nobody
consumed: a fail-closed control doing harm on invented data.

`--day-state` redirects it. The guard is a test that snapshots the shared file,
runs the whole suite in a subprocess, and fails if a byte changed.

I mention it because it is the kind of thing three reviews did not surface, and
it suggests looking at what the tests themselves touch.

## On my own tests

You said some new regressions were vacuous and the concurrency test ran its
writers sequentially. One of mine asserted that a line of code was spelled a
particular way — it would break on a rename and pass on a rewrite that dropped
the condition entirely. Replaced with a behavioural test.

The two concurrency tests here run **real subprocesses**, and I verified each
fails on every attempt with its fix removed. **If any regression I added
passes against a deliberately broken implementation, that is the most useful
thing you could tell me.**

## What I have not established

No live seat has ever emitted a `PREDICATE`, `FORMULA`, `INPUT` or `CHALLENGE`
line. The contract asks for them in the same block seats demonstrably obey for
`CLAIM`, but that is an inference from one observation, not a measurement. If
they do not comply, a run reports that nothing was adjudicated rather than
producing a wrong answer.

I have also narrowed what can eliminate twice now — first off prose, then off
challenger-supplied arithmetic. Fabricated citations and fabricated quotes no
longer remove candidates either. **Please tell me if this is now so narrow that
a paid run cannot produce a useful result.** That is a real failure mode, it
would not show up in any test I have written, and I would rather learn it from
you than from the bill.

## What I am asking

Confirm or refute that the code is built the way I have described, and tell me
whether anything here would mislead someone reading the tool's output.

I am deliberately **not** giving you a checklist: a checklist only finds what I
already thought of, and the last three reviews each found something I had not.

Where you find a defect, state what breaks and under what input so I can
reproduce it before changing anything.

If this still is not ready for a paid run, say so plainly. I will act on it.
