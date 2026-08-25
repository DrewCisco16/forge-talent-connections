# Domain profile: Software Build Under Adjudication

Add this as a sixth profile to the Adjudication Panel Console build order. It is the profile for building a software application whose correctness has to be defensible to three different audiences at once: a USPTO examiner, a government contracting officer, and the operator.

Paste-ready. Contains no confidential material.

## 0. Classification — read before the first run
GREEN, and therefore permitted:
- US 2026/0186826 A1, published 2 Jul 2026 (Appl. 19/542,902)
- US 2026/0246640 A1, published 20 Aug 2026 (Appl. 19/544,983)
Both are published USPTO documents in the public record. Their titles, abstracts, drawings, specification, and published claims may be sent to all five seats.
RED, and refused by intake:
- Any amendment, office-action response, or draft continuation claim not yet published
- Anything in provisionals 63/760,135 or 63/760,373 not carried into the published text
- Any claim language the operator is currently drafting
The rule is publication status, not subject matter. Intake asks one question — is every word of this artifact already published? — and refuses on anything other than an unqualified yes. It does not offer redaction.

## 1. What this profile is for
Building a working software application that embodies a published patent, under five-seat adjudication, producing three artifacts at once: 1) the software (running, tested, deployable); 2) a defensible correctness record (every design decision that survived, and what mechanically killed the ones that did not); 3) a hash-chained, timestamped evidence trail. The third is easiest to skip and hardest to reconstruct afterward.

## 2. What the artifact is
Not the patent (the patent is context). The artifact is one build decision document: a specific, bounded technical question written so competing answers can be stated and one proven wrong. Good: "The mutation-boundary controller must reject a state transition when the reference hash does not match — proposed check, failure modes, cost per call." "Three ways to structure the shadow region so activation is atomic under concurrent writers, with throughput/memory implications." "The DecisionToken validation path and the thirteen fields it must verify, with failure behaviour per missing/expired field." Bad (produces five essays, no elimination): "How should I build this patent?" / "Is my architecture good?" Rule: if the operator cannot state what would prove a candidate wrong, intake stops and says the question is not yet decidable. Not skippable.

## 3. What candidates look like
Two to five competing implementation decisions, each a complete assertable position with the numbers it rests on. Example:
c_shadow_copy_on_write : "Stage mutations in a copy-on-write shadow page; activation is a single pointer swap. One page per epoch, activation O(1)."
c_shadow_journal : "Stage mutations in an append-only journal replayed on activation. O(n) activation, no page duplication."
c_shadow_inline : "Mutate in place under a lock, roll back on hash mismatch. No extra memory, activation O(1), but not atomic under a crash."
Each carries claims.

## 4. Claim types that matter here, in priority order
arithmetic — the workhorse. Every capacity/throughput/latency/memory figure becomes an arithmetic claim with a real expression.
  - type: arithmetic
    text: "one shadow page per epoch at 4 KiB and 10000 epochs per hour is 40 MiB per hour"
    expression: "4096 * 10000"
    expected: "40960000"
If a number's derivation is unknown, it is judgement. Never invent an expression — a fabricated expression that evaluates true manufactures an earned kill and puts a false verification into the record.
code_behavior — proves it works. A command that actually runs, with a pass condition.
  - type: code_behavior
    text: "activation is atomic: a crash mid-activation leaves the prior state intact"
    expression: "pytest tests/test_activation_atomicity.py -q"
    expected: "exit 0"
Sandboxing is absolute. The command is one the operator wrote and approved. Model output is never executed, never determines a path, never becomes a command. A code_behavior warrant proposed by a seat is recorded as a suggested test to write, never a command to run.
unit — dimensional discipline. Throughput/memory/latency conversions; catches right-number-wrong-unit.
citation — prior art and standards. Published patents, RFCs, NIST, peer-reviewed work. DOIs must resolve AND field-match; for patent numbers and standards, retrieval must reach the primary source.
judgement — everything else, honestly labelled (architectural taste, maintainability). Escalates to the operator. A run where most claims are judgement should be told to the operator before money is spent.

## 5. Gates required for this profile
On: arithmetic, unit, schema, code_behavior (with an operator-supplied test runner), citation conjoined with source admissibility. A build run with zero earned kills is reported CONSENSUS ONLY and should be treated as a FAILED run, not a clean one — send it back to intake and demand derivations before spending again.

## 6. The evidence trail
Every run writes, and the operator keeps: run-NNN.jsonl (hash-chained audit log, never overwrite); the artifact SHA-256 and audit head (together fix exactly what text was adjudicated); the seat conduct ledger; kill provenance (earned vs structural, per run). Why it matters beyond software: under Graham v. John Deere, objective indicia (reduction to practice, commercial success, long-felt need) are relevant to non-obviousness under §103; a contemporaneous tamper-evident record of a working implementation supports that, and is more credible produced during the build than reconstructed after an office action. What it does NOT do: it does not address §101 eligibility and does not overcome §102 anticipation — those are claim-drafting/prosecution questions for patent counsel. Build the record because it is useful; do not let the plan depend on it being decisive.

## 7. Government-contract track
For an SDVOSB pursuing set-aside work, the same runs produce reusable material: technical approach narratives grounded in decisions that survived adversarial review (with rejected alternatives and why); past performance from working software with a test record; risk mitigation from the escalation queue and hole list. Two cautions: nothing here predicts an award (set-aside eligibility, NAICS fit, capability statements, SAM registration, past performance decide that); never put anything from a run into a proposal without checking its gate status — a claim that escalated as judgement is an opinion, and presenting it as verified in a federal proposal is materially different from presenting it as verified to yourself.

## 8. Intake questions for this profile
1. Is every word of this artifact already published? (RED gate — refuse on anything but yes)
2. What single build decision is this run adjudicating?
3. What would prove a candidate wrong? (refuse to proceed without an answer)
4. What are the two to five competing implementations?
5. For each numeric assertion: what is the expression that produces it?
6. Which behaviours have tests that already run, and which are tests you still need to write?
7. What do you currently believe the answer is? (recorded, so the run can be checked against the prior)

## 9. First run, recommended
Do not start with architecture. Start with the narrowest decision that has real numbers behind it — a capacity or atomicity question — because it exposes intake design problems fastest and produces earned kills on the first attempt. Ship one profile, run it, confirm at least one earned kill, then widen.
