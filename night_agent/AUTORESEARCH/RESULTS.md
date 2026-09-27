# RESULTS: autoresearch pass on Night Agent v11.2.0, producing v11.3.0

Date 2026-09-10. Stop reason: SUFFICIENT (every corpus case caught or blocked, every guardrail at zero, every package assertion passing), reached at experiment 47 of a budget of 48.

## Bottom line

| Measure | v11.2.0 (baseline) | v11.3.0 (kept tree) |
|---|---|---|
| run-folder faults caught, DEV | 3/36 | 36/36 |
| run-folder faults caught, HOLDOUT | 3/34 | 34/34 |
| transitions blocked by the guard, DEV | 0/10 | 10/10 |
| transitions blocked by the guard, HOLDOUT | 1/10 | 10/10 |
| false FAIL lines on conforming runs (guardrail) | 3 | 0 |
| false BLOCKs on legitimate transitions (guardrail) | 1 | 0 |
| package assertions passing (secondary) | 3/15 | 15/15 |
| package self-audit checks (`na_check.py --package`) | 59 | 76 |
| package's own fixture suite (19 faults, 23 guard expectations, sensitivity) | green | green, and the fixture itself now conforms |

Every number is reproducible with `python3 AUTORESEARCH/eval.py` on the respective commit. The measurement is deterministic (two baseline runs were identical), so no interval is reported; a delta of one case is real.

## What this does and does not show

PROVEN BY TEST: the v11.2.0 checker and guards, which pass their own 19-fault fixture perfectly, caught 6 of 70 spec-derived faults and blocked 1 of 20 spec-derived bad transitions written outside that fixture, and reported three failures on a conforming DIRECT run plus one false block. The v11.3.0 tree catches and blocks all of them with no false result. The spec's own rules were the source of every case (each case names its section).

DESIGN JUDGEMENT: which rules became cases, and the DEV/HOLDOUT assignment. The same agent wrote the corpus and then edited the checker. In the spec's own Section 8 terms that makes the corpus DEV-grade; a HOLDOUT that carries full weight needs a second author who has not read the checker. The DEV/HOLDOUT split still did work: it refused three experiments (exp-006, exp-019, exp-025) whose DEV case was caught for a reason other than the rule under test, and each refusal exposed a corpus flaw that was then fixed and logged (obj-001 to obj-006).

NOT TESTED, NOT CLAIMED: any real night. No model seat was called. Whether a night under v11.3 produces better answers than under v11.2 or v10 is the spec's Section 8 question and needs paired nights with real seats. NO_AUTORESEARCH_SUPERIORITY_CLAIM stands. The three WORKBOOKS PDFs were not rebuilt (P4 changed; the build needs reportlab and a font folder that were not available here) and are STALE for P4.

## Deviations from the frozen program, all logged in log.jsonl

- obj-001 to obj-006: corpus corrections after the DEV-only rule refused an experiment for a corpus flaw (a family that was not a same-rule pair; a compound fault; an incidental unlogged write). Each was logged, the kept tree re-measured, and the experiment re-run under a new id.
- obj-003: the fixture suite's exit code now also covers its conforming fixture (before, a checker rule that broke the package's own fixture would have passed the guardrail).
- obj-007: the experiment budget was raised from 40 to 48 before experiment 33, because 40 was set before the corpus had been enumerated into rule families.
- obj-008, obj-009: two package assertions were corrected because as written they could never pass whatever the documents said (a token regex that could not see CONTAMINATION or PROVISIONAL; a section scan that counted STOP_REASON as a flag).

## The trail: 47 experiments, 43 KEEP, 1 REVERT, 3 INCONCLUSIVE

Each KEEP is a git commit whose message starts with the experiment id. A REVERT or INCONCLUSIVE commits only its log line. Columns: faults caught (DEV+HOLDOUT of 70), transitions blocked (of 20), false FAIL lines, false blocks, package assertions (of 15).

| Id | Decision | Hypothesis | Files | Before | After | Newly caught or blocked |
|---|---|---|---|---|---|---|
| exp-001 | KEEP | na_check treats a DIRECT run as the spec describes it: one generator, a check, no close, no reviewer | TESTS/na_check.py | 6 / 1 / 3 / 1 / 3 | 6 / 1 / 0 / 1 / 3 |  |
| exp-002 | KEEP | G-3 accepts one seat file for a DIRECT stage, stated in the gate, the spec row and SCHEMA together | TESTS/na_gate.py, NIGHT_AGENT_SPEC.md, SCHEMA.json | 6 / 1 / 0 / 1 / 3 | 6 / 1 / 0 / 0 / 4 |  |
| exp-003 | KEEP | a claim with METHOD none can only be JUDGEMENT CALL; PASSED or FAILED on it is rejected by the checker and by G-4 | TESTS/na_check.py, TESTS/na_gate.py, NIGHT_AGENT_SPEC.md, SCHEMA.json | 6 / 1 / 0 / 0 / 4 | 8 / 2 / 0 / 0 / 4 | E01a, E01b, GA07b |
| exp-004 | KEEP | G-4 blocks a close when a PASSED source or document claim lacks support=SUPPORTED grade=A, so a quote alone never reaches the closer | TESTS/na_gate.py, NIGHT_AGENT_SPEC.md, SCHEMA.json | 8 / 2 / 0 / 0 / 4 | 8 / 3 / 0 / 0 / 4 | GA07a |
| exp-005 | KEEP | a SOURCE line without a support= status is an unfinished admission record; the checker rejects it | TESTS/na_check.py | 8 / 3 / 0 / 0 / 4 | 9 / 3 / 0 / 0 / 4 | E03b |
| exp-006 | INCONCLUSIVE | a claim id that appears twice makes every citation of it ambiguous; the checker requires ids unique across all check files | TESTS/na_check.py | 9 / 3 / 0 / 0 / 4 | 12 / 3 / 0 / 0 / 4 | E04a, E04b, O04a |
| exp-007 | KEEP | a claim id that appears twice makes every citation of it ambiguous; the checker requires ids unique across all check files (re-run of exp-006 after obj-001) | TESTS/na_check.py | 9 / 3 / 0 / 0 / 4 | 12 / 3 / 0 / 0 / 4 | E04a, E04b, O04a |
| exp-008 | KEEP | reviewer provenance exists only from REVIEW onward: check-review claims are [R], and a stage MERGED neither carries [R] nor cites a review claim id | TESTS/na_check.py | 11 / 3 / 0 / 0 / 4 | 14 / 3 / 0 / 0 / 4 | E07a, E07b, E08a |
| exp-009 | KEEP | empty braces are not a citation: a MERGED or final line must cite at least one claim id | TESTS/na_check.py | 14 / 3 / 0 / 0 / 4 | 16 / 3 / 0 / 0 / 4 | E09a, E09b |
| exp-010 | KEEP | no option after GENERATE applies to the review package and the deliverable too: option numbers there must come from the generate list | TESTS/na_check.py | 16 / 3 / 0 / 0 / 4 | 18 / 3 / 0 / 0 / 4 | O01a, O01b |
| exp-011 | REVERT | only two things kill: every KILLS entry must name a FAILED claim or an explicit hard constraint; the package fixture's own kill line is reworded to say which | TESTS/na_check.py, TESTS/make_fixture.py | 18 / 3 / 0 / 0 / 4 | 20 / 3 / 0 / 0 / 4 | O02a, O02b |
| exp-012 | KEEP | only two things kill: every KILLS entry must name a FAILED claim or an explicit hard constraint; the package fixture's own kill line now says which (exp-011 re-run with the fixture edit applied) | TESTS/na_check.py, TESTS/make_fixture.py | 18 / 3 / 0 / 0 / 4 | 20 / 3 / 0 / 0 / 4 | O02a, O02b |
| exp-013 | KEEP | a MERGE close carries all six P4 sections including DEPRIORITIZED, and a LIST close never carries MERGED | TESTS/na_check.py | 20 / 3 / 0 / 0 / 4 | 22 / 3 / 0 / 0 / 4 | O03a, O03b |
| exp-014 | KEEP | the MERGE close records OPTIONS STANDING itself, so Dispatch never decides what stands: P4 gains the section, spec 4.3 and DISPATCH 3.5 name it, the checker requires it | PROMPTS/P4_close.md, NIGHT_AGENT_SPEC.md, DISPATCH.md, TESTS/na_check.py | 22 / 3 / 0 / 0 / 4 | 22 / 3 / 0 / 0 / 5 |  |
| exp-015 | KEEP | operator selection stays inside the library and the budget: each operator at most once, only SCHEMA operators, never more stages than max_operators; enforced by the checker and by G-5 | TESTS/na_check.py, TESTS/na_gate.py, NIGHT_AGENT_SPEC.md, SCHEMA.json | 22 / 3 / 0 / 0 / 5 | 24 / 5 / 0 / 0 / 5 | O04a, O07b, GA04a, GA04b |
| exp-016 | KEEP | under PROFILE v10-fixed the operator stages must be a prefix of FMEA, IDOV, TRIZ, BAYES, or the baseline arm is not the baseline | TESTS/na_check.py | 24 / 5 / 0 / 0 / 5 | 26 / 5 / 0 / 0 / 5 | O05a, O05b |
| exp-017 | KEEP | gate CLASS and PROFILE must be values SCHEMA defines; an unknown class or profile routes the whole night nowhere | TESTS/na_check.py | 26 / 5 / 0 / 0 / 5 | 28 / 5 / 0 / 0 / 5 | G01a, G01b |
| exp-018 | KEEP | the run layout follows the gate class: DIRECT enters only DIRECT, evidence classes enter GENERATE, EXPERIMENT enters BASELINE; enforced by the checker, by G-2, and SCHEMA gains the DIRECT state it lacked | TESTS/na_check.py, TESTS/na_gate.py, NIGHT_AGENT_SPEC.md, SCHEMA.json | 28 / 5 / 0 / 0 / 5 | 31 / 7 / 0 / 0 / 6 | O06a, O06b, G02b, GA05a, GA05b |
| exp-019 | INCONCLUSIVE | a saved reply carries every heading its prompt requires (P2, P3, P5, P7, P9); a reply missing one was never a valid reply and DISPATCH says not to save it | TESTS/na_check.py | 31 / 7 / 0 / 0 / 6 | 36 / 7 / 0 / 0 / 6 | S01a, S01b, S04a, S04b, D01a |
| exp-020 | KEEP | a saved reply carries every heading its prompt requires (P2, P3, P5, P7, P9); a reply missing one was never a valid reply (exp-019 re-run after obj-004) | TESTS/na_check.py | 31 / 7 / 0 / 0 / 6 | 36 / 7 / 0 / 0 / 6 | S01a, S01b, S04a, S04b, D01a |
| exp-021 | KEEP | a counted seat file is stamped for this stage by a READY registered seat: stage name, seat id, registry membership and readiness are checked, and G-3 counts only such files | TESTS/na_check.py, TESTS/na_gate.py, NIGHT_AGENT_SPEC.md, SCHEMA.json | 36 / 7 / 0 / 0 / 6 | 39 / 9 / 0 / 0 / 6 | S02a, S02b, S03a, GA06a, GA06b |
| exp-022 | KEEP | every stage, review and final file has a log record; a file nobody logged is a file nobody can audit (the package fixture now logs its own two unlogged writes) | TESTS/na_check.py, TESTS/make_fixture.py | 39 / 9 / 0 / 0 / 6 | 41 / 9 / 0 / 0 / 6 | S10b, F03b |
| exp-023 | KEEP | a reused conversation is never independent: the registry records fresh or reused per seat (SCHEMA seat_record gains the field spec 7 already requires) and any reused seat forces the CONTAMINATION flag | TESTS/na_check.py, SCHEMA.json | 40 / 9 / 0 / 0 / 6 | 42 / 9 / 0 / 0 / 6 | S05a, S05b |
| exp-024 | KEEP | isolation starts before the run has content: the reviewer handshake must precede the first GENERATE send, checked post hoc and blocked by G-6 | TESTS/na_check.py, TESTS/na_gate.py, NIGHT_AGENT_SPEC.md, SCHEMA.json | 42 / 9 / 0 / 0 / 6 | 43 / 10 / 0 / 0 / 6 | S06a, GA08a |
| exp-025 | INCONCLUSIVE | a stage answered by fewer generators than were READY is valid only when labelled REDUCED_CREW (spec 7); the package fixture, where G4 never replies, now carries the flag it always owed | TESTS/na_check.py, TESTS/make_fixture.py | 43 / 10 / 0 / 0 / 6 | 46 / 10 / 0 / 0 / 6 | S07a, S07b, S08a |
| exp-026 | KEEP | a stage answered by fewer generators than were READY is valid only when labelled REDUCED_CREW (spec 7); the package fixture, where G4 never replies, now carries the flag (exp-025 re-run after obj-006) | TESTS/na_check.py, TESTS/make_fixture.py | 43 / 10 / 0 / 0 / 6 | 45 / 10 / 0 / 0 / 6 | S07a, S07b |
| exp-027 | KEEP | MIN_CREW cannot be set below the spec floor of two generators; a gate that lowers it has redefined what a valid stage is | TESTS/na_check.py | 45 / 10 / 0 / 0 / 6 | 47 / 10 / 0 / 0 / 6 | S08a, S08b |
| exp-028 | KEEP | a capture record describes the saved reply: byte_hash is a real sha256 of the file and char_count is its length; the package fixture now records real hashes instead of placeholders | TESTS/na_check.py, TESTS/make_fixture.py | 47 / 10 / 0 / 0 / 6 | 49 / 10 / 0 / 0 / 6 | S09a, S09b |
| exp-029 | KEEP | the verifier lives in its own file (I3): section 14 of DELIVERABLE.md stays empty, the assembled file is deliverable plus verifier, and G-8 refuses a deliverable whose section 14 was already filled | TESTS/na_check.py, TESTS/na_gate.py, NIGHT_AGENT_SPEC.md, SCHEMA.json | 49 / 10 / 0 / 0 / 6 | 51 / 11 / 0 / 0 / 6 | F01a, F01b, GA15b |
| exp-030 | KEEP | any verifier CONTRADICTION marks the run PROVISIONAL (spec 4.8); a contradiction the ledger does not carry is a contradiction the morning will not see | TESTS/na_check.py | 51 / 11 / 0 / 0 / 6 | 53 / 11 / 0 / 0 / 6 | F02a, F02b |
| exp-031 | KEEP | a run that skipped the outside review or the verifier is labelled NO_OUTSIDE_REVIEW or NO_VERIFIER, never silently completed (spec 2) | TESTS/na_check.py | 53 / 11 / 0 / 0 / 6 | 55 / 11 / 0 / 0 / 6 | F03a, F03b |
| exp-032 | KEEP | kills-all.md is every KILLS section of every close, concatenated (I10): the checker requires it complete, G-7 refuses a final without it, and the package fixture now writes the two final inputs it always owed | TESTS/na_check.py, TESTS/na_gate.py, NIGHT_AGENT_SPEC.md, SCHEMA.json, TESTS/make_fixture.py | 55 / 11 / 0 / 0 / 6 | 57 / 12 / 0 / 0 / 6 | F04a, F04b, GA09a |
| exp-033 | KEEP | P6 fixes the section order because the morning reads 14, 7, 10, 1 by position; a deliverable with sections out of order is not the P6 document | TESTS/na_check.py | 57 / 12 / 0 / 0 / 6 | 58 / 12 / 0 / 0 / 6 | F05a |
| exp-034 | KEEP | one classification per run (spec 17): the ledger's value is one of the three and equals the deliverable's, or the morning scorecard and the report disagree about what happened | TESTS/na_check.py | 58 / 12 / 0 / 0 / 6 | 61 / 12 / 0 / 0 / 6 | F06a, F07a, F07b |
| exp-035 | KEEP | a flag the schema does not define is a flag the scorecard cannot show: recorded flags must be SCHEMA flags (retired names like STRUCTURAL_GT_EARNED included) | TESTS/na_check.py | 61 / 12 / 0 / 0 / 6 | 62 / 12 / 0 / 0 / 6 | F08b |
| exp-036 | KEEP | a sound KEEP improves in the metric's known direction beyond noise on both the run and its repeat, inside the budget, with guardrails held: one definition shared by G-9 and the checker; SCHEMA records the direction and the package fixture states it | TESTS/na_gate.py, TESTS/na_check.py, NIGHT_AGENT_SPEC.md, SCHEMA.json, TESTS/make_fixture.py | 62 / 12 / 0 / 0 / 6 | 66 / 15 / 0 / 0 / 7 | X01a, X01b, X02a, X04b, GA02a, GA02b, GA03a |
| exp-037 | KEEP | the experiment log is the research trail (spec 5): every record has its line and the line says the same decision; the package fixture now writes the log line its own experiment owed | TESTS/na_check.py, TESTS/make_fixture.py | 66 / 15 / 0 / 0 / 7 | 68 / 15 / 0 / 0 / 7 | X03a, X03b |
| exp-038 | KEEP | executed experiments need a READY EXECUTOR seat (spec 1, 2); a run with experiment records and no executor either ran code nobody was allowed to run or invented results; the package fixture now registers the executor its experiment implies | TESTS/na_check.py, TESTS/make_fixture.py | 68 / 15 / 0 / 0 / 7 | 69 / 15 / 0 / 0 / 7 | G02a |
| exp-039 | KEEP | G-11 sends only to a seat that may receive now: a READY registered seat, and the REVIEWER only in the review stage; the spec gains the G-11 row it referred to but never wrote | TESTS/na_gate.py, NIGHT_AGENT_SPEC.md, SCHEMA.json | 69 / 15 / 0 / 0 / 7 | 69 / 17 / 0 / 0 / 8 | GA01a, GA11b |
| exp-040 | KEEP | a stage whose input cannot be used is not entered: G-6 needs a READY REVIEWER, G-8 a READY VERIFIER, G-7 a parseable metrics-summary; a lost seat means skip and flag (spec 2, 7), never a stage that runs against nothing | TESTS/na_gate.py, NIGHT_AGENT_SPEC.md, SCHEMA.json | 69 / 17 / 0 / 0 / 8 | 69 / 20 / 0 / 0 / 8 | GA13b, GA14b, GA10a |
| exp-041 | KEEP | DIRECT is one generator answering (DISPATCH 5); two replies in a DIRECT stage is a GENERATE without the wall, the check, or the close | TESTS/na_check.py | 69 / 20 / 0 / 0 / 8 | 70 / 20 / 0 / 0 / 8 | D02b |
| exp-042 | KEEP | one flag vocabulary: spec section 10 names every SCHEMA flag (GATE_DEFAULTED was missing) and the morning template lists exactly the SCHEMA flags instead of the v11.0 list | NIGHT_AGENT_SPEC.md, MORNING_DELIVERABLE_TEMPLATE.md | 70 / 20 / 0 / 0 / 8 | 70 / 20 / 0 / 0 / 9 |  |
| exp-043 | KEEP | v11.2 retired STRUCTURAL kills for DEPRIORITIZED in section 4.3 but not in section 8, SCHEMA, the P4 METRICS line or the morning template; one vocabulary everywhere | NIGHT_AGENT_SPEC.md, SCHEMA.json, PROMPTS/P4_close.md, MORNING_DELIVERABLE_TEMPLATE.md, TESTS/make_fixture.py | 70 / 20 / 0 / 0 / 10 | 70 / 20 / 0 / 0 / 11 |  |
| exp-044 | KEEP | prose says what the code does: DISPATCH 3.7 no longer gives the kills-all instruction twice, and make_fixture.py's docstring no longer promises eleven variants | DISPATCH.md, TESTS/make_fixture.py | 70 / 20 / 0 / 0 / 11 | 70 / 20 / 0 / 0 / 12 |  |
| exp-045 | KEEP | DISPATCH 3.7 gives the kills-all instruction exactly once, in the form the assertion looks for (exp-044 left the sentence correct but reworded past the literal check) | DISPATCH.md | 70 / 20 / 0 / 0 / 12 | 70 / 20 / 0 / 0 / 13 |  |
| exp-046 | KEEP | every guard the spec names is traceable to the code that enforces it: G-10 is named where na_check.py enforces it | TESTS/na_check.py | 70 / 20 / 0 / 0 / 13 | 70 / 20 / 0 / 0 / 14 |  |
| exp-047 | KEEP | v11.3.0: the package audit enforces the consistency rules this loop found, every document and tool docstring states the same version, and the QA record says what was measured and what was not | NIGHT_AGENT_SPEC.md, SCHEMA.json, DISPATCH.md, README.md, MIGRATION.md, TESTS/na_check.py, TESTS/na_gate.py, TESTS/ADVERSARIAL_TESTS.md, QA_REPORT.md, VALIDATION_STATUS.md | 70 / 20 / 0 / 0 / 14 | 70 / 20 / 0 / 0 / 15 |  |

## Objective changes

| Id | What | Why |
|---|---|---|
| obj-001 | holdout_corpus.py: O04b renamed O07b (max_operators is a different rule from operator repetition, so it is not O04a's HOLDOUT twin); clone_stage now renumbers claim ids in the cloned stage so a repeated operator is caught only by an operator rule, not by claim-id uniqueness. | exp-006 returned INCONCLUSIVE on a family that was never a same-rule pair; the frozen rule was right to refuse, the corpus was wrong. |
| obj-002 | clone_stage renumbers only the claim ids the cloned stage defines; earlier PASSED ids stay citable, so a repeated operator is caught only by an operator rule. | after obj-001, O04a was still caught by CIDP (the clone cited renumbered ids that were never PASSED), a wrong reason. |
| obj-003 | TESTS/make_fixture.py now exits 1 when the conforming fixture itself fails the checker; before, its exit code covered only caught faults, guard expectations and mutation sensitivity. | the legacy-suite guardrail is read from that exit code; a checker rule that made the package's own conforming fixture fail would have passed the guardrail unseen. |
| obj-004 | audited every a/b family for same-rule twins; nine HOLDOUT cases that test a different rule from their DEV namesake were moved to their own families: D01b->D02b (crew, not headings), S03b->S10b (log record, not seat readiness), F06b->F08b (flag vocabulary, not classification), X02b->X04b (guardrail, not budget), GA01b->GA11b, GA03b->GA12b, GA08b->GA13b, GA09b->GA14b, GA10b->GA15b. | exp-019 returned INCONCLUSIVE on D01, which was never a same-rule pair; the DEV-only rule needs families that are. |
| obj-005 | F03b (no verifier file, no NO_VERIFIER flag) now logs its rewritten assembled file, as a compliant Dispatch would. | after exp-022 it was caught by LOG-ALL for an unlogged write, not by the missing flag. |
| obj-006 | S08a (min_crew below the floor with a one-reply stage) now carries the REDUCED_CREW flag, so the min_crew floor is its only fault. | exp-025 caught S08a through the reduced-crew rule, not the floor, and the DEV-only rule refused correctly. |
| obj-007 | experiment budget raised from 40 to 48 before experiment 33 is run. | the budget was set before the corpus was enumerated; the corpus holds 105 cases in about 45 rule families and each experiment is one rule. Stopping at 40 would leave spec-derived rules unimplemented for a reason unrelated to evidence. Recorded here so the extension is visible, not silent. |
| obj-008 | PA04 and PA05 (flag lists equal SCHEMA flags) now recognise flag names without an underscore (CONTAMINATION, PROVISIONAL); the token regex could only see underscored names, so the assertions could never pass whatever the documents said. | an assertion that cannot pass measures nothing; fixed to test what its description says. |
| obj-009 | PA05 reads the template's flag list from the text after 'flags:' in section 10, not the whole section (STOP_REASON is a status field there, not a flag). | the assertion as written could only pass if the template stopped naming STOP_REASON, which would be editing the document to satisfy a blunt measurement. |

## What the corpus found that the package's own tests did not

- The checker rejected every conforming DIRECT run (three false failures) because it assumed a close, a reviewer and a two-seat crew; DIRECT has none of these by DISPATCH Section 5.
- G-9 checked the size of an experiment's delta but not its direction: a run that made the metric worse by more than the noise would have been KEPT. The gate had no way to learn the direction; SCHEMA now records it and a KEEP without a known direction is blocked.
- A KEEP's repeat run was required to exist but not to agree; a repeat worse than baseline passed.
- A quote-only source (support=PARTIAL) reached the closer: G-4 did not read SOURCE lines, only the post-hoc checker did.
- The reviewer could be sent run content during an operator stage; G-11 only checked dispatch ids and URLs. It could also be handshaked after GENERATE had begun and still count as isolated.
- P4 MERGE mode never asked the closer to write OPTIONS STANDING, though DISPATCH 3.5 reads it from close.md; Dispatch would have had to decide what stands, which Dispatch never does.
- The word STRUCTURAL, retired in Section 4.3 by v11.2, survived in Section 8, in three SCHEMA records, in the P4 METRICS line and in the morning template; SCHEMA had no DIRECT state; Section 15 referred to G-11 without a row; Section 10 omitted GATE_DEFAULTED; the template listed the v11.0 flags.
- The package's own fixture was itself non-conforming in six ways once the spec's rules were enforced (a kill by a PASSED claim, two unlogged writes, no final inputs, no executor seat for its experiment, placeholder capture hashes, no experiment log line, an unflagged reduced crew), and its suite's exit code would not have noticed.

## Next question

The one highest-value next step is not another checker rule. It is the watched rehearsal (TESTS/ADVERSARIAL_TESTS.md Layer B, B1 to B12) with real seats under v11.3, which is the first evidence about the night rather than about the machinery, followed by a second author writing a HOLDOUT corpus without reading the checker.
