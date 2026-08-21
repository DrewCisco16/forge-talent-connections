"""
validation_harness.py
=====================
Seeded-error harness for the blinded five-pass adjudication run.

WHAT IT IS FOR
--------------
The diagnostics in seat_independence.py need ground truth: a set of defects you
know are present, and a record of which seat caught which. This harness supplies
both against synthetic seats, so the architecture can be exercised end to end
and every reported number checked against a known answer.

WHAT IT IS NOT
--------------
The seats here are SYNTHETIC -- fixed functions that catch a predetermined
subset. Running this validates that the machinery measures divergence and
residual risk correctly. It does NOT establish anything about how real language
models behave; that requires wiring BlindedSeatRunner to actual seat callables
and re-running against defects seeded in real work.

Run: python validation_harness.py
"""

from typing import Dict, Set

import numpy as np

import adjudication_orchestrator as AO
import seat_independence as SI
from adjudication_orchestrator import ArithmeticGate, Orchestrator

# Twelve seeded defects with known ground truth. Each warrant is real arithmetic
# so the deterministic gates actually fire rather than being stubbed.
SEEDED: Dict[str, str] = {f"E{i}": f"{i} + {i} = {2 * i}" for i in range(1, 13)}

# Which pass each defect is discoverable in (index into DEFAULT_PASSES).
PASS_OF: Dict[str, int] = {
    "E1": 0, "E2": 0, "E7": 0, "E9": 0,
    "E3": 1, "E8": 1, "E10": 1,
    "E4": 2, "E11": 2,
    "E5": 3, "E12": 3,
    "E6": 4,
}


def make_seat(caught: Set[str]):
    """A synthetic seat that catches a fixed subset, reporting per pass.

    It reads the lens out of its own prompt -- which is all the blinding gives
    it -- and reports only the defects assigned to that pass.
    """
    def seat(prompt: str) -> str:
        lens = prompt.split("## Lens\n")[1].split("\n")[0]
        k = [p.name for p in AO.DEFAULT_PASSES].index(lens)
        return "\n".join(
            f"CLAIM | arithmetic | {SEEDED[e]} | defect {e}"
            for e in sorted(caught, key=lambda x: int(x[1:]))
            if PASS_OF[e] == k
        )
    return seat


def run(label: str, catches: Dict[str, Set[str]]) -> Orchestrator:
    print(f"\n{'=' * 78}\n{label}\n{'=' * 78}")
    runner = AO.BlindedSeatRunner({s: make_seat(c) for s, c in catches.items()})
    orch = Orchestrator([ArithmeticGate()])
    results = orch.run_sequential("<the artifact under review>", [], runner)

    print(f"{'pass':<46}{'clm':>4}{'acc':>4}{'jacc':>8}  status")
    for r in results:
        d = r.divergence
        jac = ("   n/a" if d.mean_pairwise_jaccard != d.mean_pairwise_jaccard
               else f"{d.mean_pairwise_jaccard:6.3f}")
        if d.collapse_warning:
            status = "COLLAPSE WARNING"
        elif d.all_seats_silent:
            status = "silent (no yield)"
        else:
            status = "divergent"
        print(f"{r.pass_name:<46}{r.record.proposed:>4}"
              f"{r.record.auto_accepted:>4}{jac:>8}  {status}")

    seat_ids = list(catches)
    errs = [f"E{i}" for i in range(1, 13)]
    X = np.array([[1 if e in catches[s] else 0 for s in seat_ids] for e in errs])
    rho = SI.mean_error_correlation(X)
    det = {s: set(c) for s, c in catches.items()}
    ch = SI.chao1(det)
    found = set().union(*det.values())
    missed = len(errs) - len(found)

    print(f"\n  seeded defects                 {len(errs)}")
    print(f"  caught by at least one seat    {len(found)}")
    print(f"  TRULY missed (ground truth)    {missed}")
    print(f"  Chao1 lower bound on missed    {ch['estimated_missed']:.1f}"
          f"   (understates by {missed - ch['estimated_missed']:.1f})")
    print(f"  singleton fraction             {ch['singleton_fraction']:.3f}")
    print(f"  mean error correlation rho     {rho:+.3f}")
    print(f"  effective seats (of {len(seat_ids)})          "
          f"{SI.effective_seats(len(seat_ids), rho):.2f}")

    yields = SI.marginal_yield_by_pass(
        [(p.name, {e for e in found if PASS_OF[e] == k})
         for k, p in enumerate(AO.DEFAULT_PASSES)],
        total_seeded=len(errs),
    )
    print(f"  marginal yield by pass         "
          f"{[round(y.marginal_yield, 3) for y in yields]}")
    return orch


if __name__ == "__main__":
    run("SCENARIO A -- DIVERGENT PANEL (partially independent failure modes)",
        {"s1": {"E7", "E8", "E9", "E10"},
         "s2": {"E7", "E8", "E10", "E11"},
         "s3": {"E7", "E8", "E11", "E12"}})

    run("SCENARIO B -- COLLAPSED PANEL (all three seats give the same answer)",
        {"s1": {"E7", "E8", "E9", "E10"},
         "s2": {"E7", "E8", "E9", "E10"},
         "s3": {"E7", "E8", "E9", "E10"}})

    print("\nNOTE: seats here are synthetic. This validates the machinery, not "
          "the behaviour of any real model.\n")
