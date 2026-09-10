#!/usr/bin/env python3
"""Builds a conforming synthetic run folder (fixture) and eleven fault-injected
variants, runs na_check.py on each, and reports whether the injected fault was
caught. This proves the CHECKER, not the night. Nothing here talks to a model.

Usage: python3 make_fixture.py <out_dir>
"""
import os, sys, json, hashlib, shutil, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "na_check.py")


def w(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return hashlib.sha256(text.encode()).hexdigest()


def conforming(root):
    log = []
    def L(seat, action, file=None, stage=None, sha=None):
        d = {"t": "2026-09-09T22:00", "seat": seat, "action": action, "result": "OK"}
        if file: d["file"] = file
        if stage: d["stage"] = stage
        if sha: d["sha256"] = sha
        log.append(d)

    w(root, "ask.md", "Should the closer seat be Fable or Astra?\n")
    w(root, "registry.json", json.dumps({"seats": [{"id": s, "ready": True} for s in ["G1", "G2", "G3", "G4", "CLOSER", "REVIEWER", "VERIFIER"]]}))
    for s in ["G1", "G2", "G3", "G4", "CLOSER", "REVIEWER", "VERIFIER"]:
        L(s, "handshake", stage="REGISTRY")
    w(root, "gate/gate.md", "CLASS - DELIBERATION\n")
    w(root, "gate/gate.json", json.dumps({"class": "DELIBERATION", "kind": "answer", "min_crew": 2, "profile": "adaptive"}))

    dispatch, capture = [], []
    def D(stage, seat, did, url=None):
        dispatch.append({"run_id": "na-fixture", "stage_id": stage, "seat_id": seat, "provider": "p", "conversation_url": url or f"https://chat.example/{seat}", "tab_id": "t", "displayed_model": "m", "displayed_effort": "high", "prompt_hash": "h", "dispatch_id": did, "expected_reply_slot": "1", "snapshot_hash": "s", "t": "22:00"})
        capture.append({"dispatch_id": did, "file": f"{stage}/seat-{seat}.md", "completion_signal_observed": True, "start_boundary": "b0", "end_boundary": "b1", "char_count": 100, "byte_hash": "x", "observed_identity": seat, "partial": False})
    seats = {
        "G1": "STAGE 01 GENERATE SEAT G1 TIME 22:10\nDISPATCH d-01-G1\nCANDIDATES\nA. Keep the closer on Fable because merging rewards fidelity.\nCLAIMS\n1. Fable closer used six messages in v10 (sum).\nKNOCKDOWN\nA dies if the closer benchmark shows invention.\nMISSING\nA benchmark for closer fidelity.\n",
        "G2": "STAGE 01 GENERATE SEAT G2 TIME 22:11\nDISPATCH d-01-G2\nCANDIDATES\nA. Move Astra to closer since vendor claims stronger reasoning.\nCLAIMS\n2. Astra scores 98 percent on FrontierMath T4 per vendor page (source).\nKNOCKDOWN\nA dies if reasoning benchmarks do not predict merge fidelity.\nMISSING\nIndependent benchmark.\n",
        "G3": "STAGE 01 GENERATE SEAT G3 TIME 22:12\nDISPATCH d-01-G3\nCANDIDATES\nA. Use Astra as the isolated reviewer and keep Fable closing.\nCLAIMS\n3. The reviewer must not have sat in a round (document).\nKNOCKDOWN\nA dies if Astra is unavailable in chat.\nMISSING\nPlan visibility.\n",
    }
    for s, t in seats.items():
        D("stage-01-generate", s, f"d-01-{s}")
        sha = w(root, f"stage-01-generate/seat-{s}.md", t)
        L(s, "send", file=f"stage-01-generate/seat-{s}.md", stage="GENERATE", sha=sha)
    check1 = ('CLAIM 1 [G1] "Fable closer used six messages in v10"\n  METHOD     sum\n  ACTION     counted five merges plus one final in v10 page 12\n  RETRIEVED  5 + 1 = 6\n  RESULT     PASSED\n  SETTLE     \n'
              'CLAIM 2 [G2] "Astra scores 98 percent on FrontierMath T4 per vendor page"\n  METHOD     source\n  ACTION     opened openai.com/index/gpt-6-astra\n  RETRIEVED  page states 98 percent on FrontierMath Tier 4, vendor claim\n  RESULT     PASSED\n  SETTLE     \n  SOURCE     provenance=institutional grade=A quote_present=yes support=SUPPORTED scope="vendor page states the figure" retrieved=2026-09-09 retraction=unchecked age=ok\n'
              'CLAIM 3 [G3] "The reviewer must not have sat in a round"\n  METHOD     document\n  ACTION     read NIGHT_AGENT_SPEC.md 4.6\n  RETRIEVED  "Runs once ... in the REVIEWER window registered before GENERATE"\n  RESULT     PASSED\n  SETTLE     \n  SOURCE     provenance=standards or official technical documentation grade=A quote_present=yes support=SUPPORTED scope="spec 4.6" retrieved=2026-09-09 retraction=unchecked age=ok\n'
              'CLAIM 4 [G2] "Reasoning benchmarks predict merge fidelity"\n  METHOD     none\n  ACTION     no method available\n  RETRIEVED  \n  RESULT     JUDGEMENT CALL\n  SETTLE     a closer-fidelity benchmark with invented-claim counts\n')
    sha = w(root, "stage-01-generate/check.md", check1); L("DISPATCH", "write", file="stage-01-generate/check.md", stage="CHECK", sha=sha)
    close1 = ("OPTIONS\n1. Fable closes, Astra reviews. [1][3]\n2. Astra closes, Fable reviews. [2]\nKILLS\nnone\nOPEN\n- Claim 4 judgement call: settle with a fidelity benchmark\nMETRICS\noptions_created=2 options_standing=2 claims_total=4 claims_checkable=3 passed=3 failed=0 judgement=1 not_testable=0 blocked=0 inconclusive=0 earned_kills=0 structural_kills=0\n")
    sha = w(root, "stage-01-generate/close.md", close1); L("CLOSER", "send", file="stage-01-generate/close.md", stage="CLOSE", sha=sha)

    for s in ["G1", "G2", "G3"]:
        D("stage-02-fmea", s, f"d-02-{s}")
        t = f"STAGE 02 FMEA SEAT {s} TIME 23:0{s[-1]}\nDISPATCH d-02-{s}\nWRONG\nnone\nMISSING\nfailure visibility of option 2\nKILLS\nOption 2: reviewer would then be Fable which closed nothing; judgement call\nOPEN\nnone\n"
        sha = w(root, f"stage-02-fmea/seat-{s}.md", t); L(s, "send", file=f"stage-02-fmea/seat-{s}.md", stage="OPERATE", sha=sha)
    check2 = 'CLAIM 5 [G1] "Option 2 leaves no seat outside the rounds"\n  METHOD     document\n  ACTION     read SCHEMA.json registry isolated_after_handshake\n  RETRIEVED  REVIEWER isolated_after_handshake true; option 2 assigns Astra to closer\n  RESULT     PASSED\n  SETTLE     \n  SOURCE     provenance=standards or official technical documentation grade=A quote_present=yes support=SUPPORTED scope="registry field" retrieved=2026-09-09 retraction=unchecked age=ok\n'
    sha = w(root, "stage-02-fmea/check.md", check2); L("DISPATCH", "write", file="stage-02-fmea/check.md", stage="CHECK", sha=sha)
    close2 = ("MERGED\n- Fable closes and Astra reviews; the reviewer stays outside the rounds. [G1][G3] {C1,C3,C5}\nKILLS\n- Option 2 killed by hard constraint (the reviewer must sit outside the rounds), established by claim 5, EARNED\nDEPRIORITIZED\nnone\nOPEN\n- Claim 4 judgement call: settle with a fidelity benchmark\nCONFLICT\nnone\nOPTIONS STANDING\n1. Fable closes, Astra reviews.\nMETRICS\noptions_created=0 options_standing=1 claims_total=1 claims_checkable=1 passed=1 failed=0 judgement=0 not_testable=0 blocked=0 inconclusive=0 earned_kills=1 structural_kills=0 decision_changed=yes\n")
    sha = w(root, "stage-02-fmea/close.md", close2); L("CLOSER", "send", file="stage-02-fmea/close.md", stage="CLOSE", sha=sha)

    pkg = "MERGED\n- The closer stays on the fidelity seat and the reviewer stays outside the rounds. [1][3][5]\nCLAIMS\nCLAIM 1 PASSED ... CLAIM 5 PASSED\nOPTIONS STANDING\n1. closer on the fidelity seat, reviewer outside\nOPEN\n- Claim 4 judgement call\nCONFLICT\nnone\n"
    sha = w(root, "review/package.md", pkg); L("DISPATCH", "write", file="review/package.md", stage="REVIEW", sha=sha)
    L("REVIEWER", "send", file="review/review.md", stage="REVIEW")
    w(root, "review/review.md", "HITS\n1. Claim 1 arithmetic: five merges plus one final is six, but a reserve of one is budget not usage. Check: read spec 2.\nGAPS\n1. Cost of the reviewer seat not stated. Settle: count messages.\nHOLDS\n1. Claim 5 holds: isolation requires an outside seat.\nOPEN\nnone\n")
    L("DISPATCH", "write", file="review/check-review.md", stage="CHECK_REVIEW")
    w(root, "review/check-review.md", 'CLAIM H1 [R] "Reserve is budget, not usage"\n  METHOD     document\n  ACTION     read spec section 2 and DISPATCH 1.5\n  RETRIEVED  "Reserve two closer messages beyond the plan"\n  RESULT     PASSED\n  SETTLE     \n  SOURCE     provenance=standards or official technical documentation grade=A quote_present=yes support=SUPPORTED scope="DISPATCH 1.5" retrieved=2026-09-09 retraction=unchecked age=ok\nCLAIM G1 [R] "Reviewer message cost not stated"\n  METHOD     sum\n  ACTION     counted reviewer sends in the plan\n  RETRIEVED  1 send, plus 1 possible re-prompt\n  RESULT     PASSED\n  SETTLE     \n')
    deliv = "\n".join([
        "1 THE RESULT", "Keep Fable as closer; use Astra as the isolated reviewer.",
        "2 WHAT SURVIVED", "- Option 1: Fable closes, Astra reviews. [G1][G3] {C1,C3,C5}",
        "3 WHY IT SURVIVED", "- Claim 1 PASSED [G1] {C1}", "- Claim 3 PASSED [G3] {C3}", "- Claim 5 PASSED [G1] {C5}", "- H1 accepted [R] {CH1}",
        "4 OBJECTIVE RESULTS", "not applicable",
        "5 WHAT DIED AND WHY", "- Option 2, claim 5, EARNED",
        "6 TRADE-OFFS", "none surviving",
        "7 OUTSIDE REVIEW", "HIT 1 PASSED, applied. GAP 1 PASSED, moved to open. HOLD 1 HOLD-ACCEPTED.",
        "8 STILL OPEN", "- Claim 4 judgement call; settle with a fidelity benchmark",
        "9 CONFIDENCE", "High for option 1: three passed claims, one earned kill.",
        "10 RUN INTEGRITY", "earned 1 deprioritized 0; stages GENERATE, FMEA; stop MARGINAL; no failures; review ran; classification KEEP_FOR_DEVELOPMENT",
        "11 EFFICIENCY", "calls 11, elapsed 61 min",
        "12 NEXT QUESTION", "Build the closer-fidelity benchmark.",
        "14 PRIVATE DOCUMENT VERIFICATION", ""]) + "\n"
    sha = w(root, "final/DELIVERABLE.md", deliv); L("CLOSER", "send", file="final/DELIVERABLE.md", stage="FINAL", sha=sha)
    ver = "CONTRADICTIONS\nnone\nCONFIRMED\n1. Claim 3 confirmed by NIGHT_AGENT_SPEC.md section 4.6\nNOT COVERED\nClaim 1\nMATERIAL OMISSIONS\nnone\n"
    w(root, "final/verifier.md", ver); L("VERIFIER", "send", file="final/verifier.md", stage="VERIFY")
    w(root, "final/DELIVERABLE_ASSEMBLED.md", deliv + "\n" + ver); L("DISPATCH", "write", file="final/DELIVERABLE_ASSEMBLED.md", stage="DELIVER")
    # experiments (a HYBRID distinguishing test) with a valid KEEP
    w(root, "experiments/baseline.json", json.dumps({"metric": "runtime_s", "baseline_value": 10.0, "noise": 0.3, "runs": 2}))
    w(root, "experiments/exp-001/record.json", json.dumps({"id": "exp-001", "hypothesis": "caching halves runtime", "delta": -4.0, "noise": 0.3,
                                                          "repeat_value": 6.1, "constraints_checked": ["output hash unchanged"],
                                                          "guardrails": [{"name": "output_hash_changed", "baseline": 0, "value": 0, "tolerance": 0}],
                                                          "decision": "KEEP"}))
    w(root, "status.json", json.dumps({"run": "na-fixture", "stage": "DONE", "step": "deliver", "started": "22:00", "last_complete": "final/DELIVERABLE_ASSEMBLED.md", "next": "none"}))
    w(root, "log.jsonl", "\n".join(json.dumps(l) for l in log) + "\n")
    w(root, "dispatch.jsonl", "\n".join(json.dumps(d) for d in dispatch) + "\n")
    w(root, "capture.jsonl", "\n".join(json.dumps(c) for c in capture) + "\n")
    w(root, "registry.json", json.dumps({"seats": [{"id": s, "ready": True, "url": f"https://chat.example/{s}", "role": "closer" if s == "CLOSER" else ("generator" if s.startswith("G") else s.lower())} for s in ["G1", "G2", "G3", "G4", "CLOSER", "REVIEWER", "VERIFIER"]]}))


FAULTS = {
    "F01_bare_passed": lambda r: edit(r, "stage-01-generate/check.md", "  RETRIEVED  5 + 1 = 6\n", "  RETRIEVED  \n"),
    "F02_status_collapsed": lambda r: edit(r, "stage-01-generate/check.md", "RESULT     JUDGEMENT CALL", "RESULT     FAILED"),
    "F03_closer_invented_claim": lambda r: edit(r, "stage-02-fmea/close.md", "MERGED\n", "MERGED\n- Astra also scored higher on ARC, so option 1 is safer.\n"),
    "F04_new_option_after_generate": lambda r: edit(r, "stage-02-fmea/close.md", "OPTIONS STANDING\n1. Fable closes, Astra reviews.\n", "OPTIONS STANDING\n1. Fable closes, Astra reviews.\n3. Use Gemini as closer.\n"),
    "F05_reviewer_contacted_early": lambda r: append_log(r, {"t": "2026-09-09T22:30", "seat": "REVIEWER", "action": "send", "result": "OK", "stage": "OPERATE"}),
    "F06_review_package_leaks_seat_file": lambda r: edit(r, "review/package.md", "MERGED\n", "STAGE 01 GENERATE SEAT G1 TIME 22:10\nMERGED\n"),
    "F07_attribution_not_stripped": lambda r: edit(r, "review/package.md", "the fidelity seat", "Fable"),
    "F08_deliverable_edited_after_write": lambda r: edit(r, "final/DELIVERABLE.md", "Keep Fable as closer", "Keep Fable as closer (edited later)"),
    "F09_missing_stamp": lambda r: edit(r, "stage-02-fmea/seat-G2.md", "STAGE 02 FMEA SEAT G2 TIME 23:02\n", ""),
    "F10_stage_below_min_crew": lambda r: (os.remove(os.path.join(r, "stage-02-fmea/seat-G2.md")), os.remove(os.path.join(r, "stage-02-fmea/seat-G3.md"))),
    "F12_keep_without_repeat": lambda r: edit(r, "experiments/exp-001/record.json", '"repeat_value": 6.1', '"repeat_value": null'),
    "F13_merged_cites_unpassed_claim": lambda r: edit(r, "stage-02-fmea/close.md", "{C1,C3,C5}", "{C1,C4,C5}"),
    "F14_second_final_write": lambda r: append_log(r, {"t": "2026-09-10T05:00", "seat": "CLOSER", "action": "send", "result": "OK", "file": "final/DELIVERABLE.md", "stage": "FINAL"}),
    "F15_duplicate_dispatch_id": lambda r: append_jsonl(r, "dispatch.jsonl", {"run_id": "na-fixture", "stage_id": "stage-02-fmea", "seat_id": "G1", "dispatch_id": "d-02-G1", "conversation_url": "https://chat.example/G1"}),
    "F16_stale_stage_reply": lambda r: edit(r, "stage-02-fmea/seat-G1.md", "DISPATCH d-02-G1", "DISPATCH d-01-G1"),
    "F17_incomplete_capture_counted": lambda r: edit(r, "capture.jsonl", '"dispatch_id": "d-02-G2", "file": "stage-02-fmea/seat-G2.md", "completion_signal_observed": true', '"dispatch_id": "d-02-G2", "file": "stage-02-fmea/seat-G2.md", "completion_signal_observed": false'),
    "F18_quote_present_but_unsupported_passed": lambda r: edit(r, "stage-01-generate/check.md", 'support=SUPPORTED scope="vendor page states the figure"', 'support=PARTIAL scope="vendor page states a different tier"'),
    "F19_winner_label_in_review_package": lambda r: edit(r, "review/package.md", "MERGED\n", "MERGED\nThe winner is option 1.\n"),
    "F11_wall_leak": lambda r: edit(r, "stage-01-generate/seat-G2.md", "CANDIDATES\n", "CANDIDATES\nA. Keep the closer on Fable because merging rewards fidelity and the closer builds merged only from passed claims which is the seat definition.\n") or edit(r, "stage-01-generate/seat-G3.md", "CANDIDATES\n", "CANDIDATES\nA. Keep the closer on Fable because merging rewards fidelity and the closer builds merged only from passed claims which is the seat definition.\n") or edit(r, "stage-01-generate/seat-G1.md", "CANDIDATES\n", "CANDIDATES\nA. Keep the closer on Fable because merging rewards fidelity and the closer builds merged only from passed claims which is the seat definition.\n"),
}


def edit(root, rel, old, new):
    p = os.path.join(root, rel)
    s = open(p, encoding="utf-8").read()
    assert old in s, (rel, old)
    open(p, "w", encoding="utf-8").write(s.replace(old, new))


def append_jsonl(root, rel, rec):
    with open(os.path.join(root, rel), "a") as f:
        f.write(json.dumps(rec) + "\n")


def append_log(root, rec):
    with open(os.path.join(root, "log.jsonl"), "a") as f:
        f.write(json.dumps(rec) + "\n")


def run_check(root):
    r = subprocess.run([sys.executable, CHECK, root], capture_output=True, text=True)
    fails = [l for l in r.stdout.splitlines() if l.startswith("FAIL")]
    return r.returncode, fails


GATE = os.path.join(HERE, "na_gate.py")


def run_gate(root, stage, *extra):
    r = subprocess.run([sys.executable, GATE, root, stage, *extra], capture_output=True, text=True)
    return r.returncode, r.stdout.strip().splitlines()


GUARD_TESTS = [
    # (name, mutate, stage, extra, expect_block)
    ("G1_allow_gate", lambda r: None, "GATE", [], False),
    ("G1_block_no_ask", lambda r: os.remove(os.path.join(r, "ask.md")), "GATE", [], True),
    ("G2_allow_generate", lambda r: None, "GENERATE", [], False),
    ("G2_block_no_gate", lambda r: os.remove(os.path.join(r, "gate/gate.json")), "GENERATE", [], True),
    ("G3_allow_check", lambda r: None, "CHECK", ["--stage-dir", "stage-02-fmea"], False),
    ("G3_block_one_seat", lambda r: (os.remove(os.path.join(r, "stage-02-fmea/seat-G2.md")), os.remove(os.path.join(r, "stage-02-fmea/seat-G3.md"))), "CHECK", ["--stage-dir", "stage-02-fmea"], True),
    ("G4_allow_close", lambda r: None, "CLOSE", ["--stage-dir", "stage-01-generate"], False),
    ("G4_block_bare_passed", lambda r: edit(r, "stage-01-generate/check.md", "  RETRIEVED  5 + 1 = 6\n", "  RETRIEVED  \n"), "CLOSE", ["--stage-dir", "stage-01-generate"], True),
    ("G4_block_no_check", lambda r: os.remove(os.path.join(r, "stage-01-generate/check.md")), "CLOSE", ["--stage-dir", "stage-01-generate"], True),
    ("G5_allow_operate_new_op", lambda r: None, "OPERATE", ["--op", "IDOV"], False),
    ("G5_block_operator_repeated", lambda r: None, "OPERATE", ["--op", "FMEA"], True),
    ("G5_block_after_stop", lambda r: edit(r, "status.json", '"next": "none"', '"next": "none", "stop_reason": "MARGINAL"'), "OPERATE", ["--op", "IDOV"], True),
    ("G6_block_reviewer_contacted", lambda r: append_log(r, {"t": "x", "seat": "REVIEWER", "action": "send", "result": "OK", "stage": "OPERATE"}), "REVIEW", [], True),
    ("G7_block_final_exists", lambda r: None, "FINAL", [], True),
    ("G7_allow_final_fresh", lambda r: (os.remove(os.path.join(r, "final/DELIVERABLE.md")), os.remove(os.path.join(r, "final/DELIVERABLE_ASSEMBLED.md")), os.remove(os.path.join(r, "final/verifier.md")),
                                          open(os.path.join(r, "final/kills-all.md"), "w").write("KILLS\n- Option 2 killed by hard constraint (the reviewer must sit outside the rounds), established by claim 5, EARNED\n"),
                                          open(os.path.join(r, "final/metrics-summary.json"), "w").write("{}")), "FINAL", [], False),
    ("G8_block_verifier_exists", lambda r: None, "VERIFY", [], True),
    ("G9_allow_keep_with_repeat", lambda r: None, "DECIDE", ["--record", "exp-001"], False),
    ("G9_block_keep_without_repeat", lambda r: edit(r, "experiments/exp-001/record.json", '"repeat_value": 6.1', '"repeat_value": null'), "DECIDE", ["--record", "exp-001"], True),
    ("G11_allow_send_fresh_seat", lambda r: None, "SEND", ["--seat", "G4"], False),
    ("G11_block_send_previous_slot_open", lambda r: edit(r, "capture.jsonl", '"dispatch_id": "d-02-G1", "file": "stage-02-fmea/seat-G1.md", "completion_signal_observed": true', '"dispatch_id": "d-02-G1", "file": "stage-02-fmea/seat-G1.md", "completion_signal_observed": false'), "SEND", ["--seat", "G1"], True),
    ("G11_block_send_wrong_conversation", lambda r: edit(r, "dispatch.jsonl", '"seat_id": "G2", "provider": "p", "conversation_url": "https://chat.example/G2", "tab_id": "t", "displayed_model": "m", "displayed_effort": "high", "prompt_hash": "h", "dispatch_id": "d-02-G2"', '"seat_id": "G2", "provider": "p", "conversation_url": "https://chat.example/OTHER", "tab_id": "t", "displayed_model": "m", "displayed_effort": "high", "prompt_hash": "h", "dispatch_id": "d-02-G2"'), "SEND", ["--seat", "G2"], True),
    ("G3_block_partial_capture", lambda r: edit(r, "capture.jsonl", '"dispatch_id": "d-02-G2", "file": "stage-02-fmea/seat-G2.md", "completion_signal_observed": true', '"dispatch_id": "d-02-G2", "file": "stage-02-fmea/seat-G2.md", "completion_signal_observed": false') or edit(r, "capture.jsonl", '"dispatch_id": "d-02-G3", "file": "stage-02-fmea/seat-G3.md", "completion_signal_observed": true', '"dispatch_id": "d-02-G3", "file": "stage-02-fmea/seat-G3.md", "completion_signal_observed": false'), "CHECK", ["--stage-dir", "stage-02-fmea"], True),
    ("G9_block_keep_within_noise", lambda r: edit(r, "experiments/exp-001/record.json", '"delta": -4.0', '"delta": -0.1'), "DECIDE", ["--record", "exp-001"], True),
]


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/na_fixture"
    if os.path.exists(out):
        shutil.rmtree(out)
    base = os.path.join(out, "conforming")
    conforming(base)
    rc, fails = run_check(base)
    conforming_ok = rc == 0
    print(f"conforming fixture: exit {rc}, {len(fails)} FAIL lines")
    for f in fails:
        print("   ", f)
    caught = 0
    for name, inject in FAULTS.items():
        d = os.path.join(out, name)
        shutil.copytree(base, d)
        inject(d)
        rc, fails = run_check(d)
        ok = rc != 0
        caught += ok
        print(f"{'CAUGHT ' if ok else 'MISSED '} {name}: {fails[:2]}")
    print(f"\n{caught} of {len(FAULTS)} injected faults caught")
    gok = 0
    for name, mut, stage, extra, expect_block in GUARD_TESTS:
        d = os.path.join(out, "guard_" + name)
        shutil.copytree(base, d)
        mut(d)
        rc2, lines = run_gate(d, stage, *extra)
        blocked = rc2 != 0
        ok = blocked == expect_block
        gok += ok
        print(f"{'OK   ' if ok else 'WRONG'} {name}: {lines[0] if lines else ''}{(' / ' + lines[1].strip()) if blocked and len(lines) > 1 else ''}")
    print(f"{gok} of {len(GUARD_TESTS)} guard expectations met")
    # candidate-mutation sensitivity: bypass a rejection branch in a COPY of the checker, oracle fixed; the matching fault must now be MISSED
    mutated = os.path.join(out, "mutated_na_check.py")
    src = open(CHECK).read()
    assert 'rep(bool(c["retrieved"]), f"EVID-2-' in src
    open(mutated, "w").write(src.replace('rep(bool(c["retrieved"]), f"EVID-2-', 'rep(True, f"EVID-2-'))
    r = subprocess.run([sys.executable, mutated, os.path.join(out, "F01_bare_passed")], capture_output=True, text=True)
    evid2_fails = [l for l in r.stdout.splitlines() if l.startswith("FAIL EVID-2")]
    sensitivity_ok = len(evid2_fails) == 0
    print(f"{'OK   ' if sensitivity_ok else 'WRONG'} mutation sensitivity: bypassing EVID-2 in the candidate makes F01 escape that rule ({len(evid2_fails)} EVID-2 fails after mutation)")
    # verification manifest
    import hashlib, time, uuid
    def sha(pth):
        return hashlib.sha256(open(pth, "rb").read()).hexdigest()
    manifest = {"verification_id": str(uuid.uuid4()), "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "suite_ids": ["faults", "guards", "mutation"], "case_ids": list(FAULTS.keys()) + [g[0] for g in GUARD_TESTS] + ["mutation_evid2"],
                "expected": {**{k: "CAUGHT" for k in FAULTS}, **{g[0]: ("BLOCK" if g[4] else "ALLOW") for g in GUARD_TESTS}, "mutation_evid2": "ESCAPES"},
                "observed_summary": {"faults_caught": caught, "faults_total": len(FAULTS), "guards_met": gok, "guards_total": len(GUARD_TESTS), "mutation_sensitivity": sensitivity_ok},
                "candidate_hashes": {"na_gate.py": sha(GATE), "na_check.py": sha(CHECK), "make_fixture.py": sha(os.path.abspath(__file__))},
                "skipped": 0, "errors": 0, "complete": True}
    open(os.path.join(out, "verification-manifest.json"), "w").write(json.dumps(manifest, indent=2))
    print("manifest written:", os.path.join(out, "verification-manifest.json"))
    sys.exit(0 if conforming_ok and caught == len(FAULTS) and gok == len(GUARD_TESTS) and sensitivity_ok else 1)
