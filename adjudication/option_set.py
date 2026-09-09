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
from dataclasses import dataclass, field, replace

from adjudication_orchestrator import Claim, undecorate_marker_line
from predicate import (
    Predicate,
    Ruling,
    TooManyCommitments,
    parse_predicates,
    refuted_commitment,
)

_FENCE = re.compile(r"^\s*(?:```|~~~)")
"""A code fence. What is inside one is an example, not a proposal."""

_OPTION_LINE = re.compile(r"^\s*OPTION\s*\|\s*(.+?)\s*$", re.IGNORECASE)
"""How a seat marks an answer, matching the CLAIM convention it already uses.

NUMBERING WAS NOT ENOUGH. A model numbers whatever it is enumerating -- its
premises, its criteria, the evidence that would settle a point. A live canary
produced forty "options" from bullets, and after restricting to numbered lines
still produced ten, of which the first three were "The panel consists of five
AI seats", "The panel evaluates over a maximum of five rounds", and "Each
round costs approximately six API calls". Those are premises the seat was
restating, not answers it was proposing.

The seats follow CLAIM | faithfully, so options use the same shape. An
explicit marker is the only thing that distinguishes "here is an answer" from
"here is part of my reasoning", because in prose it is a matter of intent and
nothing in the layout carries it.
"""

_DECLARED_OPTION = re.compile(
    r"^\s{0,3}(?:#{1,6}\s*)?(?:\*\*|__)?\s*"
    r"(?:OPTION|ANSWER|PROPOSAL|CANDIDATE)\s*"
    r"(?:\d{1,2}|[A-Z]|[IVX]{1,4})?\s*"
    r"[:.\)\u2014\u2013-]{1,3}\s*"
    r"(.+?)\s*(?:\*\*|__)?\s*$",
    re.IGNORECASE)
"""A heading in which the seat CALLS the thing an option.

NUMBERING IS NOT A DECLARATION. Any numbered line used to count, and a model
numbers whatever it is enumerating. A live canary produced forty "options" from
bullets; restricting to numbered lines still produced ten, of which eight were
one seat's premise list -- "The panel consists of five AI seats", "The panel
evaluates over a maximum of five rounds", "Each round costs approximately six
API calls". The three answers that seat actually proposed were not among them.
The panel would have spent five rounds and real money adjudicating its own
setup while the real candidates were never on the table.

Telling a premise from a proposal is a question of what the writer MEANT, and
no amount of layout carries it. So the seat has to say so. On the same canary
four of five seats wrote exactly that unprompted, in four different house
styles -- "### Option 1:", "**Option 1:**", "## Option A --" -- so this reads
what the models already produce rather than imposing a new convention. The
fifth wrote bold numbered lines with no such word, and contributes nothing
here: an empty option set is recoverable and a wrong one is not.

The required-output contract asks for OPTION | lines, which remain the primary
path. This catches the seat that answered in its own format.
"""


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

MIN_OPTION_CHARS = 3
"""Shortest text that can be an answer.

IT WAS 12, AND "Do nothing." IS ELEVEN. So were "Wait." and "Ship it." --
short answers to exactly the kind of question this tool is for, discarded
without a word, and later rounds only remove, so they were gone for good.

The floor was set when a bullet fallback was producing fragments and needed
something to filter them. That fallback is gone: an answer now has to be
DECLARED, and a seat that declares "Wait." meant it. Length was never the
thing that distinguished a fragment from an answer -- being declared is.
"""


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
    """Ids of claims MENTIONING this option. Reported, never load-bearing.

    These come from prose, and prose is exactly what could not be trusted to
    say what a warrant established. They are kept so the record shows what was
    argued about an option; they no longer remove it.
    """
    predicates: list[Predicate] = field(default_factory=list)
    """The typed commitments this option made, and the ONLY way it can go.

    Declared by the seat that proposed it, in the same reply, and fixed from
    that moment. See predicate.py for why elimination rests on these and not
    on sentences.
    """
    proposers: list[str] = field(default_factory=list)
    """Every seat that put this answer forward, in pool order.

    Two seats proposing the same answer are two advocates for it. Recording
    only the first lost the second's reasoning entirely.
    """
    parse_note: str | None = None
    """Why this option carries no commitment, when that was not the seat's
    intent. Recorded so a silently uncheckable answer is not mistaken for one
    that simply had nothing quantitative to say."""
    merged_into: str | None = None
    """Set when the closer said this is the same answer as another entry.

    IT STAYS IN THE SET. Absorbed options used to be dropped outright, so a
    model's judgment that two answers were "the same" silently removed one of
    them from consideration -- and the record showed two options created when
    three had been proposed, with no trace of the third. Whether two wordings
    are one answer is exactly the kind of semantic call this design refuses to
    let a model make about membership.

    So a merge now GROUPS rather than removes. The absorbed wording is still a
    candidate, still carries its own commitments, and can still be refuted or
    survive on its own; it is presented under its keeper so the seats are not
    re-reading the same answer five ways.
    """
    eliminated_in_round: int | None = None
    elimination_reason: str | None = None

    @property
    def alive(self) -> bool:
        return self.eliminated_in_round is None


def _parse_list(text: str) -> list[Option]:
    """Shared list reader. See parse_options for the rules it applies."""
    return parse_options(text)


def parse_options(text: str) -> list[Option]:
    """Read one seat's reply into the answers it declared.

    Round one is the only round that may create options, so this runs once.
    Anything that is not declared as an answer is reasoning about the answers
    and is ignored.

    BOTH DECLARED FORMS COUNT. An explicit OPTION line used to win OUTRIGHT,
    so a reply carrying one OPTION line and a "### Option 2:" heading kept
    only the first and dropped the second with no caveat anywhere. Later
    rounds only remove, so an answer missing from round one can never come
    back -- the omission is permanent and invisible. Reading both forms can at
    worst carry an option twice, and a duplicate is examined and reported
    while a dropped answer is simply gone.

    FENCED BLOCKS ARE NOT PROPOSALS. The contract shows seats an example
    OPTION line, and a seat quoting that example back inside a code fence had
    "This is merely an example" adjudicated as a candidate answer.
    """
    out: list[Option] = []
    seen: set[str] = set()
    blocks: list[tuple[str, list[str], bool]] = []
    current: list[str] | None = None
    in_options = True
    fenced = False

    for line in (text or "").splitlines():
        if _FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        # THE EXPLICIT MARKER, READ THROUGH WHATEVER THE MODEL DRESSED IT IN.
        # "- OPTION | ...", "**OPTION | ...**" and "1. OPTION | ..." all
        # failed this test, and _DECLARED_OPTION did not catch them either --
        # it wants a colon or a dash after the word, not a pipe. So a seat
        # that followed the contract exactly and then formatted its answer as
        # a list had that answer disappear: ten of twelve shapes measured
        # produced no option at all.
        #
        # Only this test reads the undecorated form. _SECTION_HEADING and
        # _DECLARED_OPTION keep reading the raw line, because both are about
        # markdown structure -- a heading level, a bold run -- and stripping
        # that structure first is exactly what would blind them.
        m = _OPTION_LINE.match(undecorate_marker_line(line))
        explicit = m is not None
        if m is None and _SECTION_HEADING.match(line):
            # Everything after an OPEN or KILLED heading is commentary about
            # the round, not a further answer to consider.
            in_options = False
            current = None
            continue
        if m is None:
            m = _DECLARED_OPTION.match(line)
            if m is not None and not in_options:
                # An option heading under OPEN or KILLED names that section's
                # subject; it is not a fresh answer being put forward.
                continue
        if m is None:
            if line.strip().startswith("#"):
                in_options = True      # a new heading; options may resume
                current = None
            elif current is not None:
                current.append(line)
            continue
        body = m.group(1).strip()
        if len(body) < MIN_OPTION_CHARS:
            current = None
            continue
        # ONE ANSWER, WRITTEN TWICE, IS STILL ONE ANSWER.
        #
        # Measured on the live panel: a seat heads each answer "### Option 3
        # -- floor of three rounds, then stop..." AND restates it as an
        # "OPTION | floor of three rounds, then stop..." line underneath. It
        # is being helpful -- a heading for the reader, a machine line for the
        # parser -- and reading both forms turned four answers into eight.
        #
        # The twins are not harmless. The commitments follow the OPTION line,
        # so the heading-derived copy carries none, cannot be checked, cannot
        # be removed, and survives to the end reported as untested. The panel
        # would have spent five rounds adjudicating phantoms.
        #
        # Positional, not lexical: an explicit line inside a heading's own
        # block is that heading restated, whatever words it uses.
        if explicit and blocks and blocks[-1][2] and blocks[-1][1] is current:
            blocks.pop()
        current = []
        blocks.append((body, current, not explicit))

    for body, own_lines, _from_heading in blocks:
        oid = option_id(body)
        if oid in seen:
            continue
        seen.add(oid)
        opt = Option(id=oid, text=body)
        # THE COMMITMENTS BIND BY POSITION, INSIDE THE PROPOSING SEAT'S OWN
        # REPLY. That is what makes them candidate-owned: an option can only
        # ever be removed by something the seat said about it while putting
        # it forward, never by an edge a later round invented.
        try:
            opt.predicates = list(
                parse_predicates(oid, "\n".join(own_lines)))
        except TooManyCommitments as exc:
            # FAIL CLOSED ON THE OPTION, NOT ON THE ROUND. An option that
            # declared too many figures carries none of them: it survives and
            # is reported as untested, which is the honest description. It
            # does not take the other seats' answers down with it.
            opt.predicates = []
            opt.parse_note = str(exc)
        out.append(opt)

    if len(out) > MAX_OPTIONS:
        raise TooManyOptions(
            f"one reply proposed {len(out)} options, over the {MAX_OPTIONS} a "
            f"later round can work through. Truncating would drop answers by "
            f"the order they happened to be written in, so the reply is "
            f"recorded as producing no usable option set instead."
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
              rulings: Mapping[str, Ruling],
              round_n: int,
              claims_by_id: Mapping[str, object] | None = None) -> list[Option]:
    """THE ONE FUNCTION THAT REMOVES A CANDIDATE. Both engines call it.

    An option goes when a TYPED COMMITMENT IT DECLARED ITSELF is refuted. That
    is the whole rule, and every part of it is structural:

      * the commitment is a quantity, a relation and a value, so ruling on it
        is a comparison rather than a reading;
      * the option declared it when it was proposed, so no later seat can
        attach a fresh dependency to a candidate it wants gone;
      * a FAIL means the arithmetic came out other than the option said.

    WHAT THIS REPLACED, AND WHY NOTHING LEXICAL CAME BACK. Removal used to
    need a claim to declare its target, hold a standing FAIL, and pass a rule
    that read the claim's sentence to decide whether the warrant established
    it. That last test was lexical, and every lexical version of it fell to a
    sentence it had not anticipated -- most plainly this pair, where one
    warrant supported a proposition AND its negation:

        warrant "2 + 2 = 4"  claim "The launch is 4 and safe to proceed"
        warrant "2 + 2 = 4"  claim "The launch is 4 and unsafe to proceed"

    Both were ruled supported. A refuted variant then removed an option the
    arithmetic said nothing about, and the run reported MECHANICAL
    ADJUDICATION: COMPLETE. Patching the rule would have closed those two
    strings; it would not have closed the property, because the property is
    that a sentence can always carry more than its warrant covers.

    So sentences no longer remove anything. `claims_by_id` is accepted and
    unused, kept so the legacy caller can hand over what it has without
    pretending those claims are load-bearing.

    BLOCKED and ESCALATED remove nothing. A check that could not run and a
    claim nobody ruled on are not refutations.
    """
    removed: list[Option] = []
    for opt in options:
        if not opt.alive:
            continue
        ruling = refuted_commitment(opt, rulings)
        if ruling is None:
            continue
        opt.eliminated_in_round = round_n
        opt.elimination_reason = (
            f"round {round_n}: a commitment this option declared when it was "
            f"proposed was mechanically refuted. {ruling.detail}")
        removed.append(opt)
    return removed


def render_working(options: Sequence[Option],
                   invite_challenges: bool = True) -> str:
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
    # AN ABSORBED OPTION WHOSE KEEPER IS GONE STANDS ON ITS OWN.
    #
    # Absorbed members were always shown under their keeper, so when the
    # keeper was refuted and the member was not, the member appeared nowhere:
    # not in the next round's prompt, not in the packet. The run reported one
    # option remaining and MECHANICAL ADJUDICATION: COMPLETE while the option
    # it was reporting had been silently dropped from the conversation.
    #
    # Grouping is a presentation convenience. It cannot be allowed to decide
    # what is on the table.
    living = {o.id for o in alive}
    grouped: dict[str, list[Option]] = {}
    for opt in alive:
        if opt.merged_into and opt.merged_into in living:
            grouped.setdefault(opt.merged_into, []).append(opt)
    i = 0
    for opt in alive:
        if opt.merged_into and opt.merged_into in living:
            continue                      # shown under its keeper, below
        i += 1
        lines.append(f"{i}. [{opt.id}] {opt.text}")
        # THE COMMITMENTS ARE SHOWN WITH THEIR IDS because challenging one is
        # the only way anything is removed. An option with none listed cannot
        # be eliminated by this machinery at all, and saying so plainly is
        # better than letting a seat spend the round attacking it in prose.
        for pred in opt.predicates:
            lines.append(f"      {pred.render()}")
        if not opt.predicates:
            lines.append("      (declared no checkable commitment)")
        # SAME ANSWER, ANOTHER SEAT'S WORDS. Listed rather than dropped: each
        # is still a candidate in its own right, with its own commitments,
        # and can be refuted or survive on its own.
        for other in grouped.get(opt.id, []):
            lines.append(f"   -- also proposed as [{other.id}] {other.text}")
            for pred in other.predicates:
                lines.append(f"      {pred.render()}")
    if not invite_challenges:
        # ONE SEAT CANNOT BE HANDED THE PANEL'S INSTRUCTIONS.
        #
        # Everything below invites a CHALLENGE and explains that agreement
        # between seats is what carries weight. With a single seat there is no
        # second observer, so the block describes a mechanism that cannot
        # operate -- and one_model.py's own report says so two sections later.
        # A deliverable that contradicts itself between section 3 and section 4
        # is the same defect as the calibration round being handed the removal
        # contract, and it was found the same way: by reading the output.
        return "\n".join(lines)
    lines += [
        "",
        "Each commitment shows its figure, the formula that produces it, and",
        "the numbers put into that formula. If you think one of those NUMBERS",
        "is wrong, say which and what it should be:",
        "",
        "    CHALLENGE | <commitment id> | per_round = 9",
        "",
        "You may change the inputs and nothing else. You cannot supply the",
        "formula and you cannot create a commitment: a seat that could write",
        "the computation could remove any answer it disliked by attaching",
        "arithmetic of its own choosing to it.",
        "",
        "A CHALLENGE DOES NOT REMOVE THE OPTION. It records that two seats put",
        "different numbers into the same formula and get different answers.",
        "Neither figure has been independently established, so a person",
        "settles it -- yours is not preferred for being later.",
        "",
        "WHAT REMOVES AN OPTION is its own arithmetic failing: the formula it",
        "declared, with the inputs it declared, not producing the figure it",
        "committed to. That needs nothing from you.",
        "",
        "CLAIM lines are still read, checked and reported. They remove",
        "nothing: a sentence can always assert more than its warrant covers.",
    ]
    return "\n".join(lines)


def render_record(options: Sequence[Option],
                  invite_challenges: bool = True) -> str:
    """The full picture for the audit trail and the operator's packet."""
    lines = [render_working(options, invite_challenges=invite_challenges)]
    gone = [o for o in options if not o.alive]
    if gone:
        lines += ["", "## Removed", ""]
        for opt in gone:
            lines.append(f"- [{opt.id}] {opt.text}")
            lines.append(f"      {opt.elimination_reason}")
    return "\n".join(lines)


def unexamined(options: Sequence[Option],
               verdicts: Mapping[str, object] | None = None) -> list[Option]:
    """Surviving options whose commitments were not ALL actually ruled on.

    An option survives because nothing removed it. That is a completely
    different fact from surviving scrutiny, and on the page the two look
    identical -- so the difference has to be reported.

    EVERY COMMITMENT HAS TO BE RULED, NOT MERELY ONE OF THEM. This asked
    whether ANY dependency reached a verdict, so an option resting on one
    computed figure and one BLOCKED check counted as examined and carried no
    warning. Half-checked is not checked: the unresolved half is exactly where
    the answer might fail, and a single PASS beside it produces the appearance
    of scrutiny rather than the fact.

    A CHECK THAT DID NOT RUN IS NOT A RESULT. BLOCKED means a gate could not
    reach an answer -- an outage, a paywall, a rate limit -- and an option
    whose sole dependency was a blocked `sqrt(4) = 2` was once presented under
    "the answer that survived".

    An option that declared no commitment at all is likewise untested: nothing
    about it could be computed, so nothing about it was.
    """
    if verdicts is None:
        return [o for o in options if o.alive and not o.predicates]
    return [o for o in options
            if o.alive and unexamined_reason(o, verdicts) is not None]


NO_COMMITMENT = "declared no figure this code could compute"
NOT_RULED = "declared a figure no check ever settled"
ONLY_ITS_OWN_ARITHMETIC = "checked only against its own arithmetic"

UNEXAMINED_REASONS: tuple[str, ...] = (
    NO_COMMITMENT, NOT_RULED, ONLY_ITS_OWN_ARITHMETIC)


def unexamined_reason(opt: Option,
                      verdicts: Mapping[str, object]) -> str | None:
    """WHY this surviving option counts as untested, or None if it does not.

    THREE DIFFERENT FACTS WERE BEING REPORTED AS ONE SENTENCE, and the report
    named only two of them:

        "They declared no commitment this code could compute, or none was
         ruled on, so they survived because nothing examined them."

    The third is the one `externally_tested` was written for, and the one the
    first full five-round run actually produced: eighteen of twenty-one
    commitments PASSED their self-check, every one of them a seat computing
    5 * 6 and committing to 30. Those options DID declare a figure and it WAS
    ruled on, so both halves of that sentence are false about them -- while
    the conclusion it draws is true. An operator reading it goes looking for a
    missing PREDICATE that is sitting right there, and never learns the actual
    fact: nobody outside the proposing seat ever touched the number.

    A true conclusion supported by a false reason is worse than no caveat,
    because it is checkable and it does not check out.
    """
    if not opt.predicates:
        return NO_COMMITMENT
    settled = all(
        getattr(verdicts.get(getattr(pred, "id", "")), "status", None)
        in ("pass", "fail")
        for pred in opt.predicates
    )
    if not settled:
        return NOT_RULED
    if not externally_tested(opt, verdicts):
        return ONLY_ITS_OWN_ARITHMETIC
    return None


def externally_tested(opt: Option,
                      verdicts: Mapping[str, object]) -> bool:
    """Did anything OUTSIDE this option ever touch one of its commitments?

    THE FAIL-OPEN THIS CLOSES, AND IT WAS THE WHOLE OUTPUT OF A PAID RUN.

    A self-check asks whether the option's own formula, on the option's own
    inputs, produces the option's own figure. A competent model always passes
    that, because it is a check on the seat's ARITHMETIC and not on its claim
    about the world. Measured on the first full five-round run: twenty-one
    commitments, eighteen PASS, and every one of the eighteen was of this
    shape --

        gives 30, committed equals 30      gives 12, committed equals 12
        gives  6, committed equals  6      gives 24, committed equals 24

    -- a seat computing 5 * 6 and committing to 30. Twelve options survived
    and the packet listed their commitments under rulings, which reads as
    twelve answers that were checked and held. Nothing about any of them had
    been tested. One of the panel's own escalated claims said so outright:
    "Every surviving option's cost commitment depends on the input
    per_round = 6, which no seat evidenced and no check in this run
    established."

    That is precisely the confusion `unexamined` exists to prevent, one level
    down: surviving because nothing examined you looks identical to surviving
    scrutiny, and a PASS on your own multiplication looks identical to a PASS
    somebody tried to break.

    WHAT COUNTS AS EXTERNAL. Only evidence from outside the option:

      * a DISPUTE -- another seat put different numbers into this formula.
        The commitment survived someone attacking its inputs.
      * an ALTERNATE -- another seat reached the same figure by its own route.
        Two independent derivations agreeing is corroboration.

    Nothing here reads text, and nothing depends on which seat said what: both
    facts are recorded by the machinery when a challenge is ruled or a merge
    absorbs a second advocate.

    A PASS still means the arithmetic held, and it is still reported. What it
    stops meaning is that the answer was examined.
    """
    for pred in opt.predicates:
        if getattr(pred, "alternates", ()):
            return True
        if getattr(verdicts.get(getattr(pred, "id", "")), "disputes", ()):
            return True
    return False


_MERGE = re.compile(r"^\s*MERGE\s*\|(.+)$", re.IGNORECASE)
_OPT_ID = re.compile(r"opt_[0-9a-f]{6,}", re.IGNORECASE)


def _absorb(pool: list[Option], other: Option, seat: str) -> None:
    """Fold a second proposal of the same answer into the one already held.

    A commitment both seats made, by the same route, is one commitment. A
    commitment only the second seat made is added. The same figure reached a
    different way becomes an ALTERNATE route to it, and the figure then stands
    if any declared route holds -- because one advocate's arithmetic being
    wrong refutes that advocate, not the answer they were arguing for.
    """
    keeper = next(o for o in pool if o.id == other.id)
    if seat not in keeper.proposers:
        keeper.proposers.append(seat)
    by_id = {pr.id: pr for pr in keeper.predicates}
    for pred in other.predicates:
        held = by_id.get(pred.id)
        if held is None:
            keeper.predicates.append(pred)
            by_id[pred.id] = pred
            continue
        route = (pred.formula, pred.inputs)
        if not (pred.formula or "").strip():
            continue
        existing = {(held.formula, held.inputs), *held.alternates}
        if route in existing:
            continue
        merged = replace(held, alternates=(*held.alternates, route))
        keeper.predicates[keeper.predicates.index(held)] = merged
        by_id[merged.id] = merged


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
    silent: list[str] = []
    for seat, text in sorted(thinker_texts.items()):
        try:
            mine = _parse_list(text)
        except TooManyOptions:
            # ONE SEAT'S FLOOD IS NOT THE PANEL'S FAILURE. This propagated,
            # and the round replaced the ENTIRE pool with an empty list -- so
            # a single seat emitting thirty-one lines discarded the answers
            # the other four proposed, and later rounds only remove, so they
            # were gone for good.
            silent.append(seat)
            continue
        if not mine:
            # A seat that answered and declared nothing. Recorded by name:
            # later rounds only eliminate, so an answer missing now is
            # missing permanently, and the one thing worse than losing it is
            # not knowing it was lost.
            silent.append(seat)
        for opt in mine:
            if opt.id in seen:
                # SAME ANSWER, ANOTHER ADVOCATE. The later seat used to be
                # dropped whole, taking its reasoning with it -- so whichever
                # seat sorted first decided how the answer was justified, and
                # renaming the seats changed whether it survived. Its
                # commitments are merged in instead.
                _absorb(pool, opt, seat)
                continue
            seen.add(opt.id)
            opt.proposers = [seat]
            pool.append(opt)
    # THE CEILING IS ON THE POOL, NOT ON ONE REPLY. It was applied per seat,
    # so five seats at the limit produced a hundred and fifty options -- a set
    # no later round could work through, arrived at without any single reply
    # tripping the guard.
    if len(pool) > MAX_OPTIONS:
        raise TooManyOptions(
            f"the panel proposed {len(pool)} distinct options, over the "
            f"{MAX_OPTIONS} a later round can work through. Truncating would "
            f"drop answers by the order they happened to be written in, so "
            f"the round is recorded as producing no usable option set "
            f"instead.")
    _SILENT_SEATS[:] = silent
    return pool


_SILENT_SEATS: list[str] = []
"""Seats whose reply yielded no usable option, from the last pool built.

Read by the caller straight after parse_proposals. Kept beside the parser
rather than returned in a tuple so the many existing callers keep working;
the fact matters because an answer nobody proposed in round one can never be
chosen, and silence here is permanent.
"""


def silent_seats() -> list[str]:
    """Which seats contributed no option to the last pool built."""
    return list(_SILENT_SEATS)


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
    # EVERY OPTION STAYS. The grouping is recorded on the members; nothing is
    # dropped, because a model deciding two answers are the same is a model
    # deciding what the candidates are.
    for oid, keeper_id in absorbed.items():
        by_id[oid].merged_into = _resolve(keeper_id, absorbed)
    return list(pool)


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
