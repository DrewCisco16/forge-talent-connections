"""
correctness_matrix.py
=====================
The missing join between a RUN and the DIAGNOSTICS.

adjudication_orchestrator.run_sequential produces per-pass gate outcomes and
divergence. seat_independence.diagnose consumes a correctness matrix, detection
records, and per-pass detections. Nothing built the second from the first, so a
completed five-pass run reported which claims were rejected and never reported
the one thing the system exists to establish: whether the panel converged
ELIMINATIVELY or COLLAPSED.

This module builds that input, and refuses to build it when the run does not
support it.

THE SEMANTIC DECISION, STATED IN FULL
-------------------------------------
seat_independence expects X[i, j] = 1 if seat j got item i CORRECT, 0 if wrong.
It is a strict 0/1 int array -- pairwise_error_correlation computes 1 - X and
correlates -- so there is no cell value meaning "this seat had no opinion". Every
cell must be a real measurement or the matrix must not contain that row.

An ITEM here is a PROPOSITION: one content-addressed claim, adjudicated once.
A seat's position on it is binary and always observed: the seat either asserted
the proposition or it did not. So:

    gate verdict on the claim   |  seat asserted it  |  seat stayed silent
    ---------------------------------------------------------------------
    PASS  (verified true)       |  1  found it       |  0  MISSED it
    FAIL  (false assertion)     |  0  asserted false |  1  correctly silent
    escalated (no gate ran)     |  EXCLUDED unless a human adjudication is
                                |  supplied for that claim

which is the single expression `correct = (seat_asserted_it == claim_is_true)`.

WHY SILENCE COUNTS. A seat asked to find defects that does not report a real one
has missed it -- that is the capture-recapture reading of the same event, and
scoring it as neutral would hide precisely the shared blind spot this measures.
A seat that does not repeat another seat's false assertion was right not to.

WHY ESCALATED CLAIMS ARE EXCLUDED RATHER THAN DEFAULTED. An escalated claim has
no mechanical ground truth. Defaulting it either way invents a measurement, and
the direction of the invention would bias rho: default-true makes every silent
seat look wrong together, default-false makes every asserting seat look wrong
together. Both fabricate correlation. They are dropped and COUNTED, so the
operator sees how much of the run the diagnosis could not see.

WHAT THIS CONSTRUCTION DOES AT THE EXTREMES, verified by test:

  Five seats each finding a different true defect -> the error indicators
  correlate NEGATIVELY, rho clamps to 0, effective seats = 5. Maximum
  divergence reads as maximum independence.

  Five seats asserting the identical set, including the same false one ->
  every error indicator is identical, rho = +1.0, effective seats = 1.0.
  Total collapse is reported as total collapse.

Those two cases are pinned in the suite because they are what makes the number
mean anything, and a construction that got them backwards would still produce
a plausible-looking float.

FAIL CLOSED. If no claim was mechanically adjudicated, or fewer than two seats
have data, no diagnosis is returned -- a report of blockers is. rho over one
seat, or over zero items, is not a weak signal; it is no signal, and the SOP
6.1 phrasing ("5 seats behave like 1.47") is read as a finding.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

import seat_independence as si
from adjudication_orchestrator import ClaimVerdict, SequentialPassResult


class AdjudicationConflict(ValueError):
    """A supplied human adjudication contradicts or misses a gate verdict."""


@dataclass(frozen=True)
class MatrixCoverage:
    """What the diagnosis could and could not see. Reported, never inferred."""
    n_items: int
    n_seats: int
    seats: tuple[str, ...]
    n_claims_adjudicated: int
    n_items_from_gates: int
    n_items_from_human_adjudication: int
    n_excluded_unadjudicated: int
    n_excluded_seat_error: int
    errored_passes: tuple[str, ...]

    @property
    def gate_coverage(self) -> float:
        """Fraction of adjudicated claims the matrix could actually use."""
        if self.n_claims_adjudicated == 0:
            return float("nan")
        return self.n_items / self.n_claims_adjudicated

    def summary(self) -> str:
        parts = [
            f"{self.n_items} item(s) x {self.n_seats} seat(s)",
            f"{self.n_items_from_gates} from gates",
        ]
        if self.n_items_from_human_adjudication:
            parts.append(f"{self.n_items_from_human_adjudication} from human adjudication")
        if self.n_excluded_unadjudicated:
            parts.append(f"{self.n_excluded_unadjudicated} excluded (escalated, unadjudicated)")
        if self.n_excluded_seat_error:
            parts.append(
                f"{self.n_excluded_seat_error} excluded (pass had a seat error: "
                f"{', '.join(self.errored_passes)})"
            )
        return "; ".join(parts)


@dataclass(frozen=True)
class CorrectnessMatrix:
    X: np.ndarray
    item_ids: tuple[str, ...]
    item_truth: tuple[bool, ...]
    seats: tuple[str, ...]
    coverage: MatrixCoverage
    blockers: tuple[str, ...] = field(default_factory=tuple)

    @property
    def measurable(self) -> bool:
        """False means: do not read a diagnosis off this. There isn't one."""
        return not self.blockers


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------

def _seat_order(results: Sequence[SequentialPassResult]) -> tuple[str, ...]:
    """Seats in order of first appearance -- stable across runs, not sorted,
    so the matrix columns line up with how the panel was configured."""
    seen: dict[str, None] = {}
    for res in results:
        for r in res.responses:
            seen.setdefault(r.seat_id, None)
    return tuple(seen)


def _errored_passes(results: Sequence[SequentialPassResult]) -> tuple[str, ...]:
    """A pass in which ANY seat raised.

    Every claim first adjudicated in such a pass is dropped. The errored seat
    was silent there, and its silence is uninterpretable: it did not decline to
    assert the proposition, it never saw the prompt. Coding that silence as a
    miss would manufacture exactly the correlated failure this measures.
    """
    out: dict[str, None] = {}
    for res in results:
        if any(r.error for r in res.responses):
            out.setdefault(res.pass_id, None)
    return tuple(out)


def _proposals(results: Sequence[SequentialPassResult]) -> dict[str, set[str]]:
    """claim_id -> the seats that asserted it, across every pass."""
    by_claim: dict[str, set[str]] = {}
    for res in results:
        for r in res.responses:
            if r.error:
                continue
            for claim in r.claims:
                by_claim.setdefault(claim.id, set()).add(r.seat_id)
    return by_claim


def _resolve_truth(
    verdicts: Mapping[str, ClaimVerdict],
    adjudications: Mapping[str, bool] | None,
) -> dict[str, bool]:
    """Ground truth per claim, from gates plus any supplied human verdicts.

    A human adjudication may only resolve a claim NO gate decided. Letting one
    silently override a deterministic gate would move authority from the
    mechanical bottleneck back to a judgement call, which is the failure the
    whole architecture is built to prevent, so it raises instead.
    """
    truth: dict[str, bool] = {}
    for claim_id, verdict in verdicts.items():
        decided = verdict.verified_true
        if decided is not None:
            truth[claim_id] = decided

    if not adjudications:
        return truth

    for claim_id, value in adjudications.items():
        if claim_id not in verdicts:
            raise AdjudicationConflict(
                f"adjudication supplied for unknown claim {claim_id!r}; it was "
                "never proposed in this run, so it would be silently ignored"
            )
        if claim_id in truth:
            raise AdjudicationConflict(
                f"claim {claim_id!r} was decided by gate "
                f"{verdicts[claim_id].gate!r}; a human adjudication may only "
                "resolve claims that escalated with no gate applied"
            )
        truth[claim_id] = bool(value)
    return truth


def build_correctness_matrix(
    results: Sequence[SequentialPassResult],
    verdicts: Mapping[str, ClaimVerdict],
    adjudications: Mapping[str, bool] | None = None,
) -> CorrectnessMatrix:
    """
    Assemble X for seat_independence from one completed run.

    results      : what Orchestrator.run_sequential returned
    verdicts     : Orchestrator.verdicts after that run
    adjudications: optional {claim_id -> is_true} for ESCALATED claims only,
                   i.e. the human decisions from the judgment queue

    Returns a CorrectnessMatrix whose `measurable` is False, with blockers
    stated, when the run cannot support a diagnosis.
    """
    seats = _seat_order(results)
    errored = _errored_passes(results)
    proposals = _proposals(results)
    truth = _resolve_truth(verdicts, adjudications)
    supplied = set(adjudications or {})

    item_ids: list[str] = []
    item_truth: list[bool] = []
    from_gates = 0
    from_human = 0
    excluded_unadjudicated = 0
    excluded_seat_error = 0

    for claim_id, verdict in verdicts.items():
        if verdict.pass_id in errored:
            excluded_seat_error += 1
            continue
        if claim_id not in truth:
            excluded_unadjudicated += 1
            continue
        item_ids.append(claim_id)
        item_truth.append(truth[claim_id])
        if claim_id in supplied:
            from_human += 1
        else:
            from_gates += 1

    if item_ids and seats:
        X = np.array(
            [
                [int((seat in proposals.get(cid, set())) == is_true) for seat in seats]
                for cid, is_true in zip(item_ids, item_truth, strict=True)
            ],
            dtype=int,
        )
    else:
        X = np.zeros((len(item_ids), len(seats)), dtype=int)

    coverage = MatrixCoverage(
        n_items=len(item_ids),
        n_seats=len(seats),
        seats=seats,
        n_claims_adjudicated=len(verdicts),
        n_items_from_gates=from_gates,
        n_items_from_human_adjudication=from_human,
        n_excluded_unadjudicated=excluded_unadjudicated,
        n_excluded_seat_error=excluded_seat_error,
        errored_passes=errored,
    )

    blockers: list[str] = []
    if not item_ids:
        blockers.append(
            "no claim in this run has mechanical ground truth: "
            f"{excluded_unadjudicated} escalated without adjudication, "
            f"{excluded_seat_error} dropped from passes with a seat error"
        )
    if len(seats) < 2:
        blockers.append(
            f"error correlation needs at least two seats; this run has {len(seats)}"
        )

    return CorrectnessMatrix(
        X=X,
        item_ids=tuple(item_ids),
        item_truth=tuple(item_truth),
        seats=seats,
        coverage=coverage,
        blockers=tuple(blockers),
    )


def build_detections(
    results: Sequence[SequentialPassResult],
    verdicts: Mapping[str, ClaimVerdict],
    adjudications: Mapping[str, bool] | None = None,
) -> dict[str, set[str]]:
    """
    seat_id -> the TRUE findings that seat caught. Input to chao1.

    NOT Orchestrator.detections_by_seat, which records every claim a seat
    proposed including the ones the gates rejected. Chao1 estimates how many
    real defects went uncaught by anybody; feeding it false assertions inflates
    S_obs and the singleton count, and singletons are what drive N_hat.
    """
    truth = _resolve_truth(verdicts, adjudications)
    proposals = _proposals(results)
    out: dict[str, set[str]] = {seat: set() for seat in _seat_order(results)}
    for claim_id, is_true in truth.items():
        if not is_true:
            continue
        for seat in proposals.get(claim_id, set()):
            out.setdefault(seat, set()).add(claim_id)
    return out


def build_pass_detections(
    results: Sequence[SequentialPassResult],
    verdicts: Mapping[str, ClaimVerdict],
    adjudications: Mapping[str, bool] | None = None,
) -> list[tuple[str, set[str]]]:
    """
    Ordered [(pass_id, true findings first adjudicated in that pass)].
    Input to marginal_yield_by_pass, which is order-dependent by design.
    """
    truth = _resolve_truth(verdicts, adjudications)
    by_pass: dict[str, set[str]] = {res.pass_id: set() for res in results}
    for claim_id, verdict in verdicts.items():
        if truth.get(claim_id):
            by_pass.setdefault(verdict.pass_id, set()).add(claim_id)
    return [(res.pass_id, by_pass.get(res.pass_id, set())) for res in results]


SHARED_DETECTION = "shared_detection"
OPEN_ENDED = "open_ended"

TASK_KINDS = (SHARED_DETECTION, OPEN_ENDED)
"""How the seats were asked to work, which decides whether silence means
anything.

THIS MODULE'S CORE INFERENCE IS SOUND FOR ONE REGIME AND WRONG FOR THE OTHER.

Under SHARED_DETECTION every seat is handed the same artifact and asked to
find its defects. A seat that does not report a real defect has MISSED it, and
scoring that as neutral would hide exactly the shared blind spot the statistic
exists to measure. That is the regime this module was written for, and the
reasoning in its header is correct there.

Under OPEN_ENDED each seat writes its own answer to a question. A seat that
did not mention another seat's true proposition has not missed a defect -- it
wrote about something else. Silence is MISSING DATA, and reading it as an
observation manufactures the measurement. Demonstrated on a two-seat run where
each seat independently stated a different TRUE proposition: this module
reported measurable=True, rho=-1.0 and effective_seats=2.0, while
night_loop.measure_rho() on the same raw run correctly reported NOT MEASURED.
Two paths disagreeing about one run, and the invented figure was the one that
fed a confidence label.

The regime is now required rather than assumed, because assuming it is how the
two paths came to disagree.
"""


def diagnose_run(
    results: Sequence[SequentialPassResult],
    verdicts: Mapping[str, ClaimVerdict],
    adjudications: Mapping[str, bool] | None = None,
    total_seeded: int | None = None,
    task_kind: str = OPEN_ENDED,
) -> dict[str, Any]:
    """
    The end-to-end answer: eliminative convergence, or collapse?

    Returns seat_independence.diagnose's report plus `coverage` and
    `measurable`. When the run cannot support the diagnosis, `measurable` is
    False, `blockers` says why, and NO diagnostic keys are present -- rather
    than a NaN an operator would read as a small number.

    task_kind DEFAULTS TO OPEN_ENDED, which is the conservative direction: the
    live panel answers open-ended, so a caller that does not say which regime
    it is in gets the one where no independence figure is produced. A caller
    with a genuine common-task design must say so explicitly.
    """
    if task_kind not in TASK_KINDS:
        raise ValueError(
            f"task_kind must be one of {TASK_KINDS}, got {task_kind!r}")
    if task_kind == OPEN_ENDED:
        return {
            "measurable": False,
            "blockers": [
                "independence is not measurable from open-ended generation. "
                "This diagnosis reads a seat's silence about a proposition as "
                "a correctness observation, which holds when every seat was "
                "asked to decide the same items and does not hold when each "
                "seat wrote its own answer -- there, silence is missing data. "
                "Measuring it needs a seeded set of propositions with known "
                "truth that every seat must decide."
            ],
            "coverage": None,
            "task_kind": task_kind,
        }
    matrix = build_correctness_matrix(results, verdicts, adjudications)
    report: dict[str, Any] = {
        "task_kind": task_kind,
        "measurable": matrix.measurable,
        "blockers": list(matrix.blockers),
        "coverage": matrix.coverage,
        "coverage_summary": matrix.coverage.summary(),
    }
    if not matrix.measurable:
        return report

    report.update(
        si.diagnose(
            X=matrix.X,
            detections=build_detections(results, verdicts, adjudications),
            pass_detections=build_pass_detections(results, verdicts, adjudications),
            total_seeded=total_seeded,
        )
    )
    rho = report.get("mean_error_correlation_rho")
    n_seats = report.get("n_seats", 0)
    report["reading"] = _reading(rho, report.get("effective_seats"), n_seats)
    return report


def _reading(rho: float | None, n_eff: float | None, n_seats: int) -> str:
    """Plain-language reading. States uncertainty rather than rounding it off."""
    if rho is None or n_eff is None or (isinstance(rho, float) and np.isnan(rho)):
        return (
            "rho is undefined for this run: no seat pair varied in its errors. "
            "That is not independence -- it is the absence of a measurement."
        )
    return (
        f"mean error correlation rho = {rho:+.3f}; {n_seats} seats behave like "
        f"{n_eff:.2f} independent seat(s). Read this beside the item count: a "
        "small number of items makes rho unstable regardless of its value."
    )


if __name__ == "__main__":
    # Illustrative on SYNTHETIC seats. Demonstrates the join runs end to end;
    # these are not findings about any real panel.
    from adjudication_orchestrator import (
        ArithmeticGate,
        BlindedSeatRunner,
        Orchestrator,
    )

    def seat(lines: str) -> Callable[[str], str]:
        return lambda _prompt: lines

    true_claim = "CLAIM | arithmetic | 2 + 2 = 4 | 2 + 2 = 4"
    false_claim = "CLAIM | arithmetic | 2 + 2 = 5 | 2 + 2 = 5"

    for label, fns in (
        ("divergent", {
            "s1": seat(true_claim),
            "s2": seat("CLAIM | arithmetic | 3 * 3 = 9 | 3 * 3 = 9"),
            "s3": seat(false_claim),
        }),
        ("collapsed", {
            "s1": seat(f"{true_claim}\n{false_claim}"),
            "s2": seat(f"{true_claim}\n{false_claim}"),
            "s3": seat(f"{true_claim}\n{false_claim}"),
        }),
    ):
        orch = Orchestrator([ArithmeticGate()])
        res = orch.run_sequential("artifact", [], BlindedSeatRunner(fns))

        # BOTH REGIMES, because the difference between them is the whole
        # point of task_kind and the demo showed neither.
        #
        # It called diagnose_run with no task_kind, took the OPEN_ENDED
        # default, and then indexed rep['coverage_summary'] -- a key that
        # branch deliberately omits, as its docstring says: "NO diagnostic
        # keys are present, rather than a NaN an operator would read as a
        # small number." So the demo raised KeyError and CI went red. The
        # omission is the design; the demo was what went stale.
        open_rep = diagnose_run(res, orch.verdicts)
        print(f"[{label}] open_ended  measurable={open_rep['measurable']}")
        print(f"[{label}]   {open_rep['blockers'][0]}")

        shared_rep = diagnose_run(res, orch.verdicts,
                                  task_kind=SHARED_DETECTION)
        print(f"[{label}] shared_detection  "
              f"{shared_rep.get('coverage_summary')}")
        print(f"[{label}]   {shared_rep.get('reading')}\n")
