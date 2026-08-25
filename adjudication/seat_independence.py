"""
seat_independence.py
====================
Diagnostics for multi-seat / multi-pass LLM adjudication architectures.

PURPOSE
-------
Distinguishes ELIMINATIVE convergence (seats with partially independent failure
modes progressively remove wrong answers; the survivor is true) from COLLAPSE
convergence (seats share failure modes; passes remove only *detectable*
wrongness; the survivor is a plausible shared error).

Both produce "one answer left." Only the statistics below tell them apart.

INPUT SCHEMA
------------
You need, at minimum, ONE of these two structures:

(A) For independence diagnostics -- a correctness matrix:
      X : array, shape (n_items, n_seats), dtype int
      X[i, j] = 1 if seat j got item i CORRECT, 0 if WRONG.
    Requires items with known ground truth (seeded or held-out).

(B) For capture-recapture -- detection records:
      detections : dict[seat_id -> set[error_id]]
      i.e. which seeded errors each seat caught.

Optionally, for the strongest diagnostic:
      answers : array, shape (n_items, n_seats), dtype object
      the actual answer each seat gave (not just correct/incorrect),
      plus `truth` : array, shape (n_items,)

ASSUMPTIONS AND THEIR VIOLATION DIRECTIONS ARE DOCUMENTED PER FUNCTION.
Read them. Several estimators are BOUNDS, not point estimates, under
positive error correlation -- which is the expected regime here.

References for the estimators (verify before citing):
  - Kish design effect (cluster sampling) -> effective_seats()
  - Lincoln-Petersen / Chapman -> lincoln_petersen()
  - Chao (1987) Chao1 -> chao1()
  - Eckhardt & Lee / Littlewood & Miller N-version models -> independence_gap()
"""

from __future__ import annotations

import itertools
import math
from collections import Counter
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# 1. ERROR CORRELATION AND EFFECTIVE SEAT COUNT
# ---------------------------------------------------------------------------

def pairwise_error_correlation(X: np.ndarray) -> np.ndarray:
    """
    Phi (Pearson on binary) correlation between seats' ERROR indicators.

    Parameters
    ----------
    X : (n_items, n_seats) int array. 1 = correct, 0 = wrong.

    Returns
    -------
    (n_seats, n_seats) array of pairwise correlations on the error indicator
    E = 1 - X. Diagonal is 1.0.

    NOTE: correlation on ERRORS, not on correctness. Two seats that are both
    highly accurate will correlate on correctness trivially; what matters for
    redundancy is whether they fail together.
    """
    X = np.asarray(X, dtype=float)
    E = 1.0 - X
    n_seats = E.shape[1]
    C = np.eye(n_seats)
    for a, b in itertools.combinations(range(n_seats), 2):
        ea, eb = E[:, a], E[:, b]
        # Guard against zero variance (a seat that never errs, or always errs)
        if ea.std() == 0 or eb.std() == 0:
            C[a, b] = C[b, a] = np.nan
            continue
        r = float(np.corrcoef(ea, eb)[0, 1])
        C[a, b] = C[b, a] = r
    return C


def mean_error_correlation(X: np.ndarray) -> float:
    """
    Mean off-diagonal pairwise error correlation (rho). NaNs ignored.

    Returns NaN when there is nothing to average: a single seat has no pairs,
    and a panel of constant seats has no variance in any pair. Both cases are
    handled explicitly rather than left to np.nanmean, which returns NaN with a
    "Mean of empty slice" warning -- the right answer arrived at noisily, and
    noise in a diagnostic is how a real signal gets tuned out. Found by
    property test.
    """
    C = pairwise_error_correlation(X)
    n = C.shape[0]
    if n < 2:
        return float("nan")
    off = C[~np.eye(n, dtype=bool)]
    if off.size == 0 or bool(np.all(np.isnan(off))):
        return float("nan")
    return float(np.nanmean(off))


def effective_seats(n_seats: int, rho: float) -> float:
    """
    Kish design effect applied to seat redundancy.

        n_eff = n / (1 + (n - 1) * rho)

    Interpretation: the number of INDEPENDENT seats your correlated ensemble
    is actually worth. At rho = 0.6 with 5 seats, n_eff ~= 1.47.

    rho is clamped to [0, 1], and both ends matter.

    Below 0: negative correlation would imply n_eff > n, and this function will
    not claim more independence than there are seats.

    Above 1: a Pearson correlation cannot exceed 1, so any such input is a
    measurement or plumbing error. Left unclamped it produces n_eff < 1 --
    effective_seats(2, 2.0) returned 0.67 -- and SOP 6.1 reads this number in
    plain language ("5 seats behave like 1.47"), so "0.67 seats" would be read
    as meaningful rather than as the nonsense it is. Found by property test.
    """
    # NaN IS NOT ZERO. It was clamped to 0.0 by max(0.0, nan) -- which returns
    # nan on some paths and 0.0 on others -- and a rho of 0.0 means perfectly
    # independent seats. So an UNMEASURABLE correlation produced the maximum
    # possible independence and, through confidence_ceiling, HIGH confidence.
    # That is the single worst direction this function can fail in: it is
    # exactly the runs where nobody could measure independence that get told
    # their panel is ideal.
    r = float(rho)
    if math.isnan(r):
        raise ValueError(
            "rho is NaN, which means it could not be measured. It must not be "
            "passed here: treating an unmeasurable correlation as 0.0 reports "
            "a perfectly independent panel. Handle the unmeasured case at the "
            "call site instead."
        )
    rho = min(1.0, max(0.0, r))
    if n_seats <= 1:
        return float(n_seats)
    return n_seats / (1.0 + (n_seats - 1) * rho)


def conditional_agreement_given_error(
    answers: Sequence[Sequence[Hashable]],
    truth: Sequence[Hashable],
) -> float:
    """
    P(two seats give the SAME wrong answer | both are wrong).

    This is the sharpest monoculture diagnostic and the direct analogue of
    the Kim et al. (2025, ICML) statistic. Compare against the chance
    baseline you'd expect if wrong answers were drawn independently from the
    plausible-distractor set.

    Parameters
    ----------
    answers : (n_items, n_seats) of answer labels
    truth   : (n_items,) of correct labels

    Returns
    -------
    float in [0, 1]; NaN if no item had two wrong seats.

    READING IT: near 1/k (k = number of plausible distractors) suggests
    independent failure. Near 0.6+ suggests the seats share a failure mode
    and are functioning as one channel.
    """
    agree = 0
    both_wrong = 0
    for row, t in zip(answers, truth, strict=True):
        wrong_idx = [j for j, a in enumerate(row) if a != t]
        for a, b in itertools.combinations(wrong_idx, 2):
            both_wrong += 1
            if row[a] == row[b]:
                agree += 1
    if both_wrong == 0:
        return float("nan")
    return agree / both_wrong


# ---------------------------------------------------------------------------
# 2. CAPTURE-RECAPTURE: HOW MANY ERRORS DID NOBODY CATCH?
# ---------------------------------------------------------------------------

def lincoln_petersen(n1: int, n2: int, m: int, chapman: bool = True) -> float:
    """
    Two-seat capture-recapture estimate of TOTAL error population.

    n1 : errors caught by seat 1
    n2 : errors caught by seat 2
    m  : errors caught by BOTH

    chapman=True applies the Chapman bias correction, which is preferred for
    small samples and is defined when m = 0.

    ASSUMPTION VIOLATION: assumes independent capture. Positive correlation
    between seats inflates m, which DEFLATES N_hat. Treat the result as a
    LOWER BOUND on true error count.

    FAIL CLOSED on contradictory input. m cannot exceed either sample: an error
    caught by BOTH seats was caught by each of them. Left unchecked, the
    Chapman form quietly returns a NEGATIVE population estimate --
    lincoln_petersen(0, 0, 1) returned -0.5 -- which is not a bound on
    anything. Found by property test.
    """
    if n1 < 0 or n2 < 0 or m < 0:
        raise ValueError(f"counts must be non-negative: n1={n1}, n2={n2}, m={m}")
    if m > min(n1, n2):
        raise ValueError(
            f"overlap m={m} exceeds a sample (n1={n1}, n2={n2}): an error caught "
            f"by both seats was caught by each, so this input is contradictory"
        )
    if chapman:
        return ((n1 + 1) * (n2 + 1) / (m + 1)) - 1
    if m == 0:
        return float("inf")
    return n1 * n2 / m


def chao1(detections: dict[Any, set[Any]]) -> dict[str, float]:
    """
    Chao1 estimator of total error population from k >= 2 seats.

        N_hat = S_obs + f1^2 / (2 * f2)          (f2 > 0)
        N_hat = S_obs + f1 * (f1 - 1) / 2        (f2 == 0, bias-corrected)

    where
        S_obs = distinct errors caught by at least one seat
        f1    = errors caught by EXACTLY ONE seat  ("singletons")
        f2    = errors caught by EXACTLY TWO seats ("doubletons")

    DIAGNOSTIC READING -- this is the part that matters:
      A LARGE f1 means many errors were caught by only one seat. That is
      simultaneously (a) what "each LLM caught what the others missed" feels
      like from inside, and (b) strong quantitative evidence that MORE errors
      remain uncaught. The subjective impression of the system working well
      and the statistical signal of residual risk are the same signal.

    ASSUMPTION VIOLATION: heterogeneous and positively-correlated capture
    probabilities bias N_hat DOWNWARD. Report as a LOWER BOUND.
    """
    counts: Counter[Hashable] = Counter()
    for caught in detections.values():
        for err in caught:
            counts[err] += 1

    s_obs = len(counts)
    f1 = sum(1 for c in counts.values() if c == 1)
    f2 = sum(1 for c in counts.values() if c == 2)

    if f2 > 0:
        n_hat = s_obs + (f1 ** 2) / (2 * f2)
    else:
        n_hat = s_obs + f1 * (f1 - 1) / 2

    return {
        "S_obs": float(s_obs),
        "f1_singletons": float(f1),
        "f2_doubletons": float(f2),
        "N_hat_lower_bound": float(n_hat),
        "estimated_missed": float(n_hat - s_obs),
        "singleton_fraction": float(f1 / s_obs) if s_obs else float("nan"),
    }


# ---------------------------------------------------------------------------
# 3. PER-PASS MARGINAL YIELD (IS PASS 5 EARNING ITS COMPUTE?)
# ---------------------------------------------------------------------------

@dataclass
class PassYield:
    pass_id: Any
    newly_caught: int
    cumulative: int
    marginal_yield: float          # new / total seeded
    marginal_share: float          # new / cumulative after this pass


def marginal_yield_by_pass(
    pass_detections: list[tuple[Any, set[Any]]],
    total_seeded: int | None = None,
) -> list[PassYield]:
    """
    How many NEW errors each pass caught that no prior pass had caught.

    pass_detections : ordered list of (pass_id, set_of_error_ids)
                      ORDER MATTERS -- this is a sequential design.
    total_seeded    : known number of seeded errors, if you have it.

    USE: if marginal_yield -> ~0 by pass 4, pass 5 is not earning its compute
    and the pass count k should be reduced. Do NOT assume k = 5; measure it.

    CONFOUND WARNING: this is order-dependent. Pass 1 will always look most
    productive. To separate FRAMEWORK effect from ORDER effect you must
    randomize pass order across runs and average within framework.
    """
    seen: set[Any] = set()
    out: list[PassYield] = []
    for pid, caught in pass_detections:
        new = caught - seen
        seen |= caught
        denom = total_seeded if total_seeded else max(len(seen), 1)
        out.append(
            PassYield(
                pass_id=pid,
                newly_caught=len(new),
                cumulative=len(seen),
                marginal_yield=len(new) / denom,
                marginal_share=len(new) / max(len(seen), 1),
            )
        )
    return out


# ---------------------------------------------------------------------------
# 4. SURVIVOR STABILITY (JACKKNIFE ON THE ARCHITECTURE)
# ---------------------------------------------------------------------------

def leave_one_seat_out_stability(
    answers: Sequence[Sequence[Hashable]],
    aggregator: Callable[[Sequence[Hashable]], Hashable],
) -> dict[str, Any]:
    """
    Re-run the elimination with each seat removed in turn. Does the same
    answer survive?

    answers    : (n_items, n_seats) answer labels
    aggregator : callable(list_of_answers_for_one_item) -> surviving answer.
                 Pass in YOUR elimination logic here.

    THIS IS THE CHEAPEST HIGH-VALUE TEST YOU CAN RUN and it needs no ground
    truth. If the survivor changes when you drop one seat, the convergence is
    driven by that seat rather than by elimination, and "only one answer left"
    is an artifact of the panel composition.

    Returns per-item flip rate and the identity of any decisive seat.
    """
    answers = [list(r) for r in answers]
    n_items = len(answers)
    n_seats = len(answers[0]) if n_items else 0

    full = [aggregator(r) for r in answers]
    flips_by_seat = dict.fromkeys(range(n_seats), 0)
    # Must stay a comprehension: dict.fromkeys(range(n), []) would bind ONE list
    # object to every key, so appending for one seat would append for all of them.
    flipped_items: dict[int, list[int]] = {
        j: [] for j in range(n_seats)
    }

    for j in range(n_seats):
        for i, row in enumerate(answers):
            reduced = [a for k, a in enumerate(row) if k != j]
            if not reduced:
                continue
            if aggregator(reduced) != full[i]:
                flips_by_seat[j] += 1
                flipped_items[j].append(i)

    total_flips = sum(flips_by_seat.values())
    denom = max(n_items * n_seats, 1)
    decisive = max(flips_by_seat, key=lambda j: flips_by_seat[j]) if n_seats else None

    return {
        "overall_flip_rate": total_flips / denom,
        "flips_by_seat": flips_by_seat,
        "flipped_items_by_seat": flipped_items,
        "most_decisive_seat": decisive,
        "interpretation": (
            "flip_rate near 0 => survivor is robust to panel composition; "
            "flip_rate high, concentrated on one seat => that seat is driving "
            "convergence and the ensemble is decorative."
        ),
    }


# ---------------------------------------------------------------------------
# 5. INDEPENDENCE GAP (HOW MUCH OF THE THEORETICAL GAIN ARE YOU CAPTURING?)
# ---------------------------------------------------------------------------

def independence_gap(X: np.ndarray) -> dict[str, float]:
    """
    Compare OBSERVED majority-vote accuracy against the accuracy that WOULD
    be achieved if seat failures were independent (the "independence line"
    from N-version programming reliability analysis).

    X : (n_items, n_seats) int, 1 = correct.

    Returns observed accuracy, independence-predicted accuracy, best single
    seat, and the fraction of the theoretical gain actually captured.

    HOW TO READ capture_fraction. The independence line is an upper bound
    that assumes seat failures are uncorrelated. Real panels never reach it,
    because seats trained on overlapping corpora fail on overlapping inputs.
    A low capture_fraction with ensemble_beats_best_single False means the
    ensemble is costing compute for nothing and the frameworks -- not the
    models -- are doing the work.

    Never read this number alone. It says how much of the theoretical gain
    was captured; it does not say why the gain was small. Read it beside
    mean_error_correlation, which names the cause. A capture_fraction near
    zero with rho near zero is a hard problem; the same number with rho near
    one is a monoculture.

    NO EXTERNAL BENCHMARK IS CITED HERE. An earlier draft asserted, on the
    authority of an unnamed multi-model study, that realized ensemble gains
    stay below half the independence prediction. That citation carried no
    author, venue, year, or identifier, so SourceAdmissibilityGate could not
    classify it, and the orchestrator would have rejected the same warrant
    arriving from a seat. A module that cites what its own gate refuses is
    the failure this project exists to catch, so the claim is removed rather
    than dressed up. It may return with an identifier that resolves.
    TestNoUnsourcedBenchmarkClaims keeps it out until then, and asserts the
    gate's verdict rather than restating this paragraph.

    The one empirical anchor available here is this repository's own, and it
    is reproducible: validation_harness.py, twelve seeded defects over three
    synthetic seats, measured a collapsed panel (rho = +1.000) at 1.00
    effective seats catching 4 of 12 defects against a divergent panel
    (rho = +0.500) at 1.50 effective seats catching 6 of 12. That is a
    property of those synthetic seats, not of any production model, and it
    is stated as such.
    """
    X = np.asarray(X, dtype=int)
    n_seats = X.shape[1]

    obs_majority = (X.sum(axis=1) > n_seats / 2).mean()
    per_seat_acc = X.mean(axis=0)
    best_single = float(per_seat_acc.max())

    # Independence prediction: Poisson-binomial over per-seat accuracies.
    # P(majority correct) with independent Bernoulli(p_j).
    probs = np.zeros(n_seats + 1)
    probs[0] = 1.0
    for p in per_seat_acc:
        new = np.zeros_like(probs)
        for k in range(n_seats, -1, -1):
            if probs[k] == 0:
                continue
            new[k] += probs[k] * (1 - p)
            if k + 1 <= n_seats:
                new[k + 1] += probs[k] * p
        probs = new
    threshold = int(np.floor(n_seats / 2)) + 1
    indep_majority = float(probs[threshold:].sum())

    theoretical_gain = indep_majority - best_single
    observed_gain = float(obs_majority) - best_single
    capture = (observed_gain / theoretical_gain) if theoretical_gain > 1e-12 else float("nan")

    return {
        "observed_majority_accuracy": float(obs_majority),
        "independence_predicted_accuracy": indep_majority,
        "best_single_seat_accuracy": best_single,
        "theoretical_gain_over_best_single": float(theoretical_gain),
        "observed_gain_over_best_single": observed_gain,
        "capture_fraction": float(capture),
        "ensemble_beats_best_single": bool(obs_majority > best_single),
    }


# ---------------------------------------------------------------------------
# 6. ONE-CALL REPORT
# ---------------------------------------------------------------------------

def diagnose(
    X: np.ndarray | None = None,
    detections: dict[Any, set[Any]] | None = None,
    pass_detections: list[tuple[Any, set[Any]]] | None = None,
    answers: Sequence[Sequence[Hashable]] | None = None,
    truth: Sequence[Hashable] | None = None,
    total_seeded: int | None = None,
) -> dict[str, Any]:
    """Run whichever diagnostics the supplied data supports."""
    report: dict[str, Any] = {}

    if X is not None:
        X = np.asarray(X, dtype=int)
        rho = mean_error_correlation(X)
        report["mean_error_correlation_rho"] = rho
        report["n_seats"] = int(X.shape[1])
        # None, not a number, when rho could not be measured. Passing NaN
        # here used to yield the full seat count -- a perfectly independent
        # panel -- on exactly the runs where independence was unknowable.
        report["effective_seats"] = (
            effective_seats(X.shape[1], rho) if math.isfinite(rho) else None)
        report["independence_gap"] = independence_gap(X)

    if answers is not None and truth is not None:
        report["conditional_agreement_given_error"] = (
            conditional_agreement_given_error(answers, truth)
        )

    if detections is not None:
        report["capture_recapture"] = chao1(detections)

    if pass_detections is not None:
        report["marginal_yield_by_pass"] = [
            vars(p) for p in marginal_yield_by_pass(pass_detections, total_seeded)
        ]

    return report


if __name__ == "__main__":
    # Illustrative sanity check on SYNTHETIC data.
    # These numbers demonstrate the estimators run; they are NOT findings
    # about any real system.
    rng = np.random.default_rng(7)
    n_items, n_seats = 400, 5

    # Simulate a correlated-failure regime: a shared latent difficulty factor Z
    Z = rng.random(n_items) < 0.25          # 25% of items are "shared-hard"
    X = np.zeros((n_items, n_seats), dtype=int)
    for j in range(n_seats):
        p = np.where(Z, 0.35, 0.92)         # all seats struggle on the same items
        X[:, j] = (rng.random(n_items) < p).astype(int)

    rho = mean_error_correlation(X)
    print(f"[synthetic] mean error correlation rho = {rho:.3f}")
    print(f"[synthetic] effective seats (of {n_seats}) = "
          + (f"{effective_seats(n_seats, rho):.2f}"
             if math.isfinite(rho) else "not measurable"))
    gap = independence_gap(X)
    print(f"[synthetic] observed majority acc  = {gap['observed_majority_accuracy']:.3f}")
    print(f"[synthetic] independence predicted = {gap['independence_predicted_accuracy']:.3f}")
    print(f"[synthetic] capture fraction       = {gap['capture_fraction']:.3f}")
    print(f"[synthetic] beats best single seat = {gap['ensemble_beats_best_single']}")

    det = {
        "seatA": {1, 2, 3, 7, 9},
        "seatB": {2, 3, 4, 10},
        "seatC": {3, 5, 11},
        "seatD": {1, 3, 6},
        "seatE": {3, 12},
    }
    print("[synthetic] capture-recapture:", chao1(det))


# ---------------------------------------------------------------------------
# confidence ceilings
# ---------------------------------------------------------------------------

CONFIDENCE_LEVELS = ("Low", "Medium", "High")
"""The only confidence vocabulary this tool permits.

Deliberately NOT numeric. A percentage implies a dataset, an outcome variable,
and a base rate, and this panel has none of the three: it has some models that
agreed. Emitting "87% confident" from five correlated language models is the
fabrication the whole architecture exists to prevent, and it is more dangerous
than a wrong answer because it travels downstream carrying false precision.
"""

MEDIUM_NEEDS_EFFECTIVE_SEATS = 2.0
HIGH_NEEDS_EFFECTIVE_SEATS = 3.0
"""Thresholds on n_eff, not on n.

Below 2.0 effective seats the panel is worth roughly one observer, and one
observer's agreement with itself is not corroboration at any strength. Below
3.0 it is worth about two, which can catch a blunder but cannot establish a
conclusion.

These are ceilings on what the panel's STRUCTURE can support, and they are
where they are because n_eff is the only independence figure this system
actually measures. They are not a claim that 3.0 effective seats makes a
conclusion true.
"""


def confidence_ceiling(n_seats: int, rho: float) -> str:
    """The strongest confidence this panel's independence can support.

    A CEILING, never an assignment. Evidence decides where a conclusion
    actually lands; this only says how high it is permitted to reach. A
    candidate with one weak warrant sits at Low no matter how independent the
    seats were.

    WHY THIS EXISTS. Five seats that agree look like five confirmations, and
    that appearance is what a reader acts on. If those seats fail together --
    which is exactly what rho measures -- they are closer to one confirmation
    repeated five times. On a live run of this tool, measured pairwise claim
    overlap ran between 0.0000 and 0.0238 and nothing was eliminated in any
    pass; a "High confidence" stamped on that output would have described the
    panel's size rather than its evidence.
    """
    if not math.isfinite(float(rho)):
        # Unmeasured independence is not high independence. Nothing has been
        # established about whether these seats fail together, and agreement
        # between seats not shown to fail differently is not corroboration.
        return CONFIDENCE_LEVELS[0]
    n_eff = effective_seats(n_seats, rho)
    if n_eff < MEDIUM_NEEDS_EFFECTIVE_SEATS:
        return "Low"
    if n_eff < HIGH_NEEDS_EFFECTIVE_SEATS:
        return "Medium"
    return "High"


def cap_confidence(claimed: str, n_seats: int, rho: float) -> tuple[str, str | None]:
    """Clamp a claimed confidence to the ceiling. Returns (value, why_capped).

    why_capped is None when nothing was clamped, and a sentence naming the
    measured numbers when it was. The sentence is required rather than
    optional: silently lowering a confidence would leave the operator with a
    number they cannot account for, and an unexplained downgrade is only
    marginally better than an unearned upgrade.

    An unrecognised claimed value fails CLOSED to the FLOOR, not to the
    ceiling. A model that writes "Very High" or "95%" has stepped outside the
    permitted vocabulary, and the vocabulary is the mechanism -- honouring the
    string would let any value bypass the cap. Falling back to the ceiling
    would be worse still: on an independent panel the ceiling is High, so a
    contract violation would be REWARDED with the maximum confidence the
    system can express. Default is denied, so it lands at Low.
    """
    ceiling = confidence_ceiling(n_seats, rho)
    n_eff = (effective_seats(n_seats, rho)
             if math.isfinite(float(rho)) else float("nan"))
    limit = CONFIDENCE_LEVELS.index(ceiling)

    if claimed not in CONFIDENCE_LEVELS:
        return CONFIDENCE_LEVELS[0], (
            f"claimed confidence {claimed!r} is not one of "
            f"{', '.join(CONFIDENCE_LEVELS)}. A value outside the permitted "
            f"vocabulary is not evidence of strength, so it fails closed to "
            f"{CONFIDENCE_LEVELS[0]} rather than to the {ceiling} ceiling "
            f"({n_seats} seats at measured rho {rho:.4f} are worth "
            f"{n_eff:.2f} independent seats)"
        )
    if CONFIDENCE_LEVELS.index(claimed) <= limit:
        return claimed, None
    return ceiling, (
        f"{claimed} exceeds what this panel's independence supports: "
        f"{n_seats} seats at measured rho {rho:.4f} are worth {n_eff:.2f} "
        f"independent seats, which caps confidence at {ceiling}"
    )
