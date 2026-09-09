"""Measure rho: the one number this panel has never had.

WHAT HAS BEEN MISSING, IN EVERY RUN, SINCE THE FIRST ONE. night_loop's own
measure_rho refuses to report a correlation and says exactly why:

    "Measuring it needs a seeded set of propositions with known truth that
     every seat must decide."

Error correlation needs a per-SEAT correctness vector -- for each item, was
THIS seat right or wrong. A gate verdict is per-CLAIM: it says the claim held,
not that a seat was right. And seats answer open-ended, so a seat that never
raised a claim has not been shown right or wrong about it. That is missing
data, and averaging over it manufactures agreement nobody observed.

So every run reported CORROBORATION CONFIDENCE: UNMEASURED, effective seat
count undefined, and the convergence hole permanently open. Not a bug -- the
input did not exist.

IT EXISTS NOW. eval/seeded-defects.json carries thirty seeded defects with
known ground truth, imported from the operator's earlier elimination-protocol
work. Every seat can be REQUIRED to decide each one, which is the whole
condition measure_rho names.

TWO THINGS THIS DOES THAT THE EVAL SET ALONE DOES NOT.

CONTROLS. Every case in that file contains a defect, so ground truth is always
"yes, there is an error" -- and a seat that answers yes to everything scores
100% while detecting nothing. Each seeded item is paired here with the SAME
statement arithmetically corrected, where the truth is "no error". The
corrections are computed, not invented: 65 x 1800 x 3 is 351,000 whether or
not anyone likes it.

ARITHMETIC ONLY. Of the five categories, only arithmetic_error can be scored
without a model judging, and a model grading a model reintroduces exactly the
correlated error this measurement exists to quantify. A5 is excluded even from
that: it is an insurance-requirement reading, not a calculation.
"""
from __future__ import annotations

import os
import re
import sys
import time
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))

from adjudication_orchestrator import undecorate_marker_line  # noqa: E402

ANSWER = re.compile(r"(?mi)^\s*ANSWER\s*[:|]\s*(?P<v>yes|no)\b")

CONTRACT = (
    "Below is a statement from a working document. Decide ONE thing: does it "
    "contain an arithmetic error?\n\n"
    "Check the calculation yourself. Then end your reply with exactly one "
    "line:\n\n"
    "ANSWER: yes      (if the arithmetic is wrong)\n"
    "ANSWER: no       (if the arithmetic is correct)\n\n"
    "Answer only about the ARITHMETIC. Not whether the framing is wise, not "
    "whether the figures are the right ones to use -- only whether the "
    "computation shown produces the number shown.\n\n"
    "STATEMENT:\n")


@dataclass(frozen=True)
class Item:
    """One proposition every seat must decide, with its known truth."""

    id: str
    statement: str
    has_error: bool
    why: str


# The five arithmetic cases whose seeds were verified by recomputation, each
# paired with the same statement corrected. Every figure below was computed,
# not transcribed from belief.
ITEMS: tuple[Item, ...] = (
    Item("A1", "Bid at $65/hr, 1,800 hrs/yr, 3 estimators. "
         "Revenue = 65 x 1800 x 3 = $315,000.", True,
         "65 x 1800 x 3 = 351,000; digits transposed"),
    Item("A1c", "Bid at $65/hr, 1,800 hrs/yr, 3 estimators. "
         "Revenue = 65 x 1800 x 3 = $351,000.", False, "correct"),

    Item("A2", "Gross margin: revenue $351,000, cost $246,000. "
         "Margin = (351000-246000)/246000 = 42.7%.", True,
         "margin divides by revenue: 105000/351000 = 29.9%"),
    Item("A2c", "Gross margin: revenue $351,000, cost $246,000. "
         "Margin = (351000-246000)/351000 = 29.9%.", False, "correct"),

    Item("A3", "SBA 504: $850,000 property, 10% down. Down payment $85,000. "
         "Loan = 850,000 - 85,000 = $775,000.", True,
         "850,000 - 85,000 = 765,000"),
    Item("A3c", "SBA 504: $850,000 property, 10% down. Down payment $85,000. "
         "Loan = 850,000 - 85,000 = $765,000.", False, "correct"),

    Item("A4", "Contract $677,957 over 36 months. Monthly = $18,832. "
         "Three-year total = 18,832 x 36 = $677,952, so we have $5 "
         "unallocated.", True,
         "monthly is 18,832.14; the $5 is a rounding artifact, not a variance"),
    Item("A4c", "Contract $677,957 over 36 months. Monthly = $18,832.14. "
         "Three-year total = 18,832.14 x 36 = $677,957.04, which rounds to "
         "the contract value.", False, "correct"),

    Item("A6", "Probe rule: hold rate 0.60 over 10 probes. Expected failures "
         "= 10 x 0.60 = 6, so 3 failures is below expectation.", True,
         "complement inverted: expected failures = 10 x 0.40 = 4"),
    Item("A6c", "Probe rule: hold rate 0.60 over 10 probes. Expected failures "
         "= 10 x 0.40 = 4, so 3 failures is below expectation.", False,
         "correct"),
)


def decide(reply: str) -> bool | None:
    """The seat's verdict, or None when it did not answer in the shape asked.

    None is NOT wrong. A seat that did not answer has not been shown right or
    wrong, and scoring it as an error is exactly the missing-data mistake that
    makes a fabricated correlation.
    """
    # UNDECORATED FIRST, THE WAY EVERY OTHER PARSER HERE READS A MARKER.
    #
    # This pattern anchors at the start of a line, and a model writes
    # "**ANSWER: yes**" or "- ANSWER: yes" for a line it thinks of as its
    # verdict. Seven of eight shapes measured returned None.
    #
    # None is handled correctly -- matrix() drops any item not every seat
    # decided, so a lost answer never becomes a wrong answer and rho is not
    # inflated by it. What it does instead is quieter: it SHRINKS the sample,
    # and it shrinks it toward the items where all five seats happened to
    # write bare. A correlation over nine items is already thin; measuring it
    # on a subset selected by formatting is worse, and nothing in the output
    # would show why the count fell.
    text = "\n".join(undecorate_marker_line(ln)
                     for ln in (reply or "").splitlines())
    m = ANSWER.search(text)
    return None if m is None else m.group("v").lower() == "yes"


@dataclass
class Measurement:
    seats: list[str] = field(default_factory=list)
    items: list[str] = field(default_factory=list)
    correct: dict[str, dict[str, bool | None]] = field(default_factory=dict)
    """seat -> item -> correct / wrong / did not answer."""
    dollars: float = 0.0

    def matrix(self) -> tuple[list[str], list[str], list[list[int]]]:
        """Items x seats of 1/0, over items EVERY seat decided.

        Only common items. A seat that skipped one has not been observed on
        it, and filling that cell either way invents a correlation -- the same
        reason measure_rho refuses to score silence.
        """
        common = [i for i in self.items
                  if all(self.correct.get(s, {}).get(i) is not None
                         for s in self.seats)]
        X = [[1 if self.correct[s][i] else 0 for s in self.seats]
             for i in common]
        return common, self.seats, X


def render(m: Measurement) -> list[str]:
    """rho, effective seats, and what they are worth -- or why neither exists."""
    import numpy as np

    from seat_independence import (
        confidence_ceiling,
        effective_seats,
        mean_error_correlation,
    )

    common, seats, X = m.matrix()
    out = ["=" * 72,
           "SEEDED-TRUTH MEASUREMENT -- do these seats fail together?",
           "=" * 72,
           f"  items put to every seat: {len(m.items)}"
           f"   ({sum(1 for i in ITEMS if i.has_error)} seeded defects, "
           f"{sum(1 for i in ITEMS if not i.has_error)} controls)",
           f"  seats: {', '.join(seats)}",
           f"  items EVERY seat decided: {len(common)}",
           f"  spent: ${m.dollars:.2f}",
           ""]

    out.append("  per seat, on the items all decided:")
    for j, s in enumerate(seats):
        got = sum(row[j] for row in X)
        out.append(f"    {s:10} {got}/{len(common)} correct")
    out.append("")

    MIN = 5
    if len(seats) < 2 or len(common) < MIN:
        out += [f"  RHO: NOT MEASURABLE. Needs two seats and at least {MIN} "
                f"items every seat decided; this has {len(seats)} and "
                f"{len(common)}.",
                "  A correlation over three items is noise wearing four "
                "decimal places, and it would set a confidence ceiling a "
                "reader acts on.", ""]
        return out

    rho = float(mean_error_correlation(np.array(X, dtype=int)))
    n_eff = float(effective_seats(len(seats), rho))
    ceiling = confidence_ceiling(len(seats), rho)
    out += [f"  MEASURED ERROR CORRELATION   rho = {rho:+.4f}",
            f"  EFFECTIVE SEATS              {n_eff:.2f} of {len(seats)}",
            f"  CONFIDENCE CEILING           {ceiling}",
            ""]
    if rho >= 0.8:
        out += ["  THESE SEATS FAIL TOGETHER. Agreement between them is one",
                "  confirmation repeated, not five. SOP 6.1: at this "
                "correlation",
                "  the panel is worth about one seat and the money buys "
                "nothing",
                "  a single model would not give you.", ""]
    elif rho >= 0.2:
        out += ["  PARTIALLY CORRELATED. SOP 6.7's table prices this: five "
                "seats",
                "  are justified only at rho at or below roughly 0.2. Above "
                "it you",
                "  are paying five times for well under twice the capacity.", ""]
    else:
        out += ["  THESE SEATS FAIL DIFFERENTLY on this task class, which is "
                "the",
                "  regime the five-seat design was built for.", ""]
    out += ["  WHAT THIS IS NOT. It is a correlation on ARITHMETIC "
            "detection, on",
            f"  {len(common)} items. It does not transfer to citation "
            "checking, to",
            "  regulatory reading, or to open questions with no key -- SOP "
            "10.1",
            "  gives leave-one-domain-out R-squared of -2.09 for exactly this",
            "  kind of transfer. It is one number about one task class, which "
            "is",
            "  one more than this panel has ever had.", ""]
    return out


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------

CEILING = float(os.environ.get("SEEDED_RHO_CEILING", "6.00"))
CAP = int(os.environ.get("SEEDED_RHO_CAP", "2048"))


def main() -> int:
    import json as _json

    from cost_ledger import operator_ledger, rates_from_config
    from run_adjudication import live_seats, load_env_file

    print(load_env_file())
    with open(os.path.join(HERE, "rates.json"), encoding="utf-8") as fh:
        rates_cfg = _json.load(fh)
    ledger = operator_ledger(rates_from_config(rates_cfg), per_run=CEILING)
    print(f"  daily ceiling ${ledger.per_day:.2f} across ALL tools")

    from cost_ledger import check_models_are_priced
    from night_loop import panel_identity
    identity = panel_identity(os.path.join(HERE, "profiles.json"))
    check_models_are_priced(identity, rates_cfg)

    seats = live_seats(os.path.join(HERE, "profiles.json"), ledger=ledger)
    for s in seats.values():
        if hasattr(s, "max_tokens"):
            s.max_tokens = CAP
        if hasattr(s, "set_pass"):
            s.set_pass("seeded-rho")

    m = Measurement(seats=sorted(seats), items=[i.id for i in ITEMS])
    print(f"  {len(ITEMS)} items x {len(seats)} seats = "
          f"{len(ITEMS) * len(seats)} calls, ceiling ${CEILING:.2f}")

    t0 = time.time()
    for item in ITEMS:
        line = []
        for seat_id in m.seats:
            try:
                reply = seats[seat_id](CONTRACT + item.statement)
                said = decide(reply)
            except Exception as exc:              # noqa: BLE001
                said = None
                line.append(f"{seat_id}:ERR")
                print(f"    {item.id} {seat_id}: {type(exc).__name__}",
                      flush=True)
            m.correct.setdefault(seat_id, {})[item.id] = (
                None if said is None else said == item.has_error)
            if said is not None:
                line.append(f"{seat_id}:{'OK' if said == item.has_error else 'X'}")
        print(f"  {item.id:5} truth={'error' if item.has_error else 'clean':5} "
              f"{'  '.join(line)}", flush=True)

    m.dollars = float(getattr(ledger, "spent", 0.0))
    print(f"\n  wall clock: {time.time() - t0:.0f}s")
    print("\n".join(ledger.render()))

    lines = render(m)
    print()
    print("\n".join(lines))

    out = os.path.join(HERE, "runs", f"rho-{time.strftime('%Y%m%d-%H%M%S')}")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "rho.md"), "w", encoding="utf-8") as fh:
        fh.write("# Seeded-truth rho\n\n```\n" + "\n".join(lines) + "\n```\n")
    with open(os.path.join(out, "rho.json"), "w", encoding="utf-8") as fh:
        _json.dump({"seats": m.seats, "items": m.items,
                    "correct": m.correct, "dollars": m.dollars}, fh, indent=2)
    print(f"  written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
