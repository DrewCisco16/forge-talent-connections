"""
calibrate.py
============
Measure how independent the five real seats actually are.

WHY THIS EXISTS AS A SEPARATE MODE
----------------------------------
A normal adjudication run cannot produce this number, and says so. Under
OPEN_ENDED generation each seat writes its own answer; a seat that did not
mention another seat's proposition has not MISSED it, it wrote about something
else. Silence is missing data, and correctness_matrix.diagnose_run refuses to
report rho rather than manufacture one from it.

The measurement needs the other regime: a fixed set of propositions with known
truth that EVERY seat must decide. Then silence is an observation -- the seat
was asked and did not confirm -- and `correct = (asserted == is_true)` holds.
That is SHARED_DETECTION, and this module is the only thing that produces it
from live seats.

The pieces already existed and were never joined: seat_independence has the
statistics, correctness_matrix has the scoring regime, seat_adapter has the
transport. validation_harness exercises the same path against SYNTHETIC seats
and its own header names what was missing -- "wiring BlindedSeatRunner to
actual seat callables". This is that wiring.

WHAT IT COSTS
-------------
ONE call per seat. Every item is presented in a single artifact, so the whole
calibration is five API calls, not five times the item count. Cost caps are
honoured through the same ledger the adjudication runner uses.

WHY THE CLAIM LINE REPEATS THE STATEMENT TWICE
----------------------------------------------
Two constraints meet here, and only one line shape satisfies both.

First, claim identity is content-addressed: content_claim_id hashes the kind,
the warrant, AND the normalised text. Two seats confirming the same statement
must produce the SAME claim id, or the matrix sees two one-seat items instead
of one five-seat item, every item becomes a singleton, and the correlation is
measured over nothing.

Second, the orchestrator's relevance guard refuses a warrant that does not
bear on the claim text -- the check that stops a seat attaching a true
equation to an unrelated assertion. An item id alone in the text field trips
it: the guard sees that "S03" does not mention 324 and escalates instead of
ruling, which silently drops every TRUE item from the matrix while the false
ones still fail. The first build of this module did exactly that and measured
rho over five items instead of seventeen.

The shape that satisfies both is the one the guard names as its own sanctioned
case -- text identical to warrant, "the claim IS the warrant". So a seat
repeats the statement in both fields, the id is never needed in the line, and
items are recovered by expression. A seat that paraphrases instead produces a
distinct id; that is reported by `unmatched_claims` rather than absorbed.

WHAT THIS DOES NOT ESTABLISH
----------------------------
Arithmetic is a narrow probe. A panel that is independent on arithmetic may
still share a blind spot on domain reasoning, and this number does not transfer
to that. It is the cheapest honest measurement available, not a general one.

Run:
    python calibrate.py --profiles profiles.json
    python calibrate.py --demo        # synthetic seats, no network, no spend
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TypeGuard

import adjudication_orchestrator as AO
from adjudication_orchestrator import (
    ArithmeticGate,
    BlindedSeatRunner,
    Orchestrator,
    Pass,
    SequentialPassResult,
    measure_divergence,
)
from correctness_matrix import (
    SHARED_DETECTION,
    CorrectnessMatrix,
    build_correctness_matrix,
    diagnose_run,
)

DEFAULT_N_ITEMS = 24
DEFAULT_SEED = 20260829


# ---------------------------------------------------------------------------
# the item set
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Item:
    """One proposition every seat must decide.

    `expression` is what the arithmetic gate recomputes, so truth is
    mechanical -- no human adjudicates a calibration item, and no seat's
    opinion contributes to the answer key.
    """
    item_id: str
    expression: str
    is_true: bool


def build_items(n: int = DEFAULT_N_ITEMS, seed: int = DEFAULT_SEED) -> list[Item]:
    """
    A reproducible mixed set: half true, half false.

    BOTH POLARITIES ARE REQUIRED, and this is the whole reason the set is not
    just validation_harness.SEEDED. Every seeded defect there is TRUE
    arithmetic, so a seat that confirms everything scores perfectly. With no
    false item there is no way to be wrong by over-asserting, the only error
    left is silence, and the statistic measures eagerness rather than
    correctness. The false items are what make confirming everything cost
    something.

    See the inline notes below for the two other design constraints: the
    margin false items are wrong by, and the operator mix that keeps the probe
    hard enough to separate the seats at all.
    """
    if n < 2:
        raise ValueError(f"need at least 2 items to measure anything, got {n}")
    if n % 2:
        raise ValueError(
            f"n_items must be even so true and false items balance, got {n}")

    # REPRODUCIBILITY IS THE REQUIREMENT HERE, NOT UNPREDICTABILITY.
    #
    # Two calibration runs are only comparable if the same seed produces the
    # same quiz, and global rule 4 blocks nondeterminism in replay. A CSPRNG
    # would defeat both. Nothing here is a secret, a token, or a salt: these
    # are arithmetic questions with published answers.
    #
    # Reason kept OFF the nosec line: bandit parses everything after "nosec"
    # as test IDs, so a trailing explanation silently widens the suppression.
    rng = random.Random(seed)  # nosec B311
    items: list[Item] = []
    # EVERY OPERAND PAIR MUST BE DISTINCT.
    #
    # Two items sharing a left-hand side would collapse into ONE claim id --
    # identity is content-addressed -- so the run would score fewer items than
    # it asked about while still reporting n. Worse, if one of the pair were
    # true and the other false, the same id would carry two contradictory
    # answer-key entries. No collision appears in the first 300 seeds at
    # n=24, which is exactly why this is enforced rather than relied upon:
    # the failure is silent and only shows up at larger n.
    seen_operands: set[tuple[int, int, str]] = set()
    for k in range(n):
        truth = k % 2 == 0
        # THE PROBE MUST BE HARD ENOUGH TO SEPARATE THE SEATS.
        #
        # This was three-digit addition alone, and that is a measurement
        # design error rather than a coding one: current models essentially
        # never get it wrong, so all five seats score identically, no seat
        # pair varies, and rho comes back NaN. A probe nobody fails cannot
        # rank anybody -- it yields the absence of a measurement, dressed as
        # a completed run.
        #
        # Multiplication of three-digit operands is where models actually
        # slip, so two thirds of the set is multiplication and the addition
        # is widened to six digits. The gate evaluates both through the same
        # operator table, so nothing about the answer key changes.
        while True:
            if k % 3 == 0:
                a = rng.randint(100_000, 999_999)
                b = rng.randint(100_000, 999_999)
                true_result, expr_op = a + b, "+"
            else:
                a, b = rng.randint(114, 989), rng.randint(113, 987)
                true_result, expr_op = a * b, "*"
            if (a, b, expr_op) not in seen_operands:
                seen_operands.add((a, b, expr_op))
                break
        # A false item is off by a small amount, never zero, so the statement
        # is genuinely false but not obviously so. An answer off by an order
        # of magnitude is caught by inspection and measures nothing.
        result = true_result if truth else true_result + rng.choice(
            [-9, -6, -3, -2, -1, 1, 2, 3, 6, 9])
        items.append(
            Item(f"S{k + 1:02d}", f"{a} {expr_op} {b} = {result}", truth))
    return items


def render_artifact(items: Sequence[Item]) -> str:
    """The artifact every seat is shown. Identical for all five."""
    lines = [
        "The following statements each claim an arithmetic result.",
        "Some are correct and some are not.",
        "",
    ]
    lines += [f"{it.item_id}. {it.expression}" for it in items]
    return "\n".join(lines)


CALIBRATION_INSTRUCTION = (
    "Decide EVERY statement below. For each statement you judge to be "
    "arithmetically CORRECT, emit exactly one line:\n"
    "    CLAIM | arithmetic | <the statement> | <the same statement again>\n"
    "For example, if a statement reads '111 + 222 = 333' and you judge it "
    "correct:\n"
    "    CLAIM | arithmetic | 111 + 222 = 333 | 111 + 222 = 333\n"
    "Both the third and fourth fields must be the statement copied exactly, "
    "character for character. Do NOT put the item id in the line, do not "
    "paraphrase, and do not reword.\n"
    "Emit NOTHING for a statement you judge incorrect -- silence is how you "
    "say 'not correct', and it is recorded as your decision.\n"
    "Output only these lines. No commentary, no reasoning, no other text."
)

CALIBRATION_PASS = Pass(
    "calib",
    "Arithmetic Verification",
    CALIBRATION_INSTRUCTION,
    # Not eliminative: this pass rules on propositions, it does not remove
    # candidates. Nothing is being adjudicated here.
    False,
)


# ---------------------------------------------------------------------------
# running it
# ---------------------------------------------------------------------------

@dataclass
class CalibrationResult:
    items: list[Item]
    report: dict[str, Any]
    seats: tuple[str, ...]
    """Every seat that was ASKED, whether or not it was scored."""
    scored_seats: tuple[str, ...]
    """The seats the number actually describes. See `excluded_seats`."""
    seat_errors: dict[str, str]
    excluded_seats: dict[str, str]
    """seat_id -> why it was left out of the measurement.

    A seat that raised, and a seat that returned nothing usable, are both
    excluded HERE rather than scored as decisions.

    Scoring them was the original behaviour and it was wrong in two different
    ways. A seat that returned an empty string -- a refusal, a safety filter,
    a dropped connection that still yielded 200 -- contributed a row saying
    "every statement is false", which is a decisive opinion rather than an
    absence. And a seat that RAISED voided the entire run: correctness_matrix
    drops every claim first adjudicated in a pass where any seat errored,
    which is right for a five-pass run and catastrophic for a one-pass
    calibration, because there is no other pass to carry the items. One flaky
    seat out of five produced a zero-item matrix and a wasted paid run.

    Excluding the seat and measuring the rest is sound here specifically
    because every remaining seat decided every item.
    """
    unmatched_claims: dict[str, list[str]]
    """seat_id -> claim warrants that matched no item in the set. See the
    module header: these are confirmations the matrix could not attribute, and
    they are shown rather than silently scored as silence."""
    confirmations: dict[str, int]
    """seat_id -> how many statements it confirmed. A seat far below the
    others confirmed less than it was asked to -- a truncated reply looks
    exactly like a decisive one from the content alone, so the count is
    reported and left for the operator to read."""
    seat_accuracy: dict[str, float]
    """seat_id -> share of matrix items it got right. This is what makes
    "cut seats" actionable: without it the operator is told to drop two of
    five and given nothing to choose by."""

    @property
    def rho(self) -> float | None:
        return self.report.get("mean_error_correlation_rho")

    @property
    def effective_seats(self) -> float | None:
        return self.report.get("effective_seats")

    @property
    def mean_accuracy(self) -> float | None:
        """Mean accuracy across scored seats, or None if nothing was scored.

        Separates the two panels that both produce rho = 1.0: seats sharing a
        blind spot score WELL and fail together on a few items; seats drowning
        in a probe too hard for them score badly on nearly everything. Those
        are opposite findings and the correlation alone cannot tell them apart.
        """
        if not self.seat_accuracy:
            return None
        return sum(self.seat_accuracy.values()) / len(self.seat_accuracy)


_DECORATION = re.compile(r"^[\s>*\-+•`|]+")
_EMPHASIS_BEFORE_FIRST_PIPE = re.compile(r"^([^|]*)")


def _undecorate(line: str) -> str:
    """Strip markdown decoration from a claim line without touching its fields.

    Leading bullets and emphasis are removed, and emphasis characters are also
    dropped from the CLAIM token itself -- "**CLAIM**" survives the leading
    strip as "CLAIM**", which still fails the line pattern. Only the segment
    BEFORE the first pipe is touched, so an asterisk inside a multiplication
    expression is never disturbed.
    """
    stripped = _DECORATION.sub("", line)
    head = _EMPHASIS_BEFORE_FIRST_PIPE.match(stripped)
    if not head:
        return stripped
    cleaned = re.sub(r"[*`_]", "", head.group(1))
    return cleaned + stripped[head.end():]


def _canonical_key(s: str) -> str:
    """A whitespace- and separator-insensitive key for one statement.

    DELIBERATELY MORE AGGRESSIVE THAN _norm, and the difference is the whole
    point. content_claim_id hashes the WARRANT verbatim, so a seat writing
    "463*785 = 363455" produces a different claim id from one writing
    "463 * 785 = 363455" even though both assert the identical proposition.

    That is not a cosmetic problem. The two ids become two separate one-seat
    items: each seat is scored as having MISSED the other's item, so a purely
    typographical difference manufactures disagreement in BOTH directions and
    makes the panel look more independent than it is. Measured, not supposed --
    content_claim_id returns different ids for those two strings.

    Digit-group separators are dropped for the same reason: "363,455" is the
    same number, but the arithmetic gate cannot parse it and rules the claim
    INAPPLICABLE, which escalates it out of the matrix silently.
    """
    return re.sub(r"[\s,_]", "", (s or "")).casefold()


def _index_by_expression(items: Sequence[Item]) -> dict[str, Item]:
    """Items are recovered by their expression, not their id -- the claim line
    carries the statement in both fields and never the id. See module header."""
    return {_canonical_key(it.expression): it for it in items}


def calibration_extractor(
    items: Sequence[Item],
) -> Callable[[str, str, str], list[AO.Claim]]:
    """A claim extractor that snaps a seat's wording onto the canonical item.

    Real models do not reproduce a format character for character. Measured
    against line_claim_extractor: a leading bullet or bold marker makes the
    line vanish entirely (0 claims, scored as the seat judging every statement
    false); dropping the spaces around '*' yields a different claim id; a
    thousands separator makes the gate rule INAPPLICABLE, which drops the item.

    Every one of those degrades the measurement SILENTLY, so this normalises
    the two things that are pure formatting -- leading decoration, and the
    spelling of a statement the item set already defines -- and leaves
    everything else alone. A claim that snaps is rewritten with the canonical
    expression in BOTH fields, which is the shape the relevance guard
    sanctions and the shape that makes ids collide across seats.

    What it does NOT do is repair a seat's arithmetic. A statement that is not
    in the item set does not snap; it stays as written, reaches the gate on
    its own terms, and is reported in unmatched_claims.
    """
    by_key = _index_by_expression(items)

    def extract(raw: str, seat_id: str, pass_id: str) -> list[AO.Claim]:
        stripped = "\n".join(
            _undecorate(line) if "CLAIM" in line.upper() else line
            for line in (raw or "").splitlines()
        )
        out: list[AO.Claim] = []
        for claim in AO.line_claim_extractor(stripped, seat_id, pass_id):
            item = by_key.get(_canonical_key(claim.warrant or ""))
            if item is None:
                out.append(claim)
                continue
            out.append(AO.Claim(
                AO.content_claim_id(AO.ClaimKind.ARITHMETIC,
                                    item.expression, item.expression),
                item.expression, AO.ClaimKind.ARITHMETIC, item.expression,
                pass_id, seat_id,
            ))
        return out

    return extract


def run_calibration(
    seat_fns: Mapping[str, Callable[[str], str]],
    items: Sequence[Item] | None = None,
) -> CalibrationResult:
    """
    One pass, five seats, a fixed answer key, and the resulting rho.

    The orchestrator and gate do the scoring: the ArithmeticGate recomputes
    each confirmed expression, so the answer key is mechanical and this module
    never decides truth itself.
    """
    chosen = list(items) if items is not None else build_items()
    artifact = render_artifact(chosen)
    by_key = _index_by_expression(chosen)

    runner = BlindedSeatRunner(dict(seat_fns),
                               extractor=calibration_extractor(chosen))
    orch = Orchestrator(gates=[ArithmeticGate()], passes=[CALIBRATION_PASS])

    responses = runner.run(CALIBRATION_PASS, artifact)

    seat_errors: dict[str, str] = {}
    excluded: dict[str, str] = {}
    unmatched: dict[str, list[str]] = {}
    confirmations: dict[str, int] = {}

    for r in responses:
        confirmations[r.seat_id] = len(r.claims)
        if r.error:
            seat_errors[r.seat_id] = r.error
            excluded[r.seat_id] = f"seat raised: {r.error}"
            continue
        for c in r.claims:
            if _canonical_key(c.warrant or "") not in by_key:
                unmatched.setdefault(r.seat_id, []).append(
                    (c.warrant or c.text or "").strip())
        if not r.claims:
            # A seat that confirmed NOTHING is not a seat that judged every
            # statement false. Half the set is true and stated plainly; a
            # working model confirms some of them. Zero is a refusal, a safety
            # filter, or an empty body behind a 200 -- an absence, and scoring
            # it as a decisive all-false row would put a fabricated opinion
            # into the correlation.
            excluded[r.seat_id] = (
                "returned no usable claim line: treated as no answer, not as "
                "a judgement that every statement is false")

    usable = [r for r in responses if r.seat_id not in excluded]
    claims: list[AO.Claim] = [c for r in usable for c in r.claims]

    record = orch.run_pass(CALIBRATION_PASS, [], claims)
    result = SequentialPassResult(
        CALIBRATION_PASS.id, CALIBRATION_PASS.name, record,
        measure_divergence(CALIBRATION_PASS, usable), usable,
    )

    report = diagnose_run(
        [result],
        orch.verdicts,
        total_seeded=len(chosen),
        task_kind=SHARED_DETECTION,
    )
    return CalibrationResult(
        items=chosen,
        report=report,
        seats=tuple(sorted(seat_fns)),
        scored_seats=tuple(r.seat_id for r in usable),
        seat_errors=seat_errors,
        excluded_seats=excluded,
        unmatched_claims=unmatched,
        confirmations=confirmations,
        seat_accuracy=_seat_accuracy(
            build_correctness_matrix([result], orch.verdicts)),
    )


def _seat_accuracy(matrix: CorrectnessMatrix) -> dict[str, float]:
    """Per-seat share of matrix items answered correctly.

    Read off the SAME X the correlation is computed from -- rebuilt from the
    same results and verdicts -- so the per-seat figures and rho can never
    describe different panels.
    """
    if not matrix.seats or matrix.X.size == 0:
        return {}
    return {seat: float(matrix.X[:, i].mean())
            for i, seat in enumerate(matrix.seats)}


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

def rho_measured(rho: float | None) -> TypeGuard[float]:
    """True only when rho is a real number that can be compared.

    A TypeGuard so the threshold ladder below narrows to `float` and the type
    checker enforces that no comparison happens on the unmeasured path. The
    NaN rule lives here alone; rho_undefined is its inverse rather than a
    second copy, because two hand-written copies of this rule are exactly how
    the ladder came to fall through in the first place.
    """
    return rho is not None and not math.isnan(rho)


def rho_undefined(rho: float | None) -> bool:
    """
    NaN IS AN ABSENT MEASUREMENT, NOT A LARGE ONE.

    seat_independence returns NaN when no seat pair varied in its errors --
    every seat scored identically, so there is nothing to correlate. That is
    the single most likely outcome of a first live run, because the probe is
    arithmetic and current models are good at it.

    NaN fails EVERY comparison, so a threshold ladder written as `if rho <=
    0.2 ... elif rho <= 0.5 ... else` falls all the way through to the last
    branch. This function existed only after that happened here: five
    identical, perfectly-scoring seats produced "CUT SEATS. rho=nan means the
    seats mostly fail together" -- an absent measurement converted into
    confident, expensive advice, in the wrong direction.
    """
    return not rho_measured(rho)


def verdict_line(rho: float | None, n_seats: int,
                 mean_accuracy: float | None = None) -> str:
    """
    What the operator should DO about this number.

    The thresholds are the ones already stated in the PR and SOP discussion --
    five seats are justified only at rho <= ~0.2 -- and they are named as
    conventions, not derived. An operator who wants a different cutoff should
    set one; this refuses to imply a precision it does not have.
    """
    if not rho_measured(rho):
        return (
            "NO VERDICT: rho was not produced, so nothing here justifies "
            "keeping or cutting a seat.\n"
            "If the seats all scored identically, the probe was too easy to "
            "separate them -- that is the absence of a measurement, NOT "
            "evidence of independence.\n"
            "Re-run harder: raise --n-items, change --seed, and prefer a set "
            "the seats actually disagree on. A panel that never errs on the "
            "probe cannot be measured by it."
        )
    # SATURATION AND COLLAPSE BOTH PRODUCE A HIGH rho AND MEAN OPPOSITE THINGS.
    #
    # Seats sharing a blind spot score WELL and fail together on a few items:
    # that is collapse, and cutting seats is the right response. Seats drowning
    # in a probe too hard for them fail nearly everything together, which also
    # correlates perfectly -- but says nothing about independence, only that
    # the questions were too hard. Recommending a cut there would retire seats
    # on the strength of a broken measurement.
    if mean_accuracy is not None and mean_accuracy < 0.6 and rho > 0.5:
        return (
            f"NO VERDICT -- PROBE SATURATED. rho={rho:.3f} is high, but the "
            f"seats averaged only {mean_accuracy:.0%} correct.\n"
            f"Seats that fail nearly everything correlate perfectly without "
            f"that meaning they share a blind spot, so this cannot tell "
            f"collapse from questions that were simply too hard.\n"
            f"Re-run with an easier set (change --seed) before cutting "
            f"anything."
        )
    if rho <= 0.2:
        return (f"KEEP FIVE SEATS. rho={rho:.3f} is at or below the ~0.2 "
                f"convention, so the seats are erring largely independently "
                f"and each one is still buying new coverage.")
    if rho <= 0.5:
        return (f"MARGINAL. rho={rho:.3f} is above the ~0.2 convention: the "
                f"seats share a meaningful part of their errors. Three seats "
                f"chosen for spread will likely buy most of what five buy.")
    return (f"CUT SEATS. rho={rho:.3f} means the seats mostly fail together. "
            f"You are paying {n_seats} times for close to one opinion. "
            f"Cut the lowest-accuracy seats in the table above, and replace "
            f"them with more different ones rather than adding more.")


def render_calibration(res: CalibrationResult) -> str:
    out: list[str] = []
    out.append("=" * 72)
    out.append("SEAT INDEPENDENCE CALIBRATION")
    out.append("=" * 72)
    n_true = sum(1 for i in res.items if i.is_true)
    out.append(f"items          : {len(res.items)} "
               f"({n_true} true, {len(res.items) - n_true} false)")
    out.append(f"seats asked    : {len(res.seats)} -- {', '.join(res.seats)}")
    out.append(f"regime         : {res.report.get('task_kind')}")
    out.append("")

    if res.excluded_seats:
        out.append("-" * 72)
        out.append(f"SEATS EXCLUDED FROM THE MEASUREMENT "
                   f"({len(res.excluded_seats)} of {len(res.seats)})")
        out.append("-" * 72)
        for seat, why in sorted(res.excluded_seats.items()):
            out.append(f"  {seat}: {why}")
        out.append("")
        out.append(f"  The number below describes {len(res.scored_seats)} "
                   f"seat(s), NOT the {len(res.seats)} you are paying for.")
        out.append("  An excluded seat is an absence, not an opinion, so it is")
        out.append("  left out rather than scored. Fix the seat and re-run")
        out.append("  before making a spending decision on this.")
        out.append("")

    if res.unmatched_claims:
        out.append("-" * 72)
        out.append("CONFIRMATIONS THAT MATCHED NO ITEM ID")
        out.append("-" * 72)
        for seat, texts in sorted(res.unmatched_claims.items()):
            shown = ", ".join(texts[:5])
            more = f" (+{len(texts) - 5} more)" if len(texts) > 5 else ""
            out.append(f"  {seat}: {shown}{more}")
        out.append("  These seats did not put the bare item id in the text")
        out.append("  field, so their confirmations were scored as separate")
        out.append("  items rather than agreement. The number below")
        out.append("  UNDERSTATES their agreement with the others. Re-run")
        out.append("  before trusting it.")
        out.append("")

    if not res.report.get("measurable"):
        out.append("-" * 72)
        out.append("NOT MEASURABLE")
        out.append("-" * 72)
        for b in res.report.get("blockers", []):
            out.append(f"  - {b}")
        out.append("")
        out.append("=" * 72)
        out.append(verdict_line(None, len(res.seats)))
        out.append("=" * 72)
        return "\n".join(out)

    cov = res.report.get("coverage_summary")
    if cov:
        out.append(f"coverage       : {cov}")
    rho = res.rho
    n_eff = res.effective_seats
    out.append("-" * 72)
    out.append("RESULT")
    out.append("-" * 72)
    out.append(f"  error correlation (rho) : "
               f"{'undefined' if rho_undefined(rho) else f'{rho:.3f}'}")
    out.append(f"  effective seats         : "
               f"{'undefined' if n_eff is None or math.isnan(n_eff) else f'{n_eff:.2f}'} "
               f"of {len(res.seats)} paid for")
    out.append("")
    reading = res.report.get("reading")
    if reading:
        out.append("  " + reading)
    out.append("")

    if res.seat_accuracy:
        out.append("-" * 72)
        out.append("PER SEAT -- which ones to keep if you cut")
        out.append("-" * 72)
        out.append(f"  {'seat':<16}{'confirmed':>11}{'accuracy':>11}")
        for seat in sorted(res.seat_accuracy,
                           key=lambda s: -res.seat_accuracy[s]):
            out.append(f"  {seat:<16}{res.confirmations.get(seat, 0):>11}"
                       f"{res.seat_accuracy[seat]:>10.0%}")
        out.append("")
        out.append("  A seat that confirmed far fewer than the others may have")
        out.append("  been cut off mid-reply rather than judging the rest")
        out.append("  false -- from the text alone those look identical.")
        out.append("")

    out.append("=" * 72)
    out.append(verdict_line(rho, len(res.scored_seats), res.mean_accuracy))
    out.append("=" * 72)
    out.append("")
    out.append("SCOPE: this measures agreement on ARITHMETIC only. A panel")
    out.append("independent here may still share a blind spot on domain")
    out.append("reasoning. Re-run when a vendor ships a new model.")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# demo seats -- no network, no spend
# ---------------------------------------------------------------------------

def _demo_seat(items: Sequence[Item], wrong_on: set[str]) -> Callable[[str], str]:
    """A synthetic seat that confirms every true item except those it is
    scripted to miss, and wrongly confirms every false item in `wrong_on`."""
    def seat(_prompt: str) -> str:
        lines = []
        for it in items:
            confirm = it.is_true if it.item_id not in wrong_on else not it.is_true
            if confirm:
                lines.append(
                    f"CLAIM | arithmetic | {it.expression} | {it.expression}")
        return "\n".join(lines)
    return seat


def _demo_seats(items: Sequence[Item]) -> dict[str, Callable[[str], str]]:
    """Five seats that each slip on DIFFERENT items -- the independent case."""
    ids = [it.item_id for it in items]
    return {
        f"seat_{k + 1}": _demo_seat(items, {ids[k], ids[(k + 5) % len(ids)]})
        for k in range(5)
    }


def _collapsed_demo_seats(items: Sequence[Item]) -> dict[str, Callable[[str], str]]:
    """Five seats that slip on the SAME items -- the collapse case."""
    ids = [it.item_id for it in items]
    shared = {ids[0], ids[1], ids[2]}
    return {f"seat_{k + 1}": _demo_seat(items, shared) for k in range(5)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Measure how independent the five real seats actually are."
    )
    ap.add_argument("--profiles", default="profiles.json",
                    help="settings file with each seat's request shape")
    ap.add_argument("--env", metavar="PATH",
                    help="path to the .env holding the seat credentials")
    ap.add_argument("--n-items", type=int, default=DEFAULT_N_ITEMS,
                    help=f"how many propositions, even (default {DEFAULT_N_ITEMS})")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED,
                    help="item-set seed; the same seed gives the same items")
    ap.add_argument("--max-cost", type=float, metavar="USD",
                    help="hard ceiling for this calibration run")
    ap.add_argument("--seat5", choices=("external", "in-process"),
                    default="external")
    ap.add_argument("--json", metavar="PATH",
                    help="also write the raw report as JSON")
    ap.add_argument("--demo", action="store_true",
                    help="synthetic seats: no network, no spend")
    ap.add_argument("--demo-collapsed", action="store_true",
                    help="synthetic seats that all fail together")
    args = ap.parse_args(argv)

    try:
        items = build_items(args.n_items, args.seed)
    except ValueError as exc:
        print(f"CALIBRATION NOT STARTED: {exc}", file=sys.stderr)
        return 2

    if args.demo or args.demo_collapsed:
        seats = (_collapsed_demo_seats(items) if args.demo_collapsed
                 else _demo_seats(items))
    else:
        # Imported here so --demo needs no credentials, no settings file, and
        # no network stack: the demo path must stay runnable on a machine that
        # has never been connected.
        import run_adjudication as RA
        from adjudication_orchestrator import (
            PANEL_OF_FIVE,
            PANEL_OF_FIVE_EXTERNAL,
        )

        ledger = None
        if args.max_cost is not None:
            ledger = RA.build_ledger(args.max_cost, None, None)
        try:
            RA.load_env_file(args.env)
            seats = RA.live_seats(
                args.profiles,
                specs=(PANEL_OF_FIVE if args.seat5 == "in-process"
                       else PANEL_OF_FIVE_EXTERNAL),
                ledger=ledger,
            )
        except Exception as exc:  # noqa: BLE001 - fail closed with the reason
            print(f"CALIBRATION NOT STARTED: {exc}", file=sys.stderr)
            print("Nothing was sent and nothing was spent.", file=sys.stderr)
            return 2

    res = run_calibration(seats, items)
    print(render_calibration(res))

    if args.json:
        payload = {
            "seats": list(res.seats),
            "n_items": len(res.items),
            "seed": args.seed,
            "rho": res.rho,
            "effective_seats": res.effective_seats,
            "measurable": res.report.get("measurable"),
            "blockers": res.report.get("blockers", []),
            "seat_errors": res.seat_errors,
            "unmatched_claims": res.unmatched_claims,
        }
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
        print(f"\nraw report written to {args.json}")

    # A run that produced no number is not a success: a caller that treats
    # exit 0 as "calibrated" must not get one from a run that measured nothing.
    #
    # `measurable` is TRUE for a NaN rho -- the matrix was built and scored,
    # there was simply no variation to correlate. That distinction matters
    # inside correctness_matrix and not at all to a phone-triggered workflow
    # reading an exit code, so both are non-zero here.
    if not res.report.get("measurable") or rho_undefined(res.rho):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
