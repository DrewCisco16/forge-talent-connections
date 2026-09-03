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

from adjudication_orchestrator import Claim, warrant_supports

_NUMBERED = re.compile(r"^\s{0,3}(?:\d{1,2}[.)]|[-*])\s+(.+?)\s*$")


class TooManyOptions(ValueError):
    """Round one produced more options than a later round can work through.

    SILENTLY TRUNCATING WAS WORSE THAN REFUSING. The list was cut to the first
    twelve, so reversing the closer's ordering changed which option vanished --
    an answer could be dropped from consideration by the order it happened to
    be written in, with nothing recorded anywhere.
    """


_SECTION_HEADING = re.compile(
    r"^\s{0,3}(?:#{1,6}\s*)?(OPEN|KILLED|REMOVED|HOLES|NOTES|CAVEATS|"
    r"STILL OPEN|WHAT THIS ROUND COULD NOT CLOSE)\b", re.IGNORECASE)
"""Headings after which list items are NOT options.

The closer is required to end with an OPEN list naming what the round could
not settle. Those bullets were parsed as options, so a hole became a candidate
answer.
"""

MAX_OPTIONS = 30
"""More than this and round one has not narrowed anything.

WAS 12, AND THAT REFUSED A PERFECTLY NORMAL ROUND. Five seats each proposing
three or four options is fifteen to twenty entries before any merging, and a
live canary produced sixteen -- so the whole run was recorded as having no
usable option set and nothing could be eliminated from it.

The number has to sit above what five seats genuinely produce, because merging
happens AFTER this and is what brings the count down. This is a guard against
a seat emitting a hundred lines, not a limit on how many answers a panel may
consider.
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


def _parse_list(text: str) -> list[Option]:
    """Shared list reader. See parse_options for the rules it applies."""
    return parse_options(text)


def parse_options(text: str) -> list[Option]:
    """Read a numbered or bulleted list into options.

    Round one is the only round that may create options, so this runs once.
    Anything that is not a list item is prose about the list and is ignored --
    a heading, a preamble, or the closer explaining what it did.
    """
    out: list[Option] = []
    seen: set[str] = set()
    in_options = True
    for line in (text or "").splitlines():
        if _SECTION_HEADING.match(line):
            # Everything after an OPEN or KILLED heading is commentary about
            # the round, not a further answer to consider.
            in_options = False
            continue
        if line.strip().startswith("#"):
            in_options = True          # a new heading; options may resume
            continue
        m = _NUMBERED.match(line)
        if not m or not in_options:
            continue
        body = m.group(1).strip()
        if len(body) < MIN_OPTION_CHARS:
            continue
        oid = option_id(body)
        if oid in seen:
            continue
        seen.add(oid)
        out.append(Option(id=oid, text=body))
    if len(out) > MAX_OPTIONS:
        raise TooManyOptions(
            f"round one produced {len(out)} options, over the {MAX_OPTIONS} a "
            f"later round can work through. Truncating would drop answers by "
            f"the order they happened to be written in; the round is recorded "
            f"as producing no usable option set instead."
        )
    return out


def attach_claims(options: Sequence[Option],
                  claims: Sequence[Claim]) -> None:
    """Record which claims each option depends on, from DECLARED edges only.

    THE TEXT-MATCHING VERSION WAS UNSOUND IN BOTH DIRECTIONS. It attached a
    claim when the claim's text appeared inside the option's text, so:

      - a paraphrase attached to nothing, and its option survived untested
        while looking examined;
      - a NEGATION attached, because "Do not liquidate inventory immediately"
        contains "Liquidate inventory immediately" -- so a refuted claim
        removed the option asserting its opposite.

    Similarity is not dependency. A seat that wants to say a claim bears on an
    option names that option's id, which it can do because the ids are printed
    in the prompt it was given. A claim naming no option still gets
    adjudicated and still appears in the report; it simply cannot remove
    anything, which is the correct treatment of an assertion whose target
    nobody stated.
    """
    by_id = {o.id: o for o in options}
    for claim in claims:
        target = by_id.get((claim.about_option or "").lower())
        if target is not None and claim.id not in target.claims:
            target.claims.append(claim.id)


def eliminate(options: Sequence[Option],
              verdicts: Mapping[str, object],
              round_n: int,
              claims_by_id: Mapping[str, Claim] | None = None) -> list[Option]:
    """Remove options whose declared dependencies were refuted ON THE POINT.

    THREE CONDITIONS, ALL REQUIRED:

      1. the claim DECLARED that it is about this option;
      2. its standing verdict is FAIL;
      3. the refuted warrant actually BEARS ON the claim's proposition.

    The third was missing, and its absence was the worst defect this tool has
    had. warrant_supports() ran only after a gate PASSed, so the acceptance
    side was bound to the proposition and the ELIMINATION side was not. An
    unrelated false equation therefore destroyed an option outright:

        1. Launch immediately.
        2. Abort immediately.
        CLAIM | arithmetic | 2 + 2 = 5 | Launch immediately.

    "2 + 2 = 5" is false. It says nothing whatever about launching. The run
    removed "Launch immediately", kept "Abort immediately", and reported
    MECHANICAL ADJUDICATION: COMPLETE with no caveats -- a confident wrong
    answer to a launch-or-abort question, produced by machinery that had
    checked arithmetic and nothing else.

    Removing on an unrelated warrant is strictly worse than accepting on one.
    A false acceptance leaves a wrong answer among the candidates; a false
    removal deletes the right one and makes the survivor look earned.

    BLOCKED and ESCALATED remove nothing: a check that did not happen and a
    claim nobody ruled on are not refutations.
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
            if claim is None:
                continue
            unbound = warrant_supports(claim)
            if unbound is not None:
                # Refuted, but not on this proposition. The claim stays
                # refuted in the record; the option stands.
                continue
            opt.eliminated_in_round = round_n
            opt.elimination_reason = (
                f"round {round_n}: a claim it declared it rests on was "
                f"mechanically refuted ({claim.text}) -- "
                f"{getattr(verdict, 'detail', '')}"
            )
            removed.append(opt)
            break
    return removed


def render_working(options: Sequence[Option]) -> str:
    """What carries into the next round: LIVING OPTIONS ONLY.

    render() used to include a "## Removed" section with each elimination
    reason, and that whole text became the next round's starting point -- so a
    refuted proposition appeared three times in every seat's round-two prompt.
    Removing an option from a list and then printing it to everyone is not
    removing it.

    The removed set is not lost. It goes to the audit record and the
    operator's packet, where it belongs: the operator needs to know what was
    ruled out and why, and the seats need to not be thinking about it.
    """
    alive = [o for o in options if o.alive]
    lines = ["## Options still standing", ""]
    if not alive:
        lines.append("(none -- every option had a declared claim refuted)")
    for i, opt in enumerate(alive, 1):
        lines.append(f"{i}. [{opt.id}] {opt.text}")
    lines += [
        "",
        "Cite an option by its bracketed id when a claim bears on it:",
        "    CLAIM | <kind> | <warrant> | <option id> | <the claim>",
        "A claim that names no option is still checked and still reported, but",
        "cannot remove anything -- nobody said what it was about.",
    ]
    return "\n".join(lines)


def render_record(options: Sequence[Option]) -> str:
    """The full picture for the audit trail and the operator's packet."""
    lines = [render_working(options)]
    gone = [o for o in options if not o.alive]
    if gone:
        lines += ["", "## Removed", ""]
        for opt in gone:
            lines.append(f"- [{opt.id}] {opt.text}")
            lines.append(f"      {opt.elimination_reason}")
    return "\n".join(lines)


def unexamined(options: Sequence[Option],
               verdicts: Mapping[str, object] | None = None) -> list[Option]:
    """Surviving options that nothing actually RULED ON.

    An option survives because nothing removed it. That is a completely
    different fact from surviving scrutiny, and on the page the two look
    identical -- so the difference has to be reported.

    A NON-EMPTY CLAIM LIST IS NOT EXAMINATION. This returned only options with
    no attached claims at all, so an option whose sole dependency was BLOCKED
    (a check that could not run) or ESCALATED (nobody ruled on it) counted as
    examined. A sole survivor resting on one blocked `sqrt(4) = 2` was
    presented under "the answer that survived".

    Examined means at least one declared dependency reached a real verdict --
    PASS or FAIL. Anything else leaves the option untested.
    """
    if verdicts is None:
        return [o for o in options if o.alive and not o.claims]
    out: list[Option] = []
    for opt in options:
        if not opt.alive:
            continue
        ruled = any(
            getattr(getattr(verdicts.get(cid), "status", None), "value", None)
            in ("pass", "fail")
            for cid in opt.claims
        )
        if not ruled:
            out.append(opt)
    return out


_MERGE = re.compile(r"^\s*MERGE\s*\|(.+)$", re.IGNORECASE)
_OPT_ID = re.compile(r"opt_[0-9a-f]{6,}", re.IGNORECASE)


def parse_proposals(thinker_texts: Mapping[str, str]) -> list[Option]:
    """The option pool, built from what the THINKERS actually proposed.

    ROUND ONE'S OPTION SET USED TO COME FROM THE CLOSER'S LIST, which meant
    the closer decided what the answers were. It could recombine words from
    two different proposals into a third that nobody made -- given "Hold all
    inventory until next quarter" and "Liquidate only damaged inventory this
    week", it emitted "Hold damaged inventory this week", and that became the
    SOLE option. The invention detector missed it because every word had
    occurred in some thinker's text.

    So the pool comes from the seats that wrote blind, and nothing else may
    add to it. Later immutable ids protected only the set the closer chose;
    this protects which set that is.

    Every proposal from every seat enters the pool. Identical wording collapses
    by content id, and near-duplicates are what the merge step below is for --
    which is a real job requiring judgement, and the one the closer keeps.
    """
    pool: list[Option] = []
    seen: set[str] = set()
    for _seat, text in sorted(thinker_texts.items()):
        for opt in _parse_list(text):
            if opt.id in seen:
                continue
            seen.add(opt.id)
            pool.append(opt)
    return pool


def apply_merges(pool: Sequence[Option], closer_text: str) -> list[Option]:
    """Collapse near-duplicates the closer identified, by id.

    The closer is shown the pool with ids and answers in lines like

        MERGE | opt_3f9a2c | opt_88ab01

    meaning those name the same answer. It cannot introduce an option this
    way: an id that is not in the pool is ignored, and prose is ignored
    entirely. The surviving member of a group is the FIRST one in pool order,
    chosen by this code rather than by the closer, so the wording that
    survives is a seat's own.

    A closer that merges nothing leaves the pool as it stands, which is the
    honest result when nothing was a duplicate -- and the safe one when the
    closer failed.
    """
    by_id = {o.id: o for o in pool}
    absorbed: dict[str, str] = {}
    for line in (closer_text or "").splitlines():
        m = _MERGE.match(line)
        if not m:
            continue
        ids = [i.lower() for i in _OPT_ID.findall(m.group(1))
               if i.lower() in by_id]
        # Follow any chain already recorded, so two merge lines naming an
        # option that has itself been absorbed land on the same survivor.
        ids = [_resolve(i, absorbed) for i in ids]
        unique = list(dict.fromkeys(ids))
        if len(unique) < 2:
            continue
        keeper = min(unique, key=lambda i: [o.id for o in pool].index(i))
        for other in unique:
            if other != keeper:
                absorbed[other] = keeper
    return [o for o in pool if o.id not in absorbed]


def _resolve(option_id_: str, absorbed: Mapping[str, str]) -> str:
    seen: set[str] = set()
    while option_id_ in absorbed and option_id_ not in seen:
        seen.add(option_id_)
        option_id_ = absorbed[option_id_]
    return option_id_


def render_pool(pool: Sequence[Option]) -> str:
    """The pool as the closer sees it, for the round-one merge step."""
    lines = ["## Every option the seats proposed", ""]
    for i, opt in enumerate(pool, 1):
        lines.append(f"{i}. [{opt.id}] {opt.text}")
    lines += [
        "",
        "Some of these are the same answer worded differently. Say so with",
        "one line per group, naming the ids:",
        "",
        "    MERGE | opt_3f9a2c | opt_88ab01",
        "",
        "You may not add an option here, reword one, or leave one out. The",
        "list above is what the seats proposed and it is the whole option set;",
        "your merges only say which entries are the same answer. Anything you",
        "write that is not a MERGE line is read as commentary.",
    ]
    return "\n".join(lines)
