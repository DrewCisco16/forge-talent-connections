"""Spec 17 classification and spec 10 flags, computed by Dispatch from the record, never by a seat."""
from .config import load_schema

CLASSES = ("KEEP_FOR_DEVELOPMENT", "REVERT", "PARTIAL_REPORT")


def classification(*, stop_reason, critical_failure, review_skipped, capture_partial, direct=False) -> str:
    """Computed at FINAL, before VERIFY, because the deliverable that carries it is written once (spec 4.7, I3).
    REVERT: a known critical failure at that point (a constraint broken by a kept mutation). PARTIAL_REPORT:
    evidence collection incomplete (spec 6 items 1, 2, 4; a stage closed on a partial capture; REVIEW skipped in a
    class that has one). Else KEEP_FOR_DEVELOPMENT. A verifier CONTRADICTION found afterwards sets PROVISIONAL, a
    flag for the morning (spec 4.8, 10), and never rewrites the deliverable."""
    if critical_failure:
        return "REVERT"
    if stop_reason in ("CREW", "HARD_STOP", "NONE_STANDING", "ABORT"):
        return "PARTIAL_REPORT"
    if capture_partial or (review_skipped and not direct):
        return "PARTIAL_REPORT"
    return "KEEP_FOR_DEVELOPMENT"


def derived_flags(*, deprioritized: int, earned: int, open_lines: list, all_checks_passed: bool, has_stage: bool) -> list:
    out = []
    if deprioritized > earned:
        out.append("DEPRIORITIZED_GT_EARNED")
    if has_stage and not any(l.strip() and l.strip().lower() not in ("none", "- none") for l in open_lines):
        out.append("EMPTY_OPEN_LIST")
    if has_stage and all_checks_passed:
        out.append("ALL_CLEAN")
    return out


def assert_known(flags: list) -> list:
    known = set(load_schema()["flags"])
    unknown = sorted(set(flags) - known)
    if unknown:
        raise ValueError(f"flags outside SCHEMA: {unknown}")
    return sorted(set(flags), key=flags.index)
