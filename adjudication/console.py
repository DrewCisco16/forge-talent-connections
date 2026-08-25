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

# Reason kept OFF the nosec line: bandit reads everything after "nosec" as
# test ids. subprocess here runs only this repo's own scripts with an argv
# list and shell=False; nothing a model produced ever reaches it.
import subprocess  # nosec B404
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
    # argv list, shell=False by default, and args are built from this repo's
    # own paths. No model output reaches this call.
    return subprocess.call(args, cwd=HERE)  # nosec B603 B607


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


def _progress(message: str) -> None:
    """Print a progress line immediately.

    flush=True is not decoration. Python block-buffers stdout when it is not a
    terminal, so piped or redirected output would appear only at the end --
    which is precisely the run where the operator most needs to see progress,
    because they redirected it to watch a long job.
    """
    print(f"  {message}", flush=True)


def night() -> None:
    """All five seats think blind; one of them then merges. Round 1 invents
    the options and rounds 2-5 only remove from that set."""
    sys.path.insert(0, HERE)
    from intake import ask as _ask
    from intake import ask_multiline, slugify

    _p("You write one line saying what you want. Round 1 proposes the")
    _p("options and attacks them; rounds 2-5 only eliminate.")
    _p("You do NOT need to supply candidates or a disproof test -- every")
    _p("thinker must state what would knock its own proposals down.")
    _p()
    one = _ask("What do you want? (blank to paste something longer):",
               allow_blank=True)
    ask_text = one or ask_multiline("Paste the ask:")
    if not ask_text.strip():
        _p("  Nothing to ask. Stopped.")
        return

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = os.path.join(RUNS, f"{stamp}-night-{slugify(ask_text, 32)}")
    cap = _ask("Hard spend ceiling in dollars [3.00]:", allow_blank=True) or "3.00"
    _p()
    _p("-" * 68)
    _p(f"  5 rounds x 5 blind seats + 5 merges = 30 calls. Ceiling ${cap}.")
    _p("  Allow 30-90 minutes. Reasoning models take minutes per call and")
    _p("  the seats run one at a time; progress prints as each one answers.")
    _p(f"  folder: {os.path.relpath(out, HERE)}")
    _p("-" * 68)
    if input("  Type YES to spend: ").strip() != "YES":
        _p("  Cancelled.")
        return

    from cost_ledger import CeilingReached
    from night_loop import live_night
    from run_adjudication import build_ledger
    try:
        led = build_ledger(float(cap), None, None)
        # Progress prints as it happens. Without it this is thirty silent
        # model calls, which is indistinguishable from a hang -- and the
        # only way to find out is to kill the run and lose what it cost.
        res = live_night(ask_text, os.path.join(HERE, "profiles.json"), out,
                         ledger=led, on_event=_progress)
    except CeilingReached as exc:
        _p(f"  PARTIAL -- {exc}")
        return
    except Exception as exc:  # noqa: BLE001
        _p(f"  stopped: {type(exc).__name__}: {exc}")
        return
    _p()
    for r in res:
        _p(f"  round {r.n}  {r.name[:34]:36} seats {len(r.thinkers_ok)}/5"
           f"  claims {r.claims:>3}  pass {r.passed:>3} fail {r.failed:>3}"
           f" blocked {r.blocked:>2}" + ("   DEGRADED" if r.degraded else "")
           + ("   CONTAMINATED" if r.closer_contaminated else ""))
    _p()
    _p(f"  verifier packet: {os.path.relpath(os.path.join(out, 'VERIFIER-PACKET.md'), HERE)}")
    _p("  Paste it into a NEW chat in your Claude Project. Nothing else.")


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
    with open(path, encoding="utf-8") as fh:
        entries = [json.loads(ln) for ln in fh if ln.strip()]
    for e in entries:
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
            with open(os.path.join(RUNS, d, f), encoding="utf-8") as fh:
                entries = [json.loads(ln) for ln in fh if ln.strip()]
            for e in entries:
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
    n  Five rounds            RECOMMENDED. You write one line. All five
                              seats answer blind, code checks every claim,
                              then one seat merges what survived and the
                              next round starts from that merge.
                              30 calls (5 rounds x 5 seats + 5 merges)
                              Allow 30-90 min: reasoning models take
                              minutes per call, and the seats run in turn.

    1  New problem            Guided setup, then the elimination engine:
                              you supply the candidate answers up front and
                              five passes try to knock them out.
                              25 calls (5 passes x 5 seats)
    2  Run an existing one    Same engine, already formulated.  25 calls

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
        # ANSI erase-display + cursor-home rather than os.system("clear"),
        # which starts a shell and resolves 'clear' off PATH. Nothing here
        # needs a shell, and a menu loop is a poor reason to invoke one.
        print("\033[2J\033[H", end="")
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
        elif c == "n":
            night()
        elif c == "o":
            subprocess.call(["/usr/bin/open", HERE])  # nosec B603
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
