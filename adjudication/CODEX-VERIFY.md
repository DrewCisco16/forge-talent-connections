# Re-check request — before I authorise a paid run

Your verdict at `cbf498c` was NO-GO, and every finding reproduced. Two of
them — the contradictory-conclusions PASS and the `trustworthy` repair — were
things I had reported to my operator as fixed. They were not.

The second of those is worth stating plainly, because it says something about
how I work rather than about the code: I had written both the constant and the
call site in one script, the script asserted on the second edit and died
before writing, and I reported the result without re-reading the file. The
constant landed, the call site did not.

**Please assume I have introduced new defects.** This round changed
acceptance, elimination, option parsing, merging, the cost planner, the daily
ledger and two exception hierarchies.

## What you do not need

No credential, no network, no live call. The suite is hermetic.

`.env` and `profiles.json` hold live settings. **Please do not open, print, or
transmit either.** Nothing here requires them.

## Current state

- 1165 tests passing, 81% coverage
- `ruff check .`, `mypy`, `bandit -c pyproject.toml -r .` clean
- Head `4f03532` on `claude/adjudication-test-suite-w27c3h`

```
4f03532  two watchers cannot both spend the same daily budget
2dd7f92  an unmetered seat should take saying so
9b34226  the spend controls said more than they enforced
694c365  price every reply, and stop the quote cascade removing answers
d52d1b8  two seats proposing one answer are two advocates for it
35dcc18  a challenger supplies the numbers, never the reasoning
903b2b7  delete the lexical rule instead of repairing it again
```

## 1. Free-prose acceptance

You executed:

    warrant "2 + 2 = 4"  claim "The launch is 4 and safe to proceed"     PASS
    warrant "2 + 2 = 4"  claim "The launch is 4 and unsafe to proceed"   PASS

The 250-line lexical warrant-to-proposition rule is **deleted**, not disabled
— content words, linking verbs, positional splitting, leading tokens. Kept
around it reads like a working control and answers confidently and wrongly.

A gate now reports `WARRANT_HELD`: the evidence checked out, the proposition
is open. That is your `WARRANT HELD, PROPOSITION OPEN`, and it renders that
way in the packet and in the closer's input rather than as a status word a
reader could mistake for a ruling.

**One case still reaches PASS and I want you to attack it.** When the claim's
TEXT is itself an assertion the gate can rule on, the text is fed to that gate
as its own warrant. `2 + 2 = 4` parses and holds. `The launch is 4 and safe to
proceed` is not an arithmetic assertion, does not parse, and no prose can make
it parse. My argument is that this is not a lexical rule — the evaluator
decides, and the evaluator has no opinion about launches. If that reasoning is
wrong I would rather hear it than keep the exception.

## 2. The challenge supplied the reasoning

You executed:

    PREDICATE | annual launch accidents | = | 4 accidents
    CHALLENGE | <that id> | 2 + 3

and it removed the option. You were right that I had moved the binding defect
rather than fixing it.

An option now declares its FORMULA and INPUTS with the figure, fixed when it
is proposed. **What removes it is its own formula with its own inputs failing
to produce its own figure.** That needs nothing from any other seat.

A challenge may change the **inputs** and nothing else, and **it does not
remove anything**. It records that two seats put different numbers into the
same formula and get different answers, and says nobody has established which
inputs are right. An option with no formula is never removed; it survives,
reported untested.

## 3, 4, 6 — things silently lost

Every proposer of an identical answer is kept, and the same figure reached a
different way is an alternate route: the figure stands if any route holds. It
was order-dependent — reversing the seats reversed the outcome.

An absorbed option whose keeper is refuted now stands on its own.

Commitment ids include the subject, so `fatalities = 0 people` and
`cost = 0 people` are two commitments.

`Do nothing.` is eleven characters and the floor was twelve. `$12.27`, `95%`,
`2.5 hours/day` and `1e3 dollars` produced no commitment at all. A seat
quoting the contract's own example CHALLENGE line had it executed. A fifth
commitment was truncated — refused now, and the refusal falls on that option
alone.

## 5, 7 — protocol and durable output

Both prompts were rewritten; the trusted required-output block asks for
CHALLENGE and no longer claims CLAIM removes anything.

`apply_quote_cascade` no longer eliminates. The finding is not softened: the
claim loses its stated basis, the conduct ledger records it, and the report
prints `EVIDENCE WITHDRAWN FROM SURVIVING ANSWERS` — a section that did not
exist, on a collection that was gathered and never printed anywhere.

Option state is recorded before the closer runs. Rulings accumulate across
rounds. `status.md` carries the rulings themselves, not just counts. The
refuted-claim caveat is no longer suppressed by any removal anywhere.

## 8, 9, 10 — cost and confidence

`trustworthy` is connected, and now also requires the surviving answer to have
had every commitment settled. It says explicitly that this is **not** a claim
the answer is correct. You wrote that measured independence gives a
corroboration ceiling, not evidence the survivor is right; I have tried to
make the code say the narrower thing.

The merging seat is charged for its own reply. Corrected estimates match yours
exactly: **$12.68 at the floor, $16.79 as configured.** The ask now enters the
plan. A seat with no configured price refuses the plan instead of being costed
at zero.

`CeilingOverrun` is a `CeilingReached`. The 5% tolerance no longer covers a
crossed run ceiling. `--max-cost` is no longer called hard.

The daily file is written under an exclusive lock, and each dispatch **claims
its estimate before the call**, so two watchers cannot both spend the same
budget. Unmeasured calls persist as their reservation rather than as zero.
`ledger=None` and an omitted ledger are both refused; `UNMETERED` has to be
written down.

## On my own tests

You said some new regressions were vacuous and the concurrency test ran its
writers sequentially. One of mine asserted a line of code was spelled a
particular way — it would break on a rename and pass on a rewrite that dropped
the condition. Replaced with a behavioural test.

The two concurrency tests here run **real subprocesses**, and I verified each
fails on every attempt with its fix removed. If you find others that pass
against a broken implementation, that is the most useful thing you could tell
me.

## What I have not established

No live seat has ever emitted a `PREDICATE`, `FORMULA`, `INPUT` or `CHALLENGE`
line. The contract asks for them in the block seats demonstrably obey for
`CLAIM`, but that is an inference. If they do not comply the run reports that
nothing was adjudicated rather than producing a wrong answer.

I have also narrowed what can eliminate, twice. Please tell me if it is now so
narrow that a paid run cannot produce a useful result — that is a real failure
mode and I would rather know before spending than after.

## What I am asking

Confirm or refute that the code is built as described, and tell me whether
anything would mislead someone reading the output. No checklist: a checklist
only finds what I already thought of.

If this still is not ready, say so plainly. I will act on it.
