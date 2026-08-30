"""The judgment queue: SOP 9.1 steps 7 and 8, and 6.3 condition 3.

    7  Work your escalation queue. These are the judgment items only you
       can decide.
    8  Re-run with your adjudications folded in, so they enter the rho
       calculation.

NEITHER STEP WAS REACHABLE, AND SOP 10 MAKES THAT A DO-NOT-BUILD CONDITION:
"You will not work the escalation queue -> Becomes the 17.2x independent
topology -> Do not build this." The first full five-round run produced
NINETY-THREE claims that reached no gate. They were printed in the packet as
prose bullets and nothing ever read them back, so:

  * SOP 6.3's stop rule could never be satisfied -- an unworked queue is a
    standing blocker, so no run could ever say "commit";
  * rho was UNMEASURED in every round of every run, because error correlation
    needs to know whether each SEAT was right on common items, and a claim no
    gate decided has no truth value at all until a person supplies one;
  * and therefore effective seat count -- the number that says whether five
    seats are worth five or worth one and a half -- was undefined.

`correctness_matrix.build_correctness_matrix` already does the arithmetic and
already refuses to let a human override a gate. It takes the OTHER engine's
types, so the engine that spends money could not call it. This closes that.

HOW IT WORKS, AND WHY IT IS A FILE RATHER THAN A PROMPT. `--open` writes
queue.json listing every unadjudicated claim with a `true` field set to null.
You fill those in with a text editor. `--apply` reads them back, folds them
in, and prints rho, effective seats, and what the run's stop rule says now.

That is the same shape as .env and profiles.json, for the same reason: an
operator decision typed into a prompt is gone when the process exits, and
these decisions are evidence. They belong on disk, next to the run they
describe, where they can be re-read and disagreed with months later.

ONE RULE IT ENFORCES ABSOLUTELY. A human adjudication may resolve only a
claim NO GATE DECIDED. Overriding a gate moves authority from the mechanical
bottleneck back to a judgement call, which is the failure this architecture
exists to prevent -- so build_correctness_matrix raises AdjudicationConflict
and this refuses to write such an entry in the first place.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adjudication_orchestrator import (
    Claim,
    GateStatus,
    Orchestrator,
    line_claim_extractor,
)

HERE = os.path.dirname(os.path.abspath(__file__))
CALIBRATION_ITEMS = 30
"""SOP 8.1 step 3 and 8.4: the size of the calibration set rho is meant to
be computed over. Used only to say when a figure is thinner than that."""

QUEUE_FILE = "queue.json"
"""Written into the run directory, beside the evidence it is about."""


class QueueError(ValueError):
    """The queue file cannot be used."""


@dataclass
class Replay:
    """One run, re-gated offline so its verdicts can be reproduced exactly.

    NOTHING HERE COSTS A CENT OR TOUCHES A VENDOR. The replies are on disk and
    every gate is deterministic, so the verdicts recompute. That matters for
    more than cost: a queue built from a remembered verdict could disagree
    with the run it claims to describe, and nobody would be able to tell.
    """

    run_dir: str
    orch: Orchestrator
    claims: dict[str, Claim] = field(default_factory=dict)
    proposers: dict[str, set[str]] = field(default_factory=dict)
    """claim id -> the seats that asserted it. SOP 6.6 needs this: an item's
    row in the matrix is one cell per seat, and the cell says whether that
    seat took the position, not whether the claim held."""
    seats: list[str] = field(default_factory=list)


def _pass_id(round_dir: str) -> str:
    m = re.search(r"round-(\d+)", round_dir)
    return f"p{m.group(1)}" if m else "p?"


def replay(run_dir: str, gates: Sequence[object] | None = None) -> Replay:
    """Re-read a run's thinker replies and re-rule every claim, offline."""
    if not os.path.isdir(run_dir):
        raise QueueError(f"no run at {run_dir}")
    if gates is None:
        from run_adjudication import night_gates
        gates = night_gates()
    orch = Orchestrator(list(gates))  # type: ignore[arg-type]
    rep = Replay(run_dir=run_dir, orch=orch)
    files = sorted(glob.glob(os.path.join(run_dir, "round-*", "thinker-*.md")))
    if not files:
        raise QueueError(
            f"{run_dir} holds no thinker replies; there is nothing to work")
    for path in files:
        seat = os.path.basename(path)[len("thinker-"):-len(".md")]
        pid = _pass_id(os.path.dirname(path))
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
        if seat not in rep.seats:
            rep.seats.append(seat)
        for claim in line_claim_extractor(raw, seat, pid):
            rep.claims.setdefault(claim.id, claim)
            rep.proposers.setdefault(claim.id, set()).add(seat)
    rep.seats.sort()
    # RULED THROUGH THE SAME ENTRY POINT THE LIVE ENGINE USES, so the verdicts
    # here are the verdicts that run produced rather than a second opinion.
    orch.run_pass(
        type("P", (), {"id": "replay", "name": "replay",
                       "eliminative": False})(),
        [], list(rep.claims.values()),
    )
    return rep


def open_items(rep: Replay) -> list[Claim]:
    """Claims NO GATE DECIDED -- the only ones a person may resolve.

    A gate verdict of PASS or FAIL is settled and is not offered. WARRANT_HELD
    is deliberately INCLUDED: the gate confirmed the evidence and said nothing
    about the proposition it was offered for, which is precisely a judgement
    call and precisely what this queue is for.
    """
    out = []
    for cid, claim in rep.claims.items():
        v = rep.orch.verdicts.get(cid)
        status = getattr(v, "status", None)
        if status in (GateStatus.PASS, GateStatus.FAIL):
            continue
        out.append(claim)
    return sorted(out, key=lambda c: c.id)


def write_queue(rep: Replay, path: str | None = None) -> str:
    """Write the file the operator fills in, preserving any prior decisions."""
    target = path or os.path.join(rep.run_dir, QUEUE_FILE)
    prior: dict[str, object] = {}
    if os.path.exists(target):
        try:
            with open(target, encoding="utf-8") as fh:
                for row in json.load(fh).get("items", []):
                    if row.get("true") is not None:
                        prior[row["id"]] = row["true"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            # A queue file that cannot be read is not silently replaced --
            # decisions in it are evidence. Refuse and let a person look.
            raise QueueError(
                f"{target} exists and cannot be read. It may hold decisions; "
                f"move it aside deliberately rather than losing them") from None
    items = []
    for claim in open_items(rep):
        v = rep.orch.verdicts.get(claim.id)
        items.append({
            "id": claim.id,
            "true": prior.get(claim.id),
            "claim": claim.text,
            "kind": claim.kind.value,
            "warrant": claim.warrant or "",
            "gate": getattr(v, "gate", None) or "(none applied)",
            "gate_said": getattr(v, "detail", "") or "",
            "asserted_by": sorted(rep.proposers.get(claim.id, ())),
            "why": "",
        })
    blob = {
        "_README": [
            "SOP 9.1 step 7. Set \"true\" on each item: true if the claim is "
            "correct, false if it is not, or leave it null if you cannot "
            "decide -- null items stay open and are excluded from rho rather "
            "than guessed.",
            "",
            "Put your reasoning in \"why\". It is not read by any code. It is "
            "here because a decision without a reason cannot be reviewed, and "
            "these decisions become evidence in the correctness matrix.",
            "",
            "Only claims NO GATE DECIDED appear here. A gate verdict may not "
            "be overridden: that moves authority from the mechanical "
            "bottleneck back to a judgement call, which is the failure this "
            "architecture exists to prevent.",
            "",
            "Then: .venv/bin/python judgment_queue.py --apply <this run directory>",
        ],
        "run": os.path.basename(rep.run_dir),
        "items": items,
    }
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(blob, fh, indent=2)
    os.replace(tmp, target)
    return target


def read_decisions(rep: Replay, path: str | None = None) -> dict[str, bool]:
    """The operator's decisions, refusing any that override a gate."""
    target = path or os.path.join(rep.run_dir, QUEUE_FILE)
    if not os.path.exists(target):
        raise QueueError(
            f"no {QUEUE_FILE} in {rep.run_dir}. Run --open first, fill it in, "
            f"then --apply.")
    with open(target, encoding="utf-8") as fh:
        blob = json.load(fh)
    settled = {cid for cid, v in rep.orch.verdicts.items()
               if getattr(v, "status", None) in (GateStatus.PASS,
                                                 GateStatus.FAIL)}
    out: dict[str, bool] = {}
    for row in blob.get("items", []):
        cid, value = row.get("id"), row.get("true")
        if value is None:
            continue
        if not isinstance(value, bool):
            raise QueueError(
                f"{cid}: \"true\" is {value!r}; it must be true, false or null")
        if cid in settled:
            raise QueueError(
                f"{cid}: a gate already decided this claim. A human "
                f"adjudication may resolve only a claim NO gate decided -- "
                f"overriding one moves authority away from the mechanical "
                f"bottleneck, which is the failure this design prevents.")
        if cid not in rep.claims:
            raise QueueError(f"{cid}: no such claim in this run")
        out[cid] = value
    return out


# ---------------------------------------------------------------------------
# folding the decisions back in -- SOP 9.1 step 8, 6.6, 6.1
# ---------------------------------------------------------------------------

@dataclass
class Folded:
    """What the run looks like once the queue has been worked."""

    n_items: int
    n_from_gates: int
    n_from_human: int
    still_open: int
    seats: list[str]
    rho: float | None
    n_eff: float | None
    blockers: list[str] = field(default_factory=list)


def fold(rep: Replay, decisions: dict[str, bool]) -> Folded:
    """Build the correctness matrix and read rho off it (SOP 6.6, then 6.1).

    THE CELL RULE IS THE MANUAL'S, AND IT IS NOT THE ONLY DEFENSIBLE ONE.

        correct = (the seat asserted it) == (the claim is true)

    so a seat that stayed SILENT on a true claim scores 0 -- it missed it.
    SOP 6.6 argues for that directly: "A seat asked to find defects that does
    not report a real one has missed it... Scoring it neutral would hide
    precisely the shared blind spot 6.1 exists to measure."

    `night_loop.measure_rho` declines to do this and says why: silence is
    MISSING DATA, and scoring it as error "manufactures disagreement that was
    never observed". Both readings are honest and they disagree. This follows
    the manual, because the manual is the specification and it reasons the
    case out; the objection is printed alongside the number rather than
    settled silently, so a reader can discount it if they find the objection
    better. What must not happen is one of the two being applied without the
    reader knowing which.
    """
    import numpy as np

    from seat_independence import effective_seats, mean_error_correlation

    truth: dict[str, bool] = {}
    from_gates = 0
    for cid, v in rep.orch.verdicts.items():
        status = getattr(v, "status", None)
        if status is GateStatus.PASS:
            truth[cid], from_gates = True, from_gates + 1
        elif status is GateStatus.FAIL:
            truth[cid], from_gates = False, from_gates + 1
    for cid, value in decisions.items():
        truth[cid] = value

    item_ids = sorted(truth)
    blockers: list[str] = []
    if len(rep.seats) < 2:
        blockers.append(
            f"error correlation needs at least two seats; this run has "
            f"{len(rep.seats)}")
    if not item_ids:
        blockers.append(
            "no claim in this run has a truth value: no gate settled one and "
            "the queue has not been worked")
    if blockers:
        return Folded(0, from_gates, len(decisions),
                      len(open_items(rep)) - len(decisions),
                      rep.seats, None, None, blockers)

    X = np.array(
        [[int((s in rep.proposers.get(cid, set())) == truth[cid])
          for s in rep.seats] for cid in item_ids], dtype=int)
    # THE SAME FLOOR THE OTHER ENGINE USES, imported rather than re-chosen.
    # This said two, night_loop.MIN_SHARED_ITEMS_FOR_RHO says five, and its
    # reason applies here word for word: "a correlation over two or three
    # items is noise wearing four decimal places, and this number goes on to
    # set a confidence ceiling that a reader acts on". Two engines carrying
    # two floors for one quantity is exactly the drift that put "Kill options"
    # in the calibration round.
    from night_loop import MIN_SHARED_ITEMS_FOR_RHO
    if len(item_ids) < MIN_SHARED_ITEMS_FOR_RHO:
        blockers.append(
            f"only {len(item_ids)} item(s) have a truth value; below "
            f"{MIN_SHARED_ITEMS_FOR_RHO} a correlation is noise wearing four "
            f"decimal places, and this figure sets a confidence ceiling a "
            f"reader acts on")
        return Folded(len(item_ids), from_gates, len(decisions),
                      len(open_items(rep)) - len(decisions),
                      rep.seats, None, None, blockers)
    rho = float(mean_error_correlation(X))
    return Folded(len(item_ids), from_gates, len(decisions),
                  len(open_items(rep)) - len(decisions), rep.seats,
                  rho, float(effective_seats(len(rep.seats), rho)), [])


def render(f: Folded) -> list[str]:
    out = ["=" * 72,
           "THE QUEUE, WORKED  (SOP 9.1 steps 7-8, 6.6, 6.1)",
           "=" * 72,
           f"  items with a truth value: {f.n_items}"
           f"   ({f.n_from_gates} from gates, {f.n_from_human} from you)",
           f"  still open:               {f.still_open}",
           f"  seats:                    {len(f.seats)}",
           ""]
    if f.blockers:
        out.append("  RHO: NOT MEASURABLE")
        out += [f"    - {b}" for b in f.blockers]
        out += ["",
                "  Undefined is named in words rather than printed as a "
                "number (SOP 6.6).", ""]
        return out
    if f.rho is None or f.n_eff is None:
        # UNREACHABLE THROUGH fold(), which sets a blocker whenever it cannot
        # compute one. Written as a check rather than an assert because an
        # assert disappears under -O, and what it is guarding is the printing
        # of a confidence figure a reader acts on. If it is ever reached, the
        # honest output is that nothing was measured.
        out += ["  RHO: NOT MEASURABLE (no figure was computed)", ""]
        return out
    out += [f"  MEASURED ERROR CORRELATION  rho = {f.rho:.4f}",
            f"  EFFECTIVE SEATS             {f.n_eff:.2f} of {len(f.seats)}",
            f"  RESTING ON                  {f.n_items} item(s)",
            ""]
    if f.n_items < CALIBRATION_ITEMS:
        # NOT AN INVENTED CUT-OFF. It is the size SOP 8.1 step 3 and 8.4 ask
        # for, used here for the thing 8.4 asks it for: "Compute rho. Compute
        # it separately for each pass."
        out += [f"  THIN. SOP 8.4 calibrates rho over the {CALIBRATION_ITEMS} "
                f"examples of step 3, and this",
                f"  rests on {f.n_items}. It is a real measurement of a small "
                f"sample, not a stable",
                "  estimate -- work more of the queue and it will move.", ""]
    # SOP 6.7's own table, applied rather than quoted.
    if f.rho <= 0.2:
        out.append("  At this correlation five seats are justified (SOP 6.7).")
    elif f.rho <= 0.3:
        out.append("  SOP 6.7: above roughly 0.2, the fifth seat buys little. "
                   "Four is the manual's reading here.")
    elif f.rho < 1.0:
        out.append("  SOP 6.7: at this correlation you are paying five times "
                   "for under twice. Three seats, and spend the difference on "
                   "deterministic gates.")
    else:
        out.append("  TOTAL COLLAPSE. The seats are one seat repeated. SOP "
                   "6.7: stop and fix the panel before running again.")
    out += ["",
            "  HOW THIS NUMBER SCORES SILENCE, because it changes what it "
            "means.",
            "  A seat that said nothing about a TRUE claim is scored as "
            "having missed",
            "  it (SOP 6.6: \"a seat asked to find defects that does not "
            "report a real",
            "  one has missed it\"). night_loop.measure_rho refuses to do "
            "this and calls",
            "  silence missing data rather than error. Both readings are "
            "honest and they",
            "  disagree; this follows the manual, and you are told so rather "
            "than left",
            "  to assume which one produced the figure.", ""]
    if f.still_open:
        out += [f"  {f.still_open} ITEM(S) ARE STILL OPEN, so SOP 6.3's stop "
                f"rule is not satisfied",
                "  and this run may not be committed however good the numbers "
                "above look.", ""]
    return out


def main() -> int:
    args = sys.argv[1:]
    if len(args) != 2 or args[0] not in ("--open", "--apply"):
        print(__doc__.strip().splitlines()[0])
        print("\n  .venv/bin/python judgment_queue.py --open  <run directory>")
        print("  .venv/bin/python judgment_queue.py --apply <run directory>")
        return 2
    mode, run_dir = args
    if not os.path.isabs(run_dir):
        run_dir = os.path.join(HERE, run_dir)
    try:
        rep = replay(run_dir)
    except QueueError as exc:
        print(f"  {exc}")
        return 2
    print(f"  {len(rep.claims)} claim(s) from {len(rep.seats)} seat(s), "
          f"re-ruled offline")

    if mode == "--open":
        path = write_queue(rep)
        n = len(open_items(rep))
        print(f"  {n} claim(s) reached no gate and need your decision")
        print(f"  written to {path}")
        print("\n  Open it in a text editor, set \"true\" on each item to "
              "true or false")
        print("  (or leave it null if you cannot decide), then:")
        print(f"    .venv/bin/python judgment_queue.py --apply {run_dir}")
        return 0

    try:
        decisions = read_decisions(rep)
    except (QueueError, json.JSONDecodeError) as exc:
        print(f"  {exc}")
        return 2
    print(f"  {len(decisions)} decision(s) read")
    folded = fold(rep, decisions)
    print()
    print("\n".join(render(folded)))
    out = os.path.join(run_dir, "queue-result.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# The queue, worked\n\n```\n"
                 + "\n".join(render(folded)) + "\n```\n")
    print(f"  written to {out}")
    return 0 if not folded.blockers and not folded.still_open else 1


if __name__ == "__main__":
    raise SystemExit(main())
