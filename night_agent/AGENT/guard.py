"""In-process wrapper around TESTS/na_gate.py: every transition and every send is guarded."""
import os
import sys

from . import PKG

sys.path.insert(0, os.path.join(PKG, "TESTS"))
import na_gate  # noqa: E402


class Blocked(Exception):
    def __init__(self, stage, reasons):
        super().__init__(f"BLOCK {stage}: " + "; ".join(reasons))
        self.stage = stage
        self.reasons = reasons


def require(rf, stage, stage_dir=None, op=None, record=None, seat=None):
    """Run the guard, log the result as DISPATCH 0 requires, raise Blocked on BLOCK."""
    reasons = na_gate.guard(rf.root, stage, stage_dir, op, record, seat)
    rf.log("DISPATCH", "guard", result="ALLOW" if not reasons else "BLOCK", stage=stage,
           guard_args={"stage_dir": stage_dir, "op": op, "record": record, "seat": seat}, reasons=reasons)
    if reasons:
        raise Blocked(stage, reasons)
