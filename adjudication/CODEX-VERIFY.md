# Re-check request — my own project, before I authorise a paid run

Your last verdict was **NO-GO for a decision-grade five-round paid run at
`3701fc1`**, and every finding in it reproduced. Two of them were things I had
told the user were fixed. I have rebuilt the part you said was structurally
wrong rather than patching it again.

**Please do not take my word for any of it.** Re-derive the behaviour from the
code and the offline suite, and assume I have introduced new defects — I
changed elimination, option parsing, merging, cost planning, usage accounting
and two gates in one pass.

## What you do not need

No credential, no network access, no live API call. The suite is hermetic and
builds its own fixtures.

`.env` and `profiles.json` hold my live settings. **Please do not open, print,
or transmit either one.** Nothing here requires them.

## Current state

- 1166 tests passing, 82% coverage
- `ruff check .`, `mypy`, `bandit -c pyproject.toml -r .` clean
- Head `cbf498c` on branch `claude/adjudication-test-suite-w27c3h`

```
cbf498c  an overrun stops the next call, which is not halting the run
e964d7f  the two citation gates rejected each other's format
22bb909  an empty survivor list is falsey, and that decided a run
d5b979e  the cost figure was an estimate calling itself a worst case
2f17057  a merge groups answers; it does not delete them
b66723b  elimination rests on typed commitments, not on sentences
```

```
cd adjudication
uv venv && uv pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

## 1. Structural proposition binding

You reproduced this, and it is the finding everything else waited on:

    warrant "2 + 2 = 4"  claim "The launch is 4 and safe to proceed"     PASS
    warrant "2 + 2 = 4"  claim "The launch is 4 and unsafe to proceed"   PASS

I agree with your reading. Two contradictory propositions cannot both follow
from one warrant, so the rule was the wrong kind of rule, and my previous fix
closed those two strings rather than the property.

**Sentences no longer remove anything.** An option declares a quantity, a
relation and a value when it is proposed. A later round removes it only by
computing that quantity and finding it came out otherwise. There is no text
field in the comparison.

This follows the five points you set out. Whether the code actually does what
I describe is what I am asking you to establish:

1. Options carry typed, candidate-owned commitments, parsed from the
   proposing seat's own reply and bound by position to its OPTION line.
2. A later round may `CHALLENGE` an existing commitment by id. A challenge
   naming an id that does not exist is discarded, and a `PREDICATE` line in a
   later round creates nothing.
3. The gate evaluates an expression and compares. It never reads prose.
4. One function decides removal, and it needs a pre-existing declared
   commitment to have been refuted.
5. Both engines call it. The legacy path removed a candidate for **any**
   failed claim it carried, with no binding test at all — the weaker of two
   rules for one question, and the one that decided whenever it ran.

Commitment ids include the option they bind to, which closes the collision you
found where one claim aimed at two options removed both.

**This narrows what can eliminate, and I want you to judge whether I narrowed
it too far.** A fabricated citation no longer removes the candidate carrying
it; it is recorded, counted, and reported. My reasoning is that refuting a
citation refutes the evidence rather than the answer, which is the same
non-sequitur in a different costume — but it is a real capability loss and I
would rather you challenge it than not. A refuted claim that removes nothing
is now named in the caveats, because an option that is neither eliminated nor
unexamined would otherwise carry a demonstrably false statement with nothing
in the tally to show it.

## 2. Silently omitted options

All of your parser reproductions are addressed, except that I chose **refusal
over reprompt**: a round one that yields no options stops the run rather than
asking again. Measured, that is 6 model calls instead of 30.

Both declared forms are now read — an explicit line used to win outright and
drop a valid heading. Fenced examples are excluded. One seat flooding no
longer empties the whole pool. The ceiling bounds the pool rather than each
reply, which is where 5 × 30 = 150 came from. Seats that declared nothing are
named in the record.

## 3. Merging

A merge now groups. The absorbed wording stays a candidate, keeps its own
commitments, and is shown under its keeper. You were right that this was a
model's semantic judgment changing membership.

## 4. Cost

You were right that `$7.00 worst case` was neither. Two compounding errors:

The planner priced every call at a flat 4,000 input tokens. The merging seat
quotes every reply in full, so its prompt is linear in the thinker caps —
measured at 29,511 tokens for a 4,096-token cap, 49,991 for 8,192, 90,951 for
16,384. It was undercounted by more than seven times.

And the merging seat's floor was 8,192 with a docstring calling it measured.
It was not. The failure was at 7,190 and the success at 16,384; 8,192 sat in
the untested gap.

**Honest numbers for five rounds with this panel: $12.27 at the floor, $16.39
as configured.** The field is called `estimate`, because nothing here can
bound what a provider bills.

Also fixed: the floor was skipped when the configured panel already fitted;
scaling could raise a cap **above** what the operator configured while
reporting caps had been reduced; and planning now runs before `.env` is read,
which is what its comment already claimed.

## 5, 6, 7

A vendor total that is present and unreadable no longer reads as absent — the
call is unmeasured and the authorisation stands. "Halts the run" is corrected
to what it does: refuses the next dispatch, with nothing to refuse on the last
call.

Elimination runs before the closer, so a closer that raises no longer strands
a refuted option. Whether a round observed the option set is recorded apart
from what it found. An option is examined only when **every** commitment is
settled. Eliminating every option no longer reports completion in the same
words as narrowing to one survivor.

Both citation gates read one format through one parser.

`trustworthy` required confidence to equal `"MEASURED"`, which no run can
produce. It now requires a measurement that cleared the low bar, and I would
like you to check that reasoning too: I take measured-but-LOW to be
insufficient, because Low is what a high correlation earns.

## What I have not established

The transcripts from my last paid run predate this contract, so replaying them
gives 13 options and **zero commitments** — nothing eliminable. Whether live
seats will actually emit `PREDICATE` and `CHALLENGE` lines is unverified. The
contract asks for them in the required-output block, which is the block seats
demonstrably obey for `CLAIM`, but that is an inference and not a measurement.
If they do not comply, the run reports that nothing was adjudicated rather
than producing a wrong answer — which is the direction I want it to fail in,
but it would mean the tool does not yet work.

## What I am asking

Confirm or refute that the code is built the way I have described, and tell me
whether anything here would mislead someone reading the output.

I am not giving you a checklist, because a checklist only finds what I already
thought of. If something is wrong that I have not mentioned, that is the most
useful thing you could tell me — particularly anywhere I have traded a real
capability for safety without saying so.

Where you find a defect, state what breaks and under what input so I can
reproduce it before changing anything.

If this still is not ready for a paid run, say so plainly. I will act on it.
