"""All five rounds against the real panel, read in the order SOP 9.1 specifies.

WHY A SEPARATE ENTRY POINT AND NOT `canary_run.py --rounds 5`.

The canary answers one question -- do the seats write the contract -- and its
output is shaped for that. A full run has to be read in a particular order,
and the order is a control rather than a presentation choice. SOP 9.1 step 4:

    "Do NOT read the model outputs yet. Read the GATE RESULTS first."

with the reason given in the same section: Dell'Acqua et al. (2026) found
wrong answers from AI users were graded MORE coherent, so "reading the prose
first is how a polished error gets committed". A runner that prints the merged
answer at the top defeats that, however good the numbers underneath it are.

So this prints, in order: what the gates found, then what survived and why the
others went, then the holes, then the panel diagnostics, and only then points
at the answer on disk.

IT EXITS NON-ZERO WHILE ANY HOLE REMAINS (SOP 9.1 step 11, 9.3). One
surviving candidate with an open judgment queue is a shortlist, not an answer,
"and the exit code says so without requiring you to read anything."

COST. It plans before it spends and refuses before the first call if the plan
does not fit the ceiling. FULL_RUN_CEILING sets the bound; the default is the
configured five-round estimate.
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from convergence import analyse, render
from cost_ledger import operator_ledger, rates_from_config
from night_loop import ROUNDS, RunTooExpensive, assess, live_night

HERE = os.path.dirname(os.path.abspath(__file__))

CEILING = float(os.environ.get("FULL_RUN_CEILING", "17.00"))
"""The five-round bound. $12.68 at the floor, $16.79 as configured -- both
figures independently repriced by the outside verifier and matched."""

TOLERANCE = float(os.environ.get("FULL_RUN_TOLERANCE", "0.5"))
"""SOP 6.3 condition 2. The manual is explicit that this is the operator's own
risk appetite (8.4) and 0.5 is its worked example, not a measured value."""

_ALARM = os.environ.get("FULL_RUN_SINGLETON_ALARM", "").strip()
SINGLETON_ALARM: float | None = float(_ALARM) if _ALARM else None
"""SOP 8.4: "Set your singleton-fraction alarm. Until you do, that check is
NOT ARMED." Unset by default, and an unarmed condition in the stop rule's
conjunction cannot be satisfied. That is the fail-closed reading and it is
deliberate: nobody has calibrated this for this panel yet."""

ASK_FILE = os.environ.get("FULL_RUN_ASK", "").strip()

DEFAULT_ASK = (
    "We run a five-seat AI adjudication panel. Each round costs about six API "
    "calls across five vendors. Should the panel always run all five rounds, "
    "or stop early at the first round that eliminates nothing? Give the "
    "options and what would decide between them."
)


def _ask() -> str:
    if not ASK_FILE:
        return DEFAULT_ASK
    with open(ASK_FILE, encoding="utf-8") as fh:
        return fh.read().strip()


def main() -> int:
    ask = _ask()
    with open(os.path.join(HERE, "rates.json"), encoding="utf-8") as fh:
        rates = rates_from_config(json.load(fh))
    ledger = operator_ledger(rates, per_run=CEILING)
    print(f"  daily ceiling ${ledger.per_day:.2f} across ALL tools")

    out = os.path.join(HERE, "runs", f"full-{time.strftime('%Y%m%d-%H%M%S')}")
    print(f"  five rounds, ceiling ${CEILING:.2f}")
    print(f"  output: {out}")

    t0 = time.time()
    try:
        results = live_night(
            ask, os.path.join(HERE, "profiles.json"), out, ledger=ledger,
            on_event=lambda m: print(f"  {m}", flush=True))
    except RunTooExpensive as exc:
        print(f"\n  REFUSED BEFORE SPENDING ANYTHING: {exc}")
        return 2
    print(f"\n  wall clock: {time.time() - t0:.0f}s")
    print("\n".join(ledger.render()))

    if not results:
        print("\n  no round completed.")
        return 1

    # ---- SOP 9.1 step 4: THE GATE RESULTS, BEFORE ANY PROSE ---------------
    print("\n" + "=" * 72)
    print("1. WHAT THE GATES FOUND  (SOP 9.1 step 4 -- read this before the answer)")
    print("=" * 72)
    for r in results:
        kind = "eliminative" if r.eliminative else "CALIBRATION (removes nothing)"
        print(f"  Round {r.n}  {r.name}  [{kind}]")
        print(f"    claims {r.claims}: {r.passed} pass, {r.failed} fail, "
              f"{r.blocked} blocked, {r.escalated} escalated")
        print(f"    challenges {r.challenges} ({r.challenges_ruled} naming a "
              f"commitment that exists)")
        if r.options_removed:
            print(f"    REMOVED {len(r.options_removed)}: "
                  f"{', '.join(r.options_removed)}")
        for f in r.calibration_findings:
            print(f"    REFUTED BUT NOT REMOVED (SOP 2.3): {f}")
        if r.thinkers_failed:
            for sid, why in sorted(r.thinkers_failed.items()):
                print(f"    seat failed -- {sid}: {why}")

    # ---- SOP 9.1 step 5: what survived, and why the rest went -------------
    verdict = assess(results)
    print("\n" + "=" * 72)
    print("2. THE ANSWER  (SOP 9.1 step 5)")
    print("=" * 72)
    print(f"  {verdict.headline}")
    for line in verdict.reasons:
        print(f"    - {line}")
    if verdict.caveats:
        print("\n  CAVEATS:")
        for line in verdict.caveats:
            print(f"    - {line}")

    # ---- SOP 9.1 steps 6, 9, 10 and 6.2/6.3/6.5 ---------------------------
    conv = analyse(results, tolerance=TOLERANCE,
                   singleton_alarm=SINGLETON_ALARM,
                   rounds_specified=len(ROUNDS))
    print("\n" + "=" * 72)
    print("3. CONVERGENCE, DIVERGENCE AND THE HOLES  (SOP 6.2, 6.3, 6.5, 9.3)")
    print("=" * 72)
    for line in render(conv):
        print(f"  {line}" if line else "")

    # ---- SOP 9.1 step 11 --------------------------------------------------
    print("\n" + "=" * 72)
    print("4. MAY THIS BE COMMITTED?  (SOP 9.1 step 11)")
    print("=" * 72)
    resolved = conv.stop and verdict.trustworthy
    if resolved:
        print("  YES -- one candidate survives, every stop condition holds, "
              "and no hole remains.")
    else:
        print("  NO. SOP 9.3: an answer is resolved only when one candidate "
              "survives AND no hole remains. Both halves.")
        if not verdict.trustworthy:
            print("    - the run's own verdict does not support it")
        if conv.blockers:
            print(f"    - {len(conv.blockers)} stop condition(s) unmet")
        if conv.holes:
            print(f"    - {len(conv.holes)} hole(s) open")

    # THE NEXT STEP, NAMED, WITH THE COMMAND. SOP 9.1 step 7 is "work your
    # escalation queue" and step 8 folds it back in; until today neither was
    # reachable, and a run that ends by listing holes without saying how to
    # close the biggest one leaves the operator to reinvent the route.
    if conv.holes or conv.blockers:
        print("\n" + "=" * 72)
        print("5. WHAT TO DO NEXT  (SOP 9.1 steps 7-8)")
        print("=" * 72)
        print("  Work the judgment queue. It is the largest hole above, it is")
        print("  what makes rho measurable, and SOP 6.3 cannot be satisfied")
        print("  while any item is open:")
        print(f"\n    .venv/bin/python judgment_queue.py --open {out}")
        print("    (fill in queue.json in a text editor, then)")
        print(f"    .venv/bin/python judgment_queue.py --apply {out}")

    print(f"\n  full record:     {out}")
    print(f"  verifier packet: {os.path.join(out, 'VERIFIER-PACKET.md')}")
    return 0 if resolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
