"""One paid round against the real panel, to see whether the seats cooperate.

WHAT THIS TESTS that a dry run cannot: whether five real models, given the
claim contract, actually emit claim lines a gate can rule on -- with warrants
in the documented shape and option ids where they belong. If they do not, the
five-round run would spend an hour producing an escalation queue, and this
finds that out for a few cents.
"""
import os
import sys
import time
from collections.abc import Sequence

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adjudication_orchestrator import Orchestrator
from cost_ledger import operator_ledger, rates_from_config
from night_loop import ROUNDS, RoundResult, run_night
from run_adjudication import live_seats, load_env_file, night_gates

ASK = (
    "We run a five-seat AI adjudication panel. Each round costs about six API "
    "calls across five vendors. Should the panel always run all five rounds, "
    "or stop early at the first round that eliminates nothing? Give the "
    "options and what would decide between them."
)

CEILING = float(__import__("os").environ.get("CANARY_CEILING", "3.50"))
ROUNDS_TO_RUN = int(__import__("os").environ.get("CANARY_ROUNDS", "1"))
"""ONE ROUND, BECAUSE ONE ROUND ANSWERS THE QUESTION.

Round one is where seats propose answers and declare what decides them. If
they will not write a PREDICATE, a FORMULA and its INPUTS there, no later
round can do anything -- later rounds only remove, and removal is now entirely
a matter of recomputing what an option committed to. A second round would cost
more and tell us nothing we did not already know after the first.
"""

def main() -> int:
    import json
    print(load_env_file())
    with open("rates.json", encoding="utf-8") as fh:
        rates = rates_from_config(json.load(fh))
    ledger = operator_ledger(rates, per_run=CEILING)

    seats = live_seats("profiles.json", ledger=ledger)

    # A ROUND-ONE PROPOSAL DOES NOT NEED 16,000 OUTPUT TOKENS, and the
    # pre-call bound is 5x the cap, so leaving the configured caps in place
    # makes one seat's worst case $2.06 and a five-round run's $25.51. The
    # ceiling correctly refused to start. For a smoke test, cap the reply at
    # a size that still fits two to four options and their claims.
    # Size the caps to the ceiling, the same way the console now does.
    from cost_ledger import plan_run
    with open("profiles.json", encoding="utf-8") as fh:
        profiles = json.load(fh)
    raw = profiles.get("seats", profiles)
    caps = {s: (raw[s].get("max_tokens") or 4096)
            for s in sorted(raw)
            if not s.startswith("_") and isinstance(raw[s], dict)}
    plan = plan_run(ledger, caps, rounds=ROUNDS_TO_RUN)
    print(f"  plan: {plan.calls} calls, estimated ${plan.estimate:.2f}, "
          f"fits={plan.fits}")
    print(f"        {plan.note}")
    if not plan.fits:
        return 2
    for seat_id, cap in plan.caps.items():
        seat = seats.get(seat_id)
        if seat is not None and hasattr(seat, "max_tokens"):
            seat.max_tokens = int(cap)

    closer = seats["seat_5"]
    orch = Orchestrator(night_gates())

    out = os.path.join("runs", f"canary-{time.strftime('%Y%m%d-%H%M%S')}")
    t0 = time.time()
    results = run_night(ASK, seats, closer, orch, out,
                        rounds=ROUNDS[:ROUNDS_TO_RUN],
                        on_event=lambda m: print(f"  {m}", flush=True))
    print(f"\n  wall clock: {time.time() - t0:.0f}s")
    print("\n".join(ledger.render()))
    _report_compliance(out, results)
    return 0 if results else 1


def _report_compliance(out_dir: str,
                       results: "Sequence[RoundResult]") -> None:
    """Did the seats write what the contract asked for? Per seat, by name.

    THE ONE THING NO OFFLINE TEST CAN ESTABLISH. The whole design now rests on
    seats declaring a figure, the formula that produces it, and the numbers
    going in. That contract sits in the block seats demonstrably obey for
    CLAIM lines, which is an inference from one observation rather than a
    measurement. This is the measurement.
    """
    import glob
    import re

    print("\n" + "=" * 68)
    print("CONTRACT COMPLIANCE -- what each seat actually wrote")
    print("=" * 68)
    counts = {}
    for path in sorted(glob.glob(os.path.join(out_dir, "round-1",
                                              "thinker-*.md"))):
        seat = os.path.basename(path)[len("thinker-"):-len(".md")]
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        # UNDECORATED FIRST, THE WAY THE ENGINE READS IT. Anchored at the
        # start of the raw line, a seat that wrote "- OPTION | ..." or
        # "**PREDICATE | ...**" counted as zero on every column -- so this
        # measurement, the one thing no offline test can establish, would
        # have reported perfect compliance as total silence.
        from adjudication_orchestrator import undecorate_marker_line
        flat = "\n".join(undecorate_marker_line(ln)
                         for ln in text.splitlines())
        counts[seat] = {
            kind: len(re.findall(rf"(?mi)^\s*{kind}\s*\|", flat))
            for kind in ("OPTION", "PREDICATE", "FORMULA", "INPUT", "CLAIM")
        }
        counts[seat]["chars"] = len(text)
    if not counts:
        print("  no thinker replies were written at all.")
        return
    print(f"  {'seat':10} {'OPTION':>7} {'PREDICATE':>10} {'FORMULA':>8} "
          f"{'INPUT':>6} {'CLAIM':>6}   chars")
    for seat, c in sorted(counts.items()):
        print(f"  {seat:10} {c['OPTION']:>7} {c['PREDICATE']:>10} "
              f"{c['FORMULA']:>8} {c['INPUT']:>6} {c['CLAIM']:>6} "
              f"  {c['chars']:>6}")

    declaring = sum(1 for c in counts.values()
                    if c["OPTION"] and c["PREDICATE"] and c["FORMULA"])
    print(f"\n  seats that declared a checkable commitment: "
          f"{declaring}/{len(counts)}")
    if results:
        r = results[0]
        print(f"  options parsed: {r.options_created}   "
              f"removed: {len(r.options_removed)}   "
              f"untested: {len(r.options_unexamined)}")
        if r.silent_seats:
            print(f"  seats that declared no option: "
                  f"{', '.join(r.silent_seats)}")
    print()
    if declaring == 0:
        print("  VERDICT: the contract is not being followed. Text prompting")
        print("  is not enough, and the next move is the vendors' own")
        print("  structured-output modes rather than more prompt wording.")
    elif declaring < len(counts):
        print("  VERDICT: partial. Some seats comply and some do not, which")
        print("  is the worst case for a text contract -- the panel silently")
        print("  runs short. Structured output would make it uniform.")
    else:
        print("  VERDICT: every seat followed the contract. The design holds")
        print("  as written; structured output becomes an optimisation.")


if __name__ == "__main__":
    raise SystemExit(main())
