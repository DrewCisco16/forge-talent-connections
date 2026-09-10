# QA report, Night Agent v11.2.0 package (2026-09-10, pilot integration)

## What was tested and how

| Artifact | Test | Method | Result |
|---|---|---|---|
| NIGHT_AGENT_SPEC.md, DISPATCH.md, SCHEMA.json, PROMPTS/ | Package consistency, 59 checks (v11.1 checks plus: P4 uses DEPRIORITIZED with no STRUCTURAL kills; spec separates quotation presence from support; DISPATCH writes dispatch and capture records; classification present in P6 and spec; P3 requires UNMEASURED for uncomputed statistics) | `python3 TESTS/na_check.py --package .` | 59 passed, 0 failed |
| TESTS/na_check.py | Fault detection on synthetic run folders | `python3 TESTS/make_fixture.py /tmp/na_fixture` | conforming: 0 FAIL; 19 of 19 injected faults caught (v11.1's fourteen plus duplicate dispatch id, stale-stage reply, incomplete capture counted, quote present but PARTIAL support marked PASSED, winner label in the review package) |
| TESTS/na_gate.py | Transition guards G-1 to G-9 and G-11, capture-aware G-3 | 23 allow-or-block expectations in make_fixture.py | 23 of 23 met |
| TESTS/make_fixture.py | Candidate-mutation sensitivity and verification manifest | a copy of na_check.py with the bare-PASSED rejection bypassed must let fault F01 escape that rule (oracle fixed); a manifest with unique id, case ids, expected outcomes, candidate hashes is written | sensitivity confirmed; manifest written |
| WORKBOOKS/Night_Agent_v11_Operator_Tablet_Desktop.pdf | Structure and fields | pypdf: 32 pages, 364 fields, 451 widgets all with appearance streams, 0 overlapping widgets, tab order equals reading order, 0 em-dashes, 0 thin pages | PASS |
| WORKBOOKS/Night_Agent_v11_Operator_Mobile.pdf | Same | 35 pages, 364 fields with identical names to the tablet edition, 451 widgets, 0 overlaps, 0 order issues, 0 em-dashes, 0 thin pages | PASS |
| WORKBOOKS/Night_Agent_v11_Reference_Manual.pdf | Structure, prompts | 29 pages, 14 fields, 0 overlaps, every line of every PROMPTS/ file present verbatim, 0 em-dashes, 0 thin pages | PASS |
| All three books | Visual | every page rasterised and reviewed on contact sheets; representative pages at readable size | consistent band, strip, tags, DONE WHEN; one logical unit per page on mobile |

## Changes since v11.1.0, from the pilot (MORNING_REPORT.md, NIGHT_AGENT_FINAL_PROTOCOL.md, ASTRA_REVIEW.md)
- Source admission fields and the quotation-versus-support separation; DEPRIORITIZED replaces STRUCTURAL kills; executor-owned dispatch and capture records with guard G-11 and a capture-aware G-3; packet neutrality scan; data boundary and spending permission in the gate; release classification with PARTIAL_REPORT never an acceptance; verification manifests and candidate-mutation sensitivity; model capability ledger; prospective comparison rules. Spec section 19 maps every pilot item to its disposition. The pilot's own results (336 of 336, 28 of 28, 25 captures, 18 findings) are reported by the pilot and were not reproduced here; its evidence files were not supplied.
- Operator workbook: gate page 3 (spending permission, payload authorization, rollback hash, reservations, caps known, fresh conversations); tracker rows for dispatch ids and complete captures; DEPRIORITIZED counts; review neutrality check; per-HIT dispositions; three-page scorecard with fourteen flags and the classification radio; source-admission and capability-observation audit pages. Reference Manual: two pilot-record pages, guard G-11, updated flags.

## Changes since v11.0.0, from the ScholarGPT review
- Invariants moved from prose into TESTS/na_gate.py (nine transition guards) and na_check.py (claim-id provenance, final-once, KEEP-needs-repeat, architecture decision floor). DISPATCH.md gained one guard line per stage and no new prose rules.
- Architecture criterion: eight paired runs is a floor; promotion requires a bootstrap percentile interval over paired differences on HOLDOUT tasks against a criterion written before the first pair. DEV/HOLDOUT split added with a refresh rule.
- The Experiment Engine is labelled an AutoResearch-style adaptation of karpathy/autoresearch (retrieved this session: the repository exists; its loop is described by a port as one mutable file, one metric, a fixed time budget, keep-or-revert via git) and not a reproduction. Git keep-or-revert and a fixed per-experiment budget were adopted from that pattern.
- Workbooks split: Operator (34 tablet, 32 mobile) for bedtime and breakfast; Reference Manual (26, tablet) for prompts, roles, setup, spec decisions. Mobile carries the operator core only.

## Not tested
- No real seat received any v11 prompt. No night has run. No device test of the PDFs. Layer B watched-run items B1 to B17 remain specified, not executed.
- The wall-leak heuristic only detects verbatim 12-word overlaps.
- The bootstrap interval procedure is specified in BENCHMARK_TASKS.md but no runs exist to compute it on.

## Reproduce
`cd night_agent_v11 && python3 TESTS/na_check.py --package . && python3 TESTS/make_fixture.py /tmp/na_fixture`
Books: `NA_BOOK=operator NA_EDITION=tablet python3 WORKBOOKS/build/build_v11_books.py` (also NA_EDITION=mobile; NA_BOOK=reference). Requires reportlab, DejaVu fonts, and the emoji folder beside na_ui.py; the build reads PROMPTS/ so prompt edits propagate.
