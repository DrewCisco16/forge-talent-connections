# Night Agent v11.3.0 package (autoresearch pass)

Single source of truth hierarchy (highest first):
1. NIGHT_AGENT_SPEC.md   authoritative semantics
2. DISPATCH.md           executable procedure for the browser agent
3. PROMPTS/P0..P9        the ten canonical prompts (line width 72)
4. SCHEMA.json           states, transitions, statuses, operators, records, files
5. TESTS/                na_gate.py (transition guards G-1 to G-11, run before every stage and every send), na_check.py (conformance), make_fixture.py (fault injection and guard tests), ADVERSARIAL_TESTS.md, BENCHMARK_TASKS.md (DEV/HOLDOUT, paired protocol, criterion template)
6. WORKBOOKS/            Operator workbook (Tablet_Desktop and Mobile, bedtime and breakfast only), Reference Manual (prompts, roles, setup, spec decisions), build/ to regenerate them
7. QA_REPORT.md, VALIDATION_STATUS.md, MIGRATION.md, MORNING_DELIVERABLE_TEMPLATE.md
8. AUTORESEARCH/        the loop that produced v11.3: frozen spec-derived corpus (holdout_corpus.py), the one measurement command (eval.py), the decision rule (README.md), the trail (baseline.json, log.jsonl, RESULTS.md). Not part of a night.

Human PDFs are never the authoritative executable specification.

Quick start: read MIGRATION.md, run `python3 TESTS/na_check.py --package .` and `python3 TESTS/make_fixture.py /tmp/na_fixture` and `python3 AUTORESEARCH/eval.py`, do the watched rehearsal in TESTS/ADVERSARIAL_TESTS.md Layer B, then run eight nights with PROFILE=v10-fixed before any adaptive night.
