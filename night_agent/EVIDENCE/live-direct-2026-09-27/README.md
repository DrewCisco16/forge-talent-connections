# Live DIRECT night on BT-1, 2026-09-27

Records copied verbatim from three runs of `AGENT/run_night.py` with live seats (`claude-opus-5` on every seat,
`--auth cli`, `--budget-usd 5`), from the build container. Seat replies are included only for the run that
conforms (`na-001/`); the other two attempts keep their status, log and the rejected reply or checker lines that
explain them. Costs are the SDK's client-side estimates, not invoices.

| Attempt | Outcome | Sends | Cost estimate (USD) | What it found |
|---|---|---|---|---|
| 1 (`attempt-1/`) | STOP_REASON CREW after 3 sends | 3 | 0.137 | the tool-less generator wrote out pretend commands instead of the three headings, twice; P9 and S0 amended, DIRECT hands the slot to the next generator, the checker tolerates a labelled abandoned stage |
| 2 (`attempt-2/`) | DONE, PROVISIONAL; checker 78 passed, 1 failed | 4 | 0.261 | a document claim without a quote was NOT TESTABLE beside support PARTIAL; document statuses now follow DISPATCH 3.2; DIRECT's open list comes from the reply; the closer's metrics carry the cost |
| 3 (`na-001/`) | DONE, PROVISIONAL; checker 82 passed, 0 failed; 9 guards ALLOW | 4 | 0.259 | the conforming run recorded here |

In every attempt the generator declined to state the sum because project documents reach only the VERIFIER
(spec Section 11), and in attempts 2 and 3 the VERIFIER named the twelve figures and the total 9420 from
figures.csv as CONTRADICTIONS. That is the spec's behaviour, not a runtime fault; see the note in
`TESTS/BENCHMARK_TASKS.md`.

One night is an existence proof that the runtime completes the DIRECT path with real seats and stays within the
checker and the guards. It is not evidence about answer quality, and no HYBRID night has run.
