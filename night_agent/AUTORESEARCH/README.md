# AUTORESEARCH on the Night Agent package

This folder runs an AutoResearch-style loop (after karpathy/autoresearch: one mutable artifact, one measurement command, a fixed budget per experiment, keep-or-revert recorded in git, a results log as the research trail) on the Night Agent package itself. It is an adaptation of that loop's shape, not a reproduction of that repository (which targets language-model training).

Written and committed BEFORE the first mutation. Changing anything in this file or in `holdout_corpus.py` after `baseline.json` exists is a change to the objective, not to the artifact, and is logged as such.

## What is optimized, and what is not

Optimized: the machine-checkable layer of the package. `TESTS/na_check.py` (post-hoc conformance), `TESTS/na_gate.py` (transition guards), and the consistency of `NIGHT_AGENT_SPEC.md`, `DISPATCH.md`, `PROMPTS/`, `SCHEMA.json` and the operator documents with each other. The whole package tree is the artifact; every experiment may touch any file in it.

Not optimized, and not claimed: answer quality on a real night. No model seat is called here. Whether a night under these prompts produces better answers is the spec's own Section 8 question and needs paired nights with real seats. NO_AUTORESEARCH_SUPERIORITY_CLAIM stands (spec 8).

## The measurement

```
python3 AUTORESEARCH/eval.py --json <out.json>
```

`holdout_corpus.py` builds two conforming runs from scratch (a HYBRID run through GENERATE, FMEA, IDOV, an experiment, REVIEW, FINAL, VERIFY; and a DIRECT run), then applies 70 spec-derived faults, 20 guard-block cases, 18 must-allow transitions and 15 package assertions. Every case names the spec section it is derived from. None reuse the package's own fixture (`TESTS/make_fixture.py`), which the checker was written against and which therefore proves nothing about generalization.

Reported separately, never composed:

| Name | Meaning | Direction |
|---|---|---|
| primary DEV, HOLDOUT | run-folder faults caught by `na_check.py` | higher |
| guard DEV, HOLDOUT | transitions correctly blocked by `na_gate.py` | higher |
| guardrail: false FAIL lines on clean bases | conformance failures reported on a conforming run | must not rise; target 0 |
| guardrail: false BLOCKs | legitimate transitions blocked | must not rise; target 0 |
| guardrail: package check failures | `na_check.py --package` | 0 |
| guardrail: legacy suite | `make_fixture.py` exit code (19 faults, 23 guard expectations, mutation sensitivity) | 0 |
| guardrail: runtime | eval wall clock | within 120 s |
| secondary | package assertions passing | higher |

DEV / HOLDOUT: each rule family has one surface form in DEV and a different one in HOLDOUT. Mutations are chosen looking at DEV misses only. A mutation that fixes its DEV case and not the HOLDOUT twin of the same family fitted the wording, not the rule, and is INCONCLUSIVE, never KEPT (spec 8).

Noise: the measurement is deterministic; two baseline runs were identical. MIN_DELTA is one case.

## Decision rule (frozen)

KEEP only if every guardrail is at or better than the last kept value, the package check and the legacy suite exit 0, and at least one of:

1. primary (DEV + HOLDOUT) rises by at least one and HOLDOUT does not fall;
2. guard (DEV + HOLDOUT) rises by at least one and HOLDOUT does not fall;
3. primary and guard unchanged, and a guardrail or the secondary count improves.

REVERT otherwise (`git checkout` of the last kept tree). INCONCLUSIVE for the DEV-only case above; it is reverted and logged as INCONCLUSIVE, not REVERT.

One mutation per experiment. A mutation is one rule (one checker rule, one guard clause, or one consistency fix across the documents it touches). Where a rule requires the spec, SCHEMA and code to change together, that is one mutation, labelled INTERACTION, because the spec says a guard that disagrees with the spec is a bug in the guard.

Budget: at most 40 experiments (raised to 48 by obj-007 in log.jsonl, before experiment 33); eval must finish inside 120 s. Stop on PLATEAU (three consecutive non-KEEP), BUDGET, or SUFFICIENT (every case caught or blocked, every guardrail at 0, every assertion passing).

## The trail

- `baseline.json`: the measurement before any mutation.
- `log.jsonl`: one line per experiment: id, hypothesis, files touched, before and after numbers, decision, commit.
- git: every KEEP is a commit whose message starts with the experiment id and states the hypothesis. A REVERT leaves no commit; the log line is its record.
- `RESULTS.md`: the table and the honest labels, written at the end.

## Labels

PROVEN BY TEST here: the numbers in `log.jsonl` and `RESULTS.md`, reproducible with the command above.
DESIGN JUDGEMENT: which spec rules were turned into cases, and their DEV/HOLDOUT assignment. The corpus was authored by the same agent that then edited the checker; in the spec's own terms that makes it a DEV-grade benchmark. A HOLDOUT set that carries its full weight needs a second author who has not read the checker.
NOT TESTED: any real night.
