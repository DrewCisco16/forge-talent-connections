# AI Agents: Roster, Design, and Measured Limits

## Bottom Line

- Sixteen Claude Code agents live in `.claude/agents/`. Each has one job no other agent does: seven Full Council seats for decisions, five reliability channels, one policy gate, and three builders, one per code surface.
- The Full Council runs as a saved workflow, `.claude/workflows/full-council.js`, which enforces the protocol's blinding, caps, and halts in code rather than trusting a model to follow them.
- `adjudication/decision_log.py` keeps a hash-chained Decision Log. It is the only place a success percentage may come from, and it is empty until decisions are recorded and reviewed.
- One agent has a first measurement: the claim-auditor procedure scored 12 of 12 on a fresh blinded set, Wilson 95% [75.7%, 100.0%]. Read the interval, not the midpoint, and read the limits below before relying on it.
- No success probability is claimed for any decision. None can be until outcomes are logged.

## Why Sixteen, Not As Many as Possible

The request was for as many agents as possible. A count of agents raises reliability only when their errors are independent.

- **The arithmetic** [Evidence-Based Inference]. For n reviewers whose errors correlate at rho, the effective number of independent reviewers is n / (1 + (n - 1) rho), the Kish design effect this repository already implements in `adjudication/seat_independence.py`. As n grows this approaches 1 / rho. At rho = 0.5, no number of copies is worth more than two independent reviewers. The inference assumes errors correlate uniformly; copies of one model given one prompt are the case where that assumption is most plausible.
- **What catches correlated errors** [PDF-Supported]. The repository's SOP calls the non-AI verification layer "the most valuable part of the system because their errors are completely unrelated to the models' errors" (`adjudication/SOP_v1.2.html`).
- **Different lenses find different defects** [PDF-Supported]. `adjudication/CALIBRATION-REVIEW.md` records seventeen defects in one module that was already done, tested, and green: two before it shipped, then seven from an Inversion pass, five from a Critical Systems plus TRIZ pass, and three from a Bayesian pass. That count is the document's own; it was not re-verified here.
- **Every agent has a cost** [Fact]. Each description is loaded into every session for routing, and each agent's output is something a person reviews.

So each agent here earns its place by adding a channel whose errors differ from the others': a compiler or a test, a registry lookup, a recomputation in code, a distinct analytical lens, or a distinct surface with its own gate. A seventeenth agent that repeats an existing job would add cost and correlated error, not reliability.

## A Finding About This Repository's Own Evidence

Commit f2d6071 recorded rho = 0.90 for the five-vendor panel ("1.08 effective seats of five") and concluded the panel should be cut. After a parsing fix that changed how verdicts are read but not the question asked, the merge of pull request 8 reports rho = 0.8095 ("1.18 effective seats of five") on all ten seeded items. Both runs share one confound.

1. [Fact] The probe's contract in `adjudication/seeded_rho.py` tells each seat: "Answer only about the ARITHMETIC. Not whether the framing is wise, not whether the figures are the right ones to use -- only whether the computation shown produces the number shown."
2. [Fact, recomputed in this session] For three of its five seeded defects the computation shown does produce the number shown: 105,000 / 246,000 = 42.7% (A2), 18,832 x 36 = 677,952 (A4), 10 x 0.60 = 6 (A6). Their defects are the choice of formula or the reading of a rounded figure.
3. [Fact, from the f2d6071 commit message] Those are exactly the items it reports every seat, or four of five, "missed". The two pure computation slips (A1, A3) were caught. Per-item results for the later run are not recorded in the repository.
4. [Evidence-Based Inference] The misses are what obeying the contract produces, so the correlation largely measures five models following the same instruction, not a shared blind spot. The seats' raw replies are not in the repository, so this cannot be confirmed from them.
5. [Consequence] The panel's independence is unmeasured in either direction. Do not cut or keep paid seats on the strength of either figure. Re-measuring with a contract that matches its answer key spends money at five vendors, so it is the operator's decision.

The agent files and `CLAUDE.md` rely on the Kish principle, not on either figure.

## Roster

| Agent | One job | The independent channel it adds | Tools | Acceptance check |
|---|---|---|---|---|
| `council-evidence-scout` | Seat 0: verified evidence packet with search disclosure and the weighting rubric | A registry lookup for every DOI; primary sources fetched and confirmed | Read, Grep, Glob, WebSearch, WebFetch, Bash | Every source verified this session or excluded; BLOCKED is never read as fabricated |
| `council-contrarian` | Seat 1: the strongest opposing case | Pre-mortem lens | Read, Grep, Glob | One premise challenged; a kill criterion for every failure mode |
| `council-first-principles` | Seat 2: facts versus assumptions, reference class, transfer risk | Decomposition lens | Read, Grep, Glob | Real objective and correct problem, one sentence each |
| `council-expansionist` | Seat 3: asymmetric upside | Upside lens | Read, Grep, Glob | A cost to test and a leading indicator for every play |
| `council-executor` | Seat 4: the sequenced plan, 24 hours to 90 days | Implementation lens | Read, Grep, Glob | A checkable done condition per milestone; no invented owner |
| `council-steward` | Seat 5: integrity, five capitals, family, legacy | Stewardship lens | Read, Grep, Glob | Proceed, Proceed With Conditions, or Do Not Proceed, with the constraint named |
| `council-chairman` | Synthesis, run three times blind; must decide | Evidence-weighted synthesis over anonymized seats | Read, Grep, Glob | A decision class, a clamped confidence, a standalone memo, an Assumption Test Plan |
| `gate-runner` | Runs the non-AI checks for whatever changed | Compilers, tests, linters, scanners | Bash, Read, Grep, Glob | Exact command, exit code, and evidence per gate; NOT RUN is never reported as PASS |
| `claim-auditor` | Audits numbers, citations, and claim labels in any text | Recomputation in code, then a formula check; the DOI registry | Read, Grep, Glob, Bash, WebFetch | Every number recomputed with its expression shown |
| `adversarial-verifier` | Blinded review of a finished diff | Executable failing tests | Read, Grep, Glob, Bash, Edit, Write (tests only) | Each gap proven by a test that fails |
| `fmea-engineer` | FMEA, fault tree, and FMEDA for designs, automations, and processes | Three successive lenses | Read, Grep, Glob | Dangerous undetected failures ranked first; no invented ratings |
| `reliability-statistician` | The only source of percentages; keeper of the Decision Log | Statistics on observed outcomes | Read, Grep, Glob, Bash | k/n, the Wilson interval, the dataset, the outcome variable, and the base rate, every time |
| `guardrail-auditor` | Policy gate: secrets, spend, NO MAIN, walls, permissions | A rule checklist, the wall scan, bandit | Read, Grep, Glob, Bash | PASS only when every check ran |
| `flutter-builder` | Writes `lib/` and `test/` | The Flutter suite, including the copy rules | Read, Grep, Glob, Edit, Write, Bash, WebFetch, WebSearch | `flutter analyze` and `flutter test` pass, or NOT RUN is stated |
| `adjudication-builder` | Writes `adjudication/` | ruff, mypy strict, pytest with the coverage floor, bandit, pip-audit | Read, Grep, Glob, Edit, Write, Bash, WebFetch, WebSearch | Every gate passes |
| `brand-web-builder` | Writes `index.html`, `web/`, and public copy | The copy scan and the accessibility checklist | Read, Grep, Glob, Edit, Write, Bash, WebFetch | Scan clean; every public sentence listed for the operator to approve |

`.claude/tests/agents.test.mjs` enforces least privilege on every change. Every agent declares its tools, so none inherits connector tools that send, delete, or spend. Checkers never hold Edit or Write. Council seats hold only Read, Grep, and Glob. No agent can spawn agents, so orchestration stays with the main session or a workflow.

## How to Use Them

- **Everyday work.** Ask normally; the main session routes by the table in `CLAUDE.md`. To force a specific agent, name it, for example "use gate-runner on this branch".
- **After creating the agents directory.** Claude Code loads agents from a newly created `.claude/agents/` at the next session start.
- **The Full Council.** Only for a high-stakes or hard-to-reverse decision you convene it for. Write your own answer and premises first, then ask Claude to run the `full-council` workflow with:

  ```json
  {
    "question": "Should we ...?",
    "why_full_council": "Hard to reverse because ...",
    "operator_answer": "My tentative answer, written before the run",
    "premises": ["Premise one", "Premise two"],
    "decision_types": ["strategic", "financial"],
    "green_only": true,
    "base_rate": "optional",
    "expected_without_council": "optional",
    "context": "optional background",
    "date": "2026-09-26"
  }
  ```

  Allowed decision types: factual, causal, predictive, strategic, legal_regulatory, tax, compliance, ethical, financial, technical, medical, interpersonal. One run is nine agents: one Scout, five seats, and three Chairmen.
- **The Decision Log.** From `adjudication/` with its virtual environment: `python decision_log.py template`, then `record --json filled.json` at decision time (the ex ante score locks, and the entry is stamped with its UTC write time), `review --json filled.json` at the review date, and `stats --today YYYY-MM-DD`. The log is two files, `decision-log.jsonl` and its `.head` sidecar; keep them together, because a log without its sidecar fails integrity. After each write, keep the printed ANCHOR line somewhere the log's editor cannot change, and pass it back to `verify` or `stats` to detect a truncation even if the sidecar is forged. The log defaults to `adjudication/decisions/`, which is gitignored because operator records can quote sensitive material. A cloud session's container is temporary, so keep both files somewhere durable by your own choice.
- **The copy and wall scan.** `node .claude/tools/scan-copy.mjs [--copy] <files>` checks any file for dashes, walled internal names (reported by number, never printed), and, with `--copy`, recruiting vocabulary. It reads the rules from the Dart tests, so it never drifts from them.

## How a Council Run Enforces the Protocol

| Failure mode | Safeguard in code | Test that pins it |
|---|---|---|
| The Council anchors on the operator's view | The operator's answer and expected outcome are never sent to any agent; they return only in the result | "the operator's answer and expected outcome never reach a seat or chairman" |
| A seat is shaped by another seat | Seats run in parallel, each given only the brief and the evidence | "seats see the premises and the evidence, but never another seat's output" |
| A Chairman weighs a role or a position | Seats appear as Seat A to E, in a different seeded order per Chairman, with self-references removed | order, collision, uniformity, and "words intact" tests |
| Agreement is mistaken for verification | One model family caps confidence at Medium; the clamp runs in code; a value outside Low, Medium, or High fails closed to Low | clamp and vocabulary tests |
| No verified external evidence | Opinion-only, capped at Low | "no verified external evidence makes the run Opinion-only at Low" |
| Dissent goes missing | Any missing Scout, seat, or Chairman halts the run; resume re-runs only what is missing | three halt tests |
| A regulated domain without counsel | The professional verification line is added in code | two enforcement tests |
| A fabricated percentage | No output field holds a probability; the brief is tested to contain no percentage | "the harness-written brief contains no percentage" |
| A secret in the ask | Refused before any agent runs; the value is never echoed | "refuses a credential-shaped string without echoing it" |
| A credential pasted into the ask | Every string, keys included, scanned one at a time for 13 credential shapes (including the five vendors this repository uses and its own key names); refused before any agent runs; no value echoed | 46 credential tests: 45 refusals, inline and at line starts, and one check that ordinary words are not flagged |
| The operator's answer leaks through another field | An answer of 12 or more characters repeated in the question, context, premises, or base rate is refused | containment tests |
| A malformed agent result | A Scout, seat, or Chairman result without its required shape halts the run instead of crashing it | five malformed-result tests |
| Deduplication inflates the ceiling | The ceiling is computed with duplicates merged and again with only exact duplicates merged; the lower stands | dedup and ceiling tests |
| Hindsight rewrites the ex ante score | Append-only, hash-chained log with no edit command; one lock across the duplicate check and the append; the sidecar is required; an optional anchor detects forged sidecars; tampering exits 2 | decision-log integrity, race, and anchor tests |

## Verification Performed for This Change

All figures below were measured in the session that built this change.

- **Full Council workflow:** 111 tests pass with stubbed agents, so no model is called. 41 of 41 planted mutations were caught. Before the first push, chasing a mutation survivor showed that the first seat-order generator, a bare power-of-two LCG, produced far-from-uniform positions, and review showed that a naive role scrub would have turned "stewardship" into nonsense. Both are pinned by tests.
- **Decision Log:** 105 tests, 100% line coverage of `decision_log.py`, and 29 of 29 planted mutations caught, including removal of the writer lock, which a deterministic race test detects.
- **Adjudication suite:** 1,840 tests pass. Coverage rose from 80.61% to 81.62% against the floor of 80. ruff, mypy strict, bandit, and pip-audit are clean.
- **Agent layer:** `node --test ".claude/tests/*.test.mjs"` runs 134 tests: the 111 above plus 23 covering definitions, allowed frontmatter keys, least privilege, the identical Council contract, routing, the walls over every file discovered under `.claude/`, and the scan tool's exit codes. 25 of 25 planted violations were caught. The CI step also fails when no test runs, so an empty glob cannot pass.

### An independent review, and what it changed

After the first push, a blinded adversarial review read the code against its requirements, without the builder's reasoning, and proved each finding with a reproduction it ran. It found 22 defects: 4 High, 9 Medium, 9 Low. Every one was reproduced before it was fixed, and every fix was re-run through the reviewer's own probes:

| Finding | Before | After |
|---|---|---|
| A credential at the start of a line (a pasted `.env` block) | not refused; reached all 9 agents | refused before any agent |
| OpenAI project, Google, xAI, and Mistral key shapes | not recognized | refused |
| A credential in `decision_types` | repeated in the refusal | never repeated |
| A decision log emptied to zero bytes | "no decisions recorded", exit 0 | integrity failure, exit 2 |
| The sidecar deleted and the tail cut | verified; an ex ante score could be rewritten | integrity failure, exit 2 |
| Two writers recording one id | 59 of 200 two-process trials corrupted the log | 0 of 200 |
| A lookalike id (trailing newline, full-width digits) | accepted as new | refused |
| A walled term in a file name, base64url rule entries, UTF-16 files, HTML-entity dashes | printed, skipped, or missed | withheld, decoded, and caught |
| Tests that passed with the behavior removed | six planted deletions survived | caught |

Fixing it also exposed a defect of the fix itself: the scan tool's new `--root` option silently dropped the first file argument whenever `--root` was absent. A self-scan caught it before any push, and a command-line test now pins it.
- **Flutter:** NOT RUN. This container has no Flutter toolchain, and this change touches no Dart.

## First Measurement: The Claim-Auditor Procedure

The full record, including every item, the key, and the answers, is in `adjudication/eval/numeric-audit-v1.json`. That set is now spent: it has been published, so the next measurement needs new items.

| Set | Items | Correct | Wilson 95% |
|---|---|---|---|
| Fresh | 6 seeded numerical defects, 6 corrected controls | 12 of 12 | [75.7%, 100.0%] |
| In-sample (contaminated) | 5 seeded defects from `seeded_rho.py`, 5 controls | 10 of 10 | [72.2%, 100.0%] |

**Method.** Each defect was paired with the same statement corrected, with every value computed in Python. Two batches each held exactly one member of every pair, so no answer could be found by contrast. Each batch went to a separate agent, which reported opening no files. Answers were scored against the key in code.

**What it shows** [Evidence-Based Inference]. On these items the procedure caught both pure computation slips and formula-choice defects (an unweighted average, a percent confused with percentage points, compounding computed as simple growth) without flagging the corrected controls.

**What it does not show:**
- **Small n.** A true accuracy anywhere from about 76% to 100% on items like these is consistent with 12 of 12.
- **One run per batch.** Model output varies between runs, and this is one sample.
- **Author bias.** The same author wrote the fresh items and the auditor's checklist, which names several of these defect types generically.
- **A defining question.** The question defined "error" to include a misapplied formula. The five-vendor baseline was told the opposite, so no comparison with that baseline is claimed.
- **Not the registered agent.** The instructions were delivered in a prompt to a general-purpose agent, because the registered agent type loads only after a session restart.
- **Contamination.** The in-sample set was contaminated: the checklist was written with those defect types in view, including holdout item A6.

## What Is Not Claimed

- **Some restrictions are instructions, not enforcement.** The five checkers that hold Bash are told to use it read-only (the statistician also writes the decision log through its command line), but Bash can write files. Council seats are told to read only repository files, but their Read, Grep, and Glob tools take any path; the operator's pre-committed answer is withheld from every prompt, not from the disk.
- **The chain is unsigned.** A rewrite that recomputes every hash and the sidecar is invisible without the anchor you recorded elsewhere.

- No success probability for any decision, and no percentage for any agent beyond the single measurement above.
- No independence between Claude agents. Every agent here is one model family, so agreement among them is consistency, not corroboration. Cross-vendor independence comes only from the adjudication panel (whose independence is unmeasured, per the finding above) or from separate ChatGPT and Gemini reviews via `adjudication/make_review_bundles.py`.
- Mutation testing shows the tests catch the planted deletions; it does not prove the code has no other defect.

## What Would Raise Confidence Next

Each of these is measurable.

1. Record every Council decision in the Decision Log at decision time and review it on its date. Percentages by confidence tier appear as reviews accrue, each with its interval.
2. Re-measure the panel's correlation with a probe whose contract matches its answer key. This is paid, so it is the operator's decision.
3. Extend the claim-auditor measurement with new held-out items written by someone other than the checklist's author, repeated runs, and citation items graded by the DOI registry.
4. Have an independent vendor review this change with `adjudication/make_review_bundles.py`.
