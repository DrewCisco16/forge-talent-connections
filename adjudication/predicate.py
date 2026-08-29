"""Typed, candidate-owned commitments -- the only thing that removes an option.

WHY THIS EXISTS.

Elimination used to rest on prose. A seat wrote a sentence, attached an
arithmetic warrant, and code decided by reading the sentence whether the
warrant established it. Every version of that rule was lexical, and every
lexical rule was defeated by a sentence the rule had not anticipated:

    warrant "2 + 2 = 4"  claim "The launch is 4 and safe to proceed"     PASS
    warrant "2 + 2 = 4"  claim "The launch is 4 and unsafe to proceed"   PASS

Both passed. The arithmetic establishes 4 and establishes nothing whatever
about launch safety, so a refuted variant of either sentence could remove an
option that had nothing to do with the sum. Two contradictory propositions
cannot both be supported by the same warrant; a rule that says they are is not
a strict rule with a gap, it is the wrong kind of rule.

The repair is to stop reading prose. A commitment is a QUANTITY, a RELATION, a
VALUE, the FORMULA that produces it, and the INPUTS to that formula. Ruling on
it is arithmetic, not reading. There is no text field in the comparison, so
there is nothing for "and safe to proceed" to ride in on. `subject` exists
only so a human can read the record, and nothing here ever parses it.

AND THE FIRST VERSION OF THIS WAS NOT ENOUGH. It let a later round supply the
whole expression:

    PREDICATE | annual launch accidents | = | 4 accidents
    CHALLENGE | <that id> | 2 + 3

"2 + 3" was evaluated, read as 5 accidents, and removed the option. Nothing
connects 2 + 3 to annual launch accidents -- the same defect as the prose
rule in different clothes, a later model choosing the reasoning that condemns
an answer it did not write. The formula had to move to the option too.

THREE PROPERTIES, ENFORCED STRUCTURALLY RATHER THAN BY WORDING:

1. CANDIDATE-OWNED. The figure, the formula and the inputs are all declared by
   the seat that proposed the option, in the same reply, bound by position to
   the OPTION line above them.

2. PRE-EXISTING. They are fixed the moment the options are created. A later
   round may CHALLENGE the INPUTS by id and nothing else -- it cannot supply a
   formula and cannot mint a commitment.

3. SELF-REFUTING, OR NOT REFUTED AT ALL. What removes an option is its own
   formula with its own inputs failing to produce its own figure. A challenge
   records that two seats disagree about a number; it never removes anything,
   because neither seat's figure has been independently established and
   preferring the later one lets any seat delete any answer.

WHAT THIS DELIBERATELY GIVES UP. Only quantitative commitments can eliminate.
An option resting on a judgment nobody can compute is never removed by this
machinery; it survives and is reported as unexamined. That is the intended
direction of failure. A false acceptance leaves a wrong answer among the
candidates and says so; a false removal deletes the right answer and makes
whatever remains look earned.
"""

from __future__ import annotations

import ast
import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from fractions import Fraction

from adjudication_orchestrator import (
    _bounded,
    _reject_unbounded,
    _safe_eval,
    _show,
    _split_unit,
)

# The relations a predicate may assert. Deliberately small: each maps to one
# exact comparison on Fractions, with no tolerance and no rounding, so the
# verdict is reproducible and does not depend on how a number was written.
RELATIONS: dict[str, str] = {
    "=": "equals",
    "==": "equals",
    "!=": "does not equal",
    "<": "is less than",
    "<=": "is at most",
    ">": "is greater than",
    ">=": "is at least",
}

_CANON = {"==": "=", "=": "=", "!=": "!=", "<": "<", "<=": "<=",
          ">": ">", ">=": ">="}

MAX_PREDICATES_PER_OPTION = 4
"""Ceiling on commitments one option may carry.

An option that rests on twenty separate numbers is not making a checkable
commitment, it is spreading the claim thin enough that no single refutation
bites. Four forces the seat to name what actually decides it.
"""

_PREDICATE_LINE = re.compile(
    r"^\s*PREDICATE\s*\|(?P<subject>[^|]*)\|(?P<rel>[^|]*)\|(?P<value>.*)$",
    re.IGNORECASE)

_CHALLENGE_LINE = re.compile(
    r"^\s*CHALLENGE\s*\|(?P<pid>[^|]*)\|(?P<expr>.*)$", re.IGNORECASE)

_FORMULA_LINE = re.compile(r"^\s*FORMULA\s*\|(?P<expr>.*)$", re.IGNORECASE)

_INPUT_LINE = re.compile(
    r"^\s*INPUT\s*\|\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<val>.*)$",
    re.IGNORECASE)

_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class PredicateError(ValueError):
    """A predicate line that cannot be read as a typed commitment."""


class TooManyCommitments(ValueError):
    """One option declared more figures than it may be held to."""


_FENCE = re.compile(r"^\s*(?:```|~~~)")

_INDENTED_EXAMPLE = re.compile(r"^(?: {4,}|\t)")
"""A line indented as a code block. The contract prints its own examples this
way, and a seat echoing the contract had them executed."""


@dataclass(frozen=True)
class Predicate:
    """One quantitative commitment an option makes.

    `subject` is for the record only. Nothing here parses it, and no verdict
    depends on it -- that is the whole point of the type.
    """

    option_id: str
    subject: str
    relation: str
    value: Fraction
    unit: str
    id: str = ""
    formula: str = ""
    """How the option says its quantity is computed, in named variables.

    THE FORMULA BELONGS TO THE OPTION, FIXED WHEN IT WAS PROPOSED. A challenge
    used to supply the whole expression, so a later seat could write anything:

        PREDICATE | annual launch accidents | = | 4 accidents
        CHALLENGE | <that id> | 2 + 3

    "2 + 3" was evaluated, read as 5 accidents, and removed the option.
    Nothing whatever connects 2 + 3 to annual launch accidents. That is the
    same defect as the prose rule wearing different clothes -- a later model
    choosing the reasoning that condemns an answer it did not write.

    With the formula fixed here, a challenger can dispute the NUMBERS GOING
    IN and nothing else.
    """
    inputs: tuple[tuple[str, Fraction], ...] = ()
    """The option's OWN values for the formula's variables."""
    alternates: tuple[tuple[str, tuple[tuple[str, Fraction], ...]], ...] = ()
    """Further (formula, inputs) pairs OTHER SEATS gave for this same figure.

    Two seats proposing the same answer are two advocates for it, and they may
    reach the figure differently. Identical wording used to collapse to
    whichever seat sorted first, and the other seat's reasoning vanished --
    so if the surviving seat's arithmetic was wrong the answer was removed,
    and renaming the seats changed whether it survived.

    One advocate's bad arithmetic does not refute the answer. It refutes that
    advocate. The commitment stands if ANY declared route to it holds.
    """

    def __post_init__(self) -> None:
        if self.relation not in _CANON:
            raise PredicateError(
                f"{self.relation!r} is not a relation this can rule on. "
                f"Use one of: {' '.join(sorted(set(_CANON)))}")
        object.__setattr__(self, "relation", _CANON[self.relation])
        object.__setattr__(self, "unit", (self.unit or "").strip().casefold())
        if not self.id:
            object.__setattr__(self, "id", predicate_id(
                self.option_id, self.subject, self.relation, self.value,
                self.unit))

    def render(self) -> str:
        """How it appears to a seat being invited to challenge it.

        THE FORMULA AND THE INPUT NAMES ARE PART OF IT, and leaving them out
        made challenging impossible. A challenge names an input:

            CHALLENGE | <id> | per_round = 9

        but this showed only the subject, the relation and the value, so a
        seat had no way to learn what any input was called. Measured live: the
        one seat that tried wrote `saved_calls_per_run` against a commitment
        whose input is `saving_per_run`. It named nothing, and was correctly
        ignored -- for a fault entirely in what it had been shown.

        The prompt told seats they were being given "the formula that computes
        it, and the numbers put in". They were not. This makes that true.
        """
        unit = f" {self.unit}" if self.unit else ""
        head = (f"[{self.id}] {self.subject.strip()} "
                f"{RELATIONS[self.relation]} {_show(self.value)}{unit}")
        routes = [(self.formula, self.inputs), *self.alternates]
        lines = [head]
        for formula, inputs in routes:
            if not (formula or "").strip():
                continue
            shown = ", ".join(f"{n} = {_show(v)}" for n, v in inputs)
            lines.append(f"       computed as {formula}"
                         + (f", with {shown}" if shown else ""))
        if len(lines) == 1:
            lines.append("       (no formula declared, so nothing here can be "
                         "recomputed or challenged)")
        return "\n".join(lines)


def predicate_id(option_id: str, subject: str, relation: str, value: Fraction,
                 unit: str) -> str:
    """A content id that INCLUDES THE OPTION IT BINDS TO.

    Claim ids were computed from kind, warrant and text alone, so the same
    sentence aimed at two different options received one id. A single refuted
    verdict then keyed both, and one false claim removed two unrelated
    candidates. Whatever a commitment is ABOUT is part of what it is.
    """
    # THE SUBJECT IS PART OF THE IDENTITY. Without it "fatalities = 0 people"
    # and "cost = 0 people" on the same option produced one id, so ruling on
    # either silently ruled on both -- and an option could be removed for the
    # arithmetic of a quantity nobody had checked.
    material = "\x00".join(
        (option_id, " ".join(subject.casefold().split()), relation,
         str(value), unit))
    return "pred_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]


def _quantity(text: str) -> tuple[Fraction, str]:
    """A written quantity as an exact value and its unit label.

    Accepts "30 api calls", "1,200 dollars", "6.5", "-3 degrees". Evaluated
    through the same bounded arithmetic path as a warrant so a value written
    as "2**64" cannot be used to make the parser do work.
    """
    raw = (text or "").replace(",", "").strip()
    # FORMS SEATS ACTUALLY WRITE. Every one of these produced no commitment at
    # all, which meant the option carrying it could never be checked and never
    # be removed -- a silent hole rather than a refusal.
    prefix_unit = ""
    for sym, name in (("$", "dollars"), ("\u00a3", "pounds"),
                      ("\u20ac", "euros")):
        if raw.startswith(sym):
            raw, prefix_unit = raw[len(sym):].strip(), name
            break
    if raw.endswith("%"):
        raw, prefix_unit = raw[:-1].strip(), prefix_unit or "percent"
    expr, unit = _split_unit(raw)
    expr = expr.strip()
    unit = unit or prefix_unit
    if not expr:
        raise PredicateError("no value given")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise PredicateError(f"{text.strip()!r} is not a number") from exc
    refusal = _reject_unbounded(tree)
    if refusal is not None:
        raise PredicateError(refusal)
    try:
        return _bounded(_safe_eval(tree.body, expr)), unit
    except PredicateError:
        raise
    except Exception as exc:
        raise PredicateError(
            f"{text.strip()!r} is not a value this can compare") from exc


def parse_predicates(option_id: str, block: str) -> list[Predicate]:
    """The PREDICATE lines in one option's own block of text.

    A line that cannot be read is DROPPED, not guessed at. A malformed
    commitment is not a commitment, and inventing what a seat probably meant
    is exactly the inference this module exists to remove.
    """
    out: list[Predicate] = []
    seen: set[str] = set()
    lines = (block or "").splitlines()
    fenced = False
    for i, line in enumerate(lines):
        if _FENCE.match(line):
            fenced = not fenced
            continue
        if fenced or _INDENTED_EXAMPLE.match(line):
            continue
        m = _PREDICATE_LINE.match(line)
        if m is None:
            continue
        # The FORMULA and INPUT lines belonging to this commitment are the
        # ones between it and the next PREDICATE line.
        formula = ""
        inputs: list[tuple[str, Fraction]] = []
        for follow in lines[i + 1:]:
            if _PREDICATE_LINE.match(follow):
                break
            fm = _FORMULA_LINE.match(follow)
            if fm is not None and not formula:
                formula = fm.group("expr").strip()
                continue
            im = _INPUT_LINE.match(follow)
            if im is not None:
                try:
                    inputs.append((im.group("name").strip(),
                                   _quantity(im.group("val"))[0]))
                except PredicateError:
                    continue
        rel = m.group("rel").strip()
        if rel not in _CANON:
            continue
        try:
            value, unit = _quantity(m.group("value"))
        except PredicateError:
            continue
        try:
            pred = Predicate(option_id=option_id,
                             subject=m.group("subject").strip(),
                             relation=rel, value=value, unit=unit,
                             formula=formula, inputs=tuple(inputs))
        except PredicateError:
            continue
        if pred.id in seen:
            continue
        seen.add(pred.id)
        out.append(pred)
    if len(out) > MAX_PREDICATES_PER_OPTION:
        # REFUSED, NOT TRUNCATED. The fifth and later commitments were dropped
        # in silence, so an option could be checked against four figures while
        # appearing to rest on six -- and which four depended on the order
        # they happened to be written in.
        raise TooManyCommitments(
            f"this option declared {len(out)} commitments, over the "
            f"{MAX_PREDICATES_PER_OPTION} it may carry. Keeping the first "
            f"{MAX_PREDICATES_PER_OPTION} would decide by writing order which "
            f"figures the answer is held to, so none is taken.")
    return out


@dataclass(frozen=True)
class Ruling:
    """What was found. `status` is pass, fail, blocked, or disputed."""

    predicate_id: str
    status: str
    detail: str
    disputes: tuple[str, ...] = ()
    """Objections raised against this commitment, whatever the verdict.

    A dispute does not change the verdict, so it used to vanish whenever the
    self-check settled the commitment -- and "another seat says one of these
    inputs is wrong" is exactly what a person reading the record needs, most
    of all when the arithmetic otherwise looks clean.
    """

    @property
    def refutes(self) -> bool:
        """Only a FAIL on the option's OWN formula and inputs refutes.

        BLOCKED is a check that could not run -- no formula, a variable with
        no value, arithmetic that would not evaluate. Removing an option for
        that would delete answers for being hard to check.

        DISPUTED is a later seat offering different inputs to the same
        formula. It is a real finding and it is not a refutation: neither set
        of inputs has been independently established, and preferring the later
        one would let any seat delete any answer by asserting a different
        figure. It needs a person, and it says so.
        """
        return self.status == "fail"


def _evaluate(formula: str, bindings: Mapping[str, Fraction]) -> Fraction:
    """The option's own formula, with a set of values for its variables.

    Raises PredicateError rather than returning a number it cannot stand
    behind. A formula naming a variable nobody supplied has not been computed,
    and substituting a default would be inventing the missing figure.
    """
    expr = (formula or "").strip()
    if not expr:
        raise PredicateError("no formula was declared")
    # SEATS WRITE THE FORMULA AS AN ASSIGNMENT, and four of five did on the
    # live panel: "total_calls = rounds * calls_per_round". Reading the whole
    # line as an expression made the quantity's own name an unbound variable,
    # so five of six otherwise sound commitments came back BLOCKED -- an
    # option that could not be checked, and therefore could never be removed
    # or verified, entirely because of where it put an equals sign.
    #
    # The left side is the name of the thing being computed, which `subject`
    # already carries. Only the right side is arithmetic.
    if expr.count("=") == 1 and not re.search(r"[<>!=]=|=[<>]", expr):
        left, _, right = expr.partition("=")
        if _NAME.fullmatch(left.strip()) and right.strip():
            expr = right.strip()
    names = set(_NAME.findall(expr))
    missing = sorted(names - set(bindings))
    if missing:
        raise PredicateError(
            f"no value was given for {', '.join(missing)}")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise PredicateError(f"{expr!r} is not an expression") from exc
    refusal = _reject_unbounded(tree)
    if refusal is not None:
        raise PredicateError(refusal)
    substituted = expr
    for name in sorted(names, key=len, reverse=True):
        substituted = re.sub(rf"\b{re.escape(name)}\b",
                             f"({bindings[name]})", substituted)
    try:
        tree = ast.parse(substituted, mode="eval")
        return _bounded(_safe_eval(tree.body, substituted))
    except PredicateError:
        raise
    except Exception as exc:
        raise PredicateError(f"could not evaluate {expr!r}: {exc}") from exc


def _holds(pred: Predicate, got: Fraction) -> bool:
    """Whether a computed value satisfies the relation the option declared."""
    return {
        "=": got == pred.value,
        "!=": got != pred.value,
        "<": got < pred.value,
        "<=": got <= pred.value,
        ">": got > pred.value,
        ">=": got >= pred.value,
    }[pred.relation]


def self_check(pred: Predicate) -> Ruling:
    """Rule the option's OWN formula against its OWN declared value.

    THIS IS THE ONLY THING THAT REMOVES AN OPTION NOW.

    A challenge used to supply the expression, so a later seat could remove
    any option by attaching arithmetic of its choosing -- "2 + 3" against a
    commitment about launch accidents. Nothing connected the two, and no rule
    about expressions could connect them, for the same reason no rule about
    sentences could: the relationship is a matter of meaning.

    What CAN be settled mechanically is whether an option's own numbers add up
    to its own stated figure. That needs nothing from anyone else. An option
    saying a five-round run costs 30 API calls, computed as rounds * per_round
    with rounds=5 and per_round=7, has refuted itself: 35 is not 30. It is
    the seat's own formula, the seat's own inputs, and the seat's own claim.

    An option with no formula cannot be self-checked and is never removed. It
    survives and is reported as untested, which is the honest description.
    """
    routes = [(pred.formula, pred.inputs), *pred.alternates]
    routes = [(f, i) for f, i in routes if (f or "").strip()]
    if not routes:
        return Ruling(pred.id, "blocked",
                      "no formula was declared, so there is nothing to "
                      "recompute; this commitment cannot be settled here")
    unit = f" {pred.unit}" if pred.unit else ""
    said = (f"{pred.subject.strip()} {RELATIONS[pred.relation]} "
            f"{_show(pred.value)}{unit}")
    failures: list[str] = []
    blocked: list[str] = []
    for formula, inputs in routes:
        shown = ", ".join(f"{n}={_show(v)}" for n, v in inputs)
        try:
            got = _evaluate(formula, dict(inputs))
        except PredicateError as exc:
            blocked.append(f"{formula}: {exc}")
            continue
        if _holds(pred, got):
            # ANY declared route holding settles it. Two seats proposing one
            # answer are two advocates for it, and one advocate's arithmetic
            # being wrong refutes the advocate, not the answer.
            return Ruling(pred.id, "pass",
                          f"the option's own formula {formula} with its own "
                          f"inputs ({shown}) gives {_show(got)}{unit}, and it "
                          f"committed that {said}")
        failures.append(f"the option's own formula {formula} with its own "
                        f"inputs ({shown}) gives {_show(got)}{unit}")
    if not failures:
        return Ruling(pred.id, "blocked",
                      f"no declared route to this figure could be evaluated: "
                      f"{'; '.join(blocked)}")
    unevaluated = (f" ({len(blocked)} further route(s) could not be "
                   f"evaluated)" if blocked else "")
    return Ruling(pred.id, "fail",
                  f"{'; '.join(failures)}, but it committed that "
                  f"{said}{unevaluated}")


CORROBORATION_THRESHOLD = 2
"""How many seats must independently give the SAME replacement for an input
before it outweighs the value the option declared.

WHY A SINGLE CHALLENGER CANNOT DO IT. Their figure has no more standing than
the proposer's: neither has been established, and preferring the later one
lets any seat delete any answer by asserting a different number.

WHY TWO CAN. The seats write blind, in the same round, without seeing each
other. Two of them independently arriving at the same value for the same input
is corroboration, and it is the one thing a five-seat blinded panel produces
that a single model cannot. Against it stands one voice -- the proposer's --
unless other seats also backed that figure, which is counted.

This is not proof. The majority can be wrong and the proposer right. The
removal is recorded with the count and the values so a reader can see exactly
what outweighed what, and the answer is not deleted on one model's opinion.
"""


def corroborated_inputs(
    pred: Predicate,
    challenges: Sequence[tuple[str, Mapping[str, Fraction]]],
) -> dict[str, tuple[Fraction, int, int]]:
    """Inputs where independent seats agree on a different value.

    Returns {name: (agreed value, seats for it, seats for the option's)}, and
    only for inputs where the agreement clears the threshold AND outweighs the
    support the option's own figure has.
    """
    mine = dict(pred.inputs)
    votes: dict[str, dict[Fraction, int]] = {}
    for pid, bindings in challenges:
        if pid != pred.id:
            continue
        for name, value in bindings.items():
            if name not in mine:
                continue        # not an input of this formula; it names nothing
            votes.setdefault(name, {})[value] = \
                votes.setdefault(name, {}).get(value, 0) + 1
    out: dict[str, tuple[Fraction, int, int]] = {}
    for name, tally in votes.items():
        # The option's own figure is backed by whoever proposed it, plus any
        # seat that offered the same value rather than a different one.
        held = mine[name]
        for_held = 1 + tally.get(held, 0)
        best = max((v for v in tally if v != held),
                   key=lambda v: (tally[v], str(v)), default=None)
        if best is None:
            continue
        against = tally[best]
        if against >= CORROBORATION_THRESHOLD and against > for_held:
            out[name] = (best, against, for_held)
    return out


def dispute(pred: Predicate, bindings: Mapping[str, Fraction]) -> Ruling:
    """A later seat's alternative INPUTS to the option's own formula.

    RECORDED, NEVER A REMOVAL. A challenger's numbers have no more standing
    than the proposer's -- neither has been independently established, and
    preferring the later one would let any seat delete any answer by asserting
    a different figure with more confidence.

    So this produces a DISPUTE: two parties, one formula, different inputs,
    different results, and a human to settle which inputs are right. That is a
    real finding and it goes in the record. It is not a refutation.
    """
    # THE OPTION'S OWN INPUTS, WITH THE DISPUTED ONES REPLACED. A challenger
    # objecting to one figure should not have to restate the rest, and
    # requiring it would mean every dispute silently re-specified the whole
    # computation -- which is the door this closed in the first place.
    merged = dict(pred.inputs)
    merged.update(bindings)
    try:
        got = _evaluate(pred.formula, merged)
    except PredicateError as exc:
        return Ruling(pred.id, "blocked", str(exc))
    unit = f" {pred.unit}" if pred.unit else ""
    shown = ", ".join(f"{n}={_show(v)}" for n, v in sorted(bindings.items()))
    verb = "still holds" if _holds(pred, got) else "would not hold"
    return Ruling(
        pred.id, "disputed",
        f"another seat puts {shown} into the same formula {pred.formula}, "
        f"giving {_show(got)}{unit}, on which this commitment {verb}. "
        f"NOBODY HAS ESTABLISHED WHICH INPUTS ARE RIGHT, so this removes "
        f"nothing and needs a person.")

def parse_challenges(text: str) -> list[tuple[str, dict[str, Fraction]]]:
    """CHALLENGE lines as (predicate id, alternative inputs).

    A challenge names a commitment that ALREADY EXISTS and supplies values for
    the variables in ITS formula. It cannot supply the formula, and it cannot
    create a commitment -- both of which let a later seat write the reasoning
    that condemns an answer it did not propose.

        CHALLENGE | pred_abc123 | incidents = 3, per_year = 2

    A binding that cannot be read is dropped. A challenge left with no
    readable binding names no dispute and is discarded.
    """
    # FENCES ARE NOT SKIPPED HERE, AND THAT IS DELIBERATE.
    #
    # They are skipped for OPTION and PREDICATE, where a fenced example would
    # invent a candidate or a commitment out of the contract's own sample
    # text. A challenge cannot do that: it must name a commitment that
    # already exists, and an echoed example names the literal placeholder
    # "<paste a commitment id from the list above>", which adjudicate()
    # discards along with every other unknown id.
    #
    # So the fence rule bought nothing here and cost real work. Measured live:
    # a seat wrote a correct challenge, put it in a fenced block the way a
    # model formats anything code-shaped, and it was dropped in silence. Two
    # of three challenges that round survived; the third was as valid as the
    # others and simply better formatted.
    out: list[tuple[str, dict[str, Fraction]]] = []
    for line in (text or "").splitlines():
        m = _CHALLENGE_LINE.match(line)
        if m is None:
            continue
        pid = m.group("pid").strip()
        if not pid:
            continue
        bindings: dict[str, Fraction] = {}
        for part in m.group("expr").split(","):
            name, sep, raw = part.partition("=")
            if not sep or not _NAME.fullmatch(name.strip()):
                continue
            try:
                bindings[name.strip()] = _quantity(raw)[0]
            except PredicateError:
                continue
        if bindings:
            out.append((pid, bindings))
    return out


def adjudicate(predicates: Sequence[Predicate],
               challenges: Sequence[tuple[str, Mapping[str, Fraction]]],
               ) -> dict[str, Ruling]:
    """Every commitment ruled on, keyed by predicate id.

    SELF-CHECK FIRST, AND IT IS WHAT DECIDES. Each commitment is recomputed
    from the option's own formula and the option's own inputs. That needs
    nothing from any other seat and cannot be steered by one.

    A challenge is then recorded against it as a DISPUTE. Disputes never
    overwrite a self-check verdict -- they are a second opinion about the
    inputs, and a second opinion is not a refutation. A dispute is kept only
    where the self-check could not settle the commitment at all, so the record
    still shows that somebody objected.

    A challenge naming an id that does not exist is discarded: it names no
    commitment, so it can dispute nothing.
    """
    by_id = {p.id: p for p in predicates}
    out: dict[str, Ruling] = {p.id: self_check(p) for p in predicates}
    for pid, bindings in challenges:
        pred = by_id.get(pid)
        if pred is None:
            continue
        found = dispute(pred, bindings)
        prior = out.get(pid)
        if prior is None or prior.status == "blocked":
            out[pid] = replace(found,
                               disputes=(*(prior.disputes if prior else ()),
                                         found.detail))
        else:
            # The self-check settled it. The objection still goes on the
            # record: an operator needs to see that somebody disputed the
            # inputs even when the option's own arithmetic came out clean.
            out[pid] = replace(prior,
                               disputes=(*prior.disputes, found.detail))

    # CORROBORATED INPUTS, WHICH IS THE ONE THING A PANEL ADDS.
    #
    # Without this the later rounds cannot remove anything at all: an option
    # is checked against its own arithmetic when it is proposed, and after
    # that nothing can reach it. Four of the five rounds were commentary.
    #
    # A single challenger still decides nothing. Two seats writing blind, in
    # the same round, arriving independently at the same value for the same
    # input is corroboration -- and outweighing the proposer is exactly the
    # judgement five separated observers exist to make.
    for pred in predicates:
        agreed = corroborated_inputs(pred, challenges)
        if not agreed:
            continue
        merged = dict(pred.inputs)
        merged.update({n: v for n, (v, _a, _f) in agreed.items()})
        try:
            got = _evaluate(pred.formula, merged)
        except PredicateError as exc:
            out[pred.id] = replace(
                out[pred.id],
                disputes=(*out[pred.id].disputes,
                          f"seats corroborated different inputs but the "
                          f"formula could not then be evaluated: {exc}"))
            continue
        shown = "; ".join(
            f"{n}={_show(v)} (agreed by {a} seats, against {f} for "
            f"{_show(dict(pred.inputs)[n])})"
            for n, (v, a, f) in sorted(agreed.items()))
        unit = f" {pred.unit}" if pred.unit else ""
        said = (f"{pred.subject.strip()} {RELATIONS[pred.relation]} "
                f"{_show(pred.value)}{unit}")
        if _holds(pred, got):
            out[pred.id] = replace(
                out[pred.id],
                disputes=(*out[pred.id].disputes,
                          f"seats corroborated {shown}, and the commitment "
                          f"still holds at {_show(got)}{unit}"))
            continue
        out[pred.id] = Ruling(
            pred.id, "fail",
            f"{shown}. The option's own formula {pred.formula} on those "
            f"figures gives {_show(got)}{unit}, but it committed that "
            f"{said}. NOBODY PROVED THE SEATS RIGHT -- they agreed, blind, "
            f"and outnumbered the figure this option was resting on.",
            disputes=out[pred.id].disputes)
    return out


def refuted_commitment(item: object,
                       rulings: Mapping[str, Ruling]) -> Ruling | None:
    """THE ONE RULE THAT REMOVES A CANDIDATE. Every engine calls this.

    It answers a single question: do this candidate's own numbers, put into
    this candidate's own formula, fail to produce the figure it committed to?

    There were two elimination paths and they did not agree. The five-round
    engine required a claim to declare its target and pass a rule that read
    the claim's sentence; the legacy engine removed a candidate for ANY failed
    claim it carried, with no binding test at all. Two rules meant two answers
    to the same question, and the weaker one decided whenever it ran.

    Returns the refuting ruling, or None. BLOCKED, DISPUTED and unruled all
    return None -- a check that could not run, an objection nobody has
    settled, and a commitment nobody examined are not refutations.
    """
    for pred in getattr(item, "predicates", ()) or ():
        pid = getattr(pred, "id", None)
        if not isinstance(pid, str):
            continue
        ruling = rulings.get(pid)
        if ruling is not None and ruling.refutes:
            return ruling
    return None
