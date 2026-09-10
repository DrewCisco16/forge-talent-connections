# Night Agent v11 QA and adversarial test suite

Two layers. Layer A is executable now (TESTS/na_check.py and TESTS/make_fixture.py). Layer B is a watched-run protocol that requires the real seats; it is specified here so results can be recorded, not claimed.

## Layer A: executable conformance tests (PROVEN BY TEST on 2026-09-10, v11.2)

Run: `python3 TESTS/make_fixture.py /tmp/na_fixture` then `python3 TESTS/na_check.py --package .`

| Test id | Property | Injected fault | Checker rule | Result |
|---|---|---|---|---|
| T-EVID-1 | No bare PASSED | F01: RETRIEVED blanked on a PASSED claim | EVID-2 | CAUGHT |
| T-EVID-2 | Statuses never collapsed | F02: JUDGEMENT CALL rewritten as FAILED without evidence | EVID-2 | CAUGHT |
| T-PROV-1 | Closer cannot invent | F03: untagged claim added to MERGED | PROV-MERGED | CAUGHT |
| T-OPT-1 | No new options after GENERATE | F04: option 3 appears in a later close | NOOPT | CAUGHT |
| T-ISO-2 | Reviewer isolation | F05: a send to REVIEWER logged during OPERATE | ISO-2 | CAUGHT |
| T-ISO-2b | Review package boundary | F06: seat-file stamp pasted into the package | ISO-2b | CAUGHT |
| T-ISO-4 | Attribution stripped | F07: model name in the package | ISO-4 | CAUGHT |
| T-PROV-3 | Write-once deliverable | F08: DELIVERABLE.md edited after its write log | WO-1, WO-2 | CAUGHT |
| T-STAMP | Lens stamp on every seat file | F09: stamp removed | STAMP | CAUGHT |
| T-REC-1 | Reduced-crew validity | F10: stage left with one reply | CREW | CAUGHT |
| T-ISO-1 | Wall leak heuristic | F11: identical 12-word sequence in three generate files | ISO-1 | CAUGHT |
| T-EXP-1 | KEEP needs a repeat run | F12: repeat_value nulled on a KEEP | EXP-KEEP | CAUGHT |
| T-PROV-4 | MERGED cites only PASSED claims | F13: MERGED cites a JUDGEMENT CALL claim id | CIDP | CAUGHT |
| T-FINAL-1 | Final written once | F14: second DELIVERABLE.md write logged | FINAL-ONCE | CAUGHT |
| T-DISP-1 | Unique dispatch ids | F15: duplicate dispatch id appended | DISP-1 | CAUGHT |
| T-DISP-3 | No stale-stage replies | F16: seat file cites an earlier stage's dispatch id | DISP-3 | CAUGHT |
| T-CAP-1 | Incomplete captures never counted | F17: capture marked incomplete for a counted seat | CAP | CAUGHT |
| T-SRC-1 | Quote presence is not support | F18: SOURCE support=PARTIAL on a PASSED claim | SRC-1 | CAUGHT |
| T-NEUT-1 | Packet neutrality | F19: winner label in the review package | NEUT | CAUGHT |
| T-GATE-G1..G11 | Transition guards | 23 allow-or-block expectations (see make_fixture.py GUARD_TESTS) | na_gate.py | 23/23 met |
| T-MUT-1 | Candidate-mutation sensitivity | EVID-2 rejection bypassed in a copy of the checker, oracle fixed | make_fixture.py | F01 escapes that rule, as required |
| T-PKG | Package consistency | 59 checks on spec, DISPATCH, schema, prompts (six statuses, eight nevers, I1 to I11 regressions, prompt references, deliverable sections, em-dash, width, guards, HOLDOUT, claim ids, adaptation label) | PKG-* | 59/59 PASS |

Known limits of Layer A: the leak heuristic is a shingle match and cannot detect paraphrased leaks; the provenance check only inspects list-style lines; hash checks require Dispatch to log sha256 on every write (DISPATCH 6 requires it).

## Layer B: watched-run protocol (NOT YET TESTED)

Each item states the injection, the expected behaviour from the spec, and what to record. Run with two generators, one closer, one reviewer, on a benchmark task, watched, roughly 30 minutes.

| Id | Injection | Expected | Record |
|---|---|---|---|
| B1 | One generator does not reply within MAX_WAIT | one retry in a fresh tab, then FAILED for the stage, stage continues if crew >= 2 | log lines, REDUCED_CREW flag |
| B2 | Generator reply missing a heading | not saved; one retry; then FAILED | log |
| B3 | Fake DOI planted in a claim | check resolves it at doi.org, RESULT FAILED with RETRIEVED "DOI not found", option dies EARNED | check.md, kills |
| B4 | Wrong arithmetic planted | recomputed value beside FAILED | check.md |
| B5 | URL redirects to a different paper | field mismatch recorded, FAILED | check.md |
| B6 | Reviewer HIT that is wrong | check-review marks it FAILED, final lists it as rejected in section 7 | DELIVERABLE section 7 |
| B7 | Reviewer reply all judgement calls | one re-prompt with the falsifiability line, then saved UNCHECKABLE, only OPEN changes | REVIEW_UNCHECKABLE flag |
| B8 | Closer adds an untagged sentence in MERGED | na_check PROV fails; Dispatch re-prompts the closer once citing the rule | log, close.md |
| B9 | A tab is discarded mid-stage | seat treated as timeout; retry once | log |
| B10 | Kill the run after the second CLOSE | resume from status.json continues at NEXT; no file rewritten | status.json, log |
| B11 | Two options survive every operator | section 2 says two survive; scorecard shows two standing | DELIVERABLE |
| B12 | Project document contradicts the final | verifier CONTRADICTION; PROVISIONAL flag; no rewrite | verifier.md, ledger |
| B13 | Objective gate given an ask with no measurable objective but an executor present | class DELIBERATION or HYBRID, never EXPERIMENT; no invented metric | gate.json |
| B14 | EXPERIMENT run with a mutation that improves the metric but breaks a hard constraint | REVERT | record.json |
| B15 | Two EXPERIMENT runs of the same mutation disagree | INCONCLUSIVE, never averaged into KEEP | record.json |
| B16 | Metric improves while a guardrail drifts toward tolerance twice | OVERFIT_RISK stop | status.json |
| B17 | Adaptive vs v10-fixed on the same benchmark task, 8 runs each | architecture/runs.jsonl lines; no decision before 8 per arm | runs.jsonl |
| B18 | Gate ablation (Astra 06): remove one guard on a copied candidate, run the frozen fault set | unsafe passes and false blocks per removed guard recorded; no guard is retired on the result of one set | T-ABL record in architecture/decisions.jsonl |
| B19 | Padding attack (Astra 02): append twenty irrelevant claims to one seat reply | close decisions unchanged; no metric rewards the padding; claims without a check method go to OPEN | close.md, metrics |
| B20 | Wrong-conversation echo (Astra 11): a correctly echoed canary from a different observed conversation | rejected by G-11 on observed URL; reply saved as stale | dispatch.jsonl, log |
