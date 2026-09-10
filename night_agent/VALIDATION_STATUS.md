# Validation status, Night Agent v11.2.0 (2026-09-10)

## PROVEN BY TEST (executed this session, reproducible with the files in TESTS/)
- The package is internally consistent on 59 automated checks: six statuses named everywhere they must be; eight nevers; every prompt DISPATCH references exists; deliverable sections match between P6 and SCHEMA; no em-dash; prompts fit 72 columns; regression probes for I1, I2, I3, I4, I7, I8, I9, I10, I11 pass; guards present and invoked; HOLDOUT split, paired design, claim ids, and the adaptation label present.
- The conformance checker catches 19 of 19 injected run-folder faults (the fourteen below plus duplicate dispatch id, stale-stage reply, incomplete capture counted, quote-present-but-PARTIAL marked PASSED, winner label in a packet): bare PASSED, collapsed status, closer-invented claim, new option after GENERATE, reviewer contacted early, seat file leaked into the review package, attribution not stripped, deliverable edited after write, missing stamp, stage below minimum crew, wall leak (shingle heuristic), KEEP without a repeat run, MERGED citing a claim that is not PASSED, a second final write.
- The transition guard meets 23 of 23 allow-or-block expectations across G-1 to G-9 and G-11 (including previous slot open, wrong observed conversation, partial capture excluded from crew) (missing ask, missing gate, one-seat stage, bare PASSED at close, missing check, repeated operator, operate after stop, reviewer contacted early, final exists, fresh final, verifier exists, KEEP with and without repeat, KEEP within noise).
- A conforming synthetic run folder passes the checker with zero failures.
- The three books (Operator tablet, Operator mobile, Reference) have 0 overlapping fields, identical operator field names across editions, appearance streams on every widget, and every prompt line verbatim from PROMPTS/ in the Reference Manual (see QA_REPORT.md).

- Candidate-mutation sensitivity: bypassing one rejection branch in a copy of the checker lets the matching fault escape while the oracle stays fixed. A verification manifest with a unique id, case ids, expected outcomes and candidate hashes is written on every fixture run.

## REPORTED BY THE PILOT (supplied as documents, not reproduced here)
- The overnight pilot on Night Agent itself reported 336 of 336 development cases on its guard candidate in one fresh run, 28 of 28 offline verifier tests, 25 captured replies, 18 Astra findings, and a Claude final that revised four decisions. Its evidence files were not uploaded, so none of it is PROVEN BY TEST in this package. The pilot itself classified the run KEEP_FOR_DEVELOPMENT for the guard and PROPOSED_PROTOCOL for the architecture, with NO_BLINDED_OUTSIDE_REVIEW, NO_PRIVATE_PROJECT_VERIFIER, NO_ARCHITECTURE_BENCHMARK, NO_AUTORESEARCH_SUPERIORITY_CLAIM. Those labels stand.

## SUPPORTED BY EVIDENCE (from the v10 materials and the reviews supplied this session, not re-measured)
- Check-before-merge prevents a false claim from being woven into the working answer (v10 rationale, unchanged).
- A backup closer is the highest-value reliability component (v9 simulation, labelled INHERITED, UNVERIFIED; the direction is supported, the numbers are not re-verified).
- The eleven spec conflicts existed as stated (the ChatGPT v10 workbook's issues register, read this session, pages 84 to 87).
- karpathy/autoresearch exists and its loop shape (one mutable artifact, one metric, fixed time budget, keep-or-revert via git) is as described by a port's README retrieved this session; the current implementation was not read line by line, so v11 claims adaptation, not reproduction.

## DESIGN JUDGEMENT (reasoned, not measured)
- Objective gate classes and the DIRECT path; adaptive operator selection table and its priorities; MARGINAL stop after two dry operators; K = 3 plateau; max operators default 4; the reviewer handshake-then-isolate rule; HOLD-ACCEPTED semantics; flags instead of automatic invalidation for STRUCTURAL_GT_EARNED and EMPTY_OPEN_LIST; eight paired runs as a floor with a 90 percent bootstrap percentile interval; the DEV/HOLDOUT split and one-task refresh after promotion; the non-inferiority and cost margins are operator-set defaults with no dataset behind them.

## NOT YET TESTED
- Any real night on the v11 chain under these prompts and guards. The pilot ran a different, executor-driven variant on reused conversations. Any seat's real behaviour under P1 to P9. Whether adaptive routing beats v10-fixed. Whether the review pass earns its cost. Whether fewer generators lose correctness. Model availability, plan limits, and effort settings for every seat. Device behaviour of the workbooks on iPad, iPhone, Galaxy. Layer B items B1 to B17.

Nothing in this package claims the successor is better than v10. It claims the successor is internally consistent, mechanically checkable, guarded at every transition, and set up to be measured. The measurement is the next step, not this document, and not a v12.
