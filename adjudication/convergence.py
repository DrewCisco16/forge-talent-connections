"""SOP v1.2 sections 6.2, 6.3, 6.5 and 9.3, computed over a five-round run.

WHY THIS EXISTS AS ITS OWN MODULE, AND WHAT WAS MISSING.

The manual specifies four things a run must report and one rule it must apply
before anything may be committed:

    6.2  capture-recapture -- how many errors nobody caught -- and the
         standing order that it is NEVER read without rho beside it, because
         at rho = 1.0 its output carries no information at all;
    6.3  the decay curve over VERIFIED CORRECTIONS, and the stop rule, which
         is a CONJUNCTION of four conditions including an empty judgment
         queue;
    6.5  per-pass seat divergence, where unanimity is an alarm rather than a
         result, and silence is not collapse;
    9.3  the holes -- each one named with what would close it, because "a hole
         you cannot act on is a disclaimer".

`adjudication_orchestrator` implements every underlying estimator and has done
since v1.2, and `Orchestrator.should_stop` applies the conjunction. But the
five-round LIVE engine is `night_loop.run_night`, which is a different code
path, and none of it was reachable from there. So the engine that actually
spends money reported a verdict and caveats, and never reported the residual,
the singleton fraction, the divergence, or the stop rule -- the numbers SOP 9.1
steps 9 and 10 tell the operator to read before committing.

This module closes that, by computing them from the RoundResults the live
engine already produces. It calls the SAME estimators as the other engine
rather than reimplementing them, so the two cannot drift into disagreeing
about what a residual is.

WHAT IT REFUSES TO DO. Where an input is absent it reports the quantity as
unmeasurable and says why, in words. It never substitutes a default. SOP 6.6
is explicit about the cost of the alternative: defaulting an unknown "invents
a measurement, and the direction of the invention biases rho in a known way".
"""
from __future__ import annotations

import itertools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from adjudication_orchestrator import chao1_lower_bound, fit_decay, residual_estimate


@dataclass
class Hole:
    """One thing the run could not close, and what would close it (SOP 9.3).

    The remedy is not optional. The manual's own words: "each one names its
    own remedy -- a hole you cannot act on is a disclaimer."
    """

    kind: str
    detail: str
    remedy: str


@dataclass
class Convergence:
    """Everything SOP 9.1 steps 9-11 tell the operator to read before commit."""

    yields: list[float]
    """VCY_k: verified CORRECTIONS in round k, over eliminative rounds only.

    SOP 6.3, and defect 6 in the manual's own log: "The decay fit was fed
    accepted and rejected claims... A pass that confirmed ten true claims and
    caught nothing reported a yield of ten, so the residual never decayed."
    Only refutations count. Each is counted in the round it was FIRST settled,
    because rulings accumulate across rounds and a commitment refuted in round
    two is still in the record in round four -- counting it again would make a
    decaying series look flat.

    Calibration rounds are excluded: they cannot produce a correction because
    they cannot rule anything out (SOP 2.3). The manual's worked example fits
    four yields for five passes for exactly this reason.
    """
    fit: tuple[float, float] | None
    residual: float | None
    capture: dict[str, float] | None
    rho_by_round: dict[int, float | None]
    divergence_by_round: dict[int, float | None]
    collapse_rounds: list[int]
    nesting_rounds: list[int] = field(default_factory=list)
    holes: list[Hole] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    tolerance: float = 0.5
    singleton_alarm: float | None = None

    @property
    def stop(self) -> bool:
        """SOP 6.3. A CONJUNCTION -- every condition, or the run is not done.

        "A low residual is not permission to commit."
        """
        return not self.blockers and not self.holes

    @property
    def exit_code(self) -> int:
        """SOP 9.1 step 11 and 9.3: non-zero while any hole remains.

        "One surviving candidate with an open judgment queue is a shortlist,
        not an answer, and the exit code says so without requiring you to read
        anything."
        """
        return 0 if self.stop else 1


def _content_sets(
    seat_claims: Mapping[str, Sequence[object]],
) -> list[frozenset[tuple[str, str]]]:
    """Claim sets keyed on CONTENT -- (kind, warrant) -- per SOP 6.5.

    Not on the claim id, which folds in the text: two seats phrasing the same
    finding differently must register as AGREEMENT, and an id built over the
    text records them as two findings. This is the same key
    `adjudication_orchestrator.measure_divergence` uses, deliberately.
    """
    out = []
    for claims in seat_claims.values():
        out.append(frozenset(
            (getattr(getattr(c, "kind", None), "value", str(getattr(c, "kind", ""))),
             str(getattr(c, "warrant", None) or getattr(c, "text", "") or "").strip())
            for c in claims))
    return out


def divergence(
    seat_claims: Mapping[str, Sequence[object]],
) -> tuple[float | None, bool, bool, str | None]:
    """(mean pairwise Jaccard, unanimous, all silent, collapse warning).

    SOP 6.5. SILENCE IS NOT COLLAPSE: every seat returning an empty set makes
    the sets trivially identical, but that is the marginal-yield signal -- this
    pass found nothing -- not a monoculture signal. The warning is suppressed,
    because "a warning that fires on every empty pass is one operators learn to
    ignore".
    """
    sets = _content_sets(seat_claims)
    silent = bool(sets) and all(not s for s in sets)
    if len(sets) < 2:
        return None, False, silent, None
    js = []
    for a, b in itertools.combinations(sets, 2):
        union = a | b
        js.append(1.0 if not union else len(a & b) / len(union))
    mean_j = sum(js) / len(js)
    unanimous = len(set(sets)) == 1
    warning = None
    if unanimous and not silent:
        warning = (
            f"All {len(sets)} seats produced an IDENTICAL claim set. On a "
            f"non-trivial question this is a monoculture signal, not a "
            f"confirmation: independently-failing seats do not agree exactly. "
            f"Treat the agreement as evidence they share a failure mode.")
    return mean_j, unanimous, silent, warning


def nested(sets: Sequence[frozenset[object]]) -> bool:
    """True when every pair of claim sets nests and they are not all equal.

    Nesting is the padding signature: one seat's claims are a superset of
    another's. Identical sets are unanimity and reported by that name.
    """
    if len(sets) < 2 or len(set(sets)) == 1:
        return False
    # A SILENT SEAT IS NOT A SMALLER SET. The empty set is contained in every
    # set, so one seat that said nothing next to one that spoke read as
    # "nested" -- and silence is reported by its own name (SOP 6.5), not as
    # padding. Found by an existing test the first version of this broke.
    if any(not s for s in sets):
        return False
    return all(a <= b or b <= a for a, b in itertools.combinations(sets, 2))


def nesting_warning(
    seat_claims: Mapping[str, Sequence[object]],
) -> str | None:
    """ASTRA-02. PADDING BOUGHT DIVERSITY, and it is reported SEPARATELY.

    Ten shared claims plus twenty irrelevant additions took the mean Jaccard
    from 1.0 to 0.56 and switched the collapse warning off, without one seat
    challenging anything. Jaccard measures set size as much as disagreement.
    When every pair NESTS -- the smaller set is contained in the larger --
    the seats agree on everything the smaller one said, and the extra claims
    are volume, not independence.

    Its own field, not the collapse warning. A collapse warning means the
    seats were unanimous, and code and tests rely on that meaning; a nesting
    warning means they were NOT unanimous and the difference is padding.
    Folding the two together would make "collapse" mean two opposite things.
    """
    sets = _content_sets(seat_claims)
    if not nested(sets):
        return None
    return (f"The {len(sets)} seats' claim sets NEST: every smaller set is "
            f"contained in a larger one, so they agree on every shared claim "
            f"and differ only by what one seat added. Extra claims on one "
            f"seat do not make it independent. Treat this as a monoculture "
            f"signal with padding, not as disagreement.")


def _new_failures_per_round(
    results: Sequence[object],
) -> list[tuple[int, bool, int]]:
    """[(round number, eliminative, corrections FIRST settled that round)].

    Rulings accumulate: `RoundResult.rulings` carries every commitment settled
    so far, not only this round's. Counting FAILs straight out of it would
    report the same refutation in every later round and turn a decaying series
    into a rising one -- the exact confound SOP 6.3 says makes the residual
    never decay.
    """
    seen: set[str] = set()
    out: list[tuple[int, bool, int]] = []
    for r in results:
        fails = {pid for pid, rul in (getattr(r, "rulings", {}) or {}).items()
                 if getattr(rul, "status", None) == "fail"}
        fresh = fails - seen
        seen |= fails
        out.append((getattr(r, "n", 0),
                    getattr(r, "eliminative", True),
                    len(fresh)))
    return out


def detections_by_seat(results: Sequence[object]) -> dict[str, set[str]]:
    """Which SEAT caught which refuted commitment (SOP 6.2).

    A commitment refuted by its OWN arithmetic was caught by code, not by any
    seat, and it is deliberately absent here. Capture-recapture asks how much
    of what is there the SEATS are seeing; folding in the defects code found
    unaided would inflate the observed count with detections no seat made and
    bias the estimate of what they are missing downward -- which is the one
    direction that matters, because the whole point of the estimator is the
    errors nobody caught.

    So a detection is a seat CHALLENGING a commitment that was then refuted.
    """
    refuted: set[str] = set()
    for r in results:
        refuted |= {pid for pid, rul in (getattr(r, "rulings", {}) or {}).items()
                    if getattr(rul, "status", None) == "fail"}
    out: dict[str, set[str]] = {}
    for r in results:
        for seat, pids in (getattr(r, "challenges_by_seat", {}) or {}).items():
            out.setdefault(seat, set()).update(p for p in pids if p in refuted)
    return out


def analyse(
    results: Sequence[object],
    *,
    escalations_pending: int = 0,
    tolerance: float = 0.5,
    singleton_alarm: float | None = None,
    rounds_specified: int = 5,
) -> Convergence:
    """Read a completed run against the manual's stop rule and holes table."""
    per_round = _new_failures_per_round(results)
    yields = [float(n) for _, elim, n in per_round if elim]
    fit = fit_decay(yields)
    residual = residual_estimate(yields)

    det = detections_by_seat(results)
    capture = chao1_lower_bound(det) if det else None

    rho_by_round = {getattr(r, "n", 0): getattr(r, "rho", None) for r in results}
    divergence_by_round = {getattr(r, "n", 0): getattr(r, "divergence", None)
                           for r in results}
    collapse_rounds = [getattr(r, "n", 0) for r in results
                       if getattr(r, "collapse_warning", None)]
    nesting_rounds = [getattr(r, "n", 0) for r in results
                      if getattr(r, "nesting_warning", None)]

    holes: list[Hole] = []
    blockers: list[str] = []

    observed = [r for r in results if getattr(r, "options_observed", False)]
    alive = list(getattr(observed[-1], "options_alive", [])) if observed else []
    unexamined = (list(getattr(observed[-1], "options_unexamined", []))
                  if observed else [])

    # -- SOP 9.3, row by row ----------------------------------------------
    # ASTRA-09. A CLAIM REFUTED AGAINST A SURVIVOR IS A HOLE, NOT A FOOTNOTE.
    #
    # assess() prints "N CLAIM(S) WERE MECHANICALLY REFUTED AND REMOVED
    # NOTHING" as a caveat and sets trustworthy False. This function, which
    # owns the EXIT CODE, never saw it: with yields decaying and the alarm
    # armed, a run carrying a refuted claim about its one survivor exited 0.
    # Two verdict surfaces disagreed, and the one a script acts on was the
    # permissive one. SOP 9.1 step 11 commits only when no hole remains; a
    # false statement made about the answer is a hole until a person reads it.
    refuted_standing = [
        getattr(r, "n", 0) for r in results
        if int(getattr(r, "failed", 0) or 0) > 0
        and not (getattr(r, "options_removed", None) or [])]
    if refuted_standing and alive:
        holes.append(Hole(
            "refuted claim stands against a survivor",
            f"In round(s) {', '.join(str(n) for n in refuted_standing)} a "
            f"gate refuted a claim and no option was removed, so the "
            f"refuted statement was made about an answer still standing.",
            "Read those refuted claims before committing. If one is about "
            "the surviving answer, the answer has an unrebutted defect; "
            "either the seat should have declared it as a commitment, or "
            "the claim needs a person's adjudication."))
    if observed and not alive:
        holes.append(Hole(
            "every candidate eliminated",
            "Every answer the panel proposed had a commitment mechanically "
            "refuted.",
            "Read the elimination reasons. The true answer may never have "
            "been proposed -- later rounds only remove. If a gate misfired, "
            "fix the gate; do not reinstate the candidate."))
    elif len(alive) > 1:
        holes.append(Hole(
            "not narrowed to one",
            f"{len(alive)} answers survive and nothing refuted any of them.",
            "Supply commitments that distinguish them, or accept the set as "
            "the honest result. The tool will not break the tie."))
    if unexamined:
        holes.append(Hole(
            "unadjudicated claims",
            f"{len(unexamined)} surviving answer(s) had a commitment nothing "
            f"ruled on.",
            "Decide them, then re-run with your adjudications folded in so "
            "they enter rho."))
    if escalations_pending:
        holes.append(Hole(
            "unadjudicated claims",
            f"{escalations_pending} claim(s) reached no gate and escalated.",
            "Work the queue, then re-run. SOP 10 lists an unworked queue as a "
            "do-not-build condition."))
    seat_errors = {s: why for r in results
                   for s, why in (getattr(r, "thinkers_failed", {}) or {}).items()}
    if seat_errors:
        holes.append(Hole(
            "seat error",
            f"{len(seat_errors)} seat(s) failed: "
            + "; ".join(f"{s}: {w}" for s, w in sorted(seat_errors.items())),
            "Fix the seat and re-run that pass. Its silence is neither "
            "agreement nor a miss."))
    for n in collapse_rounds:
        holes.append(Hole(
            "collapse warning",
            f"Round {n}: every seat produced an identical claim set.",
            "Change seat composition and re-run that round. Check rho before "
            "trusting anything it produced."))
    mismatch_rounds = [(getattr(r, "n", 0), getattr(r, "model_mismatch", {}))
                       for r in results if getattr(r, "model_mismatch", None)]
    for n, by_seat in mismatch_rounds:
        holes.append(Hole(
            "panel identity",
            f"Round {n}: " + "; ".join(f"{s}: {w}" for s, w in sorted(by_seat.items())),
            "The independence claim rests on which model ran. Fix the "
            "settings file so the configured id names what the vendor "
            "serves, or record the served model as the panel, and re-run."))
    for n in nesting_rounds:
        holes.append(Hole(
            "nesting warning",
            f"Round {n}: the seats' claim sets nest -- they agree on every "
            f"shared claim and differ only by what one seat added.",
            "Read the extra claims before crediting the divergence figure: "
            "padding on one seat is volume, not independence. Change seat "
            "composition and re-run that round if the shared core is all "
            "that matters."))
    if all(v is None for v in rho_by_round.values()):
        holes.append(Hole(
            "convergence not measurable",
            "Error correlation was not measured in any round, so effective "
            "seat count is undefined.",
            "Seed a set of propositions with known truth that every seat must "
            "decide. Until then treat the surviving answer as unverified."))
    if len(results) < rounds_specified:
        holes.append(Hole(
            "stop rule",
            f"Only {len(results)} of {rounds_specified} rounds ran.",
            "Run the remaining rounds; their lenses were never brought to "
            "bear."))

    # -- SOP 6.3, the conjunction -----------------------------------------
    if escalations_pending:
        blockers.append(
            f"{escalations_pending} unresolved item(s) in the judgment queue "
            f"(SOP 6.3 condition 3)")
    if residual is None:
        blockers.append(
            "yields are not decaying, so convergence is not established "
            "(SOP 6.3 condition 1). "
            + (f"Only {len([y for y in yields if y > 0])} eliminative round(s) "
               f"produced a correction, and a decay curve needs two."
               if len([y for y in yields if y > 0]) < 2
               else "The fit did not decay."))
    elif residual >= tolerance:
        blockers.append(
            f"extrapolated residual {residual:.2f} >= tolerance {tolerance} "
            f"(SOP 6.3 condition 2)")
    singleton = (capture["singleton_fraction"] if capture else float("nan"))
    if singleton_alarm is None:
        # SOP 8.4: "Set your singleton-fraction alarm. Until you do, that
        # check is NOT ARMED." An unarmed condition in a conjunction cannot be
        # satisfied, and saying so is the fail-closed reading. Treating it as
        # met would let the run stop on a condition nobody had set.
        blockers.append(
            "the singleton-fraction alarm has never been calibrated, so SOP "
            "6.3 condition 4 is NOT ARMED and cannot be satisfied (SOP 8.4)")
    elif not math.isnan(singleton) and singleton > singleton_alarm:
        blockers.append(
            f"singleton fraction {singleton:.2f} > {singleton_alarm}: seats "
            f"are not overlapping, so more errors likely remain "
            f"(SOP 6.3 condition 4)")

    return Convergence(
        yields=yields, fit=fit, residual=residual, capture=capture,
        rho_by_round=rho_by_round, divergence_by_round=divergence_by_round,
        collapse_rounds=collapse_rounds, nesting_rounds=nesting_rounds,
        holes=holes, blockers=blockers,
        tolerance=tolerance, singleton_alarm=singleton_alarm)


def render(c: Convergence) -> list[str]:
    """The §6.2/6.3/6.5/9.3 block, for the packet and the console."""
    out = ["## Convergence, divergence and the stop rule (SOP 6.2, 6.3, 6.5)", ""]

    out.append("### Did the yields decay? (SOP 6.3)")
    if not c.yields:
        out.append("- No eliminative round produced a correction, so there is "
                   "no series to fit.")
    else:
        out.append(f"- VCY by eliminative round: "
                   f"{', '.join(str(int(y)) for y in c.yields)} "
                   f"(verified corrections -- gate FAILURES only)")
    if c.fit is None:
        out.append("- Decay fit: NOT MEASURABLE. Fewer than two rounds found "
                   "anything, and a curve cannot be fitted to one point.")
    else:
        a, b = c.fit
        out.append(f"- Decay fit: a = {a:.2f}, b = {b:.3f}"
                   + ("" if b > 0 else "  -- b <= 0, the yields are NOT decaying"))
    out.append("- Extrapolated residual: "
               + ("NOT MEASURABLE" if c.residual is None
                  else f"{c.residual:.2f} against tolerance {c.tolerance}"))

    out += ["", "### How many errors nobody caught (SOP 6.2)"]
    if c.capture is None:
        out.append("- NOT MEASURABLE: no seat challenged a commitment that "
                   "was then refuted, so there are no detections to count.")
    else:
        out.append(f"- observed {int(c.capture['observed'])}, "
                   f"singletons {int(c.capture['f1_singletons'])}, "
                   f"doubletons {int(c.capture['f2_doubletons'])}")
        out.append(f"- estimated missed (LOWER BOUND): "
                   f"{c.capture['estimated_missed']:.1f}")
        out.append(f"- singleton fraction: "
                   f"{c.capture['singleton_fraction']:.2f}"
                   + (f" (alarm {c.singleton_alarm})"
                      if c.singleton_alarm is not None
                      else "  -- NO ALARM CALIBRATED, so this check is not armed"))
    # SOP 6.2, stated as a standing order rather than a footnote.
    out.append("- READ THIS ONLY WITH RHO BESIDE IT. Correlated seats catch "
               "the same things, which produces no singletons, which makes "
               "the estimator conclude nothing was missed. At rho = 1.0 its "
               "output carries no information at all.")

    out += ["", "### Was the panel actually a panel? (SOP 6.5)"]
    for n, d in sorted(c.divergence_by_round.items()):
        rho = c.rho_by_round.get(n)
        rho_s = "rho NOT MEASURED" if rho is None else f"rho = {rho:.4f}"
        d_s = "divergence NOT MEASURABLE" if d is None else f"divergence = {d:.2f}"
        out.append(f"- Round {n}: {d_s}, {rho_s}")
    if c.collapse_rounds:
        out.append(f"- COLLAPSE FLAG in round(s) "
                   f"{', '.join(str(n) for n in c.collapse_rounds)}: the seats "
                   f"agreed exactly, which is an alarm and not a result.")
    if c.nesting_rounds:
        out.append(f"- PADDING FLAG in round(s) "
                   f"{', '.join(str(n) for n in c.nesting_rounds)}: the seats' "
                   f"claim sets nest, so the divergence figure is set size, "
                   f"not disagreement.")

    out += ["", "### The stop rule (SOP 6.3 -- a CONJUNCTION)", ""]
    if c.blockers:
        out.append("**DO NOT COMMIT.** Every condition below must hold and "
                   "these do not:")
        out += [f"- {b}" for b in c.blockers]
    else:
        out.append("All four stop conditions hold.")

    out += ["", "### Holes (SOP 9.3 -- part of the answer, not an appendix)", ""]
    if not c.holes:
        out.append("None. Every hole the manual enumerates is closed.")
    for h in c.holes:
        out.append(f"- **{h.kind}** -- {h.detail}")
        out.append(f"      what closes it: {h.remedy}")
    out += ["",
            "An answer is resolved only when ONE candidate survives AND no "
            "hole remains. Both halves (SOP 9.3). This run exits "
            f"{c.exit_code}."]
    return out
