# Working Rules for Claude in This Repository

This repository holds the FORGE Talent Connections app (Flutter, `lib/` and `test/`), its public landing page (`index.html`, `web/`), and `adjudication/`, a Python tool that verifies decisions. Build steps: `BUILDING.md`. The agent roster, its design, and its measured limits: `docs/AI_AGENTS.md`.

## Truth standard (overrides everything else)

- Never invent facts, numbers, citations, costs, or timelines. Write "I do not know" or "Insufficient evidence. Missing: ..." instead of filling a gap.
- Label load-bearing claims: PDF-Supported, Empirical Finding, Evidence-Based Inference, Assumption, or Unknown.
- No success probability, confidence percentage, or point probability without a dataset, an outcome variable, a base rate, and the calculation shown. Otherwise use High, Medium, or Low with reasons. Percentages come only from `reliability-statistician`, computed from logged or measured data, with k/n and the interval.
- Legal, tax, patent, regulatory, compliance, or medical points: name the issue and the question for counsel, then write "professional verification required".
- Never report a check as passing unless it ran in this session and passed. Otherwise it is NOT RUN.

## Walls (no exceptions)

- NO SECRETS: never commit, print, or pass as a command argument `.env`, `profiles.json`, a key, or a token.
- NO MAIN, NO PRODUCTION: never push to or merge into `main`; never deploy, publish, send, or spend without a human confirming that specific action. The `adjudicate` and `calibrate` workflows spend money: they stay manual behind the SPEND confirmation.
- This is the walled consumer repository. Internal system names and filing or payment identifiers never appear anywhere in it; the list lives encoded in `test/copy/walled_repo_test.dart`, and `node .claude/tools/scan-copy.mjs <files>` checks any file without printing it. No patent claim text or prosecution strategy. No other entity's data.
- Everything under `adjudication/eval/`, and `adjudication/calibration*.txt`, is deliberately false red-team and evaluation material. Never cite it.
- `adjudication/AGENTS.md` defines Codex's verifier role. For Claude, that role is `adversarial-verifier`.

## Agents: one job each, one writer per surface

| Need | Agent |
|---|---|
| Dart and Flutter work in `lib/` or `test/` | `flutter-builder` |
| `index.html`, `web/`, and public copy | `brand-web-builder` |
| Python in `adjudication/` | `adjudication-builder` |
| After a builder reports done (give it the diff and the requirement, not the builder's reasoning) | `adversarial-verifier` |
| Before every push: the non-AI checks, then the policy gate | `gate-runner`, then `guardrail-auditor` |
| Any text with numbers, citations, or factual claims, before it is relied on or published | `claim-auditor` |
| Designs, automations, processes, anything that spends money or is hard to reverse | `fmea-engineer` |
| Any probability, success rate, or "did it improve" | `reliability-statistician` |
| Verified external evidence for any question | `council-evidence-scout` |
| A high-stakes or hard-to-reverse decision | the Full Council, below |

Never run the same check again with the same model and call it corroboration: reviewers whose errors are correlated are worth fewer independent seats than their count (the Kish design effect, n / (1 + (n - 1) rho)). Add a different channel (a gate, a tool, a lens), not another copy. `docs/AI_AGENTS.md` records what this repository has and has not measured.

## Full Council

Only for a high-stakes or hard-to-reverse decision that the operator convenes it for. Before anything runs, the operator writes a tentative answer and one to three load-bearing premises. Then run the saved workflow `full-council` with args `{question, why_full_council, operator_answer, premises, decision_types, green_only: true}` plus optional `base_rate`, `expected_without_council`, `context`, and `date` (see `.claude/workflows/full-council.js`). The seats are `council-contrarian`, `council-first-principles`, `council-expansionist`, `council-executor`, and `council-steward`; three `council-chairman` runs synthesize. Present the returned `operator_brief` as written. Then help the operator decide, and record the decision with its ex ante score right away through `reliability-statistician` (`adjudication/decision_log.py record`), before any outcome exists.

## Checks

- Flutter: `flutter analyze` must print `No issues found!`, then `flutter test`.
- `adjudication/`: ruff, mypy, pytest with `--cov-fail-under=80`, bandit, and pip-audit, as in `.github/workflows/adjudication.yml`.
- Agent layer: `node --test ".claude/tests/*.test.mjs"`.
- User-facing copy and Council output: no em dashes or en dashes.
