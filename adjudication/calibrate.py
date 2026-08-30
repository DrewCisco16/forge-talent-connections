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

import numpy as np

import adjudication_orchestrator as AO
import seat_independence as si
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

DEFAULT_N_ITEMS = 60
DEFAULT_SEED = 20260829
DEFAULT_DRAWS = 2000
CREDIBLE_MASS = 0.90


# ---------------------------------------------------------------------------
# the item set
# ---------------------------------------------------------------------------

BANDS = ("easy", "medium", "hard")
"""Difficulty bands, spanned rather than averaged.

THE PROBE HAS TO BE EASY ENOUGH TO ANSWER AND HARD ENOUGH TO SEPARATE, and
picking one difficulty is a compromise between those, which is the wrong move:
it can only be wrong in one of the two directions and cannot tell you which.
Both earlier item sets failed that way. Three-digit addition was too easy --
every seat scored identically, no pair varied, rho came back NaN. Guessing
harder fixes nothing in principle: too hard and every seat fails everything,
which correlates perfectly and reads as collapse.

Spanning the range separates the two requirements instead of trading them off.
Whatever the panel's ability, some band sits at it, and the per-band table
shows WHERE that is rather than leaving a single ambiguous number. A run where
easy is 100% and hard is 0% is legible; the same panel measured on one middle
difficulty is not.
"""


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
    band: str = "medium"


def _draw(band: str, rng: random.Random) -> tuple[int, int, str, int]:
    """One operand pair for a band. Returns (a, b, operator, true result)."""
    if band == "easy":
        a, b = rng.randint(11, 89), rng.randint(11, 89)
        return a, b, "+", a + b
    if band == "medium":
        a, b = rng.randint(114, 989), rng.randint(113, 987)
        return a, b, "*", a * b
    a, b = rng.randint(1104, 9897), rng.randint(114, 989)
    return a, b, "*", a * b


def build_items(n: int = DEFAULT_N_ITEMS, seed: int = DEFAULT_SEED) -> list[Item]:
    """
    A reproducible set: half true, half false, spread evenly across BANDS.

    BOTH POLARITIES ARE REQUIRED, and this is the whole reason the set is not
    just validation_harness.SEEDED. Every seeded defect there is TRUE
    arithmetic, so a seat that confirms everything scores perfectly. With no
    false item there is no way to be wrong by over-asserting, the only error
    left is silence, and the statistic measures eagerness rather than
    correctness. The false items are what make confirming everything cost
    something.

    Truth alternates by CYCLE rather than by index, so each band gets the same
    number of true and false items FOR ANY NUMBER OF BANDS.

    Index parity (`truth = k % 2 == 0`) happens to balance at three bands,
    because three is odd and each band therefore sees alternating parities.
    It is not equivalent, it is coincidentally equal here: at four bands it
    pins band 0 to true and band 1 to false permanently, and a band whose
    polarity is fixed rewards guessing in one direction. Verified by
    enumeration at nb=3 (balanced) and nb=4 (8/0 split). The cycle form does
    not depend on that coincidence.
    """
    period = 2 * len(BANDS)
    if n < period:
        raise ValueError(
            f"need at least {period} items to fill every band with both "
            f"polarities, got {n}")
    if n % period:
        raise ValueError(
            f"n_items must be a multiple of {period} so every band gets an "
            f"equal number of true and false items, got {n}")

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
    # answer-key entries. No collision appears below n=1000, which is exactly
    # why this is enforced rather than relied upon: the failure is silent and
    # only shows up at scale.
    seen_operands: set[tuple[int, int, str]] = set()
    for k in range(n):
        band = BANDS[k % len(BANDS)]
        truth = (k // len(BANDS)) % 2 == 0
        while True:
            a, b, expr_op, true_result = _draw(band, rng)
            if (a, b, expr_op) not in seen_operands:
                seen_operands.add((a, b, expr_op))
                break
        # A false item is off by a small amount, never zero, so the statement
        # is genuinely false but not obviously so. An answer off by an order
        # of magnitude is caught by inspection and measures nothing.
        result = true_result if truth else true_result + rng.choice(
            [-9, -6, -3, -2, -1, 1, 2, 3, 6, 9])
        items.append(Item(f"S{k + 1:02d}", f"{a} {expr_op} {b} = {result}",
                          truth, band))
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
    rho_discriminating: float | None
    """rho recomputed over only the items the seats did NOT all answer alike.

    THE HEADLINE rho AND THIS ONE ANSWER DIFFERENT QUESTIONS, and collapsing
    them into one number is what produced a wrong recommendation.

    seat_independence guards against a zero-variance SEAT (a column that is
    constant) but not a zero-variance ITEM (a row that is). A band every seat
    fails enters the correlation as perfect agreement, by construction, and
    drags rho up. Measured: a panel that was genuinely independent on the band
    that discriminated it -- each seat slipping on a different medium item --
    scored rho 0.768 and was told to CUT SEATS, because ten hard items nobody
    got right were counted as ten instances of failing together.

    Both readings are legitimate and they are answers to different questions:

      headline rho  -- "do these seats fail together on this probe?"  Five
                       seats missing the same item IS shared failure, and
                       excluding it would hide the finding.
      this one      -- "on the items that could tell them apart, do they fail
                       together?"  That is the question a decision to drop a
                       seat actually rests on.

    They are reported side by side and, when they disagree materially, no
    single verdict is issued. A tie broken by anything other than evidence is
    the vote this design exists to avoid.
    """
    rho_ci: tuple[float, float] | None
    """90% interval for rho, by resampling items. See rho_interval.

    THE VERDICT IS DECIDED BY THIS, NOT BY THE POINT ESTIMATE. rho=0.19 and
    rho=0.21 are the same measurement when the interval spans 0.1 to 0.3, and
    letting a threshold crossing between them flip a spending recommendation
    reads a precision the run does not have.
    """
    seat_accuracy_ci: dict[str, tuple[float, float]]
    """seat_id -> 90% Beta posterior interval on its accuracy. Two seats a few
    points apart over 60 items are not distinguishable, and "cut the lowest"
    needs to know that."""
    n_unanimous_items: int
    """Items every scored seat answered identically -- correlated by
    construction, contributing no information about independence."""
    band_accuracy: dict[str, tuple[int, float]]
    """band -> (items scored, mean accuracy). See _band_accuracy: this is what
    tells a saturated probe from a collapsed panel, and where to set the
    difficulty next time."""
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
    draws: int = DEFAULT_DRAWS,
    seed: int = DEFAULT_SEED,
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

    # ADJUDICATE EVERY ITEM, NOT ONLY THE ONES A SEAT SPOKE ABOUT.
    #
    # build_correctness_matrix builds its rows from the VERDICTS, and a
    # statement nobody proposed is never gated and never becomes a row. That
    # silently deletes the most dangerous finding this tool exists to catch:
    # when all five seats MISS the same true statement, no seat asserts it, no
    # verdict exists, and the shared blind spot leaves no trace at all.
    # Measured: five seats all missing three true items produced a 9-row
    # matrix and rho = NaN. Five seats all asserting three FALSE items -- the
    # visible half of the same behaviour -- produced 15 rows and rho = 1.0.
    #
    # Seeding the full item set fixes it without crediting anyone: the seat
    # that asserted a claim is read from the RESPONSES, not from the claims
    # passed here, so an item nobody spoke about scores every seat as silent,
    # which for a true item is exactly the miss it was.
    seeded = [
        AO.Claim(
            AO.content_claim_id(AO.ClaimKind.ARITHMETIC,
                                it.expression, it.expression),
            it.expression, AO.ClaimKind.ARITHMETIC, it.expression,
            CALIBRATION_PASS.id, "",
        )
        for it in chosen
    ]
    record = orch.run_pass(CALIBRATION_PASS, [], claims + seeded)
    result = SequentialPassResult(
        CALIBRATION_PASS.id, CALIBRATION_PASS.name, record,
        measure_divergence(CALIBRATION_PASS, usable), usable,
    )

    matrix = build_correctness_matrix([result], orch.verdicts)
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
        seat_accuracy=_seat_accuracy(matrix),
        rho_ci=rho_interval(matrix, draws=draws, seed=seed),
        seat_accuracy_ci=seat_accuracy_interval(matrix),
        band_accuracy=_band_accuracy(matrix, chosen),
        rho_discriminating=_discriminating_rho(matrix),
        n_unanimous_items=_n_unanimous(matrix),
    )


def rho_interval(
    matrix: CorrectnessMatrix,
    draws: int = DEFAULT_DRAWS,
    seed: int = DEFAULT_SEED,
) -> tuple[float, float] | None:
    """A 90% interval for rho, by resampling ITEMS with replacement.

    WHY THIS EXISTS. Every earlier version reported rho as a bare number and
    let a spending decision rest on which side of 0.2 or 0.5 it fell. With 60
    items and 5 seats that is a point estimate carrying unstated sampling
    error, and seat_independence's own reading line already said as much --
    "a small number of items makes rho unstable regardless of its value" --
    while nothing in the pipeline did anything about it. This is the interval
    that line was asking for.

    WHAT IT IS AND IS NOT. This is Monte Carlo resampling -- a bootstrap over
    the item axis -- NOT Markov-chain Monte Carlo. Nothing here needs a chain:
    draws are independent and the statistic is cheap, so a sampler with
    burn-in and convergence diagnostics would add machinery and no accuracy.
    Calling it MCMC would overstate what was done, which is the failure this
    codebase exists to refuse.

    Items are the resampling unit because items are what the run has many of
    and what the correlation is computed across. Seats are not resampled:
    there are five, they are the population rather than a sample of one, and
    resampling them would answer a question nobody asked.

    Seeded, so a replay reproduces the interval exactly (global rule 4).
    Returns None when fewer than three draws yield a defined rho -- an
    interval computed from almost nothing is worse than no interval.
    """
    if matrix.X.size == 0 or matrix.X.shape[0] < 2 or len(matrix.seats) < 2:
        return None
    rng = np.random.default_rng(seed)
    n_rows = matrix.X.shape[0]
    got: list[float] = []
    for _ in range(max(1, draws)):
        idx = rng.integers(0, n_rows, n_rows)
        value = si.mean_error_correlation(matrix.X[idx])
        if not math.isnan(value):
            got.append(float(value))
    if len(got) < 3:
        return None
    tail = (1.0 - CREDIBLE_MASS) / 2.0 * 100.0
    arr = np.asarray(got)
    return (float(np.percentile(arr, tail)),
            float(np.percentile(arr, 100.0 - tail)))


def seat_accuracy_interval(
    matrix: CorrectnessMatrix,
) -> dict[str, tuple[float, float]]:
    """Per-seat accuracy as a Beta posterior interval, not a bare percentage.

    Conjugate and exact: a Jeffreys prior Beta(0.5, 0.5) updated by the seat's
    correct and incorrect counts. No sampling is involved, because for a
    binomial likelihood the posterior has a closed form and drawing from it
    would only add noise to a number already known exactly.

    The point of it is the decision it feeds. "Cut the lowest-accuracy seats"
    ranks five numbers that each carry sampling error, and two seats a few
    points apart over 60 items are not distinguishable. The interval is what
    says whether a gap between two seats is real.
    """
    if matrix.X.size == 0 or not matrix.seats:
        return {}
    out: dict[str, tuple[float, float]] = {}
    n_rows = matrix.X.shape[0]
    for i, seat in enumerate(matrix.seats):
        correct = int(matrix.X[:, i].sum())
        alpha, beta_ = 0.5 + correct, 0.5 + (n_rows - correct)
        tail = (1.0 - CREDIBLE_MASS) / 2.0
        out[seat] = (float(_beta_quantile(alpha, beta_, tail)),
                     float(_beta_quantile(alpha, beta_, 1.0 - tail)))
    return out


def _beta_quantile(alpha: float, beta_: float, q: float) -> float:
    """Beta inverse CDF by bisection on the regularised incomplete beta.

    Hand-rolled rather than pulled from scipy: scipy is not a dependency of
    this project and adding one for a single quantile would be a poor trade.
    Bisection on a monotone CDF over [0, 1] converges to well past the
    precision anything downstream displays.
    """
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if _beta_cdf(mid, alpha, beta_) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _beta_cdf(x: float, alpha: float, beta_: float) -> float:
    """Regularised incomplete beta via its continued fraction."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (alpha * math.log(x) + beta_ * math.log1p(-x)
                 + math.lgamma(alpha + beta_)
                 - math.lgamma(alpha) - math.lgamma(beta_))
    front = math.exp(log_front)
    if x < (alpha + 1.0) / (alpha + beta_ + 2.0):
        return front * _beta_cf(x, alpha, beta_) / alpha
    return 1.0 - front * _beta_cf(1.0 - x, beta_, alpha) / beta_


def _beta_cf(x: float, alpha: float, beta_: float) -> float:
    """Continued fraction for the incomplete beta, by modified Lentz.

    This is the Numerical Recipes `betacf` recurrence, kept faithful to it
    rather than rewritten as a generic Lentz loop. The generic form was tried
    first and was WRONG: it returned f - 1, dropping the leading term this
    particular fraction does not carry, and Beta(1, 1) -- which is exactly
    Uniform(0, 1) -- returned a 5th percentile of 0.0528 instead of 0.0500.
    Caught by checking against closed forms rather than by inspection.
    """
    tiny = 1e-300
    qab, qap, qam = alpha + beta_, alpha + 1.0, alpha - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (beta_ - m) * x / ((qam + m2) * (alpha + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(alpha + m) * (qab + m) * x / ((alpha + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return h


def _unanimous_mask(matrix: CorrectnessMatrix) -> Any:
    """Rows where every scored seat gave the same answer."""
    if matrix.X.size == 0 or len(matrix.seats) < 2:
        return None
    return matrix.X.min(axis=1) == matrix.X.max(axis=1)


def _n_unanimous(matrix: CorrectnessMatrix) -> int:
    mask = _unanimous_mask(matrix)
    return 0 if mask is None else int(mask.sum())


def _discriminating_rho(matrix: CorrectnessMatrix) -> float | None:
    """rho over the items that actually separated the seats.

    Returns None when there are none, or too few to mean anything -- a
    correlation over one or two rows is not a measurement, and reporting it
    beside the headline would lend it equal weight.
    """
    mask = _unanimous_mask(matrix)
    if mask is None:
        return None
    keep = matrix.X[~mask]
    if keep.shape[0] < 3:
        return None
    rho = si.mean_error_correlation(keep)
    return None if math.isnan(rho) else float(rho)


def _band_accuracy(matrix: CorrectnessMatrix,
                   items: Sequence[Item]) -> dict[str, tuple[int, float]]:
    """band -> (items scored, mean accuracy across all seats).

    THIS IS WHAT MAKES A BAD NUMBER DIAGNOSABLE. rho alone cannot say whether
    a panel failed because it shares a blind spot or because the questions
    were beyond it; "easy 100%, hard 0%" says which, and says where to set the
    probe next time. It also exposes the case a single difficulty hides
    entirely: a band with no variation contributed nothing to the
    correlation, however many items it held.
    """
    if not matrix.seats or matrix.X.size == 0:
        return {}
    # Keyed by CLAIM ID, not by expression: matrix.item_ids holds the
    # content-addressed hashes, and the id is computed the same way the
    # snapping extractor computes it so the two cannot drift apart.
    band_of = {
        AO.content_claim_id(AO.ClaimKind.ARITHMETIC,
                            it.expression, it.expression): it.band
        for it in items
    }
    rows: dict[str, list[float]] = {}
    for row, claim_id in enumerate(matrix.item_ids):
        band = band_of.get(claim_id)
        if band is None:
            continue
        rows.setdefault(band, []).extend(
            float(v) for v in matrix.X[row, :])
    return {b: (len(v) // len(matrix.seats), sum(v) / len(v))
            for b, v in rows.items() if v}


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


def _items_to_resolve(rho: float, ci: tuple[float, float],
                      edge: float, n_items: int) -> int | None:
    """Roughly how many items would pull the interval clear of a threshold.

    A bootstrap interval narrows about as 1/sqrt(n), so to shrink the current
    half-width to the distance between the estimate and the threshold needs
    n * (half_width / distance)^2 items. Stated as an estimate because that
    scaling is asymptotic and the true rate depends on the panel; it is the
    difference between "re-run with more" and "re-run with roughly this
    many", which is the difference between advice and a shrug.
    """
    if n_items <= 0:
        return None
    half = (ci[1] - ci[0]) / 2.0
    distance = abs(rho - edge)
    if half <= 0 or distance <= 1e-9:
        return None
    needed = math.ceil(n_items * (half / distance) ** 2)
    period = 2 * len(BANDS)
    needed = ((needed + period - 1) // period) * period
    # A CAP, BECAUSE AN IMPRACTICAL NUMBER IS NOT ADVICE.
    #
    # When the estimate sits almost exactly on the threshold the distance
    # goes to zero and this explodes -- 12,618 items for rho=0.190 against a
    # 0.2 edge. That figure is arithmetically right and useless: it reads as
    # a plan and is not one, and the honest reading is that the true value
    # may BE the threshold, which no sample size resolves. Ten times the
    # default is the largest that still rides in one call per seat.
    if needed > DEFAULT_N_ITEMS * 10:
        return None
    return needed if needed > n_items else None


def _decision_band(rho: float) -> str:
    """Which recommendation a rho maps to. The thresholds live here once, so
    the conflict check and the verdict cannot drift apart."""
    if rho <= 0.2:
        return "keep"
    return "marginal" if rho <= 0.5 else "cut"


@dataclass(frozen=True)
class RhoReading:
    """Everything the verdict depends on, in one value.

    Collected into an object because the argument list had grown to six
    scalars and the linter was right to object: a verdict that depends on six
    loose numbers is one where a caller can silently pass them in the wrong
    order. `of()` builds it from a result so the report cannot disagree with
    what was measured.
    """
    rho: float | None
    n_seats: int
    mean_accuracy: float | None = None
    rho_discriminating: float | None = None
    rho_ci: tuple[float, float] | None = None
    n_items: int = 0

    @classmethod
    def of(cls, res: CalibrationResult) -> RhoReading:
        return cls(
            rho=res.rho,
            n_seats=len(res.scored_seats),
            mean_accuracy=res.mean_accuracy,
            rho_discriminating=res.rho_discriminating,
            rho_ci=res.rho_ci,
            n_items=res.report.get("coverage").n_items  # type: ignore[union-attr]
            if res.report.get("coverage") is not None else 0,
        )


NO_RHO = (
    "NO VERDICT: rho was not produced, so nothing here justifies keeping or "
    "cutting a seat.\n"
    "If the seats all scored identically, the probe was too easy to separate "
    "them -- that is the absence of a measurement, NOT evidence of "
    "independence.\n"
    "Re-run harder: raise --n-items, change --seed, and prefer a set the "
    "seats actually disagree on. A panel that never errs on the probe cannot "
    "be measured by it."
)


def _saturated(r: RhoReading) -> str | None:
    """Seats failing nearly everything correlate perfectly without sharing a
    blind spot. Recommending a cut there retires seats on a broken probe."""
    if r.rho is None or r.mean_accuracy is None:
        return None
    if r.mean_accuracy < 0.6 and r.rho > 0.5:
        return (
            f"NO VERDICT -- PROBE SATURATED. rho={r.rho:.3f} is high, but the "
            f"seats averaged only {r.mean_accuracy:.0%} correct.\n"
            f"Seats that fail nearly everything correlate perfectly without "
            f"that meaning they share a blind spot, so this cannot tell "
            f"collapse from questions that were simply too hard.\n"
            f"Re-run with an easier set (change --seed) before cutting "
            f"anything."
        )
    return None


def _readings_conflict(r: RhoReading) -> str | None:
    """Two legitimate answers to different questions. Picking one would be
    breaking a tie by preference rather than by evidence."""
    if r.rho is None or r.rho_discriminating is None:
        return None
    if _decision_band(r.rho) == _decision_band(r.rho_discriminating):
        return None
    return (
        f"NO SINGLE VERDICT -- THE TWO READINGS DISAGREE.\n"
        f"  Over ALL items          rho={r.rho:.3f}  "
        f"(do they fail together on this probe?)\n"
        f"  Over discriminating     rho={r.rho_discriminating:.3f}  "
        f"(do they fail together where they could differ?)\n"
        f"The gap means items every seat answered alike are driving the "
        f"headline; those correlate by construction and say nothing about "
        f"independence.\n"
        f"Read the difficulty table: a band at 0% or 100% contributed "
        f"nothing. Re-run with the probe centred on the band that "
        f"discriminated, then decide."
    )


def _interval_straddles(r: RhoReading) -> str | None:
    """The interval decides, not the point estimate."""
    if r.rho is None or r.rho_ci is None:
        return None
    lo, hi = r.rho_ci
    if _decision_band(lo) == _decision_band(hi):
        return None
    edge = 0.2 if hi <= 0.5 else 0.5
    needed = _items_to_resolve(r.rho, r.rho_ci, edge, r.n_items)
    if needed is None:
        more = ("\nNo practical item count resolves this: the estimate sits "
                "essentially ON the threshold, and the true value may be the "
                "threshold. Treat the panel as borderline and decide on cost, "
                "not on this number.")
    else:
        more = (f"\nAbout {needed} items would likely resolve it (interval "
                f"width scales with 1/sqrt(n); an estimate, not a guarantee).")
    return (
        f"NOT RESOLVED AT THIS SAMPLE SIZE. rho={r.rho:.3f}, but the "
        f"{int(CREDIBLE_MASS * 100)}% interval runs [{lo:.3f}, {hi:.3f}] "
        f"and crosses the {edge} threshold.\n"
        f"The point estimate and the interval disagree about which "
        f"recommendation applies, so the run cannot support either.{more}"
    )


def verdict_line(reading: RhoReading) -> str:
    """
    What the operator should DO about this measurement.

    The thresholds are conventions -- five seats are justified only at
    rho <= ~0.2 -- named as such rather than derived. Every refusal below
    comes before them, because a threshold applied to a number that does not
    support it is worse than no threshold at all.
    """
    # Bound to a local BEFORE the guard so the TypeGuard narrows it. Calling
    # rho_measured(reading.rho) narrows nothing -- a type checker cannot
    # assume an attribute is unchanged between two reads -- and the fix for
    # that is not an assert, which bandit flags in production code.
    rho = reading.rho
    if not rho_measured(rho):
        return NO_RHO
    for check in (_saturated, _readings_conflict, _interval_straddles):
        refusal = check(reading)
        if refusal is not None:
            return refusal
    if rho <= 0.2:
        return (f"KEEP FIVE SEATS. rho={rho:.3f} is at or below the ~0.2 "
                f"convention, so the seats are erring largely independently "
                f"and each one is still buying new coverage.")
    if rho <= 0.5:
        return (f"MARGINAL. rho={rho:.3f} is above the ~0.2 convention: the "
                f"seats share a meaningful part of their errors. Three seats "
                f"chosen for spread will likely buy most of what five buy.")
    return (f"CUT SEATS. rho={rho:.3f} means the seats mostly fail together. "
            f"You are paying {reading.n_seats} times for close to one "
            f"opinion. Cut the lowest-accuracy seats in the table above, and "
            f"replace them with more different ones rather than adding more.")


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
        out.append(NO_RHO)
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
    if res.rho_ci is not None:
        lo, hi = res.rho_ci
        out.append(f"  {int(CREDIBLE_MASS * 100)}% interval          : "
                   f"[{lo:.3f}, {hi:.3f}]  <- the verdict is decided by this,"
                   f" not the point estimate")
    if res.rho_discriminating is not None:
        out.append(f"  rho, discriminating only: "
                   f"{res.rho_discriminating:.3f} "
                   f"({res.n_unanimous_items} item(s) excluded as unanimous)")
    out.append(f"  effective seats         : "
               f"{'undefined' if n_eff is None or math.isnan(n_eff) else f'{n_eff:.2f}'} "
               f"of {len(res.seats)} paid for")
    out.append("")
    reading = res.report.get("reading")
    if reading:
        out.append("  " + reading)
    out.append("")

    if res.band_accuracy:
        out.append("-" * 72)
        out.append("BY DIFFICULTY -- where this panel's ability actually sits")
        out.append("-" * 72)
        out.append(f"  {'band':<10}{'items':>8}{'accuracy':>11}")
        for band in BANDS:
            if band not in res.band_accuracy:
                continue
            n_items, acc = res.band_accuracy[band]
            out.append(f"  {band:<10}{n_items:>8}{acc:>10.0%}")
        out.append("")
        out.append("  A band every seat got right, or every seat got wrong,")
        out.append("  contributed nothing to the correlation. If the easy band")
        out.append("  is 100% and the hard band 0%, the probe bracketed this")
        out.append("  panel and the middle band carried the measurement.")
        out.append("")

    if res.seat_accuracy:
        out.append("-" * 72)
        out.append("PER SEAT -- which ones to keep if you cut")
        out.append("-" * 72)
        out.append(f"  {'seat':<14}{'confirmed':>10}{'accuracy':>10}"
                   f"{'  90% interval':>16}")
        for seat in sorted(res.seat_accuracy,
                           key=lambda s: -res.seat_accuracy[s]):
            ci = res.seat_accuracy_ci.get(seat)
            span = f"  [{ci[0]:.0%}, {ci[1]:.0%}]" if ci else ""
            out.append(f"  {seat:<14}{res.confirmations.get(seat, 0):>10}"
                       f"{res.seat_accuracy[seat]:>9.0%}{span:>16}")
        out.append("")
        out.append("  Two seats whose intervals OVERLAP are not")
        out.append("  distinguishable at this sample size -- do not cut one")
        out.append("  and keep the other on the strength of the gap.")
        out.append("  A seat that confirmed far fewer than the others may have")
        out.append("  been cut off mid-reply rather than judging the rest")
        out.append("  false -- from the text alone those look identical.")
        out.append("")

    out.append("=" * 72)
    out.append(verdict_line(RhoReading.of(res)))
    out.append("=" * 72)
    out.append("")
    # WHOSE QUESTION IS THIS REPORT ANSWERING?
    #
    # Everything above is framed for the budget-holder: how many seats to pay
    # for next time. That framing hides the other reader entirely -- whoever
    # relies on an answer this panel already produced. A high rho is not only
    # a forward-looking spending signal; it says the agreement in runs ALREADY
    # COMPLETED was worth less than it looked, and nothing else in the system
    # will ever tell them so.
    if rho_measured(rho) and rho > 0.5:
        out.append("-" * 72)
        out.append("BACKWARD-LOOKING IMPLICATION -- read this before cutting")
        out.append("-" * 72)
        out.append(f"  rho={rho:.3f} does not only bear on what to buy next.")
        out.append("  Convergence in runs ALREADY COMPLETED with this panel")
        out.append("  was worth less than it appeared: seats agreeing while")
        out.append("  sharing errors is what this number measures.")
        out.append("  Re-examine any conclusion whose confidence rested on")
        out.append("  those seats agreeing. Cutting seats does not undo it.")
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
# preflight -- prevention rather than detection
# ---------------------------------------------------------------------------

REJECTED_SAMPLING_KEYS = ("temperature", "top_p", "top_k")

def preflight_settings(path: str) -> list[str]:
    """Problems that would cost money to discover. Empty list means clear.

    DETECTING A FAILURE AFTER PAYING FOR IT IS NOT THE SAME AS PREVENTING IT.
    The rest of this module reports what went wrong once the calls are made;
    this runs before any of them.

    The case it exists for: profiles.example.json templates
    "temperature": "{{temperature}}" in all five seat blocks, and the current
    Claude models -- Fable 5, Opus 5, Sonnet 5 and the 4.6/4.7/4.8 family --
    REMOVED the sampling parameters. Sending one returns HTTP 400. The seat is
    then excluded and the run measures four seats instead of five, which is a
    degraded measurement the operator has already paid for. The settings
    checker does not catch it: it only looks for FILL-IN markers.

    Returns strings rather than raising, so the caller decides whether a
    finding blocks the run or is merely printed.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, ValueError) as exc:
        return [f"settings file could not be read: {exc}"]
    if not isinstance(cfg, dict):
        return ["settings file is not a JSON object"]

    problems: list[str] = []
    for seat_id, block in sorted(cfg.items()):
        if seat_id.startswith("_") or not isinstance(block, dict):
            continue
        endpoint = str(block.get("endpoint", ""))
        body = block.get("body")
        if not isinstance(body, dict) or "anthropic" not in endpoint.lower():
            continue
        present = [k for k in REJECTED_SAMPLING_KEYS if k in body]
        if present:
            problems.append(
                f"seat {seat_id!r} sends {', '.join(present)} to an Anthropic "
                f"endpoint. Current Claude models removed the sampling "
                f"parameters and return HTTP 400 for them. Take "
                f"{'those keys' if len(present) > 1 else 'that key'} out of "
                f"this seat's body block."
            )
    return problems


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
                    help=f"how many propositions; multiple of {2 * len(BANDS)} "
                         f"(default {DEFAULT_N_ITEMS})")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED,
                    help="item-set seed; the same seed gives the same items")
    ap.add_argument("--max-cost", type=float, metavar="USD",
                    help="hard ceiling for this calibration run")
    ap.add_argument("--seat5", choices=("external", "in-process"),
                    default="external")
    ap.add_argument("--json", metavar="PATH",
                    help="also write the raw report as JSON")
    ap.add_argument("--ignore-preflight", action="store_true",
                    help="run even if preflight objects (it refuses by "
                         "default, because the alternative is finding out "
                         "by spending)")
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
        blocking = preflight_settings(args.profiles)
        if blocking and not args.ignore_preflight:
            print("CALIBRATION NOT STARTED -- preflight found problems that "
                  "would cost money to discover:", file=sys.stderr)
            for p in blocking:
                print(f"  - {p}", file=sys.stderr)
            print("Nothing was sent and nothing was spent. Fix these, or pass "
                  "--ignore-preflight if you are certain.", file=sys.stderr)
            return 2

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
