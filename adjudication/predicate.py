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

The repair is to stop reading prose. A predicate is a QUANTITY, a RELATION and
a VALUE. A gate evaluates an expression and compares the result. There is no
text field in that comparison, so there is nothing for "and safe to proceed"
to ride in on. `subject` exists only so a human can read the record, and
nothing in this module ever parses it.

THREE PROPERTIES, ENFORCED STRUCTURALLY RATHER THAN BY WORDING:

1. CANDIDATE-OWNED. A predicate is declared by the seat that proposed the
   option, in the same reply, bound by position to the OPTION line above it.
   An option can only ever be removed by a commitment it made itself.

2. PRE-EXISTING. Predicates are fixed when the options are created. A later
   round can CHALLENGE one by id, supplying its own arithmetic, but it cannot
   mint a new dependency. A seat that could invent an edge in round four could
   remove any option it liked by attaching a false sum to it.

3. LOAD-BEARING. Refuting the commitment refutes the option, because the seat
   said so when it proposed it -- not because code inferred a connection from
   overlapping words.

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
from dataclasses import dataclass
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


class PredicateError(ValueError):
    """A predicate line that cannot be read as a typed commitment."""


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

    def __post_init__(self) -> None:
        if self.relation not in _CANON:
            raise PredicateError(
                f"{self.relation!r} is not a relation this can rule on. "
                f"Use one of: {' '.join(sorted(set(_CANON)))}")
        object.__setattr__(self, "relation", _CANON[self.relation])
        object.__setattr__(self, "unit", (self.unit or "").strip().casefold())
        if not self.id:
            object.__setattr__(self, "id", predicate_id(
                self.option_id, self.relation, self.value, self.unit))

    def render(self) -> str:
        """How it appears to a seat being invited to challenge it."""
        unit = f" {self.unit}" if self.unit else ""
        return (f"[{self.id}] {self.subject.strip()} "
                f"{RELATIONS[self.relation]} {_show(self.value)}{unit}")


def predicate_id(option_id: str, relation: str, value: Fraction,
                 unit: str) -> str:
    """A content id that INCLUDES THE OPTION IT BINDS TO.

    Claim ids were computed from kind, warrant and text alone, so the same
    sentence aimed at two different options received one id. A single refuted
    verdict then keyed both, and one false claim removed two unrelated
    candidates. Whatever a commitment is ABOUT is part of what it is.
    """
    material = f"{option_id}{relation}{value}{unit}"
    return "pred_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]


def _quantity(text: str) -> tuple[Fraction, str]:
    """A written quantity as an exact value and its unit label.

    Accepts "30 api calls", "1,200 dollars", "6.5", "-3 degrees". Evaluated
    through the same bounded arithmetic path as a warrant so a value written
    as "2**64" cannot be used to make the parser do work.
    """
    expr, unit = _split_unit((text or "").replace(",", "").strip())
    expr = expr.strip()
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
    for line in (block or "").splitlines():
        m = _PREDICATE_LINE.match(line)
        if m is None:
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
                             relation=rel, value=value, unit=unit)
        except PredicateError:
            continue
        if pred.id in seen:
            continue
        seen.add(pred.id)
        out.append(pred)
        if len(out) >= MAX_PREDICATES_PER_OPTION:
            break
    return out


@dataclass(frozen=True)
class Ruling:
    """What a gate found. `status` is one of pass, fail, blocked."""

    predicate_id: str
    status: str
    detail: str

    @property
    def refutes(self) -> bool:
        """Only an outright FAIL refutes.

        BLOCKED is a check that could not run. It is not a refutation, and
        treating it as one would remove options for being hard to check.
        """
        return self.status == "fail"


def rule(pred: Predicate, expression: str) -> Ruling:
    """Rule on a predicate by evaluating an expression and comparing.

    The verdict is a function of the expression's value, the predicate's
    relation, its value and its unit. No text is read, so no sentence can
    smuggle a second proposition past the comparison.
    """
    expr, unit = _split_unit((expression or "").replace(",", "").strip())
    expr = expr.strip()
    if not expr:
        return Ruling(pred.id, "blocked", "no expression was supplied")
    if "=" in expr or "<" in expr or ">" in expr:
        return Ruling(
            pred.id, "blocked",
            "a challenge supplies an EXPRESSION, not an equation: the "
            "predicate already states the relation and the value, and a "
            "challenge that restated them could assert its own conclusion")
    if pred.unit and unit and pred.unit != unit:
        return Ruling(
            pred.id, "blocked",
            f"UNIT MISMATCH: the commitment is in {pred.unit!r} and this "
            f"arithmetic is in {unit!r}. Adding metres to seconds is not a "
            f"refutation, and guessing which was meant is worse than saying "
            f"so")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return Ruling(pred.id, "blocked",
                      f"{expression.strip()!r} is not an expression this "
                      f"can evaluate")
    refusal = _reject_unbounded(tree)
    if refusal is not None:
        return Ruling(pred.id, "blocked", refusal)
    try:
        got = _bounded(_safe_eval(tree.body, expr))
    except Exception as exc:  # noqa: BLE001 - reported, never raised onward
        return Ruling(pred.id, "blocked",
                      f"could not evaluate {expression.strip()!r}: {exc}")
    ok = {
        "=": got == pred.value,
        "!=": got != pred.value,
        "<": got < pred.value,
        "<=": got <= pred.value,
        ">": got > pred.value,
        ">=": got >= pred.value,
    }[pred.relation]
    unit_txt = f" {pred.unit}" if pred.unit else ""
    said = (f"{pred.subject.strip()} {RELATIONS[pred.relation]} "
            f"{_show(pred.value)}{unit_txt}")
    if ok:
        return Ruling(pred.id, "pass",
                      f"{expr} = {_show(got)}{unit_txt}, and the option "
                      f"committed that {said}")
    return Ruling(pred.id, "fail",
                  f"{expr} = {_show(got)}{unit_txt}, but the option committed "
                  f"that {said}")


def parse_challenges(text: str) -> list[tuple[str, str]]:
    """CHALLENGE lines as (predicate id, expression) pairs.

    A challenge names a commitment that ALREADY EXISTS. It cannot create one,
    which is what stops a late round from attaching a fresh false sum to an
    option it wants gone.
    """
    out: list[tuple[str, str]] = []
    for line in (text or "").splitlines():
        m = _CHALLENGE_LINE.match(line)
        if m is None:
            continue
        pid = m.group("pid").strip()
        expr = m.group("expr").strip()
        if pid and expr:
            out.append((pid, expr))
    return out


def refuted_commitment(item: object,
                       rulings: Mapping[str, Ruling]) -> Ruling | None:
    """THE ONE RULE THAT REMOVES A CANDIDATE. Every engine calls this.

    It answers a single question: did something this candidate committed to,
    when it was proposed, come out other than it said?

    There were two elimination paths and they did not agree. The five-round
    engine required a claim to declare its target and pass a rule that read
    the claim's sentence; the legacy engine removed a candidate for ANY failed
    claim it carried, with no binding test at all -- so a false sum about
    anything at all removed it. Two rules meant two answers to the same
    question, and the weaker one decided whenever it ran.

    Returns the refuting ruling, or None. BLOCKED and unruled return None:
    a check that could not run is not a refutation, and removing an option
    for being hard to check deletes answers for a property of the checker.
    """
    for pred in getattr(item, "predicates", ()) or ():
        pid = getattr(pred, "id", None)
        if not isinstance(pid, str):
            continue
        ruling = rulings.get(pid)
        if ruling is not None and ruling.refutes:
            return ruling
    return None


def adjudicate(predicates: Sequence[Predicate],
               challenges: Sequence[tuple[str, str]]) -> dict[str, Ruling]:
    """Every challenge ruled on, keyed by predicate id.

    A challenge naming an id that does not exist is DISCARDED. It names no
    commitment, so it can refute nothing, and a run that treated an unknown id
    as meaningful would let a seat remove an option by guessing at ids.

    When several challenges name the same predicate, a FAIL stands: one
    correct refutation is a refutation whether or not other seats also got
    the arithmetic right. Ties between blocked and pass keep the pass.
    """
    by_id = {p.id: p for p in predicates}
    out: dict[str, Ruling] = {}
    for pid, expr in challenges:
        pred = by_id.get(pid)
        if pred is None:
            continue
        found = rule(pred, expr)
        prior = out.get(pid)
        if prior is None or (prior.status != "fail" and found.status == "fail") or (prior.status == "blocked" and found.status == "pass"):
            out[pid] = found
    return out
