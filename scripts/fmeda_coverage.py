#!/usr/bin/env python3
"""
fmeda_coverage.py
=================
Computes the FMEA ranking and the diagnostic-coverage figure from
agents/analysis/failure-register.json.

WHY THIS IS A SCRIPT AND NOT A PARAGRAPH. Every number this system reports has
to be reproducible from data, with the arithmetic shown. A coverage figure typed
into a document is an assertion; a coverage figure computed from a register you
can open and argue with is a measurement. Re-run it after editing the register
and the number moves with it.

WHAT THIS IS NOT. It is NOT an IEC 61508 FMEDA. A real FMEDA needs a failure
rate (lambda) per component, in FIT, from field data or a reliability handbook,
and uses those to compute Safe Failure Fraction and PFH. No such failure-rate
data exists for LLM agents -- not here, and not in any published source this
session could reach. Any lambda in this file would be invented, so there is
none, and no SFF or PFH is produced.

What IS computed is the structural half of an FMEDA: every failure mode is
classified safe/dangerous and detected/undetected, and diagnostic coverage is
reported as a COUNT over the register -- what fraction of dangerous failure
modes have a detection control behind them, and what fraction of those controls
are code that blocks rather than prose someone has to remember.

On RPN. S, O and D are ordinal judgement scales. Their product has no units and
is not a probability. It is used here only to SORT, which is the one thing it
can honestly do.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REGISTER = "agents/analysis/failure-register.json"
RUNG = {1: "GATE (blocks, tested)", 2: "TEST (declared, unrun)", 3: "PROSE (human memory)"}


def load(root: Path) -> list[dict]:
    data = json.loads((root / REGISTER).read_text())
    return [m for m in data["modes"]]


def rpn(m: dict) -> int:
    return m["S"] * m["O"] * m["D"]


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    modes = load(root)
    n = len(modes)

    print("=" * 78)
    print("FMEA RANKING  --  RPN is a SORT KEY, not a risk quantity")
    print("=" * 78)
    print(f"{'ID':<7}{'RPN':>5}  {'S':>2}{'O':>3}{'D':>3}  {'RUNG':<22}ITEM / MODE")
    for m in sorted(modes, key=rpn, reverse=True):
        print(f"{m['id']:<7}{rpn(m):>5}  {m['S']:>2}{m['O']:>3}{m['D']:>3}  "
              f"{RUNG[m['rung']]:<22}{m['item']} / {m['mode'][:44]}")

    dangerous = [m for m in modes if m["class"] == "dangerous"]
    safe = [m for m in modes if m["class"] == "safe"]
    dd = [m for m in dangerous if m["detected"]]
    du = [m for m in dangerous if not m["detected"]]
    gated = [m for m in modes if m["rung"] == 1]
    d_gated = [m for m in dangerous if m["rung"] == 1]

    print()
    print("=" * 78)
    print("FMEDA-ADAPTED CLASSIFICATION  --  counts over this register, no lambda")
    print("=" * 78)
    print(f"  total failure modes ................. {n}")
    print(f"  dangerous .......................... {len(dangerous)}")
    print(f"  safe ............................... {len(safe)}")
    print()
    print(f"  dangerous DETECTED (DD) ............ {len(dd)}")
    print(f"  dangerous UNDETECTED (DU) .......... {len(du)}")
    print()
    print("  Diagnostic coverage (structural), shown:")
    print(f"    DC = DD / (DD + DU) = {len(dd)} / ({len(dd)} + {len(du)})"
          f" = {len(dd)}/{len(dangerous)} = {len(dd)/len(dangerous):.3f}")
    print()
    print("  Coverage by CODE rather than by memory, shown:")
    print(f"    gated_dangerous / dangerous = {len(d_gated)} / {len(dangerous)}"
          f" = {len(d_gated)/len(dangerous):.3f}")
    print(f"    gated_all / all             = {len(gated)} / {n}"
          f" = {len(gated)/n:.3f}")
    print()
    print("  UNDETECTED DANGEROUS MODES -- the list that matters:")
    for m in sorted(du, key=rpn, reverse=True):
        print(f"    {m['id']}  RPN {rpn(m):>4}  {m['item']}: {m['mode']}")
        print(f"             control: {m['control']}")

    print()
    print("  RUNG DISTRIBUTION:")
    for r in (1, 2, 3):
        c = [m for m in modes if m["rung"] == r]
        print(f"    rung {r} {RUNG[r]:<24} {len(c):>2}/{n}  ({len(c)/n:.1%})")

    print()
    print("NOT PRODUCED, AND WHY: Safe Failure Fraction and PFH require a failure")
    print("rate per component. None exists for LLM agents in any source reachable")
    print("from this session. An invented lambda would be worse than no number.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
