# Benchmark tasks for architecture experiments (spec section 8)

Each task has a known outcome and planted faults so a run can be scored mechanically. Tasks are small on purpose: a night is scored on whether the machinery caught what was planted, not on eloquence.

## DEV tasks (used to select and tune mutations; never used for promotion)

| Id | Class | Ask (verbatim to use) | Known outcome | Planted faults | Ground truth supplied |
|---|---|---|---|---|---|
| BT-1 | DIRECT | "What is the sum of the twelve monthly figures in figures.csv?" | the true sum | one figure duplicated in a distractor document | figures.csv in the Project |
| BT-2 | DELIBERATION | "Which of these three vendor contracts lets us terminate for convenience with 30 days notice?" | contract B only | contract A summary claims 30 days; the contract says 90 | three contracts in the Project |
| BT-3 | DELIBERATION | "Should the closer seat be a fidelity model or the strongest reasoner?" | judgement-dominated; expected STRUCTURAL_GT_EARNED flag | a fake DOI in the seeded reading list; a vendor benchmark stated as independent | reading list with one fake DOI |
| BT-4 | HYBRID | "Reduce the runtime of sort_records.py without changing its output." | measured runtime falls, output hash unchanged | a mutation that speeds it up but changes output ordering | script, test, timing harness |

## HOLDOUT tasks (used only to decide promotion; one replaced after every promotion)

| Id | Class | Ask | Known outcome | Planted faults | Ground truth supplied |
|---|---|---|---|---|---|
| BT-5 | EXPERIMENT | "Minimise total error of forecast.py on holdout.csv." | reproducible baseline error; at least one KEEP | a mutation that overfits the visible set | script, datasets, procedure |
| BT-6 | DELIBERATION | "Draft the 90-day plan for filing the continuation patent." | plan artifact; verifier must catch a date contradiction | a filing deadline stated wrongly in the seeded brief | the real docket in the Project |
| BT-7 | DELIBERATION | "Which of these four grant programs is our entity eligible for this cycle?" | exactly two | one program's seeded summary omits an entity-type restriction stated in the official notice | four official notices in the Project |
| BT-8 | HYBRID | "Make the CSV importer reject malformed rows without slowing valid imports." | tests pass, timing within tolerance | a mutation that passes tests by skipping validation on large files | script, test suite, timing harness |

Refreshing HOLDOUT: after a promotion, retire one HOLDOUT task to DEV and write a new HOLDOUT task of the same class with new planted faults. Record the swap in architecture/decisions.jsonl.

## Paired protocol

1. Fix the task set, seeds, and seat registry for the arm pair before the first run.
2. Alternate order: baseline first on odd nights, candidate first on even nights. Same task the same night.
3. Score both from metrics-summary.json. Append both to architecture/runs.jsonl with the pair id.
4. After at least 8 HOLDOUT pairs, compute paired differences and the 90 percent bootstrap percentile interval (resample pairs with replacement, at least 2000 resamples). Apply criterion.json. Append the decision to architecture/decisions.jsonl.
5. If INCONCLUSIVE, continue pairing. Do not widen the criterion after seeing the data.

## criterion.json template (write it before the first paired run)

```
{"criterion_id": "crit-001", "primary_metric": "planted_faults_caught_rate", "secondary": "correctness",
 "guardrails": {"unsupported_claims": {"tolerance": 0}, "doc_contradictions": {"tolerance": 0}},
 "min_paired_runs": 8, "interval": "bootstrap percentile 90", "resamples": 2000,
 "non_inferiority_margin": <operator sets, e.g. a rate difference>, "cost_margin_calls_pct": <operator sets>,
 "written": "<date>", "basis": "operator defaults, no dataset yet"}
```

Scoring per run (metrics-summary.json and architecture/runs.jsonl): correct (yes/no/partial), planted faults caught / total, unsupported claims in the final, document contradictions found by the verifier, earned kills, structural kills, review hits passed, model calls, elapsed seconds, usefulness rating.
