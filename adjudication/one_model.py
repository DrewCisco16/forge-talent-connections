"""One model plus deterministic gates -- what Stage 0 measured us into.

WHY THIS EXISTS. stage_zero.py ran twice, on two task classes drawn from the
operator's own written goals, and returned the same verdict both times:

    governance requirements   baseline 0.968   95% CI [0.838, 0.994]
    capture / talent / P&L    baseline 1.000   95% CI [0.890, 1.000]
    threshold 0.45            DO NOT BUILD THE ENSEMBLE

SOP 8.1 step 5: "If baseline > 0.45: STOP. Build one model plus gates. You
just saved months." Both whole intervals sit above the threshold, so that is
not a close reading -- it is the instruction.

The gate layer was never the doubtful part. SOP 2.2 calls it "the most
valuable part of the system", and the reason is that its errors are
UNCORRELATED with the model's: a calculator does not make the mistake a
language model makes, and a DOI either resolves or it does not.

WHAT SURVIVES THE DROP TO ONE SEAT, AND WHAT DOES NOT. This distinction is
the whole design of this file and it took a five-round paid run to see it.

  SELF-REFUTATION SURVIVES. An option is removed when its own formula, with
  its own inputs, fails to produce its own figure. That needs nothing from any
  other seat -- it is the model's arithmetic checked against the model's own
  claim -- so it works exactly as well with one seat as with five. It is also
  the only mechanism that ever removed anything correctly in this project.

  CORROBORATION DOES NOT. "Two seats who wrote blind independently give the
  same different value" is meaningless with one seat, so a disputed input can
  never be outweighed here. Nothing pretends otherwise: there is no challenge
  contract and no dispute path.

  THE PANEL DIAGNOSTICS DO NOT, AND SAYING SO MATTERS. Error correlation,
  effective seat count, per-pass divergence and the collapse flag are all
  properties of a PANEL. At n=1 they are undefined, not zero, and this prints
  nothing about them. A one-seat run reporting "divergence = 0.00" would be
  describing the absence of a panel as agreement.

WHAT IT IS FOR, PLAINLY: you have a draft, a brief, an analysis or a set of
figures. One model states what it is committing to, in a shape code can
recompute, and code recomputes it. What holds is reported with the evidence.
What fails is reported with the arithmetic. What no gate could reach is handed
to you, because that is the half no machine settles.
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adjudication_orchestrator import (
    Gate,
    GateStatus,
    Orchestrator,
    line_claim_extractor,
)
from option_set import eliminate, parse_proposals, render_record
from predicate import adjudicate

HERE = os.path.dirname(os.path.abspath(__file__))

CONTRACT = """
## What to write, and the shape it has to be in

Answer the question above however you reason best. Then end your reply with
the lines below. They are the only part any machine reads, and anything you
assert outside them is reported as unchecked.

FOR EVERY ANSWER YOU PUT FORWARD:

    OPTION | a short name for the answer

and for each figure that answer depends on:

    PREDICATE | <what quantity> | = | <value and unit>
    FORMULA   | <an expression in named variables>
    INPUT     | <name> = <number>

ALL FOUR PARTS OR IT CANNOT BE CHECKED. A figure with no formula cannot be
recomputed, so it can never be verified and never ruled out; it survives to
the end marked UNTESTED, which is not the same as surviving scrutiny.

WHAT THIS EXPOSES YOU TO, AND IT IS THE POINT: your own formula, with your own
inputs, is recomputed. If it does not produce your own figure, that answer is
removed. Nobody else's opinion is involved and nothing here is a vote -- it is
your arithmetic against your claim. So write the number you actually believe.

FOR ANY OTHER CHECKABLE ASSERTION:

    CLAIM | arithmetic | 3 + 1 = 4 | the quarter total is 4 units
    CLAIM | citation | 10.1038/s41586-020-2649-2 | the effect was replicated
    CLAIM | judgment |  | this depends on how the contract is read

The second field is the KIND, the third is the WARRANT -- the expression, the
identifier, the thing a machine can check -- and the fourth is what you are
asserting. That order matters: reversing the last two puts prose where the
gate expects an expression, and every arithmetic claim is then rejected for
the wrong reason.

Use kind `judgment` with an empty warrant for anything that genuinely needs a
person. That is not a failure to answer; it is the honest label, and those
items are routed to the operator rather than buried.
"""


@dataclass
class Checked:
    """What one model committed to, and what code made of it."""

    answer: str = ""
    options_standing: list[str] = field(default_factory=list)
    options_removed: list[tuple[str, str]] = field(default_factory=list)
    options_untested: list[str] = field(default_factory=list)
    record: str = ""
    passed: list[tuple[str, str]] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    blocked: list[tuple[str, str]] = field(default_factory=list)
    open_items: list[str] = field(default_factory=list)
    warrant_held: list[tuple[str, str]] = field(default_factory=list)
    dollars: float = 0.0

    @property
    def resolved(self) -> bool:
        """One answer standing, nothing refuted, nothing left open.

        The same two-halves rule SOP 9.3 states for the panel, and for the same
        reason: "Reporting a lone survivor while thirty claims sit unadjudicated
        is how a shortlist gets shipped as a conclusion."
        """
        return (len(self.options_standing) == 1
                and not self.options_untested
                and not self.failed
                and not self.open_items)

    @property
    def exit_code(self) -> int:
        return 0 if self.resolved else 1


def check(artifact: str,
          ask_model: Callable[[str], str],
          gates: Sequence[Gate] | None = None,
          on_event: Callable[[str], None] | None = None) -> Checked:
    """Put the artifact to ONE model and rule everything it commits to."""
    emit = on_event or (lambda _m: None)
    if gates is None:
        from run_adjudication import _default_gates
        gates = _default_gates()
    orch = Orchestrator(list(gates))
    out = Checked()

    prompt = f"## The question or artifact\n{artifact.strip()}\n\n{CONTRACT}"
    emit("asking one model...")
    out.answer = ask_model(prompt)
    emit(f"replied, {len(out.answer):,} chars")

    # -- the typed commitments: the model's own arithmetic against its own
    #    figure. This is the one removal mechanism that does not need a panel.
    try:
        options = parse_proposals({"seat_1": out.answer})
    except Exception as exc:                            # noqa: BLE001
        emit(f"no option set could be parsed: {exc}")
        options = []
    preds = [p for o in options for p in o.predicates]
    rulings = adjudicate(preds, [])          # no challenges: there is no panel
    removed = eliminate(options, rulings, 1)
    out.options_removed = [(o.id, o.elimination_reason or "") for o in removed]
    out.options_standing = [o.id for o in options if o.alive]
    # THE DISTINCTION ONE SEAT FORCES, and a test caught me collapsing it.
    #
    # `unexamined` counts an option as untested unless something OUTSIDE it
    # touched a commitment -- a dispute it survived, or a second seat's route
    # to the same figure. That is right for a panel and it is UNSATISFIABLE
    # here: with one seat nothing external exists, so every answer would be
    # permanently untested and the exit code could never be zero, which makes
    # it carry no information.
    #
    # So two different facts are kept apart. An option that declared no
    # computable commitment, or whose commitments were not all ruled, is
    # UNTESTED in the strong sense and blocks resolution -- nothing about it
    # was checked. An option whose own arithmetic was fully ruled is as
    # examined as one seat can make it, and the standing limit -- that no
    # answer here has been tested by anything outside itself -- is stated
    # unconditionally in section 4 rather than pretending it varies.
    out.options_untested = [
        o.id for o in options if o.alive
        and (not o.predicates
             or not all(getattr(rulings.get(getattr(p, "id", "")), "status",
                                None) in ("pass", "fail")
                        for p in o.predicates))]
    if options:
        # No challenge invitation: there is no second seat to dispute anything,
        # and printing the panel block here contradicts section 4.
        out.record = render_record(options, invite_challenges=False)
    emit(f"{len(options)} option(s), {len(preds)} commitment(s), "
         f"{len(removed)} removed on their own arithmetic")

    # -- the free claims, through the gates
    claims = line_claim_extractor(out.answer, "seat_1", "single")
    if claims:
        orch.run_pass(
            type("P", (), {"id": "single", "name": "one model plus gates",
                           "eliminative": False})(),
            [], claims,
        )
    for claim in claims:
        v = orch.verdicts.get(claim.id)
        status = getattr(v, "status", None)
        detail = (getattr(v, "detail", "") or "")
        if status is GateStatus.PASS:
            out.passed.append((claim.text, detail))
        elif status is GateStatus.FAIL:
            out.failed.append((claim.text, detail))
        elif status is GateStatus.BLOCKED:
            out.blocked.append((claim.text, detail))
        elif status is GateStatus.WARRANT_HELD:
            out.warrant_held.append((claim.text, detail))
        else:
            out.open_items.append(claim.text)
    emit(f"{len(claims)} claim(s): {len(out.passed)} pass, "
         f"{len(out.failed)} fail, {len(out.blocked)} blocked, "
         f"{len(out.warrant_held)} warrant-held, {len(out.open_items)} open")
    return out


def render(c: Checked) -> list[str]:
    """The gate results FIRST, then the answer. SOP 9.1 step 4.

    "Do NOT read the model outputs yet. Read the GATE RESULTS first." The
    reason is in the same section: Dell'Acqua et al. (2026) found wrong answers
    from AI users were graded MORE coherent, so reading the prose first is how
    a polished error gets committed.
    """
    out = ["=" * 72,
           "1. WHAT THE GATES FOUND  (read this before the answer)",
           "=" * 72]
    if c.failed:
        out.append("  REFUTED -- a gate recomputed these and they did not hold:")
        for text, detail in c.failed:
            out += [f"    - {text}", f"        {detail}"]
    if c.options_removed:
        out.append("  ANSWERS REMOVED on their own arithmetic:")
        for oid, why in c.options_removed:
            out += [f"    - {oid}", f"        {why}"]
    if c.passed:
        out.append(f"  VERIFIED -- {len(c.passed)} claim(s) recomputed and held:")
        for text, detail in c.passed[:10]:
            out += [f"    - {text}", f"        {detail[:100]}"]
    if c.warrant_held:
        out += ["", "  EVIDENCE VERIFIED, PROPOSITION OPEN:",
                "    The named check ran and held. Whether it establishes the",
                "    sentence is a reading, and no gate here settles it."]
        for text, _ in c.warrant_held[:10]:
            out.append(f"    - {text}")
    if c.blocked:
        out += ["", f"  BLOCKED -- {len(c.blocked)} check(s) could not run.",
                "    NOT evidence against the claim. A paywall, a timeout or an",
                "    expression this evaluator cannot handle is not a refutation."]
        for text, detail in c.blocked[:10]:
            out += [f"    - {text}", f"        {detail[:100]}"]
    if not (c.failed or c.passed or c.blocked or c.warrant_held
            or c.options_removed):
        out.append("  NOTHING WAS MECHANICALLY CHECKED. The reply carried no "
                   "claim or commitment any gate could reach.")

    out += ["", "=" * 72, "2. WHAT NEEDS YOU  (SOP 2.3 step 5)", "=" * 72]
    if c.open_items:
        out.append(f"  {len(c.open_items)} item(s) reached no gate. These are "
                   f"the judgment calls:")
        for text in c.open_items:
            out.append(f"    - {text}")
    else:
        out.append("  Nothing. Every assertion reached a gate.")
    if c.options_untested:
        out += ["",
                f"  {len(c.options_untested)} ANSWER(S) WERE NEVER TESTED: "
                f"{', '.join(c.options_untested)}",
                "    They declared no commitment this code could compute, so",
                "    nothing about them was checked. On the page that looks",
                "    identical to surviving scrutiny. It is not."]

    out += ["", "=" * 72, "3. THE ANSWER", "=" * 72]
    out.append(c.record.strip() if c.record else "(no option set was parsed)")

    out += ["", "=" * 72, "4. WHAT THIS IS NOT", "=" * 72,
            "  ONE MODEL. There is no panel here, so there is no independence",
            "  to measure: error correlation, effective seat count, per-pass",
            "  divergence and the collapse flag are properties of a panel and",
            "  are UNDEFINED at one seat -- not zero. Nothing above reports",
            "  them, and a figure claiming to would be describing the absence",
            "  of a panel as agreement.",
            "",
            "  NO ANSWER HERE HAS BEEN TESTED BY ANYTHING OUTSIDE ITSELF,",
            "  and that is true of every run of this instrument rather than",
            "  of this one. A commitment that survives is one whose own",
            "  arithmetic held. Scrutiny means somebody tried to break it, and",
            "  with one seat nobody can.",
            "",
            "  NO CORROBORATION. An answer is removed here only by its OWN",
            "  formula failing on its OWN inputs. 'Two seats independently gave",
            "  the same different value' cannot happen with one, so a disputed",
            "  input is never outweighed.",
            "",
            "  A VERIFIED CLAIM IS NOT A TRUE ANSWER. The gates check what was",
            "  offered. An answer standing here has not been refuted, which is",
            "  a smaller fact than being right.",
            "",
            f"  Exit code {c.exit_code}: "
            + ("one answer stands, nothing refuted, nothing open."
               if c.resolved else
               "not resolved -- see sections 1 and 2.")]
    return out


# ---------------------------------------------------------------------------
# the command
# ---------------------------------------------------------------------------

SEAT = os.environ.get("ONE_MODEL_SEAT", "seat_1")
CEILING = float(os.environ.get("ONE_MODEL_CEILING", "1.00"))
"""One call. A dollar is generous and it is still a hard refusal if the plan
does not fit -- there is no reason for this instrument to ever cost more."""
CAP = int(os.environ.get("ONE_MODEL_CAP", "8192"))
RESOLVE_DOIS = os.environ.get("ONE_MODEL_RESOLVE_DOIS", "").strip().lower() == "yes"
"""Citation gates reach Crossref and doi.org. Free and no credential, but a
default that quietly touches the network is not a default -- SOP 8.3 makes the
resolver the single most common way this build fails, so turning it on is the
operator's explicit choice."""


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: one_model.py <artifact-file>\n\n"
              "  Puts the artifact to ONE model and rules everything it\n"
              "  commits to. This is the mode Stage 0 measured us into:\n"
              "  baseline 0.968 and 1.000 on two task classes against a 0.45\n"
              "  threshold, so SOP 8.1 step 5 says one model plus gates.\n\n"
              "  ONE_MODEL_SEAT=seat_1        which seat to ask\n"
              "  ONE_MODEL_CEILING=1.00       hard spend bound for the call\n"
              "  ONE_MODEL_RESOLVE_DOIS=yes   enable citation gates (network)\n\n"
              "  Exits non-zero unless one answer stands with nothing refuted\n"
              "  and nothing left open.")
        return 2
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"no such file: {path}")
        return 2
    with open(path, encoding="utf-8") as fh:
        artifact = fh.read()
    if not artifact.strip():
        print(f"{path} is empty")
        return 2

    from cost_ledger import operator_ledger, rates_from_config
    from run_adjudication import live_seats, load_env_file, night_gates
    print(load_env_file())
    with open(os.path.join(HERE, "rates.json"), encoding="utf-8") as fh:
        rates = rates_from_config(json.load(fh))
    # COUNTS AGAINST THE DAY, and it did not. The comment here used to say
    # a single checked answer must not consume the panel's daily budget --
    # true about allocation, and it left the operator with no daily limit at
    # all, because every other tool said the same thing about itself.
    ledger = operator_ledger(rates, per_run=CEILING)
    print(f"  daily ceiling ${ledger.per_day:.2f} across ALL tools "
          f"(ADJUDICATION_DAY_CEILING to change)")
    seats = live_seats(os.path.join(HERE, "profiles.json"), ledger=ledger)
    if SEAT not in seats:
        print(f"  no seat {SEAT!r}; configured: {sorted(seats)}")
        return 2
    seat = seats[SEAT]
    if hasattr(seat, "max_tokens"):
        seat.max_tokens = CAP
    if hasattr(seat, "set_pass"):
        seat.set_pass("one-model")

    gates = night_gates() if RESOLVE_DOIS else None
    print(f"  ONE seat: {SEAT}, cap {CAP}, ceiling ${CEILING:.2f}, 1 call")
    print(f"  citation gates: {'ON (reaches Crossref and doi.org)' if RESOLVE_DOIS else 'off'}")

    t0 = time.time()
    result = check(artifact, seat, gates=gates,
                   on_event=lambda m: print(f"  {m}", flush=True))
    result.dollars = float(getattr(ledger, "spent", 0.0))
    print(f"  wall clock: {time.time() - t0:.0f}s")
    print("\n".join(ledger.render()))

    lines = render(result)
    print()
    print("\n".join(lines))

    out_dir = os.path.join(HERE, "runs", f"one-{time.strftime('%Y%m%d-%H%M%S')}")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "checked.md"), "w", encoding="utf-8") as fh:
        fh.write("# One model plus gates\n\n```\n" + "\n".join(lines) + "\n```\n")
    with open(os.path.join(out_dir, "reply.md"), "w", encoding="utf-8") as fh:
        fh.write(result.answer)
    print(f"\n  written to {out_dir}")
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
