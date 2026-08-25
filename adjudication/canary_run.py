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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adjudication_orchestrator import Orchestrator
from cost_ledger import CostLedger, rates_from_config
from night_loop import ROUNDS, run_night
from run_adjudication import live_seats, load_env_file, night_gates

ASK = (
    "We run a five-seat AI adjudication panel. Each round costs about six API "
    "calls across five vendors. Should the panel always run all five rounds, "
    "or stop early at the first round that eliminates nothing? Give the "
    "options and what would decide between them."
)

CEILING = 3.00
ROUNDS_TO_RUN = 2

def main() -> int:
    import json
    print(load_env_file())
    with open("rates.json", encoding="utf-8") as fh:
        rates = rates_from_config(json.load(fh))
    ledger = CostLedger(rates=rates, per_run=CEILING)

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
    print(f"  plan: {plan.calls} calls, worst case ${plan.worst_case:.2f}, "
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
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
