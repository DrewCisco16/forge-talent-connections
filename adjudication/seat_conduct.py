"""
seat_conduct.py
===============
Per-seat conduct: which model asserted what, and which of those assertions the
gates ruled false. AI governance for the panel itself.

WHAT THIS CAN AND CANNOT ESTABLISH -- read this before using the output.

The ask was to log lying, embellishing, hallucinating, and drifting against
the model responsible. Only the observable half of that is buildable, and the
distinction is not pedantry:

    OBSERVABLE, and recorded here
      seat_1 asserted "revenue = 665000" and the arithmetic recomputes 647500
      seat_3 cited 10.1038/s41586-000-0000-0 and it resolves nowhere
      seat_4 asserted an arithmetic claim and supplied no expression to check

    NOT OBSERVABLE, and deliberately not recorded
      whether seat_1 KNEW the figure was wrong          (lying needs intent)
      whether seat_3 BELIEVED the DOI existed           (hallucination is a
                                                         claim about an
                                                         internal state)
      whether seat_4 was being evasive or merely terse  (embellishment needs
                                                         a motive)

A ledger that claimed to detect lying would be making exactly the kind of
unfounded assertion it exists to police, and it would be doing so about a
system that cannot answer back. So the categories below are named for what a
gate saw, not for what a model meant. "FABRICATED_CITATION" is shorthand for
"cited an identifier that does not resolve" -- which is the mechanical
signature of fabrication and is grounds for corrective action -- not a finding
about the model's inner life.

DRIFT is handled the same way. What is observable is a seat's rate of ruled-
false claims changing across the five passes. That is reported as a trend and
labelled a trend. Whether the model "drifted" in any richer sense is not
something this file will assert.

WHY RATES AND NOT COUNTS. A seat that proposes 200 claims and gets 6 wrong is
not worse than one that proposes 8 and gets 4 wrong, and ranking on raw counts
would punish the most productive seat on the panel. Every summary carries the
denominator.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum


class ConductCategory(str, Enum):
    """Named for the observation, never for the intent behind it."""

    FABRICATED_CITATION = "fabricated_citation"
    """Cited an identifier that does not resolve. The mechanical signature of
    a fabricated source."""

    INADMISSIBLE_SOURCE = "inadmissible_source"
    """Offered a source class the panel does not accept as a warrant."""

    FALSE_ARITHMETIC = "false_arithmetic"
    """Stated a numeric result that recomputes to something else."""

    FALSE_UNIT = "false_unit"
    """Stated a conversion that does not hold, or mixed dimensions."""

    FAILED_SCHEMA = "failed_schema"
    """Offered a structured payload that does not parse or lacks required keys."""

    FAILED_CODE_BEHAVIOR = "failed_code_behavior"
    """Asserted a behaviour whose test command did not pass."""

    UNSOURCED_QUOTE = "unsourced_quote"
    """Quoted a string that is not at the URL it was attributed to.

    Distinct from FABRICATED_CITATION: that one invents a source, this one
    invents what a real source says. The second is harder to catch by reading
    and does more damage, because the source checks out."""

    WRONG_PAPER_CITATION = "wrong_paper_citation"
    """Cited a DOI that resolves to a different work than the one named.

    The characteristic model citation error. Resolution alone passes it."""

    MALFORMED_WARRANT = "malformed_warrant"
    """Supplied a warrant the gate could not read at all -- an assertion of
    checkability that was not actually checkable."""


_GATE_TO_CATEGORY = {
    "citation_resolution": ConductCategory.FABRICATED_CITATION,
    "source_admissibility": ConductCategory.INADMISSIBLE_SOURCE,
    "arithmetic": ConductCategory.FALSE_ARITHMETIC,
    "unit": ConductCategory.FALSE_UNIT,
    "schema": ConductCategory.FAILED_SCHEMA,
    "test_execution": ConductCategory.FAILED_CODE_BEHAVIOR,
    "quote_verification": ConductCategory.UNSOURCED_QUOTE,
    "citation_field_match": ConductCategory.WRONG_PAPER_CITATION,
}


@dataclass(frozen=True)
class ConductFinding:
    seat_id: str
    claim_id: str
    category: ConductCategory
    gate: str
    detail: str
    pass_id: str | None = None


@dataclass
class SeatRecord:
    seat_id: str
    proposed: int = 0
    findings: list[ConductFinding] = field(default_factory=list)

    @property
    def ruled_false(self) -> int:
        return len(self.findings)

    @property
    def rate(self) -> float:
        """Ruled-false share of what this seat proposed. 0.0 when it proposed
        nothing -- a silent seat has no conduct record, which is a different
        fact from a clean one and is reported as such."""
        return self.ruled_false / self.proposed if self.proposed else 0.0

    def by_category(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.findings:
            out[f.category.value] = out.get(f.category.value, 0) + 1
        return out


class ConductLedger:
    """Built after a run, from data the orchestrator already keeps.

    Attribution uses detections_by_seat, which credits EVERY seat that
    proposed a claim, not only the first. A claim is gated once; the ruling
    applies to everyone who asserted it. Attributing a false claim solely to
    whichever seat happened to speak first would let the others assert the
    same falsehood for free.
    """

    def __init__(self) -> None:
        self.seats: dict[str, SeatRecord] = {}

    @classmethod
    def from_run(
        cls,
        detections_by_seat: Mapping[str, set[str]],
        verdicts: Mapping[str, object],
        all_seat_ids: "Sequence[str] | None" = None,
    ) -> ConductLedger:
        """all_seat_ids makes SILENT seats visible.

        A seat that proposed nothing never appears in detections_by_seat, so
        without this it vanishes from the ledger entirely -- and a seat absent
        from a conduct report reads as a seat with nothing against it. Those
        are opposite facts: one was examined and found clean, the other was
        never heard from, and only the second is a reason to check whether the
        panel is actually running five seats.
        """
        led = cls()
        seats = dict(detections_by_seat)
        for sid in (all_seat_ids or ()):
            seats.setdefault(sid, set())
        for seat_id, claim_ids in seats.items():
            rec = SeatRecord(seat_id, proposed=len(claim_ids))
            for cid in sorted(claim_ids):
                v = verdicts.get(cid)
                if v is None:
                    continue                      # escalated, never ruled
                status = getattr(getattr(v, "status", None), "value", None)
                if status == "pass" or status is None:
                    continue
                gate = str(getattr(v, "gate", "") or "")
                cat = _GATE_TO_CATEGORY.get(gate, ConductCategory.MALFORMED_WARRANT)
                rec.findings.append(ConductFinding(
                    seat_id=seat_id, claim_id=cid, category=cat, gate=gate,
                    detail=str(getattr(v, "detail", "") or ""),
                    pass_id=getattr(v, "pass_id", None),
                ))
            led.seats[seat_id] = rec
        return led

    # -- reporting ---------------------------------------------------------
    def total_findings(self) -> int:
        return sum(r.ruled_false for r in self.seats.values())

    def ranked(self) -> list[SeatRecord]:
        """Worst rate first, then most findings. Seats that proposed nothing
        sort last: they have no record, not a clean one."""
        return sorted(
            self.seats.values(),
            key=lambda r: (r.proposed == 0, -r.rate, -r.ruled_false, r.seat_id),
        )

    def as_payload(self) -> dict[str, object]:
        """Audit-log shape. Claim ids only -- no claim text, so a conduct
        record of a sensitive run does not itself carry the material."""
        return {
            "total_findings": self.total_findings(),
            "seats": {
                r.seat_id: {
                    "proposed": r.proposed,
                    "ruled_false": r.ruled_false,
                    "rate": round(r.rate, 4),
                    "by_category": r.by_category(),
                    "claim_ids": [f.claim_id for f in r.findings],
                }
                for r in self.ranked()
            },
        }

    def render(self) -> list[str]:
        out: list[str] = []
        out.append("-" * 72)
        out.append("SEAT CONDUCT -- what each model asserted that did not hold")
        out.append("-" * 72)
        if not self.seats:
            out.append("  no seat proposed a claim; nothing to attribute")
            return out
        for r in self.ranked():
            if r.proposed == 0:
                out.append(f"  {r.seat_id:<14} proposed nothing -- no record "
                           f"(not the same as a clean one)")
                continue
            out.append(f"  {r.seat_id:<14} {r.ruled_false:>3} of {r.proposed:>3} "
                       f"claims ruled false  ({r.rate:.1%})")
            for cat, n in sorted(r.by_category().items(), key=lambda kv: -kv[1]):
                out.append(f"       {n:>3}  {cat}")
        out.append("")
        out.append("  Ruled false means a gate recomputed, resolved, or parsed the")
        out.append("  claim and it did not hold. It does not establish intent, and")
        out.append("  is not a finding that a model lied.")
        return out
