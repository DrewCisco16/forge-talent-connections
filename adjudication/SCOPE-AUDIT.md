# Scope audit — every specification, from the first day to now

Every requirement in `SOP_v1.2.html`, `MVP-CODEGEN-decisions-needed.md`,
`CODEX-VERIFY.md` and `START-HERE.md`, checked against the code on
2026-08-29. Status is one of **BUILT** (in the code and tested),
**BUILT — NOT LIVE** (in the code, never exercised against real seats),
or **OPEN** (not built, with the reason).

Where a row says BUILT the evidence column names the test or the module, so
the claim can be refused. Nothing here is asserted from memory.

---

## SOP §2.3 — what the tool does, step by step

| # | Specification | Status | Evidence |
|---|---|---|---|
| 2.3.1 | Preflight gate: skip the whole run if one good model already handles the task class | BUILT | `adjudication_orchestrator.preflight`, §6.4 threshold 0.45 |
| 2.3.2 | Five models propose without seeing each other, or any earlier round's results | BUILT | `test_night_loop.TestThinkersAreBlind`; the prompt builder takes no history |
| 2.3.3 | Every proposed correction sorted: can a machine check it? | BUILT | `Gate.applies_to` routing |
| 2.3.4 | Machine-checkable claims checked by machine; no AI opinion | BUILT | `ArithmeticGate`, `SchemaGate`, `UnitGate`, `CitationResolutionGate`, `SourceAdmissibilityGate` |
| 2.3.5 | Unmachine-checkable claims escalate to a human queue | BUILT | `Orchestrator.escalation_queue` |
| 2.3.6 | Five passes, in the specified order | BUILT | `night_loop.ROUNDS`, `test_convergence` pins the order |
| 2.3.7 | **Four of which can eliminate; the fifth calibrates and cannot rule anything out** | **BUILT — FIXED THIS PASS** | Was violated in the live engine. `Round.eliminates`, `TestTheCalibrationPassCannotEliminate`, 6 mutants killed |
| 2.3.8 | Measures whether new errors are still being found | BUILT | `convergence.analyse` VCY series |
| 2.3.9 | Measures how much the five models disagreed | BUILT | `convergence.divergence`, SOP 6.5 content key |
| 2.3.10 | Reports the answer: survivors, why each other was removed, every hole with what would close it | BUILT | `render_record`, `convergence.Hole` |
| 2.3.11 | Nothing selected, scored or preferred; ties not broken | BUILT | `assess` returns PARTIAL on >1 survivor and refuses to choose |

## SOP §6 — the math

| # | Specification | Status | Evidence |
|---|---|---|---|
| 6.1 | `n_eff = n / (1 + (n-1)·rho)` | BUILT | `seat_independence.effective_seats` |
| 6.2 | Chao1 `N_hat = S_obs + f1²/(2·f2)`, reported as a LOWER bound | BUILT | `chao1_lower_bound` |
| 6.2 | Never read the estimator without rho beside it | BUILT | `convergence.render` prints the standing order; pinned by test |
| 6.3 | Decay fit on gate FAILURES only, k = 1…K | BUILT | `fit_decay`; `test_only_gate_failures_count_as_yield` |
| 6.3 | Stop rule is a CONJUNCTION including an empty queue | BUILT | `Orchestrator.should_stop`, `convergence.Convergence.stop` |
| 6.4 | The 0.45 capability gate | BUILT | `preflight` |
| 6.5 | Per-pass Jaccard on (kind, warrant), not on labels | BUILT | `test_claims_are_compared_on_content_not_on_wording` |
| 6.5 | Unanimity raises a collapse flag; silence does NOT | BUILT | `test_every_seat_silent_is_not_a_collapse` |
| 6.6 | Correctness matrix, strict 1/0, escalated EXCLUDED and counted | BUILT | `correctness_matrix.build_correctness_matrix` |
| 6.6 | Fail closed: fewer than two seats or no adjudicated claim → blockers, no numbers, rho named in words | BUILT | `MatrixCoverage`, `_reading` |
| 6.6 | An operator may adjudicate only a claim no gate decided | BUILT | `AdjudicationConflict` |
| 6.7 | Cut seats, never passes | DOCUMENTED | Advisory; the engine runs all five passes and `plan_run` sizes caps rather than dropping passes |

## SOP §8 — build checklist

| # | Specification | Status | Evidence |
|---|---|---|---|
| 8.2 | Loader fails closed on a missing or blank key | BUILT | `MissingSeatCredential` |
| 8.2 | Credentials redacted from every log line, repr and error | BUILT | `approved_test_gate.redact`, `seat_adapter` redaction |
| 8.2 | `.env` and `profiles.json` never tracked by git | BUILT | verified with `git check-ignore` |
| 8.3 | Blinding verified structurally, canary test | BUILT | `test_no_thinker_sees_another_thinkers_text` |
| 8.3 | Citation resolver wired to a REAL lookup | BUILT | `doi_resolver.DoiResolver` (Crossref, then doi.org) |
| 8.3 | Resolver probed with a fake identifier, confirmed False | BUILT | `probe_resolver` |
| 8.3 | Admissibility gate NEVER routed alone | BUILT | conjunctive routing; with no resolver, citation claims escalate |
| 8.3 | Preprints rejected by default; an opt-in recorded in the audit trail | BUILT | `SourceClass`, `classify_source` |
| 8.3 | Claim line is `CLAIM \| kind \| warrant \| text`, in that order | BUILT | `line_claim_extractor`; verified against a parsed claim |
| 8.3 | Test runner wired to a real command | BUILT | `approved_test_gate.ApprovedCommandRunner`, allowlist, no shell |
| 8.3 | Durable audit log written, reopened, verified | BUILT | `audit_log` hash chain |
| 8.4 | Set your singleton-fraction alarm; until you do the check is NOT ARMED | BUILT | unarmed is a stop-rule blocker, not a pass |
| 8.5 | Every run writes an audit record | BUILT | `status.md`, `panel.md`, per-round files |
| 8.5 | Cost per run logged | BUILT | `CostLedger.render` |

## SOP §9 — daily operation

| # | Specification | Status | Evidence |
|---|---|---|---|
| 9.1 step 4 | Read GATE RESULTS before any model prose | BUILT | `full_run.py` prints gates first, by construction |
| 9.1 steps 9–10 | rho, effective seats, residual, singleton fraction, per-pass divergence | BUILT | `convergence.render` |
| 9.1 step 11 | Commit ONLY when one candidate survives AND no holes remain | BUILT | `full_run` section 4 |
| 9.1 step 12 | Log the run, verify the audit chain | BUILT | `audit_log.verify` |
| 9.2 | Six abort signals | BUILT | `should_stop` blockers + `convergence.blockers` |
| 9.3 | Holes are part of the answer; each names its own remedy | BUILT | `test_every_hole_names_what_would_close_it` |
| 9.3 | Exit non-zero while any hole remains | BUILT | `Convergence.exit_code`, `full_run` return value |

## MVP-CODEGEN — the six open decisions

| # | Specification | Status | Evidence |
|---|---|---|---|
| 1 | Cost ceiling wired to the run path; usage extraction per vendor | BUILT | `cost_ledger`, `plan_run`, pre-dispatch reservation, `fcntl.flock` day lock |
| 1.3 | On a ceiling trip: write what completed, mark PARTIAL, exit non-zero, never continue | BUILT | `CeilingReached` / `CeilingOverrun` hierarchy |
| 1.4 | Estimate from the configured cap, not a rolling average | BUILT | `plan_run` |
| 2 | Crossref field matching — title, author, year, venue | BUILT | `citation_gate.CitationFieldMatchGate` |
| 2.5 | A record too sparse to field-match is BLOCKED, not FAILED | BUILT | `citation_gate` |
| 3 | BLOCKED vs FAILED mapping across HTTP, DNS, TLS, timeout, malformed JSON | BUILT | `doi_resolver.ResolverBlocked`, `GateStatus.BLOCKED` |
| 3.3 | BLOCKED never contributes to earned kills or the conduct ledger | BUILT | `eliminate` ignores BLOCKED; `seat_conduct` |
| 4 | `code_behavior` runner: allowlist, no shell, timeout, model output never executed | BUILT | `approved_test_gate`, `approved-commands.json` |
| 5 | **Stage-6 adversarial auditors, automated** | **OPEN** | See below |
| 6 | Watched folder on macOS: debounce, quarantine, refuse to run before ceilings are wired | BUILT | `watcher.py`, `wait_until_stable` |

---

## The one open item, and why it is open rather than done

**MVP §5 — two automated adversarial auditors.**

Half of it exists. `write_verifier_packet` produces exactly what §5 specifies:
the final answer and its surviving claims only, never the round files, with
attribution stripped so a verifier cannot weight a claim by who made it. The
auditor is a human carrying it to a fresh chat.

What is not built is the automated pair. It is open because §5.1 poses a trade
that is the operator's to make and not mine:

> auditors *must not have participated in stages 1–5, which with five seats
> means the panel drops to three thinkers.*

Three thinkers × five passes is 15 seat-calls against 25, and SOP §6.7's table
prices it: effective seats fall from 1.67 to 1.50 at rho = 0.5. That is a
bounded, computable 10% loss of capacity in exchange for two auditors — a real
trade, not an obvious one, and it changes what the instrument is.

§5.3 — "what counts as a hit, mechanically?" — no longer needs an answer
invented for it. The architecture already answers it: an auditor's assertion
changes nothing, and only a `CHALLENGE` that code recomputes to a FAIL does.
So the auditors would plug into the existing machinery unchanged. The only
question left is the one above, and it needs a decision, not code.
