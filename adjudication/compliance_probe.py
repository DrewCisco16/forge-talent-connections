"""Do the five seats actually write the contract they are given?

THE ONE QUESTION NO OFFLINE TEST CAN ANSWER, and the one the whole design now
rests on. An option is removed when its own formula, with its own inputs,
fails to produce its own figure. That requires seats to write:

    OPTION | ...
    PREDICATE | <quantity> | = | <value and unit>
    FORMULA | <expression in named variables>
    INPUT | <name> = <number>

No live seat has ever been asked for those lines. The contract sits in the
same required-output block seats demonstrably obey for CLAIM lines, which is
an inference from one observation, not a measurement.

WHY THIS AND NOT THE FULL CANARY. The canary runs a whole round: five
thinkers, a merge, gates, elimination, a packet. Its floor is $2.54, almost
all of it the merging seat, which reads every reply in full and needs a
16,384-token cap to produce anything.

None of that bears on the question. The merge cannot be tested until the
seats comply, and if they do not comply there is nothing to merge. So this
calls the five thinkers with the real round-one prompt, reads what comes
back, and stops. It is the smallest thing that decides.

It writes no run directory, touches no daily spend file, and runs one round
of five calls.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cost_ledger import CostLedger, plan_run, rates_from_config
from night_loop import PERSONAS, ROUNDS, thinker_prompt
from run_adjudication import live_seats, load_env_file

ASK = (
    "We run a five-seat AI adjudication panel. Each round costs about six API "
    "calls across five vendors. Should the panel always run all five rounds, "
    "or stop early at the first round that eliminates nothing? Give the "
    "options and what would decide between them."
)

CEILING = float(os.environ.get("PROBE_CEILING", "2.50"))
"""A hard bound on this probe. It calls five seats once each and nothing else.

RAISED FROM $1.50 AFTER THE FIRST RUN. One seat billed 1.6x what it was
authorised, the overrun halt fired correctly, and three seats were never
called -- so two thirds of the measurement was lost to a ceiling set for a
cheaper answer than the vendors actually give.
"""

CAP = int(os.environ.get("PROBE_CAP", "4096"))
"""Output cap per seat.

RAISED FROM 2048 AFTER THE FIRST RUN, AND THIS IS A FINDING. At 2,048 tokens
seat_1 returned ZERO characters: it is a reasoning model, the thinking counts
against the cap, and it spent the whole budget before writing anything.

MIN_USEFUL_CAP in cost_ledger.py is 2048 and calls itself the smallest cap
worth sending to a reasoning model. That is now measured to be false for at
least one seat on this panel.
"""

ONLY = [s for s in os.environ.get("PROBE_SEATS", "").split(",") if s]
"""Seats to call, empty for all. Set PROBE_SEATS to avoid paying twice for a
seat already measured."""

WANTED = ("OPTION", "PREDICATE", "FORMULA", "INPUT", "CLAIM")


def main() -> int:
    print(load_env_file())
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "rates.json"), encoding="utf-8") as fh:
        rates = rates_from_config(json.load(fh))

    # No day_state_path: a probe must not consume the operator's daily budget.
    ledger = CostLedger(rates=rates, per_run=CEILING)
    seats = live_seats(os.path.join(here, "profiles.json"), ledger=ledger)

    caps = dict.fromkeys(sorted(seats), CAP)
    plan = plan_run(ledger, caps, rounds=1, ask_chars=len(ASK))
    # plan_run costs a full round including the merge. This probe makes only
    # the five thinker calls, so its real bound is well under that figure --
    # but the ledger enforces per call regardless, which is what matters.
    print(f"  ceiling ${CEILING:.2f}, cap {CAP} tokens/seat, "
          f"5 calls (no merge)")
    print(f"  a full round would have been ${plan.estimate:.2f}; this is the "
          f"thinkers only")

    for seat in seats.values():
        if hasattr(seat, "max_tokens"):
            seat.max_tokens = CAP
        if hasattr(seat, "set_pass"):
            seat.set_pass("probe")

    prompts = {
        seat_id: thinker_prompt(ROUNDS[0], ASK, None,
                                persona=PERSONAS[i % len(PERSONAS)])
        for i, seat_id in enumerate(sorted(seats))
    }

    wanted = [s for s in sorted(seats) if not ONLY or s in ONLY]
    print(f"  calling: {', '.join(wanted)}")
    replies: dict[str, str] = {}
    failures: dict[str, str] = {}
    for seat_id in wanted:
        t0 = time.time()
        try:
            replies[seat_id] = seats[seat_id](prompts[seat_id])
            print(f"  {seat_id}: {len(replies[seat_id])} chars in "
                  f"{time.time() - t0:.0f}s", flush=True)
        except Exception as exc:  # noqa: BLE001 - one seat must not stop the rest
            failures[seat_id] = f"{type(exc).__name__}: {exc}"
            print(f"  {seat_id}: FAILED after {time.time() - t0:.0f}s -- "
                  f"{failures[seat_id]}", flush=True)

    print("\n" + "\n".join(ledger.render()))
    _report(replies, failures, here)
    return 0 if replies else 1


def _report(replies: dict[str, str], failures: dict[str, str],
            here: str) -> None:
    print("\n" + "=" * 70)
    print("CONTRACT COMPLIANCE -- what each seat actually wrote")
    print("=" * 70)
    if not replies:
        print("  no seat answered. Nothing was measured.")
        for seat_id, why in sorted(failures.items()):
            print(f"    {seat_id}: {why}")
        return

    counts = {
        seat_id: {kind: len(re.findall(rf"(?mi)^\s*{kind}\s*\|", text))
                  for kind in WANTED}
        for seat_id, text in replies.items()
    }
    head = "  {:10}" + " {:>9}" * len(WANTED)
    print(head.format("seat", *WANTED))
    for seat_id in sorted(counts):
        row = counts[seat_id]
        print(head.format(seat_id, *(str(row[k]) for k in WANTED)))

    complete = [s for s, c in counts.items()
                if c["OPTION"] and c["PREDICATE"] and c["FORMULA"]]
    partial = [s for s, c in counts.items()
               if s not in complete and (c["OPTION"] or c["PREDICATE"])]
    silent = [s for s in counts if s not in complete and s not in partial]

    print(f"\n  fully compliant: {len(complete)}/{len(counts)}"
          + (f"  ({', '.join(sorted(complete))})" if complete else ""))
    if partial:
        print(f"  partial:         {', '.join(sorted(partial))}")
    if silent:
        print(f"  nothing usable:  {', '.join(sorted(silent))}")
    if failures:
        print(f"  call failed:     {', '.join(sorted(failures))}")

    # What the parser makes of it, which is the fact that actually matters.
    from option_set import parse_proposals, silent_seats
    from predicate import adjudicate

    try:
        pool = parse_proposals(replies)
    except Exception as exc:  # noqa: BLE001
        print(f"\n  the parser refused this pool: {exc}")
        pool = []
    preds = [pr for o in pool for pr in o.predicates]
    rulings = adjudicate(preds, [])
    ruled = sum(1 for r in rulings.values() if r.status in ("pass", "fail"))
    print(f"\n  options parsed:        {len(pool)}")
    print(f"  commitments declared:  {len(preds)}")
    print(f"  commitments ruled:     {ruled} "
          f"({sum(1 for r in rulings.values() if r.status == 'fail')} refuted)")
    if pool and silent_seats():
        print(f"  seats declaring none:  {', '.join(silent_seats())}")

    out = os.path.join(here, "runs", f"probe-{time.strftime('%Y%m%d-%H%M%S')}")
    os.makedirs(out, exist_ok=True)
    for seat_id, text in replies.items():
        with open(os.path.join(out, f"{seat_id}.md"), "w",
                  encoding="utf-8") as fh:
            fh.write(text)
    print(f"\n  replies saved to {out}")

    print()
    if not preds:
        print("  VERDICT: NO seat declared a checkable commitment. Text")
        print("  prompting is not enough. The next move is each vendor's own")
        print("  structured-output mode -- OpenAI json_schema, Gemini")
        print("  responseSchema, Anthropic tool use -- which makes the shape")
        print("  a provider-enforced guarantee instead of a request.")
    elif len(complete) < len(counts):
        print("  VERDICT: PARTIAL, which is the worst case for a text")
        print("  contract. The panel silently runs short: the seats that")
        print("  comply carry the adjudication and the rest are dead weight,")
        print("  and nothing in the output says which is which. Structured")
        print("  output would make it uniform.")
    else:
        print("  VERDICT: every seat wrote the contract. The design holds as")
        print("  written, and structured output becomes an optimisation")
        print("  rather than a rescue.")


if __name__ == "__main__":
    raise SystemExit(main())
