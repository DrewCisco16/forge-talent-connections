"""
option_set.py
=============
The answers under consideration, owned by code rather than by a model.

WHY THIS FILE EXISTS. The closing model was handed the round's material and
returned free-form prose, and that prose became both the operator's answer and
the next round's starting point. Nothing in the pipeline held a list of what
was actually still standing, so the closer's text WAS the survivor set. An
outside review demonstrated the consequence with a one-round panel:

    thinker: CLAIM | arithmetic | 2 + 2 = 5 | Liquidate inventory immediately.
    closer:  Liquidate inventory immediately.

The false warrant was caught and the claim was refuted. The proposition rode
through anyway, into the operator's packet and into round two's prompt, because
no code anywhere was tracking that it had been removed.

THE FIX IS STRUCTURAL, NOT A BETTER DETECTOR. A detector asks "did the model
smuggle something?" and can always be evaded by prose that reads differently.
This asks a different question: what is still standing? Code answers it, from
gate verdicts, and the closer renders that answer instead of deciding it.

WHAT THE CLOSER STILL DOES. Everything that needs judgement: merging duplicate
proposals into one option, wording them clearly, naming what is missing, and
saying what would separate two survivors. What it can no longer do is change
which options exist. Membership is arithmetic over verdicts; prose is not.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from adjudication_orchestrator import Claim

_NUMBERED = re.compile(r"^\s{0,3}(?:\d{1,2}[.)]|[-*])\s+(.+?)\s*$")
MAX_OPTIONS = 12
"""More than this and round one has not narrowed anything.

Five seats proposing two to four options each can produce twenty near
duplicates. A list nobody can hold in mind is not an option set, and every
later round would spend its budget re-reading it.
"""

MIN_OPTION_CHARS = 12


def option_id(text: str) -> str:
    """Content-addressed, so the same option keeps its identity across rounds.

    A positional id would move whenever the closer reordered its list, and
    every elimination recorded against position 3 would silently point at a
    different answer next round.
    """
    norm = " ".join((text or "").split()).strip(" .;:—-").casefold()
    return "opt_" + hashlib.sha256(norm.encode("utf-8")).hexdigest()[:12]


@dataclass
class Option:
    """One answer under consideration."""

    id: str
    text: str
    claims: list[str] = field(default_factory=list)
    """Ids of the claims this option rests on."""
    eliminated_in_round: int | None = None
    elimination_reason: str | None = None

    @property
    def alive(self) -> bool:
        return self.eliminated_in_round is None


def parse_options(text: str) -> list[Option]:
    """Read a numbered or bulleted list into options.

    Round one is the only round that may create options, so this runs once.
    Anything that is not a list item is prose about the list and is ignored --
    a heading, a preamble, or the closer explaining what it did.
    """
    out: list[Option] = []
    seen: set[str] = set()
    for line in (text or "").splitlines():
        m = _NUMBERED.match(line)
        if not m:
            continue
        body = m.group(1).strip()
        if len(body) < MIN_OPTION_CHARS:
            continue
        oid = option_id(body)
        if oid in seen:
            continue
        seen.add(oid)
        out.append(Option(id=oid, text=body))
        if len(out) >= MAX_OPTIONS:
            break
    return out


def attach_claims(options: Sequence[Option],
                  claims: Sequence[Claim]) -> None:
    """Record which claims each option rests on.

    A claim belongs to an option when the option's text contains a distinctive
    run of the claim's text, or the claim names the option's id outright. This
    is the one place a textual association survives, and it is used ONLY to
    attach evidence -- never to decide membership, which is what made prose
    dangerous in the first place. An option with no attached claims is not
    eliminable by evidence, and says so in the report rather than looking
    examined.
    """
    for opt in options:
        haystack = " ".join(opt.text.split()).casefold()
        for claim in claims:
            needle = " ".join((claim.text or "").split()).casefold()
            if (len(needle) >= MIN_OPTION_CHARS and needle in haystack
                    and claim.id not in opt.claims):
                opt.claims.append(claim.id)


def eliminate(options: Sequence[Option],
              verdicts: Mapping[str, object],
              round_n: int,
              claims_by_id: Mapping[str, Claim] | None = None) -> list[Option]:
    """Remove options whose own claims were refuted. Returns those removed.

    ONLY A STANDING FAIL REMOVES ANYTHING. A blocked check did not happen and
    an escalated claim has not been ruled on, so neither can take an option
    out -- that is the same rule the rest of the system runs on, applied here
    rather than left to a model's prose.
    """
    removed: list[Option] = []
    for opt in options:
        if not opt.alive:
            continue
        for cid in opt.claims:
            verdict = verdicts.get(cid)
            if getattr(getattr(verdict, "status", None), "value", None) != "fail":
                continue
            claim = (claims_by_id or {}).get(cid)
            what = f" ({claim.text})" if claim is not None else ""
            opt.eliminated_in_round = round_n
            opt.elimination_reason = (
                f"round {round_n}: a claim it rests on was mechanically "
                f"refuted{what} -- {getattr(verdict, 'detail', '')}"
            )
            removed.append(opt)
            break
    return removed


def render(options: Sequence[Option]) -> str:
    """The working answer, assembled by code from what is still standing.

    THIS TEXT, NOT THE CLOSER'S, IS WHAT CARRIES FORWARD. The closer's prose
    is attached to it as commentary. That is the whole point: a proposition
    the gates removed cannot reappear in the next round's prompt, because the
    next round's prompt is built from this list and this list is arithmetic
    over verdicts.
    """
    alive = [o for o in options if o.alive]
    lines = ["## Options still standing", ""]
    if not alive:
        lines.append("(none -- every option had a claim mechanically refuted)")
    for i, opt in enumerate(alive, 1):
        lines.append(f"{i}. [{opt.id}] {opt.text}")
    gone = [o for o in options if not o.alive]
    if gone:
        lines += ["", "## Removed", ""]
        for opt in gone:
            lines.append(f"- [{opt.id}] {opt.text}")
            lines.append(f"      {opt.elimination_reason}")
    return "\n".join(lines)


def unexamined(options: Sequence[Option]) -> list[Option]:
    """Surviving options that no claim was ever attached to.

    They survived because nothing tested them, which is a completely different
    fact from surviving scrutiny -- and on the page the two look identical.
    """
    return [o for o in options if o.alive and not o.claims]
