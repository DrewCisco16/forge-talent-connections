#!/usr/bin/env python3
"""The one measurement command for the Night Agent autoresearch loop.

    python3 AUTORESEARCH/eval.py [--package <dir>] [--out <scratch dir>] [--json <path>] [--budget-s 120]

Builds the frozen corpus (holdout_corpus.py), runs the package's own checker and
guard against every case, runs the package's legacy self-test, and prints one
table. Deterministic: two runs on the same tree give the same numbers.

Reported, always separately, never composed into one score:
  primary     run-folder faults caught, DEV and HOLDOUT (higher is better)
  guard       guard cases blocked, DEV and HOLDOUT (higher is better)
  guardrails  FAIL lines on clean bases (must be 0), false BLOCKs on clean
              transitions (must be 0), package consistency failures (must be
              0), legacy fixture suite exit code (must be 0), runtime within
              budget
  secondary   package assertions passing (higher is better)

A fault whose base is not clean under the current checker cannot be scored;
it is reported INCONCLUSIVE and counted as not caught.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import holdout_corpus as hc  # noqa: E402


def run(cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout


def fail_lines(stdout):
    return [l for l in stdout.splitlines() if l.startswith("FAIL")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", default=os.path.dirname(HERE))
    ap.add_argument("--out", default=os.path.join(HERE, ".eval-scratch"))
    ap.add_argument("--json", default=None)
    ap.add_argument("--budget-s", type=float, default=120.0)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    pkg = os.path.abspath(a.package)
    check = os.path.join(pkg, "TESTS", "na_check.py")
    gate = os.path.join(pkg, "TESTS", "na_gate.py")
    out = os.path.abspath(a.out)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)

    say = (lambda *x: None) if a.quiet else print

    # ---- bases
    base_root = os.path.join(out, "base")
    bases, base_clean, base_fail = {}, {}, {}
    for name in hc.BASES:
        root = hc.build_base(base_root, name)
        bases[name] = root
        rc, so = run([sys.executable, check, root])
        base_fail[name] = fail_lines(so)
        base_clean[name] = rc == 0
        say(f"base {name}: {'clean' if base_clean[name] else 'NOT CLEAN'} ({len(base_fail[name])} FAIL lines)")
        for l in base_fail[name][:8]:
            say("    " + l[:140])

    def fresh(name, case_id):
        d = os.path.join(out, case_id)
        shutil.copytree(os.path.join(base_root, "runs"), os.path.join(d, "runs"))
        if os.path.exists(os.path.join(base_root, "architecture")):
            shutil.copytree(os.path.join(base_root, "architecture"), os.path.join(d, "architecture"))
        return os.path.join(d, hc.BASES[name][0])

    # ---- run-folder faults
    fault_rows = []
    for fid, split, base, ref, desc, mutate in hc.FAULTS:
        root = fresh(base, fid)
        try:
            mutate(root)
        except Exception as e:  # a corpus bug, not a checker result
            fault_rows.append({"id": fid, "split": split, "status": "ERROR", "detail": repr(e)[:200]})
            continue
        rc, so = run([sys.executable, check, root])
        fl = fail_lines(so)
        if not base_clean[base]:
            status = "INCONCLUSIVE"
        else:
            status = "CAUGHT" if rc != 0 else "MISSED"
        fault_rows.append({"id": fid, "split": split, "base": base, "spec": ref, "desc": desc, "status": status,
                           "rules": sorted({l.split()[1].rsplit("-", 1)[0] if l.split()[1][-1].isdigit() else l.split()[1] for l in fl})[:4]})

    # ---- guard block cases
    guard_rows = []
    for gid, split, base, ref, desc, mutate, stage, args in hc.GUARD_BLOCK:
        root = fresh(base, gid)
        try:
            mutate(root)
        except Exception as e:
            guard_rows.append({"id": gid, "split": split, "status": "ERROR", "detail": repr(e)[:200]})
            continue
        rc, so = run([sys.executable, gate, root, stage, *args])
        guard_rows.append({"id": gid, "split": split, "base": base, "spec": ref, "desc": desc, "stage": stage,
                           "status": "BLOCKED" if rc != 0 else "ALLOWED", "reason": (so.splitlines()[1].strip() if rc != 0 and len(so.splitlines()) > 1 else "")})

    # ---- allow cases (false-block guardrail)
    allow_rows = []
    for aid, base, mutate, stage, args in hc.GUARD_ALLOW:
        root = fresh(base, aid)
        mutate(root)
        rc, so = run([sys.executable, gate, root, stage, *args])
        allow_rows.append({"id": aid, "base": base, "stage": stage, "status": "ALLOWED" if rc == 0 else "FALSE_BLOCK",
                           "reason": (so.splitlines()[1].strip() if rc != 0 and len(so.splitlines()) > 1 else "")})

    # ---- package assertions (secondary)
    pa_rows = []
    for pid, ref, desc, fn in hc.PACKAGE_ASSERTIONS:
        try:
            ok = bool(fn(pkg))
        except Exception as e:  # noqa: BLE001
            ok, desc = False, desc + f" (raised {type(e).__name__})"
        pa_rows.append({"id": pid, "spec": ref, "desc": desc, "status": "PASS" if ok else "FAIL"})

    # ---- package consistency and legacy suite (guardrails)
    rc_pkg, so_pkg = run([sys.executable, check, "--package", pkg])
    pkg_fails = fail_lines(so_pkg)
    pkg_total = [l for l in so_pkg.splitlines() if l.startswith(("PASS", "FAIL"))]
    rc_legacy, so_legacy = run([sys.executable, os.path.join(pkg, "TESTS", "make_fixture.py"), os.path.join(out, "legacy_fixture")])
    legacy_tail = [l for l in so_legacy.splitlines() if " of " in l or "sensitivity" in l]

    elapsed = time.time() - t0

    def tally(rows, ok_status, split):
        sel = [r for r in rows if r.get("split") == split]
        return sum(1 for r in sel if r["status"] == ok_status), len(sel)

    res = {
        "primary": {s: dict(zip(("caught", "total"), tally(fault_rows, "CAUGHT", s))) for s in ("DEV", "HOLDOUT")},
        "guard": {s: dict(zip(("blocked", "total"), tally(guard_rows, "BLOCKED", s))) for s in ("DEV", "HOLDOUT")},
        "guardrails": {
            "false_fail_lines_on_clean_bases": sum(len(v) for v in base_fail.values()),
            "bases_not_clean": [k for k, v in base_clean.items() if not v],
            "false_blocks": sum(1 for r in allow_rows if r["status"] != "ALLOWED"),
            "package_check_failures": len(pkg_fails),
            "package_check_total": len(pkg_total),
            "legacy_suite_exit": rc_legacy,
            "corpus_errors": sum(1 for r in fault_rows + guard_rows if r["status"] == "ERROR"),
            "runtime_s": round(elapsed, 2),
            "within_budget": elapsed <= a.budget_s,
        },
        "secondary": {"package_assertions_passing": sum(1 for r in pa_rows if r["status"] == "PASS"), "total": len(pa_rows)},
        "detail": {"faults": fault_rows, "guards": guard_rows, "allows": allow_rows, "package_assertions": pa_rows,
                   "legacy": legacy_tail, "package_check_fail_lines": pkg_fails[:20]},
    }
    p = res["primary"]; g = res["guard"]; gr = res["guardrails"]; sec = res["secondary"]
    say("")
    say(f"PRIMARY   faults caught   DEV {p['DEV']['caught']}/{p['DEV']['total']}   HOLDOUT {p['HOLDOUT']['caught']}/{p['HOLDOUT']['total']}")
    say(f"GUARD     cases blocked   DEV {g['DEV']['blocked']}/{g['DEV']['total']}   HOLDOUT {g['HOLDOUT']['blocked']}/{g['HOLDOUT']['total']}")
    say(f"GUARDRAIL false FAIL lines on clean bases {gr['false_fail_lines_on_clean_bases']}  (bases not clean: {gr['bases_not_clean']})")
    say(f"GUARDRAIL false BLOCKs {gr['false_blocks']}   package check failures {gr['package_check_failures']}/{gr['package_check_total']}   legacy suite exit {gr['legacy_suite_exit']}   corpus errors {gr['corpus_errors']}")
    say(f"SECONDARY package assertions {sec['package_assertions_passing']}/{sec['total']}")
    say(f"RUNTIME   {gr['runtime_s']} s (budget {a.budget_s} s, within: {gr['within_budget']})")
    say("")
    for r in fault_rows:
        if r["status"] != "CAUGHT":
            say(f"  {r['status']:12} {r['id']:5} {r['split']:7} {r.get('desc', r.get('detail', ''))}")
    for r in guard_rows:
        if r["status"] != "BLOCKED":
            say(f"  {r['status']:12} {r['id']:5} {r['split']:7} {r.get('desc', r.get('detail', ''))}")
    for r in allow_rows:
        if r["status"] != "ALLOWED":
            say(f"  {r['status']:12} {r['id']:5}         {r['stage']} {r['reason']}")
    for r in pa_rows:
        if r["status"] != "PASS":
            say(f"  PA-FAIL      {r['id']:5}         {r['desc']}")
    if a.json:
        with open(a.json, "w") as f:
            json.dump(res, f, indent=1)
    return res


if __name__ == "__main__":
    main()
