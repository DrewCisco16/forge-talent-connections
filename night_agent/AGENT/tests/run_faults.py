#!/usr/bin/env python3
"""Layer B faults the fake seats can inject (TESTS/ADVERSARIAL_TESTS.md), each run as a whole night and checked
against na_check.py plus the flag or log line the spec expects. Exit 0 only if every case behaves.

    python3 AGENT/tests/run_faults.py <out_dir>
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from AGENT.tests import helpers  # noqa: E402

CASES = [
    # id, extra args, ask, expectations(run_dir) -> list of problems
    ("B1_timeout_generator", ["--fault", "B1:G2:GENERATE"], "ask_hybrid.md",
     lambda run, st, log, led: ([] if "REDUCED_CREW" in led["flags"] else ["REDUCED_CREW missing"])
     + ([] if any(l["action"] == "seat-failed" and l["seat"] == "G2" for l in log) else ["G2 not marked FAILED"])
     + ([] if any(c.get("aborted") for c in helpers.jsonl(os.path.join(run, "capture.jsonl"))) else ["no aborted capture"])
     + ([] if os.path.exists(os.path.join(run, "stage-02-fmea", "seat-G2.md")) else ["G2 did not return in the next stage"])),
    ("B2_missing_heading", ["--fault", "B2:G3:GENERATE"], "ask_hybrid.md",
     lambda run, st, log, led: ([] if os.path.exists(os.path.join(run, "stage-01-generate", "rejected-G3-1.md")) else ["no rejected file"])
     + ([] if os.path.exists(os.path.join(run, "stage-01-generate", "seat-G3.md")) else ["retry did not succeed"])
     + ([] if "REDUCED_CREW" not in led["flags"] else ["crew wrongly reduced"])),
    ("B4_wrong_sum_default", [], "ask_hybrid.md",
     lambda run, st, log, led: [] if "RESULT     FAILED" in open(os.path.join(run, "stage-01-generate", "check.md")).read() else ["wrong sum not FAILED"]),
    ("B7_review_all_judgement", ["--fault", "B7"], "ask_hybrid.md",
     lambda run, st, log, led: [] if "REVIEW_UNCHECKABLE" in led["flags"] else ["REVIEW_UNCHECKABLE missing"]),
    ("B8_untagged_merged_line", ["--fault", "B8:CLOSER:CLOSE"], "ask_hybrid.md",
     lambda run, st, log, led: ([] if any(f.startswith("rejected-CLOSER") for f in os.listdir(os.path.join(run, "stage-02-fmea"))) else ["closer reply not rejected"])
     + ([] if any(l["action"] == "retry" and l["seat"] == "CLOSER" for l in log) else ["no closer re-prompt logged"])),
    ("B11_two_survive_default", [], "ask_hybrid.md",
     lambda run, st, log, led: [] if led["options_standing"] >= 2 and "options survive" in open(os.path.join(run, "final", "DELIVERABLE.md")).read() else ["section 2 does not say several survive"]),
    ("B12_verifier_contradiction", ["--fault", "B12"], "ask_hybrid.md",
     lambda run, st, log, led: ([] if "PROVISIONAL" in led["flags"] else ["PROVISIONAL missing"])
     + ([] if "CONTRADICTIONS\n1." in open(os.path.join(run, "final", "verifier.md")).read() else ["contradiction not saved"])
     + ([] if led["classification"] == json.load(open(os.path.join(run, "ledger.json")))["classification"] else ["ledger disagrees"])),
    ("B13_gate_invents_metric", ["--fault", "B13"], "ask_hybrid.md",
     lambda run, st, log, led: ([] if json.load(open(os.path.join(run, "gate", "gate.json")))["class"] != "EXPERIMENT" else ["EXPERIMENT accepted without a procedure"])
     + ([] if "GATE_DEFAULTED" in led["flags"] else ["GATE_DEFAULTED missing"])),
    ("B19_padding", ["--fault", "B19:G1:GENERATE"], "ask_hybrid.md",
     lambda run, st, log, led: [] if open(os.path.join(run, "stage-01-generate", "check.md")).read().count("JUDGEMENT CALL") >= 20 and led["earned_kills"] >= 2 else ["padding changed the decisions or was not filed as judgement"]),
]


def main(out):
    if os.path.exists(out):
        shutil.rmtree(out)
    bad = 0
    for cid, extra, ask, expect in CASES:
        root = os.path.join(out, cid)
        r = helpers.run_night(root, ask=ask, extra=extra)
        run = os.path.join(root, "runs", "na-001")
        problems = []
        if r.returncode != 0:
            problems.append(f"exit {r.returncode}: {(r.stderr or r.stdout)[-300:]}")
        rc, fails = helpers.na_check(run) if os.path.isdir(run) else (1, ["no run folder"])
        if rc != 0:
            problems += fails[:3]
        if os.path.exists(os.path.join(run, "ledger.json")):
            st = json.load(open(os.path.join(run, "status.json")))
            log = helpers.jsonl(os.path.join(run, "log.jsonl"))
            led = json.load(open(os.path.join(run, "ledger.json")))
            problems += expect(run, st, log, led)
        elif not problems:
            problems.append("no ledger.json")
        bad += bool(problems)
        print(f"{'OK   ' if not problems else 'WRONG'} {cid}: {problems if problems else 'na_check 0 FAIL, expectation met'}")
    print(f"\n{len(CASES) - bad} of {len(CASES)} fault cases behaved")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/na_faults"))
