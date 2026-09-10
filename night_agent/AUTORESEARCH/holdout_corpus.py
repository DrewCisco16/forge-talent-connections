#!/usr/bin/env python3
"""Frozen fault corpus for the Night Agent autoresearch loop.

FROZEN 2026-09-10 before the first mutation of the package. Every case here is
derived from a rule stated in NIGHT_AGENT_SPEC.md (the spec_ref field names
the section). Nothing here was written from reading where the checker is weak;
cases were enumerated from the spec text and then split DEV / HOLDOUT by rule
family, one surface form per split, so a check that fits the DEV wording
without enforcing the rule fails its HOLDOUT twin.

Two conforming base runs are built from scratch (they do not reuse
TESTS/make_fixture.py, which is the package's own training fixture):

  hybrid  runs/na-001  HYBRID class, GENERATE + FMEA + IDOV, review, final,
                       verify, one experiment, ledger, architecture history.
  direct  runs/na-002  DIRECT class, one generator, check, final, verify.

Editing this file after the baseline is recorded is a change to the objective,
not to the artifact, and must be logged as such in AUTORESEARCH/log.jsonl.
"""
import hashlib
import json
import os
import re
import shutil

MODEL_NAMES = ("Sol", "Gemini", "Grok", "Magistral", "Fable", "Astra", "GPT", "Claude", "Mistral")


def sha_text(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, t):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(t)


# ----------------------------------------------------------------------------- builder
class RunBuilder:
    def __init__(self, root, run_id):
        self.root = root
        self.run_id = run_id
        self.log = []
        self.dispatch = []
        self.capture = []
        self.metrics = []
        self.tick = 0
        os.makedirs(root, exist_ok=True)

    def t(self):
        self.tick += 1
        return f"2026-09-09T22:{self.tick // 60:02d}:{self.tick % 60:02d}"

    def L(self, seat, action, file=None, stage=None, sha=None):
        d = {"t": self.t(), "seat": seat, "action": action, "result": "OK"}
        if file:
            d["file"] = file
        if stage:
            d["stage"] = stage
        if sha:
            d["sha256"] = sha
        self.log.append(d)

    def put(self, rel, text, seat="DISPATCH", action="write", stage=None):
        write(os.path.join(self.root, rel), text)
        self.L(seat, action, file=rel, stage=stage, sha=sha_text(text))
        return text

    def D(self, stage_dir, seat, did):
        self.dispatch.append({
            "run_id": self.run_id, "stage_id": stage_dir, "seat_id": seat, "provider": "p",
            "conversation_url": f"https://chat.example/{seat}", "tab_id": "t", "displayed_model": "m",
            "displayed_effort": "high", "prompt_hash": "h", "dispatch_id": did, "expected_reply_slot": "1",
            "snapshot_hash": "s", "t": self.t()})

    def seat_file(self, stage_dir, stage_name, seat, did, body, stage_label):
        text = f"{stage_name} SEAT {seat} TIME 22:{10 + self.tick % 40:02d}\nDISPATCH {did}\n" + body
        self.D(stage_dir, seat, did)
        rel = f"{stage_dir}/seat-{seat}.md"
        self.put(rel, text, seat=seat, action="send", stage=stage_label)
        self.capture.append({
            "dispatch_id": did, "file": rel, "completion_signal_observed": True, "start_boundary": "b0",
            "end_boundary": "b1", "char_count": len(text), "byte_hash": sha_text(text),
            "observed_identity": seat, "partial": False})

    def finish(self, status, ledger):
        write(os.path.join(self.root, "status.json"), json.dumps(status))
        write(os.path.join(self.root, "ledger.json"), json.dumps(ledger))
        write(os.path.join(self.root, "log.jsonl"), "\n".join(json.dumps(x) for x in self.log) + "\n")
        write(os.path.join(self.root, "dispatch.jsonl"), "\n".join(json.dumps(x) for x in self.dispatch) + "\n")
        write(os.path.join(self.root, "capture.jsonl"), "\n".join(json.dumps(x) for x in self.capture) + "\n")
        write(os.path.join(self.root, "metrics.jsonl"), "\n".join(json.dumps(x) for x in self.metrics) + "\n")


def SRC(scope, support="SUPPORTED", grade="A"):
    return (f'  SOURCE     provenance=standards or official technical documentation grade={grade} '
            f'quote_present=yes support={support} scope="{scope}" retrieved=2026-09-09T23:00 '
            f'retraction=checked age=ok\n')


def claim(cid, prov, text, method, action, retrieved, result, settle="", source=""):
    return (f'CLAIM {cid} [{prov}] "{text}"\n  METHOD     {method}\n  ACTION     {action}\n'
            f'  RETRIEVED  {retrieved}\n  RESULT     {result}\n  SETTLE     {settle}\n{source}')


def build_hybrid(root):
    """runs/na-001: a complete, conforming HYBRID run."""
    b = RunBuilder(root, "na-001")
    seats = ["G1", "G2", "G3", "G4", "CLOSER", "REVIEWER", "VERIFIER", "EXECUTOR"]
    b.put("ask.md", "Make the CSV importer reject malformed rows without slowing valid imports.\n", seat="OP")
    reg = {"seats": [{"id": s, "role": ("generator" if s.startswith("G") else s.lower()),
                      "url": f"https://chat.example/{s}", "model": f"model-{s}",
                      "ready": s != "G4", "fresh": True, "handshake_time": "22:01",
                      "failed_stages": [], "retired": False} for s in seats]}
    reg["seats"][0]["backup_closer"] = True
    b.put("registry.json", json.dumps(reg))
    for s in seats:
        if s != "G4":
            b.L(s, "handshake", stage="REGISTRY")
        else:
            b.L(s, "handshake", stage="REGISTRY")
            b.log[-1]["result"] = "FAILED"
    b.put("gate/gate.md", "CLASS - HYBRID\nCLASS BASIS - part measurable (timing harness), part judgement.\nKIND - build\n",
          seat="CLOSER", action="send", stage="GATE")
    gate = {"ask": "Make the CSV importer reject malformed rows without slowing valid imports.",
            "class": "HYBRID", "class_basis": "model: a timing harness exists; validation policy is judgement",
            "kind": "build", "success_criteria": "tests pass; p95 import time within 5 percent of baseline",
            "hard_constraints": ["output hash unchanged on valid inputs"],
            "available_ground_truth": ["project documents", "test suite"],
            "objectives": [{"name": "runtime_s", "direction": "lower", "procedure": "python3 bench.py --n 10000",
                            "not_measured": "memory", "gaming": "skip validation on large files",
                            "guardrail": "output_hash_changed", "tolerance": 0}],
            "budget": {"max_calls": 40, "max_operators": 4, "max_experiments": 8, "max_wait_min": 10,
                       "reviewer_wait_min": 10, "min_delta": None, "plateau_k": 3, "experiment_budget_s": 600},
            "hard_stop": "06:00", "profile": "adaptive", "min_crew": 2, "backup_closer": "G1",
            "planned_calls": 20, "spending_permission": "none",
            "priority_order": ["correctness", "evidence integrity", "reproducibility", "cost and time"],
            "payload_authorization": "default", "rollback_hash": ""}
    b.put("gate/gate.json", json.dumps(gate))

    # ---- stage 01 GENERATE
    gen = {
        "G1": ("CANDIDATES\nA. Validate every row with a schema before insert.\n   APPROACH / ASSUMPTIONS / REQUIRED CLAIMS 1 / FALSIFICATION CONDITIONS\n"
               "B. Sample rows and validate the sample only.\nCLAIMS\n1. The current importer handles 12 columns at 1800 rows per second (sum).\n"
               "KNOCKDOWN\nA dies if schema validation doubles runtime.\nMISSING\nA timing baseline.\n"),
        "G2": ("CANDIDATES\nA. Reject rows at parse time using the vendor library's strict mode.\n"
               "CLAIMS\n2. The parser library documents a strict mode that rejects ragged rows (source).\n4. Strict mode is what most teams use (judgement call).\n"
               "KNOCKDOWN\nA dies if strict mode is not in the pinned version.\nMISSING\nThe pinned version.\n"),
        "G3": ("CANDIDATES\nA. Two-pass import: count columns first, then load.\n"
               "CLAIMS\n3. The project brief requires malformed rows to be reported, not dropped (document).\n6. The reference branch test suite passes (command).\n"
               "KNOCKDOWN\nA dies if the second pass exceeds the timing budget.\nMISSING\nWhether the brief allows partial loads.\n"),
    }
    for s, body in gen.items():
        b.seat_file("stage-01-generate", "STAGE 01 GENERATE", s, f"d-01-{s}", body, "GENERATE")
    check1 = (
        claim("C1", "G1", "The current importer handles 12 columns at 1800 rows per second", "sum",
              "recomputed from bench.log: 21600 rows in 12 s", "21600 / 12 = 1800", "PASSED")
        + claim("C2", "G2", "The parser library documents a strict mode that rejects ragged rows", "source",
                "read the pinned library docs page, section Dialects", '"strict: when True, raise Error on bad CSV input"', "PASSED",
                source=SRC("library docs, Dialects section"))
        + claim("C3", "G3", "The project brief requires malformed rows to be reported, not dropped", "document",
                "read brief.md section 4", '"every rejected row is written to rejects.csv with its line number"', "PASSED",
                source=SRC("brief.md section 4"))
        + claim("C4", "G2", "Strict mode is what most teams use", "none", "no method available", "", "JUDGEMENT CALL",
                settle="a survey of importer configurations in comparable projects")
        + claim("C5", "G1", "Schema validation adds under 5 percent runtime", "source",
                "read the library performance page", "page reports 3 to 9 percent depending on row width", "INCONCLUSIVE",
                settle="run the timing harness on the 12-column file", source=SRC("performance page, partial figure", support="PARTIAL", grade="B"))
        + claim("C6", "G3", "The reference branch test suite passes", "command", "ran pytest on the reference branch", "", "BLOCKED",
                settle="rerun when the package index is reachable; pip timed out")
    )
    b.put("stage-01-generate/check.md", check1, stage="CHECK")
    close1 = ("OPTIONS\n1. Schema validation before insert. Requires C1, C2. Falsified if runtime rises more than 5 percent.\n"
              "2. Two-pass import with a reject report. Requires C3. Falsified if the second pass exceeds the budget.\n"
              "3. Sample-and-validate. Requires C7. Falsified if a malformed row escapes the sample.\n"
              "KILLS\nnone\n"
              "OPEN\n- C4 judgement call: settle with a configuration survey\n- C5 partial support: settle with the timing harness\n- C6 blocked: rerun when the index is reachable\n"
              "METRICS\noptions_created=3 options_standing=3 claims_total=6 claims_checkable=5 passed=3 failed=0 judgement=1 not_testable=0 blocked=1 inconclusive=1 earned_kills=0 deprioritized=0\n")
    b.put("stage-01-generate/close.md", close1, seat="CLOSER", action="send", stage="CLOSE")
    b.metrics.append({"stage": "stage-01-generate", "options_standing": 3, "passed": 3, "failed": 0, "earned_kills": 0, "deprioritized": 0, "model_calls": 4})

    # ---- stage 02 FMEA
    for s in ["G1", "G2", "G3"]:
        body = ("WRONG\nnone found; check C1 by rerunning bench.py (command)\nMISSING\nfailure visibility when the sample misses a malformed row\n"
                "KILLS\nOption 3: a sampled validation cannot guarantee every malformed row is rejected; checkable by the sample size sum\n"
                "OPEN\nwhat sample rate the brief would accept\n")
        b.seat_file("stage-02-fmea", "STAGE 02 FMEA", s, f"d-02-{s}", body, "OPERATE")
    check2 = (
        claim("C7", "G1", "A 10 percent sample catches every malformed row in a 9000-row file with 5 malformed rows", "sum",
              "computed the probability that all 5 fall in the sample", "0.1 ^ 5 = 0.00001, so the sample misses at least one in all practical runs", "FAILED")
        + claim("C8", "G2", "The brief sets the reject report as a hard requirement", "document", "read brief.md section 4",
                '"rejected rows MUST be reported"', "PASSED", source=SRC("brief.md section 4"))
    )
    b.put("stage-02-fmea/check.md", check2, stage="CHECK")
    close2 = ("MERGED\n- The importer processes 1800 rows per second today and the library offers a strict mode. [G1][G2] {C1,C2}\n"
              "- The brief requires rejected rows to be reported with line numbers. [G3][G2] {C3,C8}\n"
              "KILLS\n- Option 3 killed by claim C7 FAILED (sampling cannot reject every malformed row), EARNED\n"
              "DEPRIORITIZED\n- Option 2: the seats found the second pass less persuasive on cost; it stays standing\n"
              "OPEN\n- C4 judgement call: settle with a configuration survey\n- C5 partial support: settle with the timing harness\n- C6 blocked: rerun when the index is reachable\n"
              "CONFLICT\nnone\n"
              "OPTIONS STANDING\n1. Schema validation before insert.\n2. Two-pass import with a reject report.\n"
              "METRICS\noptions_created=0 options_standing=2 claims_total=2 claims_checkable=2 passed=1 failed=1 judgement=0 not_testable=0 blocked=0 inconclusive=0 earned_kills=1 deprioritized=1 decision_changed=yes\n")
    b.put("stage-02-fmea/close.md", close2, seat="CLOSER", action="send", stage="CLOSE")
    b.metrics.append({"stage": "stage-02-fmea", "options_standing": 2, "passed": 1, "failed": 1, "earned_kills": 1, "deprioritized": 1, "model_calls": 4})

    # ---- stage 03 IDOV
    for s in ["G1", "G2", "G3"]:
        body = ("WRONG\nnone\nMISSING\na measured runtime for option 1 on the 12-column file\n"
                "KILLS\nnone\nOPEN\nwhether option 2 can be built inside the timing budget; settle with the harness\n")
        b.seat_file("stage-03-idov", "STAGE 03 IDOV", s, f"d-03-{s}", body, "OPERATE")
    check3 = (
        claim("C9", "G3", "The reference branch test suite passes", "command", "ran pytest on the reference branch after the index recovered",
              "12 passed in 3.1 s", "PASSED")
        + claim("C10", "G1", "Option 2 fits the timing budget", "experiment", "ran the harness once on option 2",
                "", "INCONCLUSIVE", settle="a second harness run; the first was within noise of baseline")
    )
    b.put("stage-03-idov/check.md", check3, stage="CHECK")
    close3 = ("MERGED\n- The importer processes 1800 rows per second today and the library offers a strict mode. [G1][G2] {C1,C2}\n"
              "- The brief requires rejected rows to be reported with line numbers. [G3][G2] {C3,C8}\n"
              "- The reference branch test suite passes. [G3] {C9}\n"
              "KILLS\nnone\n"
              "DEPRIORITIZED\n- Option 2: unchanged from the previous close\n"
              "OPEN\n- C4 judgement call: settle with a configuration survey\n- C5 partial support: settle with the timing harness\n- C10 inconclusive: settle with a second harness run\n"
              "CONFLICT\nnone\n"
              "OPTIONS STANDING\n1. Schema validation before insert.\n2. Two-pass import with a reject report.\n"
              "METRICS\noptions_created=0 options_standing=2 claims_total=2 claims_checkable=2 passed=1 failed=0 judgement=0 not_testable=0 blocked=0 inconclusive=1 earned_kills=0 deprioritized=1 decision_changed=no\n")
    b.put("stage-03-idov/close.md", close3, seat="CLOSER", action="send", stage="CLOSE")
    b.metrics.append({"stage": "stage-03-idov", "options_standing": 2, "passed": 1, "failed": 0, "earned_kills": 0, "deprioritized": 1, "model_calls": 4})

    # ---- experiments (EXPERIMENT operator ran inside HYBRID)
    b.put("experiments/baseline.json", json.dumps({"metric": "runtime_s", "direction": "lower", "baseline_value": 10.0, "noise": 0.3,
                                                   "runs": 2, "environment": "py3.11 linux", "procedure": "python3 bench.py --n 10000"}))
    b.put("experiments/exp-001/proposal.md", "ID - exp-001\nHYPOTHESIS - caching the schema halves runtime\n", seat="G1", action="send", stage="PROPOSE")
    b.put("experiments/exp-001/output.txt", "runtime_s 6.0\n", seat="EXECUTOR", action="write", stage="EXECUTE")
    rec = {"id": "exp-001", "hypothesis": "caching the schema halves runtime", "metric": "runtime_s", "baseline_value": 10.0,
           "result_value": 6.0, "delta": -4.0, "noise": 0.3, "repeat_value": 6.1,
           "constraints_checked": ["output hash unchanged on valid inputs"],
           "guardrails": [{"name": "output_hash_changed", "baseline": 0, "value": 0, "tolerance": 0}],
           "decision": "KEEP", "within_budget": True, "budget_s": 600, "cost": {"runs": 2, "elapsed_s": 25},
           "artifact_hash": "a" * 64, "git_commit": "exp-001"}
    b.put("experiments/exp-001/record.json", json.dumps(rec), stage="DECIDE")
    b.put("experiments/log.jsonl", json.dumps({"id": "exp-001", "decision": "KEEP", "delta": -4.0, "repeat_value": 6.1}) + "\n", stage="DECIDE")

    # ---- review
    pkg = ("MERGED\n- The importer processes 1800 rows per second today and the library offers a strict mode. [1][2] {C1,C2}\n"
           "- The brief requires rejected rows to be reported with line numbers. [3][2] {C3,C8}\n"
           "- The reference branch test suite passes. [3] {C9}\n"
           "CLAIMS\nC1 PASSED 21600 / 12 = 1800\nC2 PASSED strict mode documented\nC3 PASSED brief section 4\nC8 PASSED brief section 4\nC9 PASSED 12 tests\n"
           "C4 JUDGEMENT CALL\nC5 INCONCLUSIVE\nC10 INCONCLUSIVE\n"
           "OPTIONS STANDING\n1. Schema validation before insert.\n2. Two-pass import with a reject report.\n"
           "OPEN\n- C4 judgement call\n- C5 partial support\n- C10 inconclusive\nCONFLICT\nnone\n")
    b.put("review/package.md", pkg, stage="REVIEW")
    b.D("review", "REVIEWER", "d-05-REVIEWER")
    b.L("REVIEWER", "send", file="review/review.md", stage="REVIEW")
    review = ("HITS\n1. The 1800 rows per second figure was measured on a 12-column file; the brief's widest file has 40 columns. Check: bench.py --cols 40 (command).\n"
              "GAPS\n1. Nothing states what happens to a partially loaded file when a reject is found. Settle: read brief.md section 5.\n"
              "HOLDS\n1. C3 and C8 hold: the brief wording is quoted and unambiguous.\n"
              "OPEN\nnone\n")
    write(os.path.join(root, "review/review.md"), review)
    b.log[-1]["sha256"] = sha_text(review)
    b.capture.append({"dispatch_id": "d-05-REVIEWER", "file": "review/review.md", "completion_signal_observed": True, "start_boundary": "b0",
                      "end_boundary": "b1", "char_count": len(review), "byte_hash": sha_text(review), "observed_identity": "REVIEWER", "partial": False})
    checkr = (
        claim("H1", "R", "The throughput figure does not hold at 40 columns", "command", "ran bench.py --cols 40",
              "40 columns: 9000 rows in 12 s = 750 rows per second", "PASSED")
        + claim("GP1", "R", "Partial-load behaviour is unspecified", "document", "read brief.md section 5", "", "INCONCLUSIVE",
                settle="section 5 is silent; the operator must decide", source=SRC("brief.md section 5 is silent", support="UNSUPPORTED", grade="C"))
        + "HOLD 1 HOLD-ACCEPTED (C3, C8 PASSED)\n"
    )
    b.put("review/check-review.md", checkr, stage="CHECK_REVIEW")

    # ---- final
    b.put("final/kills-all.md", "KILLS stage-02-fmea\n- Option 3 killed by claim C7 FAILED (sampling cannot reject every malformed row), EARNED\nKILLS stage-03-idov\nnone\n", stage="FINAL")
    b.put("final/metrics-summary.json", json.dumps({"model_calls": 18, "elapsed_s": 5400, "earned_kills": 1, "deprioritized": 1, "options_standing": 2, "experiments": 1}), stage="FINAL")
    deliv = "\n".join([
        "1 THE RESULT", "Add schema validation before insert, with a reject report; the throughput claim is scoped to 12 columns.",
        "2 WHAT SURVIVED", "- Option 1: schema validation before insert. [G1][G2] {C1,C2}", "- Option 2: two-pass import with a reject report, deprioritized, still standing. [G3] {C3}", "Two options survive.",
        "3 WHY IT SURVIVED", "- C1 PASSED 21600 / 12 = 1800, scoped to 12 columns by H1. [G1] {C1}", "- C2 PASSED strict mode documented. [G2] {C2}",
        "- C3 PASSED brief section 4. [G3] {C3}", "- C8 PASSED brief section 4. [G2] {C8}", "- C9 PASSED 12 tests. [G3] {C9}", "- H1 PASSED 750 rows per second at 40 columns. [R] {H1}",
        "4 OBJECTIVE RESULTS", "baseline runtime_s 10.0 noise 0.3; exp-001 caching, delta -4.0, repeat 6.1, guardrail output_hash_changed 0, KEEP",
        "5 WHAT DIED AND WHY", "- Option 3, claim C7 FAILED, EARNED", "DEPRIORITIZED: option 2, cost, still standing",
        "6 TRADE-OFFS", "option 1 is faster to build; option 2 reports more; not resolved by arithmetic",
        "7 OUTSIDE REVIEW", "HIT 1 PASSED, FIXED: the throughput line now says 12 columns. GAP 1 JUDGEMENT CALL, OPEN. HOLD 1 HOLD-ACCEPTED. SURVIVING DEFECTS: none known.",
        "8 STILL OPEN", "- C4 judgement call; settle with a configuration survey", "- C5 partial support; settle with the timing harness", "- C10 inconclusive; second harness run", "- GAP 1; operator decides partial-load policy",
        "9 CONFIDENCE", "Medium for option 1: throughput scoped by H1. Low for option 2: C10 inconclusive.",
        "10 RUN INTEGRITY", "earned 1 deprioritized 1; stages GENERATE, FMEA, IDOV; stop BUDGET; no seats failed; no closer swap; review ran; flags none; classification KEEP_FOR_DEVELOPMENT",
        "11 EFFICIENCY", "calls 18, elapsed 90 min, experiments 1",
        "12 NEXT QUESTION", "Run the timing harness on option 1 with the 40-column file.",
        "14 PRIVATE DOCUMENT VERIFICATION", ""]) + "\n"
    b.put("final/DELIVERABLE.md", deliv, seat="CLOSER", action="send", stage="FINAL")
    ver = "CONTRADICTIONS\nnone\nCONFIRMED\n1. C3 confirmed by brief.md section 4 line 12\nNOT COVERED\nC1, C2, C9\nMATERIAL OMISSIONS\nnone\n"
    b.put("final/verifier.md", ver, seat="VERIFIER", action="send", stage="VERIFY")
    b.put("final/DELIVERABLE_ASSEMBLED.md", deliv + "\n" + ver, stage="DELIVER")

    status = {"run": "na-001", "stage": "DONE", "step": "deliver", "started": "22:00", "last_complete": "final/DELIVERABLE_ASSEMBLED.md",
              "next": "none", "stop_reason": "BUDGET", "sends_used": 18, "sends_reserved_for_tail": 0, "experiments_used": 1,
              "caps_known": {"p": False}, "flags": []}
    ledger = {"run": "na-001", "class": "HYBRID", "profile": "adaptive", "stages": ["GENERATE", "FMEA", "IDOV"], "stop_reason": "BUDGET",
              "options_created": 3, "options_standing": 2, "earned_kills": 1, "deprioritized": 1, "review_hits_passed": 1, "review_hits_failed": 0,
              "holds_accepted": 1, "verifier_contradictions": 0, "verifier_confirmed": 1, "seats_failed": [], "closer_swaps": 0,
              "model_calls": 18, "elapsed_s": 5400, "flags": [], "morning_usefulness_1_to_5": None, "tonights_question": "",
              "classification": "KEEP_FOR_DEVELOPMENT", "rollback_hash_verified": None}
    b.finish(status, ledger)
    # architecture history two levels up
    arch = os.path.join(root, "..", "..", "architecture")
    write(os.path.join(arch, "criterion.json"), json.dumps({"criterion_id": "crit-001", "primary_metric": "planted_faults_caught_rate", "min_paired_runs": 8,
                                                           "interval": "bootstrap percentile 90", "resamples": 2000, "written": "2026-09-01"}))
    write(os.path.join(arch, "decisions.jsonl"), json.dumps({"id": "dec-001", "candidate": "adaptive", "baseline": "v10-fixed", "split": "HOLDOUT",
                                                             "paired_runs": 8, "mean_diff": 0.12, "ci_low": 0.03, "ci_high": 0.21,
                                                             "criterion_id": "crit-001", "decision": "KEEP"}) + "\n")


def build_direct(root):
    """runs/na-002: a conforming DIRECT run (one generator, check, final, verify)."""
    b = RunBuilder(root, "na-002")
    seats = ["G1", "G2", "CLOSER", "VERIFIER"]
    b.put("ask.md", "What is the sum of the twelve monthly figures in figures.csv?\nCLASS: DIRECT\n", seat="OP")
    reg = {"seats": [{"id": s, "role": ("generator" if s.startswith("G") else s.lower()), "url": f"https://chat.example/{s}",
                      "model": f"model-{s}", "ready": True, "fresh": True, "handshake_time": "22:01", "failed_stages": [], "retired": False} for s in seats]}
    b.put("registry.json", json.dumps(reg))
    for s in seats:
        b.L(s, "handshake", stage="REGISTRY")
    b.put("gate/gate.md", "CLASS - DIRECT OPERATOR SET\nKIND - answer\n", seat="CLOSER", action="send", stage="GATE")
    b.put("gate/gate.json", json.dumps({"ask": "What is the sum of the twelve monthly figures in figures.csv?", "class": "DIRECT",
                                        "class_basis": "operator: CLASS line in ask.md", "kind": "answer", "success_criteria": "the true sum",
                                        "hard_constraints": [], "available_ground_truth": ["figures.csv"], "objectives": [],
                                        "budget": {"max_calls": 6, "max_operators": 0, "max_experiments": 0, "max_wait_min": 10},
                                        "hard_stop": "06:00", "profile": "adaptive", "min_crew": 2, "backup_closer": "G1", "planned_calls": 4,
                                        "spending_permission": "none", "payload_authorization": "default", "rollback_hash": ""}))
    b.seat_file("stage-01-direct", "STAGE 01 DIRECT", "G1", "d-01-G1",
                "ANSWER\n41,880\nCLAIMS\n1. The twelve figures sum to 41,880 (sum).\n2. figures.csv has twelve rows (document).\nOPEN\nnone\n", "DIRECT")
    check = (claim("C1", "G1", "The twelve figures sum to 41,880", "sum", "summed column B of figures.csv in Python", "sum = 41880", "PASSED")
             + claim("C2", "G1", "figures.csv has twelve rows", "document", "read figures.csv", "12 data rows after the header", "PASSED",
                     source=SRC("figures.csv row count")))
    b.put("stage-01-direct/check.md", check, stage="CHECK")
    b.put("final/kills-all.md", "KILLS\nnone\n", stage="FINAL")
    b.put("final/metrics-summary.json", json.dumps({"model_calls": 4, "elapsed_s": 600}), stage="FINAL")
    deliv = "\n".join([
        "1 THE RESULT", "41,880",
        "2 WHAT SURVIVED", "- The direct answer. [G1] {C1}",
        "3 WHY IT SURVIVED", "- C1 PASSED sum = 41880. [G1] {C1}", "- C2 PASSED 12 data rows. [G1] {C2}",
        "4 OBJECTIVE RESULTS", "not applicable",
        "5 WHAT DIED AND WHY", "nothing; DIRECT run",
        "6 TRADE-OFFS", "none",
        "7 OUTSIDE REVIEW", "NO OUTSIDE REVIEW: DIRECT class runs no review stage.",
        "8 STILL OPEN", "none",
        "9 CONFIDENCE", "High: the sum was recomputed.",
        "10 RUN INTEGRITY", "earned 0 deprioritized 0; stages DIRECT; stop SUFFICIENT; review did not run; flags NO_OUTSIDE_REVIEW; classification KEEP_FOR_DEVELOPMENT",
        "11 EFFICIENCY", "calls 4, elapsed 10 min",
        "12 NEXT QUESTION", "none",
        "14 PRIVATE DOCUMENT VERIFICATION", ""]) + "\n"
    b.put("final/DELIVERABLE.md", deliv, seat="CLOSER", action="send", stage="FINAL")
    ver = "CONTRADICTIONS\nnone\nCONFIRMED\n1. C1 confirmed by figures.csv\nNOT COVERED\nnone\nMATERIAL OMISSIONS\nnone\n"
    b.put("final/verifier.md", ver, seat="VERIFIER", action="send", stage="VERIFY")
    b.put("final/DELIVERABLE_ASSEMBLED.md", deliv + "\n" + ver, stage="DELIVER")
    status = {"run": "na-002", "stage": "DONE", "step": "deliver", "started": "22:00", "last_complete": "final/DELIVERABLE_ASSEMBLED.md",
              "next": "none", "stop_reason": "SUFFICIENT", "sends_used": 4, "sends_reserved_for_tail": 0, "experiments_used": 0,
              "caps_known": {}, "flags": ["NO_OUTSIDE_REVIEW"]}
    ledger = {"run": "na-002", "class": "DIRECT", "profile": "adaptive", "stages": ["DIRECT"], "stop_reason": "SUFFICIENT", "options_created": 1,
              "options_standing": 1, "earned_kills": 0, "deprioritized": 1 - 1, "review_hits_passed": 0, "review_hits_failed": 0, "holds_accepted": 0,
              "verifier_contradictions": 0, "verifier_confirmed": 1, "seats_failed": [], "closer_swaps": 0, "model_calls": 4, "elapsed_s": 600,
              "flags": ["NO_OUTSIDE_REVIEW"], "morning_usefulness_1_to_5": None, "tonights_question": "", "classification": "KEEP_FOR_DEVELOPMENT",
              "rollback_hash_verified": None}
    b.finish(status, ledger)


BASES = {"hybrid": ("runs/na-001", build_hybrid), "direct": ("runs/na-002", build_direct)}


# ----------------------------------------------------------------------------- mutation helpers
def edit(root, rel, old, new, count=1):
    p = os.path.join(root, rel)
    s = read(p)
    assert old in s, (rel, old)
    write(p, s.replace(old, new, count) if count else s.replace(old, new))


def rm(root, rel):
    p = os.path.join(root, rel)
    if os.path.isdir(p):
        shutil.rmtree(p)
    else:
        os.remove(p)


def jsonl_map(root, rel, fn):
    p = os.path.join(root, rel)
    rows = [json.loads(l) for l in read(p).splitlines() if l.strip()]
    rows = fn(rows)
    write(p, "".join(json.dumps(r) + "\n" for r in rows))


def json_edit(root, rel, fn):
    p = os.path.join(root, rel)
    d = json.load(open(p))
    fn(d)
    write(p, json.dumps(d))


def resign(root, log=True, captures=True):
    """Re-sign the run as a compliant Dispatch would have: log sha256 and capture hashes follow the files on disk."""
    if log:
        def f(rows):
            for r in rows:
                if r.get("sha256") and r.get("file") and os.path.exists(os.path.join(root, r["file"])):
                    r["sha256"] = sha_file(os.path.join(root, r["file"]))
            return rows
        jsonl_map(root, "log.jsonl", f)
    if captures and os.path.exists(os.path.join(root, "capture.jsonl")):
        def g(rows):
            for r in rows:
                p = os.path.join(root, r.get("file", ""))
                if r.get("file") and os.path.exists(p):
                    t = read(p)
                    r["byte_hash"] = sha_text(t)
                    r["char_count"] = len(t)
            return rows
        jsonl_map(root, "capture.jsonl", g)


def set_ledger_flags(root, flags):
    json_edit(root, "ledger.json", lambda d: d.__setitem__("flags", flags))
    json_edit(root, "status.json", lambda d: d.__setitem__("flags", flags))


def move_handshake_after_generate(root):
    def f(rows):
        hs = [r for r in rows if r.get("seat") == "REVIEWER" and r.get("action") == "handshake"]
        rest = [r for r in rows if r not in hs]
        idx = next(i for i, r in enumerate(rest) if r.get("stage") == "GENERATE" and r.get("action") == "send")
        return rest[:idx + 1] + hs + rest[idx + 1:]
    jsonl_map(root, "log.jsonl", f)


def drop_review_send(root):
    jsonl_map(root, "log.jsonl", lambda rows: [r for r in rows if not (r.get("seat") == "REVIEWER" and r.get("action") == "send")])


def rename_stage(root, old_dir, new_dir, old_name, new_name):
    """Rename a stage folder and every reference to it (stamps, dispatch, capture, log, kills-all), then re-sign."""
    os.rename(os.path.join(root, old_dir), os.path.join(root, new_dir))
    for dp, _, fs in os.walk(root):
        for fn in fs:
            p = os.path.join(dp, fn)
            s = read(p)
            s2 = s.replace(old_dir, new_dir).replace(old_name, new_name)
            if s2 != s:
                write(p, s2)
    resign(root)


def clone_stage(root, src_dir, dst_dir, src_num, dst_num, src_name, dst_name):
    shutil.copytree(os.path.join(root, src_dir), os.path.join(root, dst_dir))
    # a repeated operator would check NEW claims: renumber only the ids this stage defines, everywhere in the clone,
    # so the repetition itself is the only fault (earlier PASSED ids stay citable)
    own = re.findall(r"^CLAIM\s+C(\d+)\s", read(os.path.join(root, dst_dir, "check.md")), re.M)
    for fn in os.listdir(os.path.join(root, dst_dir)):
        p = os.path.join(root, dst_dir, fn)
        s = read(p).replace(f"STAGE {src_num} {src_name}", f"STAGE {dst_num} {dst_name}").replace(f"d-{src_num}-", f"d-{dst_num}-")
        for n in own:
            s = re.sub(rf"\bC{n}\b", f"C{int(n) + 100}", s)
        write(p, s)
    disp = [json.loads(l) for l in read(os.path.join(root, "dispatch.jsonl")).splitlines() if l.strip()]
    caps = [json.loads(l) for l in read(os.path.join(root, "capture.jsonl")).splitlines() if l.strip()]
    log = [json.loads(l) for l in read(os.path.join(root, "log.jsonl")).splitlines() if l.strip()]
    for d in [d for d in disp if d["stage_id"] == src_dir]:
        d2 = dict(d, stage_id=dst_dir, dispatch_id=d["dispatch_id"].replace(f"d-{src_num}-", f"d-{dst_num}-"))
        disp.append(d2)
    for c in [c for c in caps if c["file"].startswith(src_dir)]:
        caps.append(dict(c, file=c["file"].replace(src_dir, dst_dir), dispatch_id=c["dispatch_id"].replace(f"d-{src_num}-", f"d-{dst_num}-")))
    for r in [r for r in log if r.get("file", "").startswith(src_dir)]:
        log.append(dict(r, file=r["file"].replace(src_dir, dst_dir)))
    write(os.path.join(root, "dispatch.jsonl"), "".join(json.dumps(x) + "\n" for x in disp))
    write(os.path.join(root, "capture.jsonl"), "".join(json.dumps(x) + "\n" for x in caps))
    write(os.path.join(root, "log.jsonl"), "".join(json.dumps(x) + "\n" for x in log))
    resign(root)


def add_seat_file(root, stage_dir, stage_name, seat, did, body, stage_label):
    text = f"{stage_name} SEAT {seat} TIME 23:30\nDISPATCH {did}\n" + body
    rel = f"{stage_dir}/seat-{seat}.md"
    write(os.path.join(root, rel), text)
    with open(os.path.join(root, "dispatch.jsonl"), "a") as f:
        f.write(json.dumps({"run_id": "na-001", "stage_id": stage_dir, "seat_id": seat, "conversation_url": f"https://chat.example/{seat}",
                            "dispatch_id": did, "provider": "p", "tab_id": "t", "displayed_model": "m", "displayed_effort": "high",
                            "prompt_hash": "h", "expected_reply_slot": "1", "snapshot_hash": "s", "t": "23:29"}) + "\n")
    with open(os.path.join(root, "capture.jsonl"), "a") as f:
        f.write(json.dumps({"dispatch_id": did, "file": rel, "completion_signal_observed": True, "start_boundary": "b0", "end_boundary": "b1",
                            "char_count": len(text), "byte_hash": sha_text(text), "observed_identity": seat, "partial": False}) + "\n")
    with open(os.path.join(root, "log.jsonl"), "a") as f:
        f.write(json.dumps({"t": "2026-09-09T23:30:00", "seat": seat, "action": "send", "result": "OK", "file": rel, "stage": stage_label, "sha256": sha_text(text)}) + "\n")


def drop_seat(root, stage_dir, seat):
    rm(root, f"{stage_dir}/seat-{seat}.md")
    jsonl_map(root, "log.jsonl", lambda rows: [r for r in rows if r.get("file") != f"{stage_dir}/seat-{seat}.md"])


def deliverable_swap_sections(root):
    p = os.path.join(root, "final/DELIVERABLE.md")
    s = read(p)
    a = s.index("2 WHAT SURVIVED"); b_ = s.index("3 WHY IT SURVIVED"); c = s.index("4 OBJECTIVE RESULTS")
    s2 = s[:a] + s[b_:c] + s[a:b_] + s[c:]
    write(p, s2)
    asm = os.path.join(root, "final/DELIVERABLE_ASSEMBLED.md")
    write(asm, s2 + "\n" + read(os.path.join(root, "final/verifier.md")))


def set_contradiction(root, line):
    edit(root, "final/verifier.md", "CONTRADICTIONS\nnone\n", f"CONTRADICTIONS\n{line}\n")
    write(os.path.join(root, "final/DELIVERABLE_ASSEMBLED.md"), read(os.path.join(root, "final/DELIVERABLE.md")) + "\n" + read(os.path.join(root, "final/verifier.md")))


def remove_review(root):
    rm(root, "review")
    edit(root, "final/DELIVERABLE.md", "- H1 PASSED 750 rows per second at 40 columns. [R] {H1}\n", "")
    edit(root, "final/DELIVERABLE.md", "HIT 1 PASSED, FIXED: the throughput line now says 12 columns. GAP 1 JUDGEMENT CALL, OPEN. HOLD 1 HOLD-ACCEPTED. SURVIVING DEFECTS: none known.",
         "NO OUTSIDE REVIEW: the reviewer window was lost.")
    edit(root, "final/DELIVERABLE.md", "scoped to 12 columns by H1. ", "")
    edit(root, "final/DELIVERABLE.md", "Medium for option 1: throughput scoped by H1.", "Medium for option 1.")
    write(os.path.join(root, "final/DELIVERABLE_ASSEMBLED.md"), read(os.path.join(root, "final/DELIVERABLE.md")) + "\n" + read(os.path.join(root, "final/verifier.md")))
    jsonl_map(root, "log.jsonl", lambda rows: [r for r in rows if not (r.get("file") or "").startswith("review/")])


def clear_stop(root):
    json_edit(root, "status.json", lambda d: d.pop("stop_reason", None))


def strip_final(root):
    for f in ("final/DELIVERABLE.md", "final/DELIVERABLE_ASSEMBLED.md", "final/verifier.md"):
        rm(root, f)
    jsonl_map(root, "log.jsonl", lambda rows: [r for r in rows if r.get("file") not in ("final/DELIVERABLE.md", "final/DELIVERABLE_ASSEMBLED.md", "final/verifier.md")])


def strip_verify(root):
    for f in ("final/DELIVERABLE_ASSEMBLED.md", "final/verifier.md"):
        rm(root, f)
    jsonl_map(root, "log.jsonl", lambda rows: [r for r in rows if r.get("file") not in ("final/DELIVERABLE_ASSEMBLED.md", "final/verifier.md")])


def log_file(root, rel, seat="DISPATCH", action="write", stage="DELIVER"):
    with open(os.path.join(root, "log.jsonl"), "a") as f:
        f.write(json.dumps({"t": "2026-09-10T05:59:00", "seat": seat, "action": action, "result": "OK", "file": rel, "stage": stage,
                            "sha256": sha_file(os.path.join(root, rel))}) + "\n")


def R(fn):
    """Apply a mutation then re-sign log and captures (the fault is in what Dispatch wrote, not tampering after the write)."""
    def inner(root):
        fn(root)
        resign(root)
    return inner


# ----------------------------------------------------------------------------- run-folder faults
# Each: id, split, base, spec_ref, description, mutate(root)
FAULTS = [
    # ---- evidence rules, spec 3
    ("E01a", "DEV", "hybrid", "3", "METHOD none but RESULT PASSED (model agreement written as evidence)",
     R(lambda r: edit(r, "stage-01-generate/check.md", "  RETRIEVED  \n  RESULT     JUDGEMENT CALL", "  RETRIEVED  three seats agreed it is common\n  RESULT     PASSED"))),
    ("E01b", "HOLDOUT", "hybrid", "3", "METHOD none but RESULT FAILED",
     R(lambda r: edit(r, "stage-01-generate/check.md", "  RETRIEVED  \n  RESULT     JUDGEMENT CALL", "  RETRIEVED  two seats called it false\n  RESULT     FAILED"))),
    ("E02a", "DEV", "hybrid", "3", "source claim PASSED with evidence_grade B",
     R(lambda r: edit(r, "stage-01-generate/check.md", 'grade=A quote_present=yes support=SUPPORTED scope="library docs', 'grade=B quote_present=yes support=SUPPORTED scope="library docs'))),
    ("E02b", "HOLDOUT", "hybrid", "3", "document claim PASSED with evidence_grade C",
     R(lambda r: edit(r, "stage-01-generate/check.md", 'grade=A quote_present=yes support=SUPPORTED scope="brief.md section 4"', 'grade=C quote_present=yes support=SUPPORTED scope="brief.md section 4"'))),
    ("E03a", "DEV", "hybrid", "3", "source claim PASSED with no SOURCE line",
     R(lambda r: edit(r, "stage-01-generate/check.md", SRC("library docs, Dialects section"), ""))),
    ("E03b", "HOLDOUT", "hybrid", "3", "document claim PASSED, SOURCE line lacks support=",
     R(lambda r: edit(r, "stage-01-generate/check.md", 'support=SUPPORTED scope="brief.md section 4"', 'scope="brief.md section 4"'))),
    ("E04a", "DEV", "hybrid", "3", "claim id reused across stages with different text",
     R(lambda r: edit(r, "stage-03-idov/check.md", 'CLAIM C10', claim("C8", "G3", "A second claim wearing an old id", "sum", "x", "1 + 1 = 2", "PASSED") + 'CLAIM C10'))),
    ("E04b", "HOLDOUT", "hybrid", "3", "claim id duplicated inside one check file",
     R(lambda r: edit(r, "stage-01-generate/check.md", 'CLAIM C6', claim("C1", "G2", "Another claim with the C1 id", "sum", "x", "2 + 2 = 4", "PASSED") + 'CLAIM C6'))),
    ("E05a", "DEV", "hybrid", "3", "source PASSED with support=NOT_FOUND",
     R(lambda r: edit(r, "stage-01-generate/check.md", 'support=SUPPORTED scope="library docs', 'support=NOT_FOUND scope="library docs'))),
    ("E05b", "HOLDOUT", "hybrid", "3", "document PASSED with support=CONTRADICTED",
     R(lambda r: edit(r, "stage-01-generate/check.md", 'support=SUPPORTED scope="brief.md section 4"', 'support=CONTRADICTED scope="brief.md section 4"'))),
    ("E07a", "DEV", "hybrid", "3, 4.6", "[R] provenance in a stage MERGED before REVIEW ran",
     R(lambda r: edit(r, "stage-02-fmea/close.md", "KILLS\n", "- The brief also names the vendor. [R] {C3}\nKILLS\n"))),
    ("E07b", "HOLDOUT", "hybrid", "3, 4.6", "check-review claim tagged with a generator id instead of [R]",
     R(lambda r: edit(r, "review/check-review.md", 'CLAIM H1 [R]', 'CLAIM H1 [G1]'))),
    ("E08a", "DEV", "hybrid", "3", "stage MERGED cites a review-stage claim id before REVIEW",
     R(lambda r: edit(r, "stage-02-fmea/close.md", "[G1][G2] {C1,C2}", "[G1][G2] {C1,C2,H1}"))),
    ("E08b", "HOLDOUT", "hybrid", "3", "stage 02 MERGED cites a claim first checked in stage 03",
     R(lambda r: edit(r, "stage-02-fmea/close.md", "[G1][G2] {C1,C2}", "[G1][G2] {C1,C2,C9}"))),
    ("E09a", "DEV", "hybrid", "3", "MERGED line with empty claim-id braces",
     R(lambda r: edit(r, "stage-02-fmea/close.md", "[G3][G2] {C3,C8}", "[G3][G2] {}"))),
    ("E09b", "HOLDOUT", "hybrid", "3", "MERGED line with whitespace-only claim-id braces",
     R(lambda r: edit(r, "stage-02-fmea/close.md", "[G3][G2] {C3,C8}", "[G3][G2] { }"))),
    # ---- options and close, spec 4.1, 4.3
    ("O01a", "DEV", "hybrid", "4.1", "deliverable section 2 names an option never created in GENERATE",
     R(lambda r: edit(r, "final/DELIVERABLE.md", "Two options survive.", "- Option 4: stream and validate lazily. [G1] {C1}\nThree options survive."))),
    ("O01b", "HOLDOUT", "hybrid", "4.1", "review package OPTIONS STANDING lists an option never created",
     R(lambda r: edit(r, "review/package.md", "2. Two-pass import with a reject report.\n", "2. Two-pass import with a reject report.\n5. Validate in the database instead.\n"))),
    ("O02a", "DEV", "hybrid", "4.3", "KILLS entry names no FAILED claim and no constraint",
     R(lambda r: edit(r, "stage-03-idov/close.md", "KILLS\nnone\n", "KILLS\n- Option 2 killed: the seats found it weak\n"))),
    ("O02b", "HOLDOUT", "hybrid", "4.3", "KILLS entry cites a claim that is PASSED, not FAILED",
     R(lambda r: edit(r, "stage-03-idov/close.md", "KILLS\nnone\n", "KILLS\n- Option 2 killed by claim C3, EARNED\n"))),
    ("O03a", "DEV", "hybrid", "4.3", "MERGE close missing the DEPRIORITIZED section",
     R(lambda r: edit(r, "stage-02-fmea/close.md", "DEPRIORITIZED\n- Option 2: the seats found the second pass less persuasive on cost; it stays standing\n", ""))),
    ("O03b", "HOLDOUT", "hybrid", "4.3", "LIST close (after GENERATE) contains a MERGED section",
     R(lambda r: edit(r, "stage-01-generate/close.md", "KILLS\nnone\n", "MERGED\n- The importer is fast enough today. [G1] {C1}\nKILLS\nnone\n"))),
    ("O04a", "DEV", "hybrid", "4.4, 15 G-5", "the same operator ran twice in one night",
     lambda r: clone_stage(r, "stage-02-fmea", "stage-04-fmea", "02", "04", "FMEA", "FMEA")),
    ("O07b", "HOLDOUT", "hybrid", "6", "more operator stages than gate max_operators",
     R(lambda r: json_edit(r, "gate/gate.json", lambda d: d["budget"].__setitem__("max_operators", 1)))),
    ("O05a", "DEV", "hybrid", "4.4", "v10-fixed profile skipped IDOV (FMEA then TRIZ)",
     lambda r: (json_edit(r, "gate/gate.json", lambda d: d.__setitem__("profile", "v10-fixed")), rename_stage(r, "stage-03-idov", "stage-03-triz", "STAGE 03 IDOV", "STAGE 03 TRIZ"))),
    ("O05b", "HOLDOUT", "hybrid", "4.4", "v10-fixed profile ran IDOV before FMEA",
     lambda r: (json_edit(r, "gate/gate.json", lambda d: d.__setitem__("profile", "v10-fixed")),
                rename_stage(r, "stage-02-fmea", "stage-02-tmpx", "STAGE 02 FMEA", "STAGE 02 TMPX"),
                rename_stage(r, "stage-03-idov", "stage-03-fmea", "STAGE 03 IDOV", "STAGE 03 FMEA"),
                rename_stage(r, "stage-02-tmpx", "stage-02-idov", "STAGE 02 TMPX", "STAGE 02 IDOV"))),
    ("O06a", "DEV", "hybrid", "1, 5 DISPATCH", "gate CLASS is DIRECT but GENERATE and operator stages exist",
     R(lambda r: json_edit(r, "gate/gate.json", lambda d: d.__setitem__("class", "DIRECT")))),
    ("O06b", "HOLDOUT", "direct", "1, 4", "gate CLASS is DELIBERATION but the run has only a DIRECT stage",
     R(lambda r: json_edit(r, "gate/gate.json", lambda d: d.__setitem__("class", "DELIBERATION")))),
    # ---- seat files, crew, isolation, spec 7 and DISPATCH 3.1, 3.5
    ("S01a", "DEV", "hybrid", "DISPATCH 3.1", "GENERATE seat file missing the KNOCKDOWN heading",
     R(lambda r: edit(r, "stage-01-generate/seat-G1.md", "KNOCKDOWN\nA dies if schema validation doubles runtime.\n", ""))),
    ("S01b", "HOLDOUT", "hybrid", "DISPATCH 3.5", "OPERATE seat file missing the WRONG heading",
     R(lambda r: edit(r, "stage-02-fmea/seat-G1.md", "WRONG\nnone found; check C1 by rerunning bench.py (command)\n", ""))),
    ("S02a", "DEV", "hybrid", "7 stamp", "stamp names a different operator than the stage folder",
     R(lambda r: edit(r, "stage-02-fmea/seat-G2.md", "STAGE 02 FMEA", "STAGE 02 IDOV"))),
    ("S02b", "HOLDOUT", "hybrid", "2, 7", "stamp names a seat id that is not in the registry",
     R(lambda r: edit(r, "stage-03-idov/seat-G2.md", "SEAT G2", "SEAT G7"))),
    ("S03a", "DEV", "hybrid", "7", "a seat that is not READY in the registry has a reply file counted in a stage",
     R(lambda r: add_seat_file(r, "stage-02-fmea", "STAGE 02 FMEA", "G4", "d-02-G4", "WRONG\nnone\nMISSING\nnone\nKILLS\nnone\nOPEN\nnone\n", "OPERATE"))),
    ("S10b", "HOLDOUT", "hybrid", "DISPATCH 6", "a seat file exists with no log record of its write",
     R(lambda r: jsonl_map(r, "log.jsonl", lambda rows: [x for x in rows if x.get("file") != "stage-03-idov/seat-G2.md"]))),
    ("S04a", "DEV", "hybrid", "4.6", "review.md missing the HOLDS heading",
     R(lambda r: edit(r, "review/review.md", "HOLDS\n1. C3 and C8 hold: the brief wording is quoted and unambiguous.\n", ""))),
    ("S04b", "HOLDOUT", "hybrid", "4.8", "verifier.md missing the NOT COVERED heading",
     R(lambda r: (edit(r, "final/verifier.md", "NOT COVERED\nC1, C2, C9\n", ""), edit(r, "final/DELIVERABLE_ASSEMBLED.md", "NOT COVERED\nC1, C2, C9\n", "")))),
    ("S05a", "DEV", "hybrid", "7 reused conversations", "REVIEWER window is a reused conversation and no CONTAMINATION flag",
     R(lambda r: json_edit(r, "registry.json", lambda d: [s.__setitem__("fresh", False) for s in d["seats"] if s["id"] == "REVIEWER"]))),
    ("S05b", "HOLDOUT", "hybrid", "7 reused conversations", "a GENERATE seat is a reused conversation and no CONTAMINATION flag",
     R(lambda r: json_edit(r, "registry.json", lambda d: [s.__setitem__("fresh", False) for s in d["seats"] if s["id"] == "G2"]))),
    ("S06a", "DEV", "hybrid", "4.6, 7 handshake", "REVIEWER handshake logged after the first GENERATE send",
     R(move_handshake_after_generate)),
    ("S07a", "DEV", "hybrid", "7 reduced crew", "an OPERATE stage has fewer replies than READY generators and no REDUCED_CREW flag",
     R(lambda r: drop_seat(r, "stage-02-fmea", "G3"))),
    ("S07b", "HOLDOUT", "hybrid", "7 reduced crew", "GENERATE has fewer replies than READY generators and no REDUCED_CREW flag",
     R(lambda r: drop_seat(r, "stage-01-generate", "G3"))),
    ("S08a", "DEV", "hybrid", "2 minimum crew", "gate min_crew below the spec floor of 2 and a one-reply stage",
     R(lambda r: (json_edit(r, "gate/gate.json", lambda d: d.__setitem__("min_crew", 1)), drop_seat(r, "stage-02-fmea", "G2"), drop_seat(r, "stage-02-fmea", "G3"),
                  set_ledger_flags(r, ["REDUCED_CREW"])))),
    ("S08b", "HOLDOUT", "hybrid", "2 minimum crew", "gate min_crew below the spec floor of 2",
     R(lambda r: json_edit(r, "gate/gate.json", lambda d: d.__setitem__("min_crew", 1)))),
    ("S09a", "DEV", "hybrid", "7 capture records", "seat file bytes differ from the capture record byte_hash",
     lambda r: (edit(r, "stage-02-fmea/seat-G1.md", "OPEN\nwhat sample rate", "OPEN\nappended after capture\nwhat sample rate"), resign(r, captures=False))),
    ("S09b", "HOLDOUT", "hybrid", "7 capture records", "capture char_count does not match the saved reply",
     lambda r: (jsonl_map(r, "capture.jsonl", lambda rows: [dict(x, char_count=5) if x["dispatch_id"] == "d-03-G1" else x for x in rows]))),
    # ---- final and verify, spec 4.7, 4.8, I3
    ("F01a", "DEV", "hybrid", "4.8, I3", "verifier output pasted under section 14 of DELIVERABLE.md",
     R(lambda r: edit(r, "final/DELIVERABLE.md", "14 PRIVATE DOCUMENT VERIFICATION\n", "14 PRIVATE DOCUMENT VERIFICATION\nCONTRADICTIONS\nnone\nCONFIRMED\n1. C3 confirmed by brief.md\n"))),
    ("F01b", "HOLDOUT", "hybrid", "4.8, I3", "DELIVERABLE_ASSEMBLED.md lacks the verifier tail",
     R(lambda r: write(os.path.join(r, "final/DELIVERABLE_ASSEMBLED.md"), read(os.path.join(r, "final/DELIVERABLE.md"))))),
    ("F02a", "DEV", "hybrid", "4.8", "verifier CONTRADICTION recorded but no PROVISIONAL flag",
     R(lambda r: set_contradiction(r, "1. Section 1 says 12 columns; brief.md section 2 says the widest file has 40 columns (brief.md p.2)"))),
    ("F02b", "HOLDOUT", "hybrid", "4.8", "verifier CONTRADICTION (parenthesis numbering) but no PROVISIONAL flag",
     R(lambda r: set_contradiction(r, "1) The result names rejects.csv; the brief names errors.csv (brief.md section 4)"))),
    ("F03a", "DEV", "hybrid", "2, 10", "no review stage and no NO_OUTSIDE_REVIEW flag",
     R(remove_review)),
    ("F03b", "HOLDOUT", "hybrid", "2, 10", "no verifier file and no NO_VERIFIER flag",
     R(lambda r: (strip_verify(r), write(os.path.join(r, "final/DELIVERABLE_ASSEMBLED.md"), read(os.path.join(r, "final/DELIVERABLE.md"))),
                  log_file(r, "final/DELIVERABLE_ASSEMBLED.md")))),
    ("F04a", "DEV", "hybrid", "4.7, I10", "kills-all.md omits a KILLS line from a close",
     R(lambda r: edit(r, "final/kills-all.md", "- Option 3 killed by claim C7 FAILED (sampling cannot reject every malformed row), EARNED\n", ""))),
    ("F04b", "HOLDOUT", "hybrid", "4.7, I10", "kills-all.md missing although the final was written",
     R(lambda r: rm(r, "final/kills-all.md"))),
    ("F05a", "DEV", "hybrid", "4.7 P6 order", "deliverable sections out of order",
     R(deliverable_swap_sections)),
    ("F06a", "DEV", "hybrid", "17", "ledger classification is not one of the three",
     R(lambda r: json_edit(r, "ledger.json", lambda d: d.__setitem__("classification", "KEEP")))),
    ("F08b", "HOLDOUT", "hybrid", "10", "ledger carries a flag name the schema does not define",
     R(lambda r: set_ledger_flags(r, ["STRUCTURAL_GT_EARNED"]))),
    ("F07a", "DEV", "hybrid", "17", "ledger classification disagrees with the deliverable",
     R(lambda r: json_edit(r, "ledger.json", lambda d: d.__setitem__("classification", "REVERT")))),
    ("F07b", "HOLDOUT", "hybrid", "17", "deliverable classification disagrees with the ledger",
     R(lambda r: (edit(r, "final/DELIVERABLE.md", "classification KEEP_FOR_DEVELOPMENT", "classification PARTIAL_REPORT"),
                  edit(r, "final/DELIVERABLE_ASSEMBLED.md", "classification KEEP_FOR_DEVELOPMENT", "classification PARTIAL_REPORT")))),
    # ---- experiment engine, spec 5
    ("X01a", "DEV", "hybrid", "5 COMPARE", "KEEP with the delta in the wrong direction for a lower-is-better metric",
     R(lambda r: json_edit(r, "experiments/exp-001/record.json", lambda d: (d.__setitem__("delta", 4.0), d.__setitem__("result_value", 14.0))))),
    ("X01b", "HOLDOUT", "hybrid", "5 COMPARE", "KEEP whose repeat run is worse than baseline",
     R(lambda r: json_edit(r, "experiments/exp-001/record.json", lambda d: d.__setitem__("repeat_value", 10.4)))),
    ("X02a", "DEV", "hybrid", "5 EXECUTE", "KEEP on a run that exceeded the experiment budget",
     R(lambda r: json_edit(r, "experiments/exp-001/record.json", lambda d: d.__setitem__("within_budget", False)))),
    ("X04b", "HOLDOUT", "hybrid", "5 COMPARE", "KEEP with a guardrail beyond tolerance",
     R(lambda r: json_edit(r, "experiments/exp-001/record.json", lambda d: d["guardrails"][0].__setitem__("value", 1)))),
    ("X03a", "DEV", "hybrid", "5 LOG", "experiment record with no line in experiments/log.jsonl",
     R(lambda r: write(os.path.join(r, "experiments/log.jsonl"), ""))),
    ("X03b", "HOLDOUT", "hybrid", "5 LOG", "experiment log decision disagrees with record.json",
     R(lambda r: edit(r, "experiments/log.jsonl", '"decision": "KEEP"', '"decision": "REVERT"'))),
    # ---- DIRECT path, DISPATCH 5
    ("D01a", "DEV", "direct", "DISPATCH 5, P9", "DIRECT seat file missing the CLAIMS heading",
     R(lambda r: edit(r, "stage-01-direct/seat-G1.md", "CLAIMS\n1. The twelve figures sum to 41,880 (sum).\n2. figures.csv has twelve rows (document).\n", ""))),
    ("D02b", "HOLDOUT", "direct", "DISPATCH 5", "DIRECT stage has two generator replies",
     R(lambda r: add_seat_file(r, "stage-01-direct", "STAGE 01 DIRECT", "G2", "d-01-G2", "ANSWER\n41,880\nCLAIMS\n1. sum (sum).\nOPEN\nnone\n", "DIRECT"))),
    # ---- gate record, spec 1
    ("G01a", "DEV", "hybrid", "1", "gate CLASS is not one of the five classes",
     R(lambda r: json_edit(r, "gate/gate.json", lambda d: d.__setitem__("class", "MIXED")))),
    ("G01b", "HOLDOUT", "hybrid", "1, 4.4", "gate PROFILE is not adaptive or v10-fixed",
     R(lambda r: json_edit(r, "gate/gate.json", lambda d: d.__setitem__("profile", "fixed")))),
    ("G02a", "DEV", "hybrid", "1, 2", "experiments were executed with no READY EXECUTOR seat",
     R(lambda r: json_edit(r, "registry.json", lambda d: [s.__setitem__("ready", False) for s in d["seats"] if s["id"] == "EXECUTOR"]))),
    ("G02b", "HOLDOUT", "hybrid", "1", "gate CLASS EXPERIMENT with no EXECUTOR registered at all",
     R(lambda r: (json_edit(r, "gate/gate.json", lambda d: d.__setitem__("class", "EXPERIMENT")),
                  json_edit(r, "registry.json", lambda d: d.__setitem__("seats", [s for s in d["seats"] if s["id"] != "EXECUTOR"]))))),
]

# ----------------------------------------------------------------------------- guard cases (na_gate.py must BLOCK)
# Each: id, split, base, spec_ref, description, mutate(root), stage, args
GUARD_BLOCK = [
    ("GA01a", "DEV", "hybrid", "4.6, 15 G-11", "send to REVIEWER during an operator stage",
     lambda r: drop_review_send(r), "SEND", ["--seat", "REVIEWER", "--stage-dir", "stage-02-fmea"]),
    ("GA11b", "HOLDOUT", "hybrid", "7, 15 G-11", "send to a seat that is not READY",
     lambda r: None, "SEND", ["--seat", "G4", "--stage-dir", "stage-03-idov"]),
    ("GA02a", "DEV", "hybrid", "5, 15 G-9", "KEEP with delta in the wrong direction",
     lambda r: json_edit(r, "experiments/exp-001/record.json", lambda d: (d.__setitem__("delta", 4.0), d.__setitem__("result_value", 14.0))), "DECIDE", ["--record", "exp-001"]),
    ("GA02b", "HOLDOUT", "hybrid", "5, 15 G-9", "KEEP whose repeat run does not improve on baseline",
     lambda r: json_edit(r, "experiments/exp-001/record.json", lambda d: d.__setitem__("repeat_value", 10.4)), "DECIDE", ["--record", "exp-001"]),
    ("GA03a", "DEV", "hybrid", "5, 15 G-9", "KEEP on a run that exceeded the per-experiment budget",
     lambda r: json_edit(r, "experiments/exp-001/record.json", lambda d: d.__setitem__("within_budget", False)), "DECIDE", ["--record", "exp-001"]),
    ("GA12b", "HOLDOUT", "hybrid", "5, 15 G-9", "KEEP with a guardrail beyond tolerance",
     lambda r: json_edit(r, "experiments/exp-001/record.json", lambda d: d["guardrails"][0].__setitem__("value", 1)), "DECIDE", ["--record", "exp-001"]),
    ("GA04a", "DEV", "hybrid", "6, 15 G-5", "OPERATE when max_operators is already reached",
     lambda r: (clear_stop(r), json_edit(r, "gate/gate.json", lambda d: d["budget"].__setitem__("max_operators", 2))), "OPERATE", ["--op", "TRIZ"]),
    ("GA04b", "HOLDOUT", "hybrid", "4.4, 15 G-5", "OPERATE with an operator that is not in the library",
     lambda r: clear_stop(r), "OPERATE", ["--op", "FOO"]),
    ("GA05a", "DEV", "hybrid", "1, 15 G-2", "GENERATE when the gate class is DIRECT",
     lambda r: json_edit(r, "gate/gate.json", lambda d: d.__setitem__("class", "DIRECT")), "GENERATE", []),
    ("GA05b", "HOLDOUT", "direct", "1, 15 G-2", "DIRECT when the gate class is DELIBERATION",
     lambda r: json_edit(r, "gate/gate.json", lambda d: d.__setitem__("class", "DELIBERATION")), "DIRECT", []),
    ("GA06a", "DEV", "hybrid", "7, 15 G-3", "CHECK counting seat files whose stamp stage number mismatches the folder",
     lambda r: (edit(r, "stage-02-fmea/seat-G2.md", "STAGE 02 FMEA", "STAGE 03 FMEA"), edit(r, "stage-02-fmea/seat-G3.md", "STAGE 02 FMEA", "STAGE 03 FMEA"), resign(r)),
     "CHECK", ["--stage-dir", "stage-02-fmea"]),
    ("GA06b", "HOLDOUT", "hybrid", "2, 15 G-3", "CHECK counting seat files stamped with seat ids not in the registry",
     lambda r: (edit(r, "stage-02-fmea/seat-G2.md", "SEAT G2", "SEAT G8"), edit(r, "stage-02-fmea/seat-G3.md", "SEAT G3", "SEAT G9"), resign(r)),
     "CHECK", ["--stage-dir", "stage-02-fmea"]),
    ("GA07a", "DEV", "hybrid", "3, 15 G-4", "CLOSE with a PASSED source claim whose SOURCE says support=PARTIAL",
     lambda r: edit(r, "stage-01-generate/check.md", 'support=SUPPORTED scope="library docs', 'support=PARTIAL scope="library docs'), "CLOSE", ["--stage-dir", "stage-01-generate"]),
    ("GA07b", "HOLDOUT", "hybrid", "3, 15 G-4", "CLOSE with a METHOD none claim marked PASSED",
     lambda r: edit(r, "stage-01-generate/check.md", "  RETRIEVED  \n  RESULT     JUDGEMENT CALL", "  RETRIEVED  three seats agreed\n  RESULT     PASSED"), "CLOSE", ["--stage-dir", "stage-01-generate"]),
    ("GA08a", "DEV", "hybrid", "4.6, 15 G-6", "REVIEW when the reviewer handshake came after GENERATE began",
     lambda r: (drop_review_send(r), move_handshake_after_generate(r)), "REVIEW", []),
    ("GA13b", "HOLDOUT", "hybrid", "7, 15 G-6", "REVIEW when the REVIEWER seat is not READY",
     lambda r: (drop_review_send(r), json_edit(r, "registry.json", lambda d: [s.__setitem__("ready", False) for s in d["seats"] if s["id"] == "REVIEWER"])), "REVIEW", []),
    ("GA09a", "DEV", "hybrid", "4.7, 15 G-7", "FINAL when kills-all.md omits a KILLS line from a close",
     lambda r: (strip_final(r), edit(r, "final/kills-all.md", "- Option 3 killed by claim C7 FAILED (sampling cannot reject every malformed row), EARNED\n", "")), "FINAL", []),
    ("GA14b", "HOLDOUT", "hybrid", "4.7, 15 G-7", "FINAL when metrics-summary.json is not valid JSON",
     lambda r: (strip_final(r), write(os.path.join(r, "final/metrics-summary.json"), "{not json")), "FINAL", []),
    ("GA10a", "DEV", "hybrid", "4.8, 15 G-8", "VERIFY when no VERIFIER seat is READY",
     lambda r: (strip_verify(r), json_edit(r, "registry.json", lambda d: [s.__setitem__("ready", False) for s in d["seats"] if s["id"] == "VERIFIER"])), "VERIFY", []),
    ("GA15b", "HOLDOUT", "hybrid", "4.8, I3, 15 G-8", "VERIFY when section 14 of DELIVERABLE.md already has content",
     lambda r: (strip_verify(r), edit(r, "final/DELIVERABLE.md", "14 PRIVATE DOCUMENT VERIFICATION\n", "14 PRIVATE DOCUMENT VERIFICATION\nCONTRADICTIONS\nnone\n")), "VERIFY", []),
]

# ----------------------------------------------------------------------------- guard cases that must ALLOW (false-block guardrail)
GUARD_ALLOW = [
    ("AL01", "hybrid", lambda r: None, "GATE", []),
    ("AL02", "hybrid", lambda r: None, "GENERATE", []),
    ("AL03", "hybrid", lambda r: None, "CHECK", ["--stage-dir", "stage-01-generate"]),
    ("AL04", "hybrid", lambda r: None, "CHECK", ["--stage-dir", "stage-02-fmea"]),
    ("AL05", "hybrid", lambda r: None, "CLOSE", ["--stage-dir", "stage-01-generate"]),
    ("AL06", "hybrid", lambda r: None, "CLOSE", ["--stage-dir", "stage-02-fmea"]),
    ("AL07", "hybrid", lambda r: None, "CLOSE", ["--stage-dir", "stage-03-idov"]),
    ("AL08", "hybrid", clear_stop, "OPERATE", ["--op", "TRIZ"]),
    ("AL09", "hybrid", drop_review_send, "REVIEW", []),
    ("AL10", "hybrid", strip_final, "FINAL", []),
    ("AL11", "hybrid", strip_verify, "VERIFY", []),
    ("AL12", "hybrid", lambda r: None, "DECIDE", ["--record", "exp-001"]),
    ("AL13", "hybrid", lambda r: None, "SEND", ["--seat", "G1", "--stage-dir", "stage-03-idov"]),
    ("AL14", "direct", lambda r: None, "GATE", []),
    ("AL15", "direct", lambda r: None, "DIRECT", []),
    ("AL16", "direct", lambda r: None, "CHECK", ["--stage-dir", "stage-01-direct"]),
    ("AL17", "direct", strip_final, "FINAL", []),
    ("AL18", "direct", strip_verify, "VERIFY", []),
]


# ----------------------------------------------------------------------------- package assertions (secondary metric, frozen)
def _spec_body_without_history(spec):
    """Spec text minus the change logs, the I1..I11 resolution table (section 12) and the pilot record (section 19)."""
    out = []
    skip = False
    for line in spec.splitlines():
        if line.startswith("## 12.") or line.startswith("## 19."):
            skip = True
        elif line.startswith("## "):
            skip = False
        if skip or line.startswith("Change log") or "formerly" in line:
            continue
        out.append(line)
    return "\n".join(out)


def _section(text, start_pat, end_pat=r"^## "):
    m = re.search(start_pat, text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    e = re.search(end_pat, rest, re.M)
    return rest[:e.start()] if e else rest


def _underscore_tokens(t):
    return set(re.findall(r"\b[A-Z]+(?:_[A-Z]+)+\b", t))


def _flag_tokens(t, known):
    """Flag names in a text: every ALLCAPS token with an underscore, plus any known flag name (some flags have no underscore)."""
    return _underscore_tokens(t) | {k for k in known if re.search(rf"\b{re.escape(k)}\b", t)}


def pa_no_structural(p):
    spec = _spec_body_without_history(read(os.path.join(p, "NIGHT_AGENT_SPEC.md")))
    bad = "STRUCTURAL" in spec
    bad |= "structural_kills" in read(os.path.join(p, "SCHEMA.json"))
    bad |= "structural" in read(os.path.join(p, "PROMPTS", "P4_close.md")).lower()
    bad |= "STRUCTURAL" in read(os.path.join(p, "MORNING_DELIVERABLE_TEMPLATE.md")) or "structural" in read(os.path.join(p, "MORNING_DELIVERABLE_TEMPLATE.md"))
    return not bad


def pa_schema_direct_state(p):
    s = json.load(open(os.path.join(p, "SCHEMA.json")))
    return "DIRECT" in s["states"] and "DIRECT" in s["transitions"].get("GATE", []) and "DIRECT" in s["transitions"]


def pa_spec_g11_row(p):
    return re.search(r"^\| G-11 \|", read(os.path.join(p, "NIGHT_AGENT_SPEC.md")), re.M) is not None


def pa_flags_spec_eq_schema(p):
    s = json.load(open(os.path.join(p, "SCHEMA.json")))
    sec = _section(read(os.path.join(p, "NIGHT_AGENT_SPEC.md")), r"^## 10\. ")
    toks = _flag_tokens(sec, s["flags"]) - {"STRUCTURAL_GT_EARNED"}
    return set(s["flags"]) <= toks and toks <= set(s["flags"])


def pa_flags_template_eq_schema(p):
    s = json.load(open(os.path.join(p, "SCHEMA.json")))
    t = read(os.path.join(p, "MORNING_DELIVERABLE_TEMPLATE.md"))
    toks = _flag_tokens(_section(t, r"^10 RUN INTEGRITY", r"^\d+ [A-Z]"), s["flags"])
    return set(s["flags"]) <= toks and toks <= set(s["flags"])


def pa_options_standing_in_merge_close(p):
    p4 = read(os.path.join(p, "PROMPTS", "P4_close.md"))
    merge = p4.split("If MODE is MERGE", 1)[1] if "If MODE is MERGE" in p4 else ""
    ok = re.search(r"^OPTIONS STANDING\s+-", merge, re.M) is not None
    spec = _section(read(os.path.join(p, "NIGHT_AGENT_SPEC.md")), r"^### 4\.3 ", r"^### ")
    ok &= "OPTIONS STANDING" in spec
    disp = read(os.path.join(p, "DISPATCH.md"))
    ok &= re.search(r"headings MERGED, KILLS, DEPRIORITIZED, OPEN, CONFLICT, OPTIONS STANDING, METRICS", disp) is not None
    return ok


def pa_tool_versions_match_schema(p):
    v = json.load(open(os.path.join(p, "SCHEMA.json")))["schema_version"]
    tag = "v" + ".".join(v.split(".")[:2])
    return all(tag in read(os.path.join(p, "TESTS", f)).splitlines()[1] for f in ("na_gate.py", "na_check.py"))


def pa_guard_rows_consistent(p):
    s = json.load(open(os.path.join(p, "SCHEMA.json")))
    spec = read(os.path.join(p, "NIGHT_AGENT_SPEC.md"))
    code = read(os.path.join(p, "TESTS", "na_gate.py")) + read(os.path.join(p, "TESTS", "na_check.py"))
    for g in s["transition_guards"]:
        if not g.startswith("G-"):
            continue
        if re.search(rf"^\| {re.escape(g)} \|", spec, re.M) is None or g not in code:
            return False
    return True


def pa_doc_counts_match_suite(p):
    import importlib.util
    spec_ = importlib.util.spec_from_file_location("mf", os.path.join(p, "TESTS", "make_fixture.py"))
    mod = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(mod)
    nf, ng = len(mod.FAULTS), len(mod.GUARD_TESTS)
    docs = "".join(read(os.path.join(p, f)) for f in ("QA_REPORT.md", "VALIDATION_STATUS.md", "TESTS/ADVERSARIAL_TESTS.md"))
    wrong = re.findall(r"(\d+) of (\d+) (?:injected faults|injected run-folder faults|guard|allow-or-block)", docs)
    for a, b in wrong:
        if a != b or int(a) not in (nf, ng):
            return False
    return f"{nf} of {nf}" in docs and f"{ng} of {ng}" in docs


def pa_versions_agree(p):
    v = json.load(open(os.path.join(p, "SCHEMA.json")))["schema_version"]
    spec = read(os.path.join(p, "NIGHT_AGENT_SPEC.md"))
    m = re.search(r"^Version: (\d+\.\d+\.\d+)", spec, re.M)
    readme = read(os.path.join(p, "README.md")).splitlines()[0]
    disp = read(os.path.join(p, "DISPATCH.md")).splitlines()[0]
    return bool(m) and m.group(1) == v and v in readme and v in disp


def pa_close_sections_named_everywhere(p):
    need = ["MERGED", "KILLS", "DEPRIORITIZED", "OPEN", "CONFLICT", "METRICS"]
    p4 = read(os.path.join(p, "PROMPTS", "P4_close.md")).split("If MODE is MERGE", 1)[-1]
    disp = read(os.path.join(p, "DISPATCH.md"))
    spec = _section(read(os.path.join(p, "NIGHT_AGENT_SPEC.md")), r"^### 4\.3 ", r"^### ")
    return all(re.search(rf"^{h}\s+-", p4, re.M) for h in need) and all(h in disp for h in need) and all(h in spec for h in need)


def pa_g9_names_direction(p):
    s = json.load(open(os.path.join(p, "SCHEMA.json")))
    row = _section(read(os.path.join(p, "NIGHT_AGENT_SPEC.md")), r"^\| G-9 \|", r"^\|")
    return "direction" in s["transition_guards"]["G-9"] and "direction" in row


def pa_g3_names_direct(p):
    s = json.load(open(os.path.join(p, "SCHEMA.json")))
    row = _section(read(os.path.join(p, "NIGHT_AGENT_SPEC.md")), r"^\| G-3 \|", r"^\|")
    return "DIRECT" in s["transition_guards"]["G-3"] and "DIRECT" in row


def pa_dispatch_no_duplicate_sentence(p):
    return read(os.path.join(p, "DISPATCH.md")).count("Write `final/kills-all.md`") == 1


def pa_fixture_docstring_current(p):
    return "eleven" not in read(os.path.join(p, "TESTS", "make_fixture.py")).split('"""')[1]


PACKAGE_ASSERTIONS = [
    ("PA01", "4.3, 8, 10", "no STRUCTURAL kill vocabulary outside the history sections (spec 8, SCHEMA, P4, template)", pa_no_structural),
    ("PA02", "1, DISPATCH 5", "SCHEMA states and GATE transitions include DIRECT", pa_schema_direct_state),
    ("PA03", "15, 19", "spec section 15 has a G-11 row", pa_spec_g11_row),
    ("PA04", "10", "flag list in spec section 10 equals SCHEMA flags", pa_flags_spec_eq_schema),
    ("PA05", "10", "flag list in the morning template equals SCHEMA flags", pa_flags_template_eq_schema),
    ("PA06", "4.3, DISPATCH 3.5", "OPTIONS STANDING is an output section of the MERGE close in P4, spec 4.3 and DISPATCH 3.5", pa_options_standing_in_merge_close),
    ("PA07", "14", "na_gate.py and na_check.py docstrings carry the SCHEMA version", pa_tool_versions_match_schema),
    ("PA08", "15", "every SCHEMA guard has a spec section 15 row and appears in the guard or checker code", pa_guard_rows_consistent),
    ("PA09", "17", "QA_REPORT, VALIDATION_STATUS and ADVERSARIAL_TESTS counts equal the fixture suite sizes", pa_doc_counts_match_suite),
    ("PA10", "14", "spec, SCHEMA, README and DISPATCH state the same version", pa_versions_agree),
    ("PA11", "4.3", "the six MERGE close sections are named in P4, DISPATCH and spec 4.3", pa_close_sections_named_everywhere),
    ("PA12", "5, 15", "G-9 names the metric direction in SCHEMA and spec", pa_g9_names_direction),
    ("PA13", "DISPATCH 5, 15", "G-3 names the DIRECT one-seat exception in SCHEMA and spec", pa_g3_names_direct),
    ("PA14", "DISPATCH 3.7", "DISPATCH 3.7 does not repeat the kills-all sentence", pa_dispatch_no_duplicate_sentence),
    ("PA15", "TESTS", "make_fixture.py docstring no longer says eleven variants", pa_fixture_docstring_current),
]


def build_base(out_root, name):
    rel, fn = BASES[name]
    root = os.path.join(out_root, rel)
    if os.path.exists(root):
        shutil.rmtree(root)
    fn(root)
    return root


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/na_holdout"
    for n in BASES:
        print(build_base(out, n))
    print(f"{len(FAULTS)} run faults, {len(GUARD_BLOCK)} guard block cases, {len(GUARD_ALLOW)} allow cases, {len(PACKAGE_ASSERTIONS)} package assertions")
