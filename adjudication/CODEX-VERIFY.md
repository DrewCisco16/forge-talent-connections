# Re-check request — my own project, before I authorise a paid run

This is my code. I am asking you to check my work before I spend real money
on it, because I am the only person reviewing it and I would rather find a
problem now than in the results.

You have reviewed this twice. Both times you found real defects and both times
I reproduced them. Your last verdict was **NO-GO for the five-round paid run —
fix structural proposition binding first.** I believe that is now fixed, along
with a set of failures that only appeared once I paid for live runs and read
what the models actually wrote back.

**Please do not take my word for any of it.** Re-derive the behaviour yourself
from the code and the offline test suite.

## What the tool is

Five language models from five different vendors answer one hard question
independently, without seeing each other. Each is asked to state its claims in
a fixed line format with the evidence attached. Code then checks the evidence
mechanically — arithmetic is evaluated, citations are resolved, quotes are
matched against sources. A claim that is mechanically refuted eliminates the
answer it was declared to be about. This repeats over five analytical rounds,
and whatever survives is reported alongside an explicit statement of what was
never checked.

The design commitment is that **it fails closed on the conclusion and never on
the candidate.** A demonstrably wrong answer is eliminated. An answer nobody
could check survives and is listed as open rather than accepted. Only a
verified answer is presented as verified.

## What you do not need

No credential, no network access, and no live API call. Everything here can be
established by reading the code and running the offline suite.

`.env` and `profiles.json` hold my live settings. **Please do not open, print,
or transmit either one.** Nothing in this review requires them; the suite is
hermetic and builds its own fixtures.

## Current state

- 1138 tests passing, 81% coverage
- `ruff check .`, `mypy`, and `bandit -c pyproject.toml -r .` all clean
- Head commit `3701fc1` on branch `claude/adjudication-test-suite-w27c3h`

```
3701fc1  the option set was the seats' premises, not their answers
420e13e  Size the run to the ceiling instead of refusing when it does not fit
1c1fc83  What a paid canary found that no dry run could
1b35d52  The over-correction you warned about: quantity claims usable again
d70dc0c  Re-check #11: the night path checks citations
a970b3c  Re-check #3: the option set comes from the seats, not the closer
```

## How to run it

```
cd adjudication
uv venv && uv pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

## What changed since your last review

I am describing what I intended and what I observed. **Whether the code does
this is the question I am asking you** — please establish it independently
rather than confirming my account.

### 1. The option set was the seats' premises, not their answers

I replayed the last paid run's five real transcripts through the parser
offline. Round one produced ten "options". Eight were one seat's numbered
premise list — "The panel consists of five AI seats", "Each round costs
approximately six API calls across five vendors". The three answers that seat
actually proposed, written as `### Option 1: Static-State Termination`
headings, were not among them.

The panel would have spent five rounds and real money adjudicating its own
setup while the real candidates were never on the table, and nothing in the
output would have said so.

My reading is that telling a premise from a proposal is a question of what the
writer meant, and no amount of layout carries it. So the seat now has to say
which it is. Bare numbering no longer declares an option. A heading that names
itself one does — four of five seats wrote exactly that unprompted, in four
different house styles. The fifth wrote bold numbered lines with no such word
and now contributes nothing, on the reasoning that an empty option set is
recoverable and a wrong one is not.

### 2. No seat ever wrote the line the parser was built around

Every seat obeyed the `CLAIM |` convention faithfully. Not one wrote an
`OPTION |` line. Options were requested in a mid-prompt section, while the
required-output block said "write your analysis normally, then end with claim
lines". The seats followed the output contract, which is what an output
contract is for.

The option line now lives in that same contract, and only in rounds that
invent options.

### 3. Caps were planned in one caller and not in the others

Reply-size caps are sized to the operator's spending ceiling. Only the canary
script did that, and it does not go through the shared entry point — so the
console and the folder watcher, the two ways a real run is actually started,
ran with whatever the profile file happened to say. That is a $25.51 worst
case for five rounds, which the ceiling would then stop mid-run, after paying
for the rounds already completed.

Planning moved inside the shared entry point, before the panel is built, so a
run that cannot fit its ceiling is turned away without reading a credential.

### 4. The merging seat needs more room than a thinker

It reads every other seat's reply plus the option list plus the check results,
and on a reasoning model the thinking counts against the same cap. Scaling
every seat by one uniform factor starved it: at 7,190 tokens it was cut off
before writing a single character, the merge failed, and a paid run ended
after round one. It completed at 16,384. It now has a floor of its own.

A five-round run now fits a **$7.00** worst case, down from $25.51.

### 5. A cost refusal is not a crash

A run refused for cost used to reach the watcher's generic handler and be
written out as a stack trace in the failures folder. Nothing had failed and
nothing had been spent — the ceiling simply could not fund the run. It is now
recorded as a refusal that names the figure that would resolve it.

## What I observed offline afterwards

Replaying the same five real transcripts: 13 options, no premises. A declared,
mechanically refuted claim in round two removes exactly the option it names,
leaving 12. The run reports `MECHANICAL ADJUDICATION: PARTIAL` and
`CORROBORATION CONFIDENCE: UNMEASURED`.

**Please check whether that last part is honest.** The tool is supposed to
report error correlation between seats as unmeasured, because I do not believe
it is measurable from open-ended generation — a seat that never raised a claim
has not been shown right or wrong about it, and that is missing data rather
than agreement. If you think that reasoning is wrong, or that the code
overclaims anywhere else, I would rather hear it now.

## What I am asking

Confirm or refute that the code is built the way I have described, and tell me
whether anything here would mislead someone reading the tool's output.

I am specifically **not** giving you a checklist, because a checklist only
finds what I already thought of. If something is wrong that I have not
mentioned, that is the most useful thing you could tell me.

Where you find a defect, please state what breaks and under what input, so I
can reproduce it before changing anything.

If your conclusion is that this is not ready for a paid run, say so plainly.
That is a useful answer and I will act on it.
