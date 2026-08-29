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
import random
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import adjudication_orchestrator as AO
from adjudication_orchestrator import (
    ArithmeticGate,
    BlindedSeatRunner,
    Orchestrator,
    Pass,
    SequentialPassResult,
    measure_divergence,
)
from correctness_matrix import SHARED_DETECTION, diagnose_run

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

    False items are wrong by a SMALL margin. An answer off by one is a
    plausible slip a model may actually make; one off by an order of magnitude
    is caught by inspection and measures nothing.
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
    for k in range(n):
        a = rng.randint(112, 989)
        b = rng.randint(113, 987)
        truth = k % 2 == 0
        # A false item is off by +/- a small amount, never zero, so the
        # statement is genuinely false but not obviously so.
        result = a + b if truth else a + b + rng.choice([-2, -1, 1, 2])
        items.append(Item(f"S{k + 1:02d}", f"{a} + {b} = {result}", truth))
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
    seat_errors: dict[str, str]
    unmatched_claims: dict[str, list[str]]
    """seat_id -> claim warrants that matched no item in the set. See the
    module header: these are confirmations the matrix could not attribute, and
    they are shown rather than silently scored as silence."""

    @property
    def rho(self) -> float | None:
        return self.report.get("mean_error_correlation_rho")

    @property
    def effective_seats(self) -> float | None:
        return self.report.get("effective_seats")


def _norm(s: str) -> str:
    """Match the normalisation content_claim_id uses, so this module's idea of
    'the same statement' cannot drift from the engine's."""
    return " ".join((s or "").split()).casefold()


def _index_by_expression(items: Sequence[Item]) -> dict[str, Item]:
    """Items are recovered by their expression, not their id -- the claim line
    carries the statement in both fields and never the id. See module header."""
    return {_norm(it.expression): it for it in items}


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
    by_expr = _index_by_expression(chosen)

    runner = BlindedSeatRunner(dict(seat_fns))
    orch = Orchestrator(gates=[ArithmeticGate()], passes=[CALIBRATION_PASS])

    responses = runner.run(CALIBRATION_PASS, artifact)
    divergence = measure_divergence(CALIBRATION_PASS, responses)

    claims: list[AO.Claim] = []
    seat_errors: dict[str, str] = {}
    unmatched: dict[str, list[str]] = {}
    for r in responses:
        if r.error:
            seat_errors[r.seat_id] = r.error
        for c in r.claims:
            if _norm(c.warrant or "") not in by_expr:
                unmatched.setdefault(r.seat_id, []).append(
                    (c.warrant or c.text or "").strip())
        claims.extend(r.claims)

    record = orch.run_pass(CALIBRATION_PASS, [], claims)
    result = SequentialPassResult(
        CALIBRATION_PASS.id, CALIBRATION_PASS.name, record, divergence, responses
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
        seat_errors=seat_errors,
        unmatched_claims=unmatched,
    )


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

def verdict_line(rho: float | None, n_seats: int) -> str:
    """
    What the operator should DO about this number.

    The thresholds are the ones already stated in the PR and SOP discussion --
    five seats are justified only at rho <= ~0.2 -- and they are named as
    conventions, not derived. An operator who wants a different cutoff should
    set one; this refuses to imply a precision it does not have.
    """
    if rho is None:
        return ("NO VERDICT: rho was not produced. Read the blockers above; "
                "nothing here justifies keeping or cutting a seat.")
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
            f"Replace seats with more different ones rather than adding more.")


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

    if res.seat_errors:
        out.append("-" * 72)
        out.append(f"SEAT ERRORS ({len(res.seat_errors)})")
        out.append("-" * 72)
        for seat, err in sorted(res.seat_errors.items()):
            out.append(f"  {seat}: {err}")
        out.append("  A seat that errored contributes NO decisions. rho is")
        out.append("  computed over the seats that answered, and it is a")
        out.append("  measurement of THAT panel, not of the five you intended.")
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
               f"{'undefined' if rho is None else f'{rho:.3f}'}")
    out.append(f"  effective seats         : "
               f"{'undefined' if n_eff is None else f'{n_eff:.2f}'} "
               f"of {len(res.seats)} paid for")
    out.append("")
    reading = res.report.get("reading")
    if reading:
        out.append("  " + reading)
    out.append("")
    out.append("=" * 72)
    out.append(verdict_line(rho, len(res.seats)))
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
    return 0 if res.report.get("measurable") else 1


if __name__ == "__main__":
    raise SystemExit(main())
