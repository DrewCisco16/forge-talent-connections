#!/usr/bin/env python3
"""Measure one experiment, apply the frozen decision rule from README.md, and record it.

    python3 AUTORESEARCH/decide.py <exp-id> "<hypothesis>" [--files f1 f2 ...] [--interaction] [--no-git]

KEEP        commit the working tree (message = id and hypothesis), update last_kept.json
REVERT      git checkout the package back to the last kept tree
INCONCLUSIVE a DEV case was fixed while its HOLDOUT twin stayed missed: reverted, logged as such
Every outcome appends one line to log.jsonl, and that line is committed.
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
REPO = os.path.dirname(PKG)
LAST = os.path.join(HERE, "last_kept.json")
LOG = os.path.join(HERE, "log.jsonl")


def sh(*cmd, check=True):
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(r.stdout, r.stderr)
        raise SystemExit(f"command failed: {' '.join(cmd)}")
    return r.stdout.strip()


def summary(res):
    p, g, gr, s = res["primary"], res["guard"], res["guardrails"], res["secondary"]
    return {"primary_dev": p["DEV"]["caught"], "primary_holdout": p["HOLDOUT"]["caught"],
            "guard_dev": g["DEV"]["blocked"], "guard_holdout": g["HOLDOUT"]["blocked"],
            "false_fail": gr["false_fail_lines_on_clean_bases"], "false_block": gr["false_blocks"],
            "pkg_fail": gr["package_check_failures"], "legacy_exit": gr["legacy_suite_exit"],
            "corpus_errors": gr["corpus_errors"], "within_budget": gr["within_budget"],
            "secondary": s["package_assertions_passing"]}


def statuses(res, key, ok):
    return {r["id"]: r["status"] for r in res["detail"][key]}


def decide(before, after):
    b, a = summary(before), summary(after)
    reasons = []
    guard_ok = (a["false_fail"] <= b["false_fail"] and a["false_block"] <= b["false_block"] and a["pkg_fail"] == 0
                and a["legacy_exit"] == 0 and a["corpus_errors"] == 0 and a["within_budget"])
    if not guard_ok:
        reasons.append("guardrail regressed or failed")
        return "REVERT", reasons, a
    # DEV-only fits: a family whose DEV case flipped to caught while the HOLDOUT twin stays missed
    for key, okv in (("faults", "CAUGHT"), ("guards", "BLOCKED")):
        sb, sa = statuses(before, key, okv), statuses(after, key, okv)
        for cid, st in sa.items():
            if cid.endswith("a") and st == okv and sb.get(cid) != okv:
                twin = cid[:-1] + "b"
                if twin in sa and sa[twin] != okv:
                    reasons.append(f"{cid} fixed but HOLDOUT twin {twin} still {sa[twin]}")
    if reasons:
        return "INCONCLUSIVE", reasons, a
    prim_b, prim_a = b["primary_dev"] + b["primary_holdout"], a["primary_dev"] + a["primary_holdout"]
    gu_b, gu_a = b["guard_dev"] + b["guard_holdout"], a["guard_dev"] + a["guard_holdout"]
    if a["primary_holdout"] < b["primary_holdout"] or a["guard_holdout"] < b["guard_holdout"]:
        return "REVERT", ["HOLDOUT fell"], a
    if prim_a >= prim_b + 1:
        return "KEEP", [f"primary {prim_b} -> {prim_a}"], a
    if gu_a >= gu_b + 1:
        return "KEEP", [f"guard {gu_b} -> {gu_a}"], a
    if prim_a == prim_b and gu_a == gu_b and (a["false_fail"] < b["false_fail"] or a["false_block"] < b["false_block"] or a["secondary"] > b["secondary"]):
        return "KEEP", [f"guardrail/secondary improved: false_fail {b['false_fail']}->{a['false_fail']} false_block {b['false_block']}->{a['false_block']} secondary {b['secondary']}->{a['secondary']}"], a
    return "REVERT", ["no improvement beyond MIN_DELTA"], a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exp_id")
    ap.add_argument("hypothesis")
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--interaction", action="store_true")
    ap.add_argument("--no-git", action="store_true")
    a = ap.parse_args()
    before = json.load(open(LAST if os.path.exists(LAST) else os.path.join(HERE, "baseline.json")))
    out_json = os.path.join(HERE, ".eval-scratch-result.json")
    t0 = time.time()
    r = subprocess.run([sys.executable, os.path.join(HERE, "eval.py"), "--quiet", "--json", out_json], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out_json):
        print(r.stdout, r.stderr)
        raise SystemExit("eval failed")
    after = json.load(open(out_json))
    os.remove(out_json)
    decision, reasons, a_sum = decide(before, after)
    b_sum = summary(before)
    changed = {k: (b_sum[k], a_sum[k]) for k in a_sum if a_sum[k] != b_sum[k]}
    print(f"{a.exp_id}: {decision}  {'; '.join(reasons)}")
    print("  changed:", changed)
    newly = [cid for cid, st in statuses(after, "faults", "CAUGHT").items() if st == "CAUGHT" and statuses(before, "faults", "CAUGHT").get(cid) != "CAUGHT"]
    newly += [cid for cid, st in statuses(after, "guards", "BLOCKED").items() if st == "BLOCKED" and statuses(before, "guards", "BLOCKED").get(cid) != "BLOCKED"]
    lost = [cid for cid, st in statuses(before, "faults", "CAUGHT").items() if st == "CAUGHT" and statuses(after, "faults", "CAUGHT").get(cid) != "CAUGHT"]
    lost += [cid for cid, st in statuses(before, "guards", "BLOCKED").items() if st == "BLOCKED" and statuses(after, "guards", "BLOCKED").get(cid) != "BLOCKED"]
    print("  newly caught/blocked:", newly, " lost:", lost)
    line = {"id": a.exp_id, "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "hypothesis": a.hypothesis, "files": a.files,
            "interaction": a.interaction, "before": b_sum, "after": a_sum, "newly_caught": newly, "lost": lost,
            "decision": decision, "reasons": reasons, "eval_runtime_s": round(time.time() - t0, 1)}
    if a.no_git:
        print(json.dumps(line))
        return
    if decision == "KEEP":
        json.dump(after, open(LAST, "w"), indent=1)
        with open(LOG, "a") as f:
            f.write(json.dumps(line) + "\n")
        sh("git", "add", "-A", "night_agent")
        msg = f"{a.exp_id}: {a.hypothesis}\n\nKEEP. {'; '.join(reasons)}.\nnewly caught or blocked: {', '.join(newly) or 'none'}"
        sh("git", "commit", "-q", "-m", msg + "\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01GZpMeLUgL97fbaVdH9bgmf")
    else:
        sh("git", "checkout", "--", "night_agent")
        sh("git", "clean", "-fdq", "night_agent")
        with open(LOG, "a") as f:
            f.write(json.dumps(line) + "\n")
        sh("git", "add", "-A", "night_agent/AUTORESEARCH/log.jsonl")
        sh("git", "commit", "-q", "-m", f"{a.exp_id}: {decision}, {a.hypothesis}\n\n{'; '.join(reasons)}\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01GZpMeLUgL97fbaVdH9bgmf")
    line["commit"] = sh("git", "rev-parse", "--short", "HEAD")
    print("  commit:", line["commit"])


if __name__ == "__main__":
    main()
