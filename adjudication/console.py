"""
console.py
==========
The panel console. Formulate a problem, run it, read what survived.

Everything that costs money says so on the menu line, with the call count.
A menu that hides which button spends is the wrong menu.
"""
from __future__ import annotations

import json
import math
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
    #
    # B607 was listed here and suppresses nothing: bandit reports a nosec with
    # no matching finding, and a stale suppression is indistinguishable from a
    # live one, so it teaches the next reader that this line needs an
    # exemption it does not need.
    return subprocess.call(args, cwd=HERE)  # nosec B603


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
    cap = ask_ceiling()
    _p(f"  ceiling    : ${cap:.2f}")
    _p("-" * 68)
    if input("  Type YES to spend: ").strip() != "YES":
        _p("  Not run. The folder is saved -- you can run it later from the menu.")
        return
    execute(spec["run_dir"], spec["gates"], spec["resolve_dois"], cap)


def ask_ceiling(default: str = "3.00") -> float | None:
    """A finite positive spend ceiling, or None if the operator backs out.

    THE PAID PATHS DID NOT ASK FOR ONE. execute() built the command line with
    no --max-cost, so build_ledger returned None and the run had no ceiling at
    all. The console said "about 25 calls" and "Type YES to spend", the
    operator typed YES, and five vendors were called with nothing bounding the
    bill. Only the night path asked.
    """
    from intake import ask as _ask
    while True:
        raw = _ask(f"  Spend ceiling in dollars [{default}]:",
                   allow_blank=True) or default
        try:
            value = float(raw)
        except ValueError:
            _p(f"  {raw!r} is not a number of dollars.")
            continue
        if not math.isfinite(value) or value <= 0:
            _p("  A ceiling must be a finite positive number. 'nan' and 'inf' "
               "compare False against every total, so they bound nothing.")
            continue
        return value


def execute(run_dir: str, gates: str, dois: bool,
            max_cost: float | None = None) -> None:
    if max_cost is None:
        max_cost = ask_ceiling()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    art = os.path.join(run_dir, "artifact.txt")
    cand = os.path.join(run_dir, "candidates.json")
    audit = os.path.join(run_dir, f"run-{stamp}.jsonl")
    queue = os.path.join(run_dir, f"queue-{stamp}.json")
    args = [PY, "run_adjudication.py", art, "--profiles", "profiles.json",
            "--candidates", cand, "--gates", gates,
            "--export-queue", queue, "--audit", audit,
            # Without this the run has no ledger and therefore no ceiling.
            "--max-cost", f"{max_cost:.2f}"]
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


def _wrap(text: str, width: int) -> list[str]:
    """Wrap for a terminal without importing textwrap for one call."""
    words, line, out = text.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > width:
            out.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        out.append(line)
    return out


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
    cap = f"{ask_ceiling():.2f}"
    _p()
    _p("-" * 68)
    # THE OPERATOR SHOULD KNOW WHAT WILL ACTUALLY BE CHECKED before being
    # asked to spend. The gate set was invisible here, and it did not include
    # the citation gates at all -- so a run could be paid for on the
    # understanding that DOIs would be verified when nothing verified them.
    from run_adjudication import night_gates
    _p(f"  checks that will run: "
       f"{', '.join(g.name for g in night_gates())}")
    _p("  citation and quote checks make free lookups to Crossref, doi.org,")
    _p("  and the pages a seat cites. No credential is sent to them.")
    # SIZE THE RUN TO THE CEILING, and say so before asking for a YES.
    #
    # With the configured caps a five-round run's worst case was $25.51, so a
    # sensible ceiling refused on the first call -- or worse, stopped the run
    # twenty minutes in with four rounds unpaid for and no answer. The
    # operator now sees what their ceiling buys and chooses.
    import json as _json

    from cost_ledger import CostLedger, plan_run
    from run_adjudication import build_ledger

    led = build_ledger(float(cap), None, None)
    if not isinstance(led, CostLedger):
        # ask_ceiling only returns a finite positive number, so this cannot
        # happen -- and a paid panel with nothing counting is the one thing
        # that must not run.
        _p("  could not build a spend ledger; not running.")
        return
    with open(os.path.join(HERE, "profiles.json"), encoding="utf-8") as fh:
        _seats = _json.load(fh)
    _seats = _seats.get("seats", _seats)
    caps = {s: (_seats[s].get("max_tokens") or 4096)
            for s in sorted(_seats)
            if not s.startswith("_") and isinstance(_seats[s], dict)}
    plan = plan_run(led, caps)
    _p(f"  5 rounds x 5 blind seats + 5 merges = {plan.calls} calls.")
    _p(f"  ceiling ${cap}   worst case ${plan.worst_case:.2f}")
    if not plan.fits:
        _p("")
        _p(f"  THIS CEILING IS TOO LOW: {plan.note}")
        _p("  Raise it, or the run stops partway with nothing to show.")
        return
    if plan.caps != caps:
        _p(f"  reply cap reduced to {max(plan.caps.values())} tokens so all "
           f"{plan.calls} calls fit.")
        _p("  Shorter answers, but the run finishes. Raise the ceiling for "
           "longer ones.")
    _p("  The ceiling is checked against an ESTIMATE of each call, because no")
    _p("  vendor publishes a guaranteed maximum for a request plus all its")
    _p("  billable output. If a call ever bills more than it was authorised")
    _p("  for, the run stops there rather than spending again.")
    _p("  Allow 30-90 minutes. Reasoning models take minutes per call and")
    _p("  the seats run one at a time; progress prints as each one answers.")
    _p(f"  folder: {os.path.relpath(out, HERE)}")
    _p("-" * 68)
    if input("  Type YES to spend: ").strip() != "YES":
        _p("  Cancelled.")
        return

    from cost_ledger import CeilingReached
    from night_loop import live_night
    try:
        # Progress prints as it happens. Without it this is thirty silent
        # model calls, which is indistinguishable from a hang -- and the
        # only way to find out is to kill the run and lose what it cost.
        res = live_night(ask_text, os.path.join(HERE, "profiles.json"), out,
                         ledger=led, on_event=_progress, caps=plan.caps)
    except CeilingReached as exc:
        _p(f"  PARTIAL -- {exc}")
        for line in led.render():
            _p(f"  {line}")
        return
    except Exception as exc:  # noqa: BLE001
        _p(f"  stopped: {type(exc).__name__}: {exc}")
        for line in led.render():
            _p(f"  {line}")
        return
    _p()
    for r in res:
        _p(f"  round {r.n}  {r.name[:34]:36} seats {len(r.thinkers_ok)}/5"
           f"  claims {r.claims:>3}  pass {r.passed:>3} fail {r.failed:>3}"
           f" blocked {r.blocked:>2}" + ("   DEGRADED" if r.degraded else "")
           + ("   CONTAMINATED" if r.closer_contaminated else ""))
    # THE VERDICT, BEFORE THE FILE PATH. The operator reads the last thing
    # printed. A run that refuted nothing must not end with a tidy "done" and
    # a path, because that reads as success.
    # TWO FIELDS, NOT ONE LABEL. The console printed "CONSENSUS is not
    # ADJUDICATION" for every non-ADJUDICATED outcome, including runs where
    # machinery HAD refuted something -- telling the operator their real
    # result was consensus.
    from night_loop import assess
    v = assess(res)
    _p()
    _p("=" * 68)
    _p(f"  MECHANICAL ADJUDICATION : {v.adjudication}")
    _p(f"  CORROBORATION CONFIDENCE: {v.confidence}")
    _p("=" * 68)
    for reason in v.reasons:
        for line in _wrap(reason, 64):
            _p(f"  {line}")
    if v.caveats:
        _p()
        _p("  CAVEATS")
        for caveat in v.caveats:
            for line in _wrap(caveat, 62):
                _p(f"    {line}")
    _p()
    if v.adjudication == "NONE":
        _p("  Nothing was removed by machinery, so the text below is what the")
        _p("  panel agreed on rather than what survived being attacked.")
    elif not v.trustworthy:
        _p("  Machinery DID remove options -- that result is real. The caveats")
        _p("  above say what it does not settle.")
    # WHAT IT COST, ON EVERY EXIT PATH.
    #
    # render() was never called here, so the console night run -- the one an
    # operator actually uses -- printed no cost at all, and never showed the
    # seats whose price has no documented maximum. A ceiling nobody can see
    # the result of is not a control the operator can act on.
    _p()
    for line in led.render():
        _p(f"  {line}")
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
            # Discovery, not two filenames. This named the original pair, so
            # the console's "Test suite" ran 561 of 909 tests and reported a
            # pass -- the four newer files, which cover the gates, the ledger,
            # the round engine and the watcher, were run by nobody here.
            sh([PY, "-m", "pytest", "-q"])
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
