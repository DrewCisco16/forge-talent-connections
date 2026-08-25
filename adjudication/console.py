"""
console.py
==========
The panel console. Formulate a problem, run it, read what survived.

Everything that costs money says so on the menu line, with the call count.
A menu that hides which button spends is the wrong menu.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")
PY = os.path.join(HERE, ".venv", "bin", "python")


def _p(s: str = "") -> None:
    print(s)


def pause() -> None:
    input("\n  Return for the menu... ")


def sh(args: list[str]) -> int:
    """Run a child command inheriting stdio.

    NOT piped, deliberately. A pipeline's exit status is the last command's,
    and the engine's exit code is the thing that says whether the run
    resolved -- 0 for resolved, 1 for holes remaining. Piping it through tail
    silently turns every outcome into success.
    """
    return subprocess.call(args, cwd=HERE)


def run_dirs() -> list[str]:
    if not os.path.isdir(RUNS):
        return []
    return sorted((d for d in os.listdir(RUNS)
                   if os.path.isdir(os.path.join(RUNS, d))), reverse=True)


def pick_run() -> str | None:
    ds = run_dirs()
    if not ds:
        _p("  no runs yet")
        return None
    for i, d in enumerate(ds[:15], 1):
        _p(f"  {i:>2}  {d}")
    raw = input("\n  Which? (blank to cancel) ").strip()
    if not raw.isdigit() or not 1 <= int(raw) <= min(len(ds), 15):
        return None
    return os.path.join(RUNS, ds[int(raw) - 1])


# ---------------------------------------------------------------------------
# actions
# ---------------------------------------------------------------------------

def new_problem() -> None:
    sys.path.insert(0, HERE)
    from intake import run_intake

    spec = run_intake()
    if not spec:
        return

    _p("-" * 68)
    _p("  This next step makes REAL calls: 5 seats x 5 passes, about 25 calls.")
    _p(f"  gates      : {spec['gates']}" + ("  + DOI resolution" if spec["resolve_dois"] else ""))
    _p(f"  artifact   : {os.path.relpath(spec['artifact'], HERE)}")
    if spec["gateable"] == 0:
        _p("  NOTE       : nothing in this run can be checked mechanically.")
    _p("-" * 68)
    if input("  Type YES to spend: ").strip() != "YES":
        _p("  Not run. The folder is saved -- you can run it later from the menu.")
        return
    execute(spec["run_dir"], spec["gates"], spec["resolve_dois"])


def execute(run_dir: str, gates: str, dois: bool) -> None:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    art = os.path.join(run_dir, "artifact.txt")
    cand = os.path.join(run_dir, "candidates.json")
    audit = os.path.join(run_dir, f"run-{stamp}.jsonl")
    queue = os.path.join(run_dir, f"queue-{stamp}.json")
    args = [PY, "run_adjudication.py", art, "--profiles", "profiles.json",
            "--candidates", cand, "--gates", gates,
            "--export-queue", queue, "--audit", audit]
    if dois:
        args.append("--resolve-dois")
    code = sh(args)
    _p()
    _p(f"  exit {code}   (0 = resolved, 1 = holes remain, 2 = could not start)")
    _p(f"  audit: {os.path.relpath(audit, HERE)}")


def rerun() -> None:
    d = pick_run()
    if not d:
        return
    sys.path.insert(0, HERE)
    from domains import BY_KEY
    prob = os.path.join(d, "PROBLEM.md")
    key = "general"
    if os.path.exists(prob):
        with open(prob, encoding="utf-8") as fh:
            head = fh.read(600)
        for k, dom in BY_KEY.items():
            if dom.title in head:
                key = k
                break
    dom = BY_KEY[key]
    _p(f"  domain: {dom.title}")
    _p("  About 25 real calls.")
    if input("  Type YES to spend: ").strip() != "YES":
        _p("  Cancelled.")
        return
    execute(d, ",".join(dom.gates), dom.resolve_dois)


def show_verdict() -> None:
    d = pick_run()
    if not d:
        return
    logs = sorted(f for f in os.listdir(d) if f.startswith("run-") and f.endswith(".jsonl"))
    if not logs:
        _p("  that problem has never been run")
        return
    path = os.path.join(d, logs[-1])
    _p(f"\n  {logs[-1]}")
    _p("-" * 68)
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        if e.get("kind") != "pass":
            continue
        p = e["payload"]
        elim = p.get("eliminated_candidates") or []
        _p(f"  {p.get('pass_id')} {str(p.get('pass_name'))[:38]:40}"
           f" seats {len(p.get('seats_responding') or [])}/5"
           f"  err {len(p.get('seats_errored') or [])}"
           f"  acc {p.get('auto_accepted')} rej {p.get('auto_rejected')}"
           f" esc {p.get('escalated')}"
           + (f"  killed {', '.join(elim)}" if elim else ""))
    prob = os.path.join(d, "PROBLEM.md")
    if os.path.exists(prob):
        _p("\n  Prior belief recorded at intake — check the run against it, not the")
        _p("  other way round:")
        with open(prob, encoding="utf-8") as fh:
            txt = fh.read()
        if "## Prior belief" in txt:
            seg = txt.split("## Prior belief (not sent to any seat)")[1]
            _p("    " + seg.split("##")[0].strip()[:300])


def conduct_across_runs() -> None:
    """Governance view: which seat asserts things that do not hold, over time."""
    totals: dict[str, list[int]] = {}
    runs = 0
    for d in run_dirs():
        for f in sorted(os.listdir(os.path.join(RUNS, d))):
            if not (f.startswith("run-") and f.endswith(".jsonl")):
                continue
            runs += 1
            for line in open(os.path.join(RUNS, d, f), encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                if e.get("kind") != "seat_conduct":
                    continue
                for seat, rec in (e["payload"].get("seats") or {}).items():
                    cur = totals.setdefault(seat, [0, 0])
                    cur[0] += int(rec.get("proposed", 0))
                    cur[1] += int(rec.get("ruled_false", 0))
    _p()
    _p(f"  SEAT CONDUCT across {runs} run(s)")
    _p("-" * 68)
    if not totals:
        _p("  no conduct records yet (no run has produced one)")
        return
    for seat, (prop, bad) in sorted(totals.items(),
                                    key=lambda kv: -(kv[1][1] / kv[1][0]) if kv[1][0] else 0):
        if prop == 0:
            _p(f"  {seat:<14} proposed nothing -- no record (not the same as clean)")
            continue
        _p(f"  {seat:<14} {bad:>4} of {prop:>5} claims ruled false  ({bad/prop:.1%})")
    _p()
    _p("  Ruled false means a gate recomputed, resolved, or parsed it and it did")
    _p("  not hold. It is not a finding that a model lied.")


MENU = """
======================================================================
  ADJUDICATION PANEL
  five blinded seats  |  elimination, not voting
======================================================================

  SOLVE A PROBLEM
    1  New problem            guided setup, then run   (~25 calls)
    2  Run an existing one    already formulated       (~25 calls)

  LOOK AT RESULTS                                          free
    3  Verdict from a run
    4  Seat conduct across all runs   (AI governance)

  MAINTENANCE                                              free
    5  Check keys and seats
    6  Validate profiles
    7  Demo on fake seats
    8  Test suite
    9  Ping all five seats            (~5 calls, under a cent)

    o  Open this folder      q  Quit
"""


def main() -> int:
    while True:
        os.system("clear")
        _p(MENU)
        c = input("  Choose: ").strip().lower()
        _p()
        if c == "1":
            new_problem()
        elif c == "2":
            rerun()
        elif c == "3":
            show_verdict()
        elif c == "4":
            conduct_across_runs()
        elif c == "5":
            sh(["./set-key.command", "check"])
        elif c == "6":
            sh([PY, "run_adjudication.py", "--check-profiles", "profiles.json"])
        elif c == "7":
            sh([PY, "run_adjudication.py", "--demo"])
        elif c == "8":
            sh([PY, "-m", "pytest", "test_suite.py", "test_properties.py", "-q"])
        elif c == "9":
            _p("  5 real calls, ~6 tokens each. Under a cent.")
            if input("  Type YES: ").strip() == "YES":
                sh([PY, "diagnose-seats.py", "seat_1", "seat_2", "seat_3",
                    "seat_4", "seat_5"])
            else:
                _p("  Cancelled.")
        elif c == "o":
            subprocess.call(["open", HERE])
        elif c == "q":
            return 0
        else:
            _p("  not a choice")
        pause()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
