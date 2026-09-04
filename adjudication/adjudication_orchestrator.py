"""
adjudication_orchestrator.py
============================
Automated sequential adjudication with a preserved verification bottleneck.

DESIGN PRINCIPLE
----------------
Kim et al. (2026, Nature Machine Intelligence 8, 1157-1172) measured trace-level
error amplification by coordination topology under matched compute:

    single agent    1.0x
    CENTRALIZED     4.4x   <- orchestrator verifies before aggregation
    hybrid          5.1x
    decentralized   7.8x
    INDEPENDENT    17.2x   <- parallel seats, no verification bottleneck

Independent MAS showed NO error correction (+4.6% amplification). The verifying
bottleneck is the entire difference. This orchestrator therefore automates
SEQUENCING and MECHANICAL VERIFICATION, but never replaces the verification
bottleneck with another prompted LLM.

Claims are routed:
    tier 1  deterministic gate  -> auto-accept / auto-reject   (rho ~ 0 vs LLMs)
    tier 2  no applicable gate  -> ESCALATE to human queue
Nothing is accepted on an LLM's say-so alone.

PLUGGABILITY
------------
No vendor SDK is imported. Supply your own callables:
    seat_fn(prompt: str) -> str
    resolver_fn(identifier: str) -> bool      (e.g. DOI resolution)
    test_runner_fn(cmd: str) -> bool
"""

from __future__ import annotations

import ast
import hashlib
import itertools
import json
import math
import operator
import os
import re
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import Enum
from fractions import Fraction
from typing import Any, Protocol

# ===========================================================================
# 0. PREFLIGHT — the 45% capability-saturation gate
# ===========================================================================

CAPABILITY_SATURATION_THRESHOLD = 0.45
"""
Kim et al. (2026): single-agent baselines above ~0.45 predict zero-to-negative
multi-agent gains. Validated selection rule; matched the sign of the multi-agent
gain in 94% of 16 SWE-bench Verified / Terminal-Bench configurations.

NOTE ON SCOPE: this threshold was fitted on six agentic benchmarks. Leave-one-
dataset-out R^2 was -2.09, i.e. absolute cross-domain prediction failed. Treat
0.45 as a starting prior for YOUR domain and re-estimate it from your own
single-seat baseline once you have 30+ scored tasks.
"""

MAX_RECOMMENDED_SEATS = 3
"""
Turn count scales super-linearly with seat count:
    T = 2.72 * (n + 0.5)^1.724,  R^2 = 0.974,  95% CI exponent [1.685, 1.763]
Kim et al. report per-agent reasoning capacity becomes 'prohibitively thin'
beyond three to four agents under a fixed budget. Five seats is past the knee.
"""


@dataclass
class PreflightVerdict:
    run_ensemble: bool
    reason: str
    single_agent_baseline: float
    recommended_seats: int


def preflight(
    single_agent_baseline: float,
    task_is_decomposable: bool,
    requested_seats: int = 5,
) -> PreflightVerdict:
    """
    Decide whether the ensemble should run at all, BEFORE spending tokens.

    single_agent_baseline : measured accuracy of ONE strong seat on this task
                            class. You must measure this. Do not estimate it.
    task_is_decomposable  : can the task be split into independently verifiable
                            streams? Kim et al. found decomposability, not
                            difficulty, determines coordination viability
                            (Finance Agent +80.8% decomposable vs
                             PlanCraft -70.0% strictly sequential).
    """
    seats = min(requested_seats, MAX_RECOMMENDED_SEATS)

    if not task_is_decomposable:
        return PreflightVerdict(
            False,
            "Task is sequentially interdependent. Coordination overhead exceeds "
            "task complexity; expect degradation. Use a single seat.",
            single_agent_baseline,
            1,
        )

    if single_agent_baseline > CAPABILITY_SATURATION_THRESHOLD:
        return PreflightVerdict(
            False,
            f"Single-seat baseline {single_agent_baseline:.2f} exceeds the "
            f"{CAPABILITY_SATURATION_THRESHOLD} saturation threshold. Little room "
            "for coordination gain; expect zero-to-negative. Run one seat plus "
            "deterministic gates.",
            single_agent_baseline,
            1,
        )

    return PreflightVerdict(
        True,
        f"Baseline {single_agent_baseline:.2f} is below saturation and the task "
        f"decomposes. Ensemble justified at {seats} seats.",
        single_agent_baseline,
        seats,
    )


# ===========================================================================
# 1. CLAIMS AND CANDIDATES
# ===========================================================================

class ClaimKind(str, Enum):
    ARITHMETIC = "arithmetic"
    CITATION = "citation"
    CODE_BEHAVIOR = "code_behavior"
    SCHEMA = "schema"
    UNIT = "unit"
    QUOTE_VERIFICATION = "quote_verification"
    """"string Q appears at URL U" -- fully checkable, no model judgment.

    Exists because a quote can support its answer perfectly and still not be
    in the source. That failure is invisible to every check that reads the
    quote against the answer, and it is the one that reverses a correct
    conclusion while looking better-sourced than the truth.
    """
    JUDGMENT = "judgment"          # no mechanical warrant -> always escalates


@dataclass
class Claim:
    id: str
    text: str
    kind: ClaimKind
    warrant: str | None = None   # expression, DOI, test command, schema...
    source_pass: str | None = None
    source_seat: str | None = None
    about_option: str | None = None
    """The id of the option this claim is about, as the seat declared it.

    A STRUCTURAL EDGE, DECLARED, NOT INFERRED. Options were matched to claims
    by testing whether the claim's text appeared inside the option's text. A
    paraphrase therefore attached to nothing and its option survived
    untested, while a NEGATION -- "Do not liquidate inventory" contains
    "liquidate inventory" -- attached and removed the option that said the
    opposite of the refuted claim.

    Text similarity cannot carry this relationship. The seat is shown the
    option ids and names one.
    """
    supports: list[str] = field(default_factory=list)
    """Claim ids this claim is offered as evidence FOR.

    Used by the quote cascade: when a quote_verification claim FAILS, the
    claims it was offered in support of lose their stated evidentiary basis
    and are downgraded. A claim whose supporting quote is fabricated is worse
    off than one with no quote at all, because the quote actively
    misrepresented the state of the evidence.
    """

    def __post_init__(self) -> None:
        """An id-less claim gets its content id, rather than keeping "".

        THE FAILURE THIS REMOVES. Every consumer treats the id as identity:
        run_pass skips a claim whose id it has already adjudicated. Two claims
        both carrying "" are therefore the SAME claim to that check, so the
        first is gated and every later one is silently dropped -- not
        escalated, not blocked, not recorded as anything. A candidate standing
        on a dropped claim can never be eliminated, because the assertion that
        would have killed it was never ruled on.

        Both production entry points -- parse_candidates and
        line_claim_extractor -- already assign a content id, so this was not
        reachable through them. It was reachable from anywhere else, silently,
        and "silently" is the part that matters: the run completes, the report
        renders, and the missing verdicts leave no trace.

        Computing the id here makes the invariant true by construction instead
        of by convention. An explicitly supplied id is left alone, because
        callers that mint their own ids depend on them.
        """
        if not self.id:
            self.id = content_claim_id(self.kind, self.warrant, self.text)


@dataclass
class Candidate:
    id: str
    content: str
    claims: list[Claim] = field(default_factory=list)
    eliminated: bool = False
    elimination_reason: str | None = None
    elimination_kind: str | None = None
    """"earned" or "structural", set where the elimination happens.

    Was inferred by substring-matching the reason prose, which broke the
    moment a new elimination path worded itself differently: the quote cascade
    read as STRUCTURAL and a run whose candidate died to a fabricated quote
    was headed CONSENSUS ONLY. A quote proven absent from its source is the
    most earned kill available, and the report said the opposite. Provenance
    is recorded at the site now, not guessed from wording afterwards.
    """
    confidence: float | None = None


# ===========================================================================
# 2. DETERMINISTIC GATES — the automated verification bottleneck
# ===========================================================================

class GateStatus(str, Enum):
    # B105 below is a false positive: "pass" is a gate verdict, not a
    # credential. Bandit flags it only because the member is named PASS.
    # Keep the reason OFF the nosec line -- bandit parses everything after
    # "nosec" as test ids and warns about each prose word.
    PASS = "pass"  # nosec B105
    FAIL = "fail"
    INAPPLICABLE = "inapplicable"
    BLOCKED = "blocked"
    """The check could not be performed. NOT a finding, and never a kill.

    A firewall, a rate limit, a timeout, and a paywall are all reasons a gate
    learned nothing. Recording any of them as FAIL would let a network outage
    eliminate a true candidate and would enter a fabrication finding against a
    seat that fabricated nothing. BLOCKED claims are counted separately, never
    contribute to earned kills, and never reach the conduct ledger.
    """


@dataclass
class GateResult:
    gate: str
    status: GateStatus
    detail: str = ""


class Gate(Protocol):
    name: str
    def applies_to(self, claim: Claim) -> bool: ...
    def check(self, claim: Claim) -> GateResult: ...


# Binary and unary operators are SEPARATE tables, not one merged dict.
# Merged, `type(node.op) in _SAFE_OPS` on a BinOp also matched ast.USub and
# ast.UAdd, so the lookup would hand operator.neg two arguments. CPython's
# parser never builds that node, so it was unreachable rather than wrong --
# but the arity was enforced by the grammar rather than by this table, and
# the only thing catching a mismatch was the broad except in the caller.
# Split, each table's domain is its arity, and mypy can type both.
_BINARY_OPS: dict[type[ast.operator], Callable[[Fraction, Fraction], Fraction]] = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_UNARY_OPS: dict[type[ast.unaryop], Callable[[Fraction], Fraction]] = {
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


MAX_RESULT_DIGITS = 5000


def _bounded(value: Fraction) -> Fraction:
    """Refuse an intermediate result too large to keep working with.

    THE EXPONENT CAP BOUNDS EACH LITERAL, NOT THE RUNNING RESULT. A chain of
    individually permitted powers stays under it while the value it builds
    does not: exact rationals have no overflow to stop them, so the process
    adjudicating the operator's question is the one that runs out of memory.

    Raised as ValueError so the gate reports BLOCKED. An expression this code
    declined to finish evaluating has established nothing about the claim.
    """
    for part in (value.numerator, value.denominator):
        if part and len(str(abs(part))) > MAX_RESULT_DIGITS:
            raise ValueError(
                f"an intermediate result exceeded {MAX_RESULT_DIGITS} digits; "
                f"the expression was not evaluated to completion")
    return value


def _literal_text(node: ast.AST, source: str | None) -> str:
    """The characters the operator actually typed for this literal."""
    if not source:
        return ""
    try:
        seg = ast.get_source_segment(source, node)
    except Exception:  # noqa: BLE001 - a missing segment is not a finding
        return ""
    return (seg or "").strip()


def _safe_eval(node: ast.AST, source: str | None = None) -> Fraction:
    """
    Evaluate an arithmetic AST without exec/eval on arbitrary code.

    bool is EXCLUDED even though it is a subclass of int. Without that, the
    literal True satisfies isinstance(value, (int, float)), so the warrant
    "True = 1" evaluated to True, compared equal to 1.0, and the gate returned
    PASS with the detail "True confirmed". That is a vacuous warrant: a seat
    could attach it to any arithmetic claim and be auto-accepted, which is the
    arithmetic-gate equivalent of the permissive resolver SOP 8.3 warns about.
    Found by a fuzz property on CI's random seed, not by any example.
    """
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body, source)
    if (isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)):
        # EXACT, FROM THE TEXT THE OPERATOR WROTE.
        #
        # A float literal loses information the moment Python parses it:
        # 9999999999999999.0 and 10000000000000000 become the same double, so
        # a gate comparing them found them equal and reported PASS on two
        # plainly different numbers. Reading the literal back out of the
        # source and carrying it as a Fraction keeps every digit, so the
        # comparison is between what was written and what was computed.
        if isinstance(node.value, int):
            return Fraction(node.value)
        literal = _literal_text(node, source)
        try:
            return Fraction(Decimal(literal)) if literal else Fraction(node.value)
        except (InvalidOperation, ValueError):
            return Fraction(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
        left, right = _safe_eval(node.left, source), _safe_eval(node.right, source)
        if isinstance(node.op, ast.Pow) and right.denominator != 1:
            # A fractional exponent leaves the rationals. Refuse rather than
            # fall back to float and lose the exactness this gate depends on.
            raise ValueError("fractional exponents are not supported here")
        return _bounded(_BINARY_OPS[type(node.op)](left, right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _bounded(_UNARY_OPS[type(node.op)](
            _safe_eval(node.operand, source)))
    raise ValueError("unsupported expression")


_NUMBER = re.compile(r"-?\d[\d,]*\.?\d*")
_WORDISH = re.compile(r"[a-z0-9]+")


def _numbers(text: str) -> set[str]:
    """Numeric literals, normalised so 1,200 and 1200 and 1200.0 all match.

    NORMALISED THROUGH Decimal, NOT float. Going through float collapsed
    distinct integers above 2**53: a claim reading "the total is
    9007199254740992" matched a warrant computing 9007199254740993, because
    both became the same double. A verifier that cannot tell two integers
    apart is not verifying arithmetic.
    """
    out: set[str] = set()
    for raw in _NUMBER.findall(text or ""):
        cleaned = raw.replace(",", "").rstrip(".")
        try:
            v = Decimal(cleaned)
        except (InvalidOperation, ValueError):
            continue
        out.add(str(int(v)) if v == v.to_integral_value() else str(v))
    return out


def _tokens(text: str) -> set[str]:
    return set(_WORDISH.findall((text or "").casefold()))


_NEGATION = frozenset(["not", "no", "never", "none", "nor", "cannot", "cant", "won't", "wont", "doesn't", "doesnt", "isn't", "isnt", "aren't", "arent", "wasn't", "wasnt", "shouldn't", "shouldnt", "without", "fails", "failed", "unable", "false", "untrue", "incorrect", "wrong", "denies", "denied", "refutes", "refuted", "contradicts"])

_QUALIFIERS = frozenset(["under", "over", "about", "approximately", "roughly", "nearly", "almost", "around", "circa", "least", "most", "below", "above", "beyond", "within", "some", "many", "few", "several", "perhaps", "maybe", "possibly", "likely", "unlikely", "estimated", "projected", "expected", "assumed", "upwards", "downwards"])
"""Words that change what a number ASSERTS.

"the total is 4" restates a warrant computing 4. "the total is UNDER 4" and
"the total is ABOUT 4" are different propositions and the arithmetic settles
neither -- but all three mention the number, so a number-matching test
accepted all three. These were previously in the free vocabulary below, which
is what made them invisible.
"""

_UNIT_WORDS = frozenset(["dollar", "dollars", "usd", "cent", "cents", "euro", "euros", "pound", "pounds", "gbp", "eur", "metre", "metres", "meter", "meters", "km", "kilometre", "kilometres", "cm", "mm", "mile", "miles", "foot", "feet", "inch", "inches", "yard", "yards", "second", "seconds", "ms", "minute", "minutes", "hour", "hours", "day", "days", "week", "weeks", "month", "months", "year", "years", "kg", "kilogram", "kilograms", "gram", "grams", "tonne", "tonnes", "lb", "lbs", "ounce", "ounces", "percent", "pct", "byte", "bytes", "kb", "mb", "gb", "tb"])
"""Units carry a dimension the bare arithmetic does not.

"5 km = 5000 m" is a true conversion and establishes nothing about 5000
DOLLARS. A number without its dimension is not the same claim, and "dollars"
was previously free vocabulary, so "the price is 5000 dollars" was accepted on
a distance conversion.
"""

_QUANTITY_VOCABULARY = frozenset(["total", "totals", "totalling", "sum", "sums", "adds", "add", "equals", "equal", "is", "are", "was", "were", "comes", "come", "to", "of", "at", "each", "per", "unit", "units", "item", "items", "count", "counts", "value", "values", "amount", "amounts", "figure", "figures", "result", "results", "number", "numbers", "times", "multiplied", "divided", "plus", "minus", "exactly", "and", "the", "a", "an", "it", "that", "this", "in", "for", "from", "with", "by", "cost", "costs", "price", "prices", "distance", "length", "duration", "weight", "size", "quantity"])
"""Words a restatement of a quantity may contain without asserting anything
beyond it.

QUALIFIERS AND UNIT NAMES ARE DELIBERATELY ABSENT. They used to be here, and
that is precisely how "under 4", "about 4" and "5000 dollars" passed as
restatements of arithmetic that established none of them."""


def _content_words(text: str) -> list[str]:
    return [w for w in _WORDISH.findall((text or "").casefold()) if len(w) > 1]


_PER_PHRASE = re.compile(r"\bper\s+\w+", re.IGNORECASE)

_LINKING = re.compile(
    r"\b(?:is|are|was|were|totals|totalling|comes to|come to|amounts to|"
    r"equals|costs?|adds up to|works out to|will be|would be|uses?|requires?|"
    r"takes?|needs?|avoids?|saves?|spends?|consumes?|yields?|produces?|"
    r"means?|gives?|leaves?|returns?)\b",
    re.IGNORECASE)
"""Verbs that introduce what a quantity claim ASSERTS.

The list was six verbs long and real model output does not oblige. A live
canary produced "At six API calls per round, a five-round run USES 30 API
calls" -- a textbook restatement of arithmetic that had just passed -- and no
verb matched, so the whole sentence counted as the assertion and it was
rejected for mentioning five, round and run.

Bare "total" is still deliberately absent: it matched "in total" at the end of
an ordinary cost sentence and left the assertion empty."""
"""Verbs that introduce what a quantity claim ASSERTS.

Bare "total" is deliberately absent. It matched "in total" at the end of an
ordinary cost sentence, so the assertion after the last linking verb was the
empty string and every genuine claim was rejected."""


def _leading_token(assertion: str) -> str:
    """The first content token of an assertion, normalised if numeric.

    Articles and prepositions are skipped: "the 30 API calls" and "30 API
    calls" assert the same thing.
    """
    skip = {"a", "an", "the", "of", "at", "in", "to", "for", "about", "only",
            "just", "some", "around", "roughly"}
    text = (assertion or "").strip()

    # Drop leading articles and prepositions, then look for a number FIRST.
    # Tokenising by word split "1,200" into "1" and "200", so a perfectly
    # ordinary formatted figure looked like an assertion about 1.
    while True:
        m = re.match(r"\s*([A-Za-z]+)\b", text)
        if not m or m.group(1).casefold() not in skip:
            break
        text = text[m.end():]

    number = _NUMBER.match(text.strip())
    if number:
        nums = _numbers(number.group(0))
        if nums:
            return next(iter(nums))

    # Raw tokens, not _content_words: that drops single characters, so an
    # assertion of exactly "4" had no leading token at all and the plainest
    # possible restatement -- "the total is 4" -- was rejected.
    for word in _WORDISH.findall(text.casefold()):
        if word in skip:
            continue
        nums = _numbers(word)
        return next(iter(nums)) if nums else word
    return ""


def _quantity_claim_unsupported(claim: Claim, warrant: str,
                                text: str) -> str | None:
    """Whether a verified quantity establishes what this claim asserts.

    THE RULE IS POSITIONAL: the checked value must be what the sentence
    ASSERTS, not merely a token it contains.

    Everything before the linking verb NAMES the quantity and may say
    anything -- "the vendor licence", "two engineers for two quarters",
    "renting for six months". Everything after it is the assertion, and must
    be the computed value plus quantity words.

    An earlier rule required the whole sentence to contain nothing outside a
    fixed vocabulary. It was safe and useless: a five-round dry run with three
    genuine cost claims eliminated NOTHING, because "the vendor licence is
    47000 per year in total" mentions a vendor and a licence. A tool that
    cannot rule on an ordinary cost claim produces a reading list rather than
    an answer, which is the other way to be worthless.

    It still catches the case it was built for. "The launch is SAFE to
    proceed, code 4" carries 4, but what it ASSERTS after the verb is being
    safe -- and arithmetic settles nothing about that.
    """
    # THE MOST LITERAL RESTATEMENT: the claim IS the warrant. A seat writing
    # "CLAIM | arithmetic | 2 + 2 = 4 | 2 + 2 = 4" has asserted exactly what
    # was checked and nothing else, and every positional rule below is about
    # sentences, which this is not.
    squeeze = " ".join((text or "").split()).casefold()
    if squeeze and squeeze == " ".join(warrant.split()).casefold():
        return None

    _, _, rhs = warrant.rpartition("=")
    results = _numbers(rhs)
    claimed = _numbers(text)
    if results and not (results & claimed):
        return (
            f"WARRANT DOES NOT BEAR ON THE CLAIM: the check verified "
            f"{warrant.strip()!r}, and the claim text does not mention "
            f"{' or '.join(sorted(results))}."
        )

    verbs = list(_LINKING.finditer(text))
    assertion = text[verbs[-1].end():] if verbs else text

    # "per year", "per seat", "per request" name what the quantity is PER.
    # That is the same labelling job the words before the verb do, and it is
    # stripped for the same reason: rejecting it made every ordinary rate --
    # "the licence is 47000 dollars per year" -- unusable, while the number
    # asserted is exactly the one that was computed.
    assertion_core = _PER_PHRASE.sub(" ", assertion)
    asserted = _content_words(assertion_core)

    hedges = sorted(set(asserted) & _QUALIFIERS)
    if hedges:
        return (
            f"THE CLAIM QUALIFIES THE NUMBER: "
            f"{', '.join(repr(h) for h in hedges)}. The check confirmed a "
            f"value; it established nothing about being under, over, or near "
            f"it."
        )

    if results and not (results & _numbers(assertion)):
        return (
            f"THE NUMBER IS NOT WHAT THE CLAIM ASSERTS: it says "
            f"{assertion.strip()[:60]!r}, and mentions "
            f"{' or '.join(sorted(results))} elsewhere. A verified quantity "
            f"settles the quantity, not whatever else the sentence says."
        )

    # A unit the warrant does not measure means a different quantity. "5 km =
    # 5000 m" is a true conversion and establishes nothing about 5000 dollars.
    warrant_units = set(_content_words(warrant)) & _UNIT_WORDS
    foreign = sorted((set(asserted) & _UNIT_WORDS) - warrant_units)
    if foreign:
        return (
            f"THE CLAIM IS ABOUT A DIFFERENT QUANTITY: it asserts "
            f"{', '.join(repr(u) for u in foreign)}, which the warrant "
            f"{warrant.strip()!r} does not measure. A number without its "
            f"dimension is not the same claim."
        )

    # THE VALUE MUST LEAD THE ASSERTION.
    #
    # Requiring the assertion to contain ONLY quantity words rejected every
    # real claim: "30 API calls per item at six calls per round" mentions
    # items and rounds, and is exactly a restatement of the arithmetic. What
    # actually separates it from "SAFE to proceed, code 4" is WHERE the number
    # sits. In a restatement the value is what the predicate is about, so it
    # comes first; in the other the predicate is about being safe and the
    # number trails as an aside.
    lead = _leading_token(assertion_core)
    if results and lead not in results:
        return (
            f"THE NUMBER IS NOT WHAT THE CLAIM ASSERTS: after the verb it "
            f"says {assertion.strip()[:60]!r}, which is about "
            f"{lead or 'something else'} rather than "
            f"{' or '.join(sorted(results))}. A verified quantity settles the "
            f"quantity, not whatever else the sentence says."
        )
    return None


def warrant_supports(claim: Claim) -> str | None:
    """None if the warrant ESTABLISHES this proposition; else why it does not.

    A GATE CHECKS A WARRANT. IT DOES NOT CHECK THE PROPOSITION.

    An earlier version of this function used shared words and shared numbers
    as a test of relevance. That was wrong in the way that matters: token
    overlap is not entailment. Both of these were accepted on the warrant
    "2 + 2 = 4", because both contain the token 4:

        "The launch is SAFE to proceed, code 4"
        "The launch is NOT SAFE to proceed, code 4"

    An equation establishes neither. The check confirmed that 2 + 2 is 4 and
    said nothing whatever about a launch.

    So lexical similarity no longer ACCEPTS anything. A verified warrant
    accepts a claim only when the claim is a RESTATEMENT of that warrant --
    when the checked object and the accepted proposition are the same object.
    Everything else escalates to a person: not eliminated, because it may well
    be true, and not accepted, because nothing here established it.

    That is deliberately strict and it will escalate more. The alternative is
    a system that stamps [PASS] on prose nothing examined, which is the one
    failure that makes every other safeguard pointless.
    """
    text = claim.text or ""
    warrant = claim.warrant or ""

    # A negation or contrast marker anywhere means the proposition is not a
    # plain restatement, and no token comparison can tell which way it points.
    negations = sorted(set(_content_words(text)) & _NEGATION)
    if negations:
        return (
            f"NOT A RESTATEMENT OF THE WARRANT: the claim contains "
            f"{', '.join(repr(n) for n in negations)}, so what it asserts is "
            f"not what the check confirmed. A verified warrant cannot settle "
            f"a proposition that qualifies or reverses it."
        )

    if claim.kind in (ClaimKind.ARITHMETIC, ClaimKind.UNIT):
        return _quantity_claim_unsupported(claim, warrant, text)

    if claim.kind is ClaimKind.CITATION:
        return (
            "SOURCE VERIFIED, PROPOSITION NOT ESTABLISHED: the citation "
            "resolves and matches the work named, which rules out a fabricated "
            "reference. It does not establish that the work SUPPORTS this "
            "claim -- misrepresenting a real paper is invisible to every "
            "mechanical check and needs a person who has read it."
        )

    if claim.kind is ClaimKind.SCHEMA:
        return (
            "SHAPE VALID, PROPOSITION NOT ESTABLISHED: the document parsed "
            "and matched its schema. Schema validity is a fact about "
            "structure and carries no information about any assertion made "
            "alongside it."
        )

    if claim.kind is ClaimKind.QUOTE_VERIFICATION:
        # The quote is present at the URL. Whether the source SAYS what the
        # claim says is a reading, and a shared-word test cannot make it: a
        # page reading "revenue tripled" shares every content word with
        # "revenue did not triple". The negation check above catches the
        # reversal; the rest is a person's judgement.
        return (
            "QUOTE FOUND, PROPOSITION NOT ESTABLISHED: the quoted text is "
            "present at the cited URL, which rules out a fabricated quote. "
            "Whether it supports this claim is a reading, and no string "
            "comparison settles it."
        )

    if claim.kind is ClaimKind.CODE_BEHAVIOR:
        ct = {w for w in _content_words(warrant) if len(w) > 2}
        tt = {w for w in _content_words(text) if len(w) > 2}
        if ct and tt and not (ct & tt):
            return (
                f"COMMAND DOES NOT BEAR ON THE CLAIM: {warrant.strip()!r} "
                f"exited zero, which establishes that it exited zero. The "
                f"claim text is about something else."
            )
        return None

    return None


MAX_AST_NODES = 200
MAX_EXPONENT = 64
MAX_INT_DIGITS = 100


def _reject_unbounded(tree: ast.AST) -> str | None:
    """Refuse an expression that could take unbounded time or memory.

    `2 ** 1000000000` is a legal expression made of supported operators. The
    evaluator would simply try to build the integer, and the process this runs
    in is the one adjudicating the operator's question. A reviewer declined to
    execute that reproduction because it could exhaust the machine, which is
    the finding.

    BLOCKED rather than FAIL: an expression we refused to evaluate has not
    been shown false.
    """
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_AST_NODES:
        return (f"expression has {len(nodes)} nodes, over the "
                f"{MAX_AST_NODES} allowed; it was not evaluated")
    for node in nodes:
        if (isinstance(node, ast.Constant) and isinstance(node.value, int)
                and not isinstance(node.value, bool)
                and len(str(abs(node.value))) > MAX_INT_DIGITS):
            return (f"a literal has more than {MAX_INT_DIGITS} digits; "
                    f"it was not evaluated")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            right = node.right
            if not (isinstance(right, ast.Constant)
                    and isinstance(right.value, (int, float))
                    and abs(right.value) <= MAX_EXPONENT):
                return (f"exponent must be a literal no greater than "
                        f"{MAX_EXPONENT}; the expression was not evaluated")
    return None


def _exact(value: object) -> Fraction:
    """A value as an exact rational, or raise.

    Decimal via str() so "0.1" is one tenth rather than the binary double
    nearest to it -- a verifier that reads the operator's decimal as something
    else is checking a different number from the one written down.
    """
    if isinstance(value, bool):
        raise ValueError("a boolean is not a number here")
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, Fraction):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("not finite")
        if value != int(value):
            raise ValueError("not an exact integer")
        return Fraction(int(value))
    if isinstance(value, str):
        return Fraction(Decimal(value.strip()))
    raise ValueError(f"cannot make {type(value).__name__} exact")


def _agrees_to_written_precision(actual: Fraction, claimed: str) -> bool:
    """True when the computed value rounds to exactly what was written.

    The comparison uses the precision the OPERATOR chose, not a tolerance this
    code picked. Someone who writes four decimal places has asserted four
    decimal places; someone who writes sixteen has asserted sixteen.
    """
    text = claimed.strip()
    if "." not in text or "e" in text.lower():
        return False
    places = len(text.split(".", 1)[1])
    if places > 30:
        return False
    try:
        quantum = Decimal(1).scaleb(-places)
        rounded = Decimal(actual.numerator) / Decimal(actual.denominator)
        return rounded.quantize(quantum, rounding=ROUND_HALF_UP) == Decimal(text)
    except (InvalidOperation, ValueError, ZeroDivisionError):
        return False


_UNIT_AFTER_NUMBER = re.compile(r"(?<=[\d)])\s*([A-Za-z][A-Za-z ]*)")


def _split_unit(side: str) -> tuple[str, str]:
    """An arithmetic side split into its expression and its unit label.

    "30 API calls - 6 API calls" -> ("30  - 6 ", "api calls")

    A unit is an alphabetic run FOLLOWING a number, wherever it appears --
    seats write "30 API calls - 6 API calls", not just a trailing label. Runs
    that do not follow a number are left alone, so `sqrt(4)` is still an
    unsupported call rather than a quantity in sqrts.

    A side using two different units returns no label, which leaves the
    expression unparseable and the claim BLOCKED: this code does not know how
    to add metres to seconds, and guessing is worse than saying so.
    """
    text = (side or "").strip()
    found = [" ".join(m.group(1).split()).casefold()
             for m in _UNIT_AFTER_NUMBER.finditer(text)]
    if not found:
        return text, ""
    if len(set(found)) > 1:
        return text, ""
    return _UNIT_AFTER_NUMBER.sub(" ", text).strip(), found[0]


def _show(value: object) -> str:
    """Print a number without inventing precision it does not have.

    Arithmetic is carried as an exact Fraction, and str(Fraction) reads as
    "1/2" -- correct, and not what an operator checking a cost figure wants to
    see. A value with a terminating decimal is shown as that decimal; anything
    else keeps the fraction, because rendering 1/3 as a rounded decimal would
    print precision the value does not have.
    """
    if isinstance(value, Fraction):
        if value.denominator == 1:
            return str(value.numerator)
        try:
            dec = Decimal(value.numerator) / Decimal(value.denominator)
            if Fraction(dec) == value:
                return format(dec.normalize(), "f")
        except (InvalidOperation, ValueError, ZeroDivisionError):
            pass
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


class ArithmeticGate:
    """
    Recomputes a stated numeric result. warrant format: "<expression> = <claimed>"
    Kim et al. found centralized verification cut numerical drift ~24%; this
    gate removes it entirely for anything expressible as an expression.
    """
    name = "arithmetic"

    def applies_to(self, claim: Claim) -> bool:
        return claim.kind is ClaimKind.ARITHMETIC and bool(claim.warrant)

    def check(self, claim: Claim) -> GateResult:
        warrant = claim.warrant
        if not warrant:
            return GateResult(self.name, GateStatus.FAIL,
                              "no warrant supplied")
        if "=" not in warrant:
            return GateResult(self.name, GateStatus.INAPPLICABLE,
                              "warrant is not '<expression> = <value>'")
        expr, claimed = warrant.rsplit("=", 1)

        # A UNIT LABEL ON BOTH SIDES IS PART OF THE CLAIM, NOT A PARSE ERROR.
        #
        # The contract tells seats to put units in the warrant so the currency
        # or the thing counted is checked rather than assumed. A live canary
        # then produced "5 * 6 API calls = 30 API calls" and the evaluator
        # BLOCKED all of them: it cannot parse "API calls", so following the
        # instruction made the claim uncheckable. Guidance and gate have to
        # agree.
        #
        # The label is stripped for evaluation and compared separately, so
        # "5 dollars * 6 = 30 euros" is still refused -- the arithmetic holds
        # and the units do not.
        expr, expr_unit = _split_unit(expr)
        claimed, claimed_unit = _split_unit(claimed)
        if expr_unit and claimed_unit and expr_unit != claimed_unit:
            return GateResult(
                self.name, GateStatus.FAIL,
                f"UNIT MISMATCH: the expression is in {expr_unit!r} and the "
                f"result is claimed in {claimed_unit!r}")

        try:
            tree = ast.parse(expr.strip(), mode="eval")
        except SyntaxError as exc:
            # NOT A FINDING. An expression this evaluator cannot parse has told
            # us nothing about whether the claim is true. Recording it as FAIL
            # made "we could not check this" indistinguishable from "we checked
            # and it is false" -- and eliminated the candidate on the strength
            # of it. `sqrt(4) = 2` is true; the evaluator simply has no sqrt.
            return GateResult(self.name, GateStatus.BLOCKED,
                              f"could not parse the expression: {exc.msg}")
        blocked = _reject_unbounded(tree)
        if blocked is not None:
            return GateResult(self.name, GateStatus.BLOCKED, blocked)

        try:
            actual = _safe_eval(tree, expr.strip())
        except (TypeError, OverflowError, ZeroDivisionError) as exc:
            # A COMPLEX, INFINITE, OR UNDEFINED RESULT IS NOT A REFUTATION.
            # (-1) ** 0.5 is complex and raised TypeError out of the gate;
            # 1e308 * 1e308 raised OverflowError. Both escaped as crashes
            # rather than verdicts, taking the run with them.
            return GateResult(self.name, GateStatus.BLOCKED,
                              f"the expression does not evaluate to a real "
                              f"finite number: {type(exc).__name__}: {exc}")
        except ValueError as exc:
            # The evaluator refuses names, calls and operators it does not
            # support. Same reasoning as above: unsupported is not false.
            return GateResult(self.name, GateStatus.BLOCKED,
                              f"this evaluator cannot compute it: {exc}")
        except Exception as exc:  # noqa: BLE001
            return GateResult(self.name, GateStatus.BLOCKED,
                              f"evaluation failed: {type(exc).__name__}: {exc}")

        try:
            expected = _exact(claimed.strip())
        except (ValueError, ArithmeticError):
            return GateResult(self.name, GateStatus.INAPPLICABLE,
                              f"{claimed.strip()!r} is not a number")

        # EXACT COMPARISON WHERE BOTH SIDES ARE EXACT.
        #
        # Both were coerced to float and compared with rel_tol=1e-9, which is a
        # RELATIVE tolerance: at a billion it permits a gap of one, so
        # "1000000000 = 1000000001" passed. Past 2**53 adjacent integers are
        # not even distinct as floats, so "9007199254740993 = 9007199254740992"
        # passed too. A verifier that cannot tell two different numbers apart
        # is not verifying arithmetic.
        try:
            exact_actual = _exact(actual)
        except (ValueError, ArithmeticError):
            exact_actual = None
        if exact_actual is not None:
            if exact_actual == expected:
                return GateResult(self.name, GateStatus.PASS,
                                  f"{_show(actual)} confirmed exactly")
            # A TRUNCATED DECIMAL IS IMPRECISE, NOT FALSE.
            #
            # "1/3 = 0.3333333333333333" is exactly wrong and honestly
            # written. Refuting it would be the dangerous direction -- a FAIL
            # removes an option -- so a value that agrees to every digit the
            # operator actually wrote is BLOCKED, with what to do about it.
            # Only a value that differs within the written precision is a
            # refutation.
            if _agrees_to_written_precision(exact_actual, claimed.strip()):
                return GateResult(
                    self.name, GateStatus.BLOCKED,
                    f"recomputed {_show(actual)} against a claimed "
                    f"{_show(claimed.strip())}: they agree to every digit "
                    f"written, and differ beyond it. State the value exactly, "
                    f"or have a person settle whether the rounding matters")
            return GateResult(
                self.name, GateStatus.FAIL,
                f"claimed {_show(claimed.strip())}, recomputed "
                f"{_show(actual)}")

        # A GENUINE FLOAT RESULT IS NOT CONFIRMED, IT IS APPROXIMATED.
        #
        # A tolerance was reported as a PASS, so "0.1 + 0.2 = 0.3000000000005"
        # and "9999999999999999.0 = 10000000000000000" both came back
        # confirmed. Those are different numbers; binary floating point simply
        # cannot separate them, which is a fact about the arithmetic and not
        # evidence about the claim.
        #
        # Close enough to be worth a person's attention is BLOCKED. Plainly
        # different is still a refutation.
        if not isinstance(actual, float) or not math.isfinite(actual):
            return GateResult(self.name, GateStatus.BLOCKED,
                              f"result {actual!r} is not a finite real number")
        if math.isclose(float(actual), float(expected),
                        rel_tol=1e-12, abs_tol=1e-12):
            return GateResult(
                self.name, GateStatus.BLOCKED,
                f"recomputed {actual!r} against a claimed {expected}: equal "
                f"within binary floating point, which cannot separate them. "
                f"State the value exactly, or have a person settle it")
        return GateResult(
            self.name, GateStatus.FAIL,
            f"claimed {expected}, recomputed {actual}")


class CitationResolutionGate:
    """
    Confirms a cited identifier actually resolves. Magesh et al. (2025, JELS
    22(2), 216-242) found retrieval-augmented legal tools hallucinated in
    17-33% of queries -- retrieval does NOT guarantee the warrant exists.

    resolver_fn must perform a real network resolution and return True only on
    a confirmed record. A resolver that returns True by default defeats the gate.
    """
    name = "citation_resolution"
    _DOI = re.compile(r"^10\.\d{4,9}/\S+$")

    def __init__(self, resolver_fn: Callable[[str], bool]):
        self.resolver_fn = resolver_fn

    def applies_to(self, claim: Claim) -> bool:
        return claim.kind is ClaimKind.CITATION and bool(claim.warrant)

    def check(self, claim: Claim) -> GateResult:
        warrant = claim.warrant
        if not warrant:
            return GateResult(self.name, GateStatus.FAIL,
                              "no warrant supplied")
        ident = warrant.strip()
        if not (self._DOI.match(ident) or ident.startswith("http")):
            return GateResult(self.name, GateStatus.FAIL, "malformed identifier")
        try:
            ok = self.resolver_fn(ident)
        except Exception as exc:  # noqa: BLE001 - see below
            # A resolver that could not reach its source has not shown the
            # identifier to be absent. Reporting FAIL here turned an offline
            # machine into a fabrication detector, blaming seats for citing
            # real papers. The resolver signals this by raising; anything it
            # raises is treated as "check did not happen".
            return GateResult(self.name, GateStatus.BLOCKED,
                              f"resolver could not check {ident}: {exc}")
        return GateResult(
            self.name,
            GateStatus.PASS if ok else GateStatus.FAIL,
            "resolved" if ok else "did not resolve",
        )


PERMISSIVE_RESOLVER_PROBE = "10.9999/probe-identifier-that-cannot-exist"
"""A syntactically valid DOI that resolves nowhere. See probe_resolver."""


def probe_resolver(resolver_fn: Callable[[str], bool]) -> GateResult:
    """
    SOP 8.3 names the single most common way this build fails: a resolver that
    returns True by default. Its checklist requires "Resolver returns False on
    failure -- verified with a fake identifier."

    This performs that check. A resolver that confirms a DOI which cannot exist
    is permissive, and a permissive resolver silently converts a verified system
    back into an unverified ensemble. A resolver that RAISES is acceptable: the
    gate already fails closed on exceptions.
    """
    try:
        answered = resolver_fn(PERMISSIVE_RESOLVER_PROBE)
    except Exception as exc:  # noqa: BLE001 - see below
        # A resolver that cannot reach its source has not demonstrated
        # anything about its strictness. Treating a raise as a pass meant an
        # OFFLINE resolver certified itself, and then failed every honest DOI
        # for the rest of the run. The probe now reports that it could not be
        # performed, which is a different fact from "the resolver is sound".
        return GateResult("resolver_probe", GateStatus.BLOCKED,
                          f"could not probe the resolver: {exc}. Its "
                          f"strictness is unknown, so citation verdicts from "
                          f"this run are not trustworthy.")
    if answered:
        return GateResult(
            "resolver_probe", GateStatus.FAIL,
            "PERMISSIVE RESOLVER: confirmed an identifier that cannot exist. "
            "The citation gate is inert; every citation will pass.",
        )
    return GateResult("resolver_probe", GateStatus.PASS,
                      "resolver correctly denied a non-existent identifier")


class TestExecutionGate:
    """Runs the test command that a code claim asserts will pass."""
    name = "test_execution"

    def __init__(self, test_runner_fn: Callable[[str], bool]):
        self.test_runner_fn = test_runner_fn

    def applies_to(self, claim: Claim) -> bool:
        return claim.kind is ClaimKind.CODE_BEHAVIOR and bool(claim.warrant)

    def check(self, claim: Claim) -> GateResult:
        warrant = claim.warrant
        if not warrant:
            return GateResult(self.name, GateStatus.FAIL,
                              "no warrant supplied")
        try:
            ok = self.test_runner_fn(warrant)
        except Exception as exc:  # noqa: BLE001 - fail-closed: any error denies
            return GateResult(self.name, GateStatus.FAIL, f"runner error: {exc}")
        return GateResult(
            self.name,
            GateStatus.PASS if ok else GateStatus.FAIL,
            "tests passed" if ok else "tests failed",
        )


class SchemaGate:
    """Validates that a structured payload parses and carries required keys."""
    name = "schema"

    def __init__(self, required_keys: Sequence[str] = ()):
        self.required_keys = list(required_keys)

    def applies_to(self, claim: Claim) -> bool:
        return claim.kind is ClaimKind.SCHEMA and bool(claim.warrant)

    def check(self, claim: Claim) -> GateResult:
        warrant = claim.warrant
        if not warrant:
            return GateResult(self.name, GateStatus.FAIL,
                              "no warrant supplied")
        try:
            payload = json.loads(warrant)
        except Exception as exc:  # noqa: BLE001
            # UNPARSEABLE IS NOT FALSE. The gate learned nothing about the
            # claim from a payload it could not read, and recording that as a
            # refutation is a finding it never made.
            return GateResult(self.name, GateStatus.BLOCKED,
                              f"the warrant is not valid JSON: {exc}")
        if self.required_keys and not isinstance(payload, dict):
            # `k not in payload` MEANS SOMETHING DIFFERENT FOR EVERY TYPE. On
            # a list it tests membership among the ELEMENTS, so ["id"] passed
            # a required key of "id"; on a string it tests substrings, so
            # "id" passed too; on a number or null it raises TypeError and
            # took the run with it. A key check only means anything on a
            # mapping.
            return GateResult(
                self.name, GateStatus.BLOCKED,
                f"required keys were configured but the payload is a "
                f"{type(payload).__name__}, not an object; there is nothing "
                f"to look a key up in")
        missing = [k for k in self.required_keys if k not in payload]
        if missing:
            return GateResult(self.name, GateStatus.FAIL, f"missing keys: {missing}")
        return GateResult(self.name, GateStatus.PASS, "schema valid")


_UNIT_TABLE: dict[str, tuple[str, float]] = {
    # unit -> (dimension, multiplier to that dimension's base)
    "nm": ("length", 1e-9), "um": ("length", 1e-6), "mm": ("length", 1e-3),
    "cm": ("length", 1e-2), "m": ("length", 1.0), "km": ("length", 1e3),
    "in": ("length", 0.0254), "ft": ("length", 0.3048),
    "yd": ("length", 0.9144), "mi": ("length", 1609.344),
    "mg": ("mass", 1e-6), "g": ("mass", 1e-3), "kg": ("mass", 1.0),
    "t": ("mass", 1e3), "oz": ("mass", 0.028349523125),
    "lb": ("mass", 0.45359237),
    "ms": ("time", 1e-3), "s": ("time", 1.0), "min": ("time", 60.0),
    "h": ("time", 3600.0), "hr": ("time", 3600.0), "day": ("time", 86400.0),
    "wk": ("time", 604800.0),
    "b": ("data", 1.0), "kb": ("data", 1e3), "mb": ("data", 1e6),
    "gb": ("data", 1e9), "tb": ("data", 1e12),
    "kib": ("data", 1024.0), "mib": ("data", 1024.0 ** 2),
    "gib": ("data", 1024.0 ** 3), "tib": ("data", 1024.0 ** 4),
}

_UNIT_WARRANT = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*([A-Za-z]+)\s*=\s*"
    r"(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*([A-Za-z]+)\s*$"
)


class UnitGate:
    """
    Confirms a stated unit conversion. warrant format: "<qty><unit> = <qty><unit>"
    for example "5 km = 5000 m", "1 lb = 0.45359237 kg".

    ClaimKind.UNIT existed with nothing to adjudicate it: seats emitted unit
    claims and every one escalated, because no gate anywhere applied. A claim
    kind the tool can never settle is a promise it cannot keep, so either the
    kind goes or the gate arrives. The gate arrives.

    NOT APPLICABLE RATHER THAN FAIL on an unrecognised unit or an
    unparseable warrant. Every other gate here treats a bad warrant as FAIL,
    but those gates own their whole domain: any arithmetic expression is
    either evaluable or wrong. This table is a fixed list of units, and a
    conversion in furlongs or fortnights is not false -- it is outside what
    this gate knows. Returning FAIL would eliminate a candidate on the
    strength of a gap in a lookup table, so an unknown unit routes to the
    human queue instead, which is what "no applicable gate" already means.
    Mixing dimensions -- metres against seconds -- IS a failure, and is
    reported as one.
    """
    name = "unit"

    def _parse(
        self, warrant: str | None
    ) -> tuple[float, tuple[str, float], float, tuple[str, float]] | None:
        if not warrant:
            return None
        m = _UNIT_WARRANT.match(warrant)
        if not m:
            return None
        lhs_q, lhs_u, rhs_q, rhs_u = m.groups()
        lu = _UNIT_TABLE.get(lhs_u.lower())
        ru = _UNIT_TABLE.get(rhs_u.lower())
        if lu is None or ru is None:
            return None
        return float(lhs_q), lu, float(rhs_q), ru

    def applies_to(self, claim: Claim) -> bool:
        return (claim.kind is ClaimKind.UNIT
                and self._parse(claim.warrant) is not None)

    def check(self, claim: Claim) -> GateResult:
        parsed = self._parse(claim.warrant)
        if parsed is None:  # unreachable via _route; guard, not cast
            return GateResult(self.name, GateStatus.INAPPLICABLE,
                              "unit or format not recognised")
        lhs_q, (lhs_dim, lhs_f), rhs_q, (rhs_dim, rhs_f) = parsed
        if lhs_dim != rhs_dim:
            return GateResult(
                self.name, GateStatus.FAIL,
                f"dimension mismatch: {lhs_dim} stated as {rhs_dim}",
            )
        left, right = lhs_q * lhs_f, rhs_q * rhs_f
        if math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-12):
            return GateResult(self.name, GateStatus.PASS,
                              f"{left} {lhs_dim} base units confirmed")
        return GateResult(
            self.name, GateStatus.FAIL,
            f"stated {rhs_q}, converts to {left / rhs_f}",
        )


# ---------------------------------------------------------------------------
# Evidence admissibility: what may count as a warrant at all
# ---------------------------------------------------------------------------

class SourceClass(str, Enum):
    PEER_REVIEWED = "peer_reviewed"        # scholarly article, published
    EMPIRICAL_DATA = "empirical_data"      # dataset with provenance
    TECHNICAL_MANUAL = "technical_manual"  # standard, specification, manual
    PRIMARY_SOURCE = "primary_source"      # source literature, filings, records
    PREPRINT = "preprint"                  # NOT peer reviewed
    INADMISSIBLE = "inadmissible"


ADMISSIBLE_CLASSES = frozenset({
    SourceClass.PEER_REVIEWED,
    SourceClass.EMPIRICAL_DATA,
    SourceClass.TECHNICAL_MANUAL,
    SourceClass.PRIMARY_SOURCE,
})
"""
The only evidence classes that may support a claim: scholarly articles,
empirical data, technical manuals, and primary source literature.

PREPRINT is deliberately excluded. A preprint has not cleared peer review, so
it is not a scholarly article in the sense this gate enforces; admitting one
requires an explicit opt-in at construction, recorded in the gate's detail.
"""

_DATA_REPOSITORIES = ("zenodo", "dryad", "figshare", "osf.io", "icpsr",
                      "datadryad", "pangaea", "dataverse")
_PREPRINT_HOSTS = ("arxiv", "biorxiv", "medrxiv", "ssrn", "chemrxiv", "psyarxiv")
_STANDARD_BODIES = ("ISO", "IEC", "IEEE", "RFC", "NIST", "ASTM", "ANSI",
                    "MIL-STD", "ETSI", "ITU", "BS", "DIN", "SAE")

_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
_PMID_RE = re.compile(r"^PMID:\s*\d+$", re.IGNORECASE)
_ISBN_RE = re.compile(r"^ISBN(?:-1[03])?:?\s*[\d\- ]{9,17}[\dXx]$", re.IGNORECASE)
_STD_RE = re.compile(r"^(" + "|".join(_STANDARD_BODIES) + r")[\s\-/:]", re.IGNORECASE)
_ACCESSION_RE = re.compile(r"^(GSE|SRR|PRJNA|E-MTAB|PDB)[-_]?\w+$", re.IGNORECASE)


def classify_source(identifier: str) -> SourceClass:
    """
    Classify an evidence identifier by structure alone. No network call.

    FAIL CLOSED: anything this function cannot positively place in an
    admissible class is INADMISSIBLE. There is no "probably fine" branch. A
    blog post, a vendor landing page, a wiki, a forum thread, a chat
    transcript, and an unsupported model assertion all land in the same
    bucket, which is the point -- none of them is source literature.
    """
    ident = (identifier or "").strip()
    if not ident:
        return SourceClass.INADMISSIBLE

    low = ident.lower()

    if any(h in low for h in _PREPRINT_HOSTS):
        return SourceClass.PREPRINT
    if _STD_RE.match(ident):
        return SourceClass.TECHNICAL_MANUAL
    if _ISBN_RE.match(ident):
        return SourceClass.TECHNICAL_MANUAL
    if _ACCESSION_RE.match(ident):
        return SourceClass.EMPIRICAL_DATA
    if _PMID_RE.match(ident):
        return SourceClass.PEER_REVIEWED
    if _DOI_RE.match(ident):
        # a DOI minted by a data repository is data, not an article
        if any(r in low for r in _DATA_REPOSITORIES):
            return SourceClass.EMPIRICAL_DATA
        return SourceClass.PEER_REVIEWED
    return SourceClass.INADMISSIBLE


class SourceAdmissibilityGate:
    """
    Enforces the evidence rule: only scholarly articles, empirical data,
    technical manuals, and primary source literature may support a claim.

    This gate decides ADMISSIBILITY, not existence. Pair it with
    CitationResolutionGate, which decides whether the thing actually resolves.
    Both apply to CITATION claims and Orchestrator._route requires every
    applicable gate to pass, so a citation must be both admissible in class
    and confirmed to exist.

    allow_preprints=True admits PREPRINT and records that it was admitted by
    explicit opt-in, so the concession is visible in the audit record rather
    than buried in a config file.
    """
    name = "source_admissibility"

    def __init__(self, allow_preprints: bool = False,
                 classifier: Callable[[str], SourceClass] = classify_source):
        self.allow_preprints = allow_preprints
        self.classifier = classifier

    def applies_to(self, claim: Claim) -> bool:
        return claim.kind is ClaimKind.CITATION and bool(claim.warrant)

    def check(self, claim: Claim) -> GateResult:
        warrant = claim.warrant
        if not warrant:
            return GateResult(self.name, GateStatus.FAIL,
                              "no warrant supplied")
        try:
            cls = self.classifier(warrant.strip())
        except Exception as exc:  # noqa: BLE001 - fail-closed: any error denies
            return GateResult(self.name, GateStatus.FAIL, f"classifier error: {exc}")

        if cls in ADMISSIBLE_CLASSES:
            return GateResult(self.name, GateStatus.PASS, f"admissible: {cls.value}")
        if cls is SourceClass.PREPRINT and self.allow_preprints:
            return GateResult(
                self.name, GateStatus.PASS,
                "preprint admitted by explicit opt-in; NOT peer reviewed",
            )
        if cls is SourceClass.PREPRINT:
            return GateResult(
                self.name, GateStatus.FAIL,
                "preprint is not peer-reviewed; set allow_preprints to admit it",
            )
        return GateResult(
            self.name, GateStatus.FAIL,
            "inadmissible source: not a scholarly article, empirical dataset, "
            "technical manual, or primary source",
        )


# ===========================================================================
# 3. PASSES
# ===========================================================================

@dataclass
class Pass:
    id: str
    name: str
    instruction: str
    eliminative: bool
    """
    eliminative=True  : the pass can RULE OUT a candidate (fault trees reason
                        deductively from effect to necessary cause).
    eliminative=False : the pass can only REWEIGHT. A Bayesian posterior never
                        reaches zero from a nonzero prior, so pass 5 is a
                        calibration/escalation stage, not an elimination stage.
    """


DEFAULT_PASSES = [
    Pass(
        "p1",
        "Inversion Analysis",
        "Assume the artifact is WRONG. Enumerate every way it could be wrong and "
        "what would have to be true for each. Do not defend it.",
        True,
    ),
    Pass(
        "p2",
        "FMEA + FTA + FMEDA",
        "Build the failure-mode table; then the fault tree reasoning from effect "
        "back to necessary cause; then the diagnostic-coverage table. State which "
        "failure modes are mechanically detectable and which are not.",
        True,
    ),
    Pass(
        "p3",
        "IDOV",
        "Identify, Design, Optimise, Validate. Check the artifact against its "
        "stated design requirements and name every requirement it fails to meet.",
        True,
    ),
    Pass(
        "p4",
        "Critical Systems Thinking + TRIZ + Quality Zero Defects",
        "Name the boundary judgements the artifact makes: what it includes, "
        "what it excludes, and whose perspective its framing privileges. State "
        "the contradictions that surfaces, and resolve them by TRIZ separation "
        "rather than by compromise. Then run the zero-defects checklist against "
        "what survives.",
        True,
    ),
    Pass(
        "p5",
        "Bayesian + MCMC",
        "Assign calibrated posterior confidence to each surviving candidate. "
        "Sample the posterior and report the interval, never a point estimate.",
        False,
    ),
]
"""
The fixed five-pass framework. Order is part of the design.

Each pass applies a DIFFERENT lens to the SAME artifact. Passes do not consume
one another's output -- see BLINDING_CONTRACT below -- so the sequence is a
sequence of independent lenses, not a relay.

Pass 5 is the only non-eliminative stage. A Bayesian posterior never reaches
zero from a nonzero prior, so MCMC sampling calibrates the survivors; it cannot
rule a candidate out.
"""


# ===========================================================================
# 3b. BLINDED SEAT LAYER
# ===========================================================================

BLINDING_CONTRACT = """
A seat is shown EXACTLY three things: the artifact under review, the lens for
the pass it is running, and the output format. It is never shown:

  - any other seat's response, on this round or any earlier one
  - the pass number, or which passes have already run
  - anything at all, in round 1, beyond the artifact and the lens

WHAT A SEAT IS SHOWN FROM ROUND 2 ONWARD. The comprised answer of the earlier
rounds: what the gates verified, what they refuted, what is still open, and
which candidates remain. That is the iterative loop -- round k+1 refines round
k instead of re-reading the same text through a new lens. It is composed by
the orchestrator from ADJUDICATED material only, it never names a seat, and it
is composed once per round so every seat of that round sees the same text.
Run with carry_forward=False to restore fully independent rounds.

WHY THE WITHIN-ROUND RULE IS ABSOLUTE. Showing a seat another seat's answer is
what turns a panel of adversaries into a panel of agreers. A seat that sees a
peer's claim anchors on it, and the errors it makes stop being independent of
the errors already in the record. That is the mechanism behind the
amplification numbers at the top of this module: seats that see each other
converge, and convergence without independence is COLLAPSE, not corroboration.
Within a round the five seats are therefore sealed from one another, always.

WHY THE BETWEEN-ROUND CARRY IS ACCEPTED ANYWAY, AND WHAT IT COSTS. The carried
section is a COMMON INPUT to all five seats of every later round. An error
that survives into it is inherited by the whole panel at once, and the panel
then agrees about it because it was handed to them -- not because five
analysts checked it independently. So agreement in rounds 2..5 is evidence of
a shared input, and a correlation computed across those rounds is measuring a
panel that shares text by design. This is a deliberate trade: iteration is
bought with independence. Round 1 is the only round that pays nothing for it,
and `SequentialPassResult.carried_from_round` records the rest so a reader
never has to assume an independence the run did not have.

HOW IT IS ENFORCED. build_blinded_prompt() is the only constructor of seat
input, and its signature accepts no history parameter of any kind. There is no
argument through which a prior result could be passed, so the leak cannot be
introduced by a caller mistake -- only by editing this function, which the
test suite asserts against.

HOW IT IS ENFORCED, STILL. build_blinded_prompt() remains the only constructor
of seat input and still accepts no history parameter of any kind: there is no
argument through which one seat's response could be handed to another. The
carry does not travel through it. It is folded into the ARTIFACT by
compose_carry_forward() before the round begins, from claims the gates have
already ruled on -- so what reaches a seat is adjudicated material, never a
peer's raw answer in flight.

The orchestrator -- code, not a model -- remains the only component that sees
everything, and it still decides by mechanical gate rather than by vote.
"""


@dataclass(frozen=True)
class SeatPrompt:
    """
    The complete, immutable input to one seat for one pass.

    Frozen so that a prompt cannot be mutated after construction, and so the
    prompt log is a faithful record of what each seat was actually shown.
    """
    pass_id: str
    pass_name: str
    seat_id: str
    artifact: str
    instruction: str

    def render(self) -> str:
        return (
            f"## Lens\n{self.pass_name}\n\n"
            f"## Instruction\n{self.instruction}\n\n"
            f"## Artifact under review\n{self.artifact}\n\n"
            f"## Output format\n"
            f"One line per claim, and nothing else:\n"
            f"    CLAIM | <kind> | <warrant> | <text>\n"
            f"where <kind> is one of: "
            f"{', '.join(k.value for k in ClaimKind)}\n"
            f"<warrant> is the mechanically checkable evidence -- an "
            f"arithmetic expression as '<expr> = <result>', a DOI, a test "
            f"command, or a JSON payload. Leave it EMPTY only if the claim "
            f"genuinely has no mechanical warrant; such claims are escalated "
            f"to a human, never auto-accepted.\n"
        )


def build_blinded_prompt(p: Pass, seat_id: str, artifact: str) -> SeatPrompt:
    """
    Construct the only thing a seat is ever shown.

    This signature is the enforcement mechanism for BLINDING_CONTRACT: there is
    no parameter for prior responses, prior verdicts, or pass history, so no
    caller can pass them in. Adding such a parameter breaks the blinding and
    the test suite is written to catch it.
    """
    return SeatPrompt(
        pass_id=p.id,
        pass_name=p.name,
        seat_id=seat_id,
        artifact=artifact,
        instruction=p.instruction,
    )


@dataclass
class SeatResponse:
    seat_id: str
    pass_id: str
    raw: str
    claims: list[Claim] = field(default_factory=list)
    error: str | None = None


def _edge_is_own(target_id: str,
                 unsupported: Mapping[str, tuple[str, str]],
                 own_ids: set[str]) -> bool:
    """True when the failed quote that condemned this claim belongs to the
    same candidate.

    THE EDGE IS READ FROM THE RECORD, NOT FOUND IN THE PROSE. This previously
    did `any(cid in why for cid in own_ids)` -- substring-searching a rendered
    English sentence for a claim id. A failed quote whose URL merely CONTAINED
    another candidate's claim id therefore read as belonging to that candidate
    as well, and eliminated it: candidate A's fabricated quote took candidate
    B down with it, for no reason but a coincidence of characters. An
    identifier must never be recovered by looking for it inside a sentence.
    """
    edge = unsupported.get(target_id)
    if edge is None:
        return False
    condemning_quote_id, _why = edge
    return condemning_quote_id in own_ids


def content_claim_id(kind: ClaimKind, warrant: str | None, text: str) -> str:
    """
    Content-addressed claim id: two seats that independently make the SAME
    claim produce the SAME id.

    This is what makes the capture-recapture statistics work. Orchestrator.
    run_pass registers a detection against the seat BEFORE its duplicate check,
    so both seats are credited with the catch while the claim is gated once.
    Seat-scoped ids would make every claim a singleton and inflate the Chao1
    estimate of what nobody caught.

    THE PROPOSITION IS PART OF THE IDENTITY. It was not, and the consequence
    was severe: identity was (kind, warrant OR text), so whenever a warrant
    existed the text was discarded entirely. "the launch is safe" and "the
    launch is UNSAFE" both carrying the warrant "2 + 2 = 4" hashed to the same
    id, were gated once, and BOTH received that PASS. A gate checks a warrant;
    binding that verdict to whatever text happened to accompany it means a
    model could attach a true equation, or an approved passing command, to any
    false assertion and have it verified.

    Text is normalised before hashing -- case folded, whitespace collapsed,
    surrounding punctuation dropped -- so two seats phrasing the same
    proposition slightly differently still collide, which is what the
    capture-recapture statistics need. What no longer collides is two
    DIFFERENT propositions leaning on one warrant.
    """
    norm = " ".join((text or "").split()).strip(" .;:\u2014-").casefold()
    material = f"{kind.value}|{(warrant or '').strip()}|{norm}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


_CLAIM_LINE = re.compile(r"^\s*CLAIM\s*\|([^|]*)\|([^|]*)\|(.*)$", re.IGNORECASE)
_ABOUT = re.compile(r"^\s*(opt_[0-9a-f]{6,})\s*\|\s*(.*)$", re.IGNORECASE)
"""An option id at the head of the text field: "CLAIM | kind | warrant |
opt_abc123 | the claim". Optional, and only meaningful in a round where
options exist -- round one creates them, so nothing there can name one."""


_DECORATION = re.compile(r"^[\s>*\-+\u2022`|]+")
_EMPHASIS_BEFORE_FIRST_PIPE = re.compile(r"^([^|]*)")
_ORDERED_MARKER = re.compile(r"^\s*\d+[.)]\s+")
_TRAILING_EMPHASIS = re.compile(r"[*`]+\s*$")
_LEADING_EMPHASIS = re.compile(r"^\s*(?:[>\-+\u2022]\s*)*[*`]")


def undecorate_claim_line(line: str) -> str:
    """Strip list and emphasis decoration from a claim line, fields untouched.

    WHY THE REAL PATH NEEDS THIS. The extractor below only considers a line
    that STARTS WITH "CLAIM". A model that writes its findings as a markdown
    list -- which is what a model asked for a list of findings does -- produces
    "- CLAIM | ..." or "**CLAIM | ...**" or "1. CLAIM | ...", none of which
    start with CLAIM. Those lines were not malformed-and-escalated; they were
    skipped before the fail-closed branch could see them, and the claim
    vanished with nothing counted and nothing raised. Measured on the four
    commonest list shapes, all four lost the claim entirely.

    Only the segment BEFORE the first pipe is de-emphasised, so an asterisk
    inside a multiplication expression is never disturbed. Ordered-list markers
    are removed separately because a leading digit is not decoration in
    general -- only when it is followed by "." or ")" and a space.
    """
    # Ordered-list marker first, and the opener test below runs against the
    # RESULT of this rather than the original line: "1. **CLAIM | ... |
    # text**" opens with a digit, so testing the raw line found no emphasis,
    # left the closing "**" on the last field, and split the claim id from the
    # identical finding written without a number.
    after_marker = _ORDERED_MARKER.sub("", line)
    stripped = _DECORATION.sub("", after_marker)

    # TRAILING EMPHASIS, BUT ONLY WHEN IT CLOSES SOMETHING THIS LINE OPENED.
    #
    # Why it must be stripped at all: "**CLAIM | ... | the total is 47**"
    # strips at the front and leaves the asterisks on the LAST field, so the
    # text becomes "the total is 47**". content_claim_id hashes that text, so
    # a seat that bolded its finding and a seat that did not produce DIFFERENT
    # claim ids for the same finding, and the run reads two agreeing seats as
    # two disagreeing ones.
    #
    # Why it must be conditional: a trailing marker is not always decoration.
    # "CLAIM | ... | value of `total_sum`" ends in a backtick that CLOSES an
    # inline code span and belongs to the text. Stripping unconditionally
    # corrupted it to "value of `total_sum" -- trading one text-mangling bug
    # for another. Decoration wraps: strip the closer only when this line
    # opened with an emphasis marker.
    if _LEADING_EMPHASIS.match(after_marker):
        stripped = _TRAILING_EMPHASIS.sub("", stripped)

    head = _EMPHASIS_BEFORE_FIRST_PIPE.match(stripped)
    if not head:
        return stripped
    cleaned = re.sub(r"[*`_]", "", head.group(1))
    return cleaned + stripped[head.end():]


def line_claim_extractor(raw: str, seat_id: str, pass_id: str) -> list[Claim]:
    """
    Reference extractor for the documented output format.

    FAIL-CLOSED: a line that announces itself as a CLAIM but does not parse,
    or names a kind that does not exist, becomes a JUDGMENT claim with no
    warrant. JUDGMENT has no applicable gate, so it escalates to a human. A
    malformed claim is never silently dropped -- dropping it would let a model
    smuggle an unverified assertion past the gates by writing it badly.

    Each line is undecorated first (see undecorate_claim_line). Without that
    the fail-closed guarantee above had a hole: it only ever applied to lines
    STARTING with "CLAIM", so a claim written as a markdown list item was
    skipped before the guarantee could reach it and disappeared silently.
    """
    claims: list[Claim] = []
    for raw_line in raw.splitlines():
        # Undecorate BEFORE the startswith test, not after. A decorated line
        # fails that test and is skipped outright, which is a silent drop --
        # the one outcome this extractor's fail-closed design exists to avoid.
        line = undecorate_claim_line(raw_line)
        if not line.strip().upper().startswith("CLAIM"):
            continue
        m = _CLAIM_LINE.match(line)
        if not m:
            text = line.strip()
            claims.append(Claim(
                content_claim_id(ClaimKind.JUDGMENT, None, text),
                text, ClaimKind.JUDGMENT, None, pass_id, seat_id,
            ))
            continue
        kind_raw, warrant_raw, text = (g.strip() for g in m.groups())
        try:
            kind = ClaimKind(kind_raw.lower())
        except ValueError:
            claims.append(Claim(
                content_claim_id(ClaimKind.JUDGMENT, None, line.strip()),
                line.strip(), ClaimKind.JUDGMENT, None, pass_id, seat_id,
            ))
            continue
        warrant = warrant_raw or None
        about = None
        m_about = _ABOUT.match(text)
        if m_about:
            about, text = m_about.group(1).lower(), m_about.group(2).strip()
        claims.append(Claim(
            content_claim_id(kind, warrant, text),
            text, kind, warrant, pass_id, seat_id,
            about_option=about,
        ))
    return claims


class BlindedSeatRunner:
    """
    Runs every seat on one pass, each in isolation.

    seat_fns : {seat_id -> callable(prompt_text) -> raw_response}
    extractor: callable(raw, seat_id, pass_id) -> List[Claim]

    prompt_log records every SeatPrompt ever constructed, so an auditor (and
    the test suite) can verify after the fact that no seat was shown a prior
    result.
    """

    def __init__(
        self,
        seat_fns: Mapping[str, Callable[[str], str]],
        extractor: Callable[[str, str, str], list[Claim]] = line_claim_extractor,
    ):
        if not seat_fns:
            raise ValueError("at least one seat is required")
        self.seat_fns = dict(seat_fns)
        self.extractor = extractor
        self.prompt_log: list[SeatPrompt] = []

    def run(self, p: Pass, artifact: str) -> list[SeatResponse]:
        out: list[SeatResponse] = []
        for seat_id, fn in self.seat_fns.items():
            prompt = build_blinded_prompt(p, seat_id, artifact)
            self.prompt_log.append(prompt)
            try:
                raw = fn(prompt.render())
            except BudgetExceeded:
                # A ceiling is not a seat failure and must not be absorbed as
                # one. Recording it here would mark the seat FAILED, continue
                # to the next seat, and keep spending -- which is the precise
                # behaviour a hard ceiling exists to prevent. It propagates so
                # the run stops and writes a partial result.
                raise
            except Exception as exc:  # noqa: BLE001 - fail-closed: seat error recorded  # noqa: BLE001 - fail-closed: any error denies
                # Fail closed: a seat that errors contributes no claims, and
                # the failure is recorded rather than silently swallowed.
                out.append(SeatResponse(seat_id, p.id, "", [], error=str(exc)))
                continue
            out.append(SeatResponse(seat_id, p.id, raw, self.extractor(raw, seat_id, p.id)))
        return out


# ---------------------------------------------------------------------------
# Panel configuration: five seats, four external credentials plus Claude
# ---------------------------------------------------------------------------

class BudgetExceeded(RuntimeError):
    """A spend ceiling stopped the run. Declared here, raised by cost_ledger.

    Lives in this module so BlindedSeatRunner can let it through without
    importing the ledger, keeping the orchestrator free of cost concerns while
    still refusing to swallow the one exception that must never be treated as
    a seat error.
    """


class MissingSeatCredential(RuntimeError):
    """Raised when a configured seat has no credential in the environment."""


@dataclass(frozen=True)
class SeatSpec:
    """
    Declares one seat. Holds the NAME of the environment variable carrying the
    credential, never the credential itself -- nothing in this module reads a
    key into a default argument, a class attribute, or a repr.

    api_key_env=None marks the in-process Claude seat, which is reached through
    the host session rather than an outbound API key.
    """
    seat_id: str
    api_key_env: str | None
    model_env: str | None = None


PANEL_OF_FIVE = (
    SeatSpec("seat_1", "ADJ_SEAT_1_API_KEY", "ADJ_SEAT_1_MODEL"),
    SeatSpec("seat_2", "ADJ_SEAT_2_API_KEY", "ADJ_SEAT_2_MODEL"),
    SeatSpec("seat_3", "ADJ_SEAT_3_API_KEY", "ADJ_SEAT_3_MODEL"),
    SeatSpec("seat_4", "ADJ_SEAT_4_API_KEY", "ADJ_SEAT_4_MODEL"),
    SeatSpec("seat_5_claude", None, "ADJ_SEAT_5_MODEL"),
)
"""
Five seats: four reached by outbound API key, plus Claude in-process.

CONFLICT WITH MAX_RECOMMENDED_SEATS. This module caps preflight at three seats
and its own docstring places five past the knee of the turn-count curve. A
five-seat panel is therefore a deliberate override of this module's own
recommendation, not a configuration it endorses. preflight() still returns 3;
nothing here silently raises that cap.

CONFLICT WITH THE ORCHESTRATOR CONTRACT. The orchestrator is code, not a model.
If the Claude session that runs the orchestrator is ALSO seat 5, that seat is
not blind to the run: it can see the gate verdicts the orchestrator computes.
Its errors are then correlated with the adjudication itself, which is the exact
failure the blinding exists to prevent. Seat 5 must be a separate session or
call with no visibility into orchestrator state, or the panel is four blind
seats plus one that is not.
"""


PANEL_OF_FIVE_EXTERNAL = (
    SeatSpec("seat_1", "ADJ_SEAT_1_API_KEY", "ADJ_SEAT_1_MODEL"),
    SeatSpec("seat_2", "ADJ_SEAT_2_API_KEY", "ADJ_SEAT_2_MODEL"),
    SeatSpec("seat_3", "ADJ_SEAT_3_API_KEY", "ADJ_SEAT_3_MODEL"),
    SeatSpec("seat_4", "ADJ_SEAT_4_API_KEY", "ADJ_SEAT_4_MODEL"),
    SeatSpec("seat_5", "ADJ_SEAT_5_API_KEY", "ADJ_SEAT_5_MODEL"),
)
"""
All five seats reached by API key, including Claude. THE RECOMMENDED SHAPE.

PANEL_OF_FIVE above makes seat 5 in-process, and its own docstring records why
that is a problem: the orchestrator is code, but if the session DRIVING the
orchestrator is also seat 5, that seat can see gate verdicts. It is then not
blind, and its errors correlate with the adjudication itself -- the exact
failure the blinding exists to prevent. The docstring could warn about it; it
could not stop it.

This spec removes the hazard rather than documenting it. Seat 5 becomes an
ordinary outbound call with its own credential, prompted through
build_blinded_prompt like every other seat, with no access to orchestrator
state of any kind. All five seats are then blinded IDENTICALLY, and there is no
special case for a future reader to reason about incorrectly.

The cost is one more API key. That is a smaller price than a rho computed over
a panel where one seat was not actually blind, because that number would look
exactly like a valid measurement.

Both specs remain available: PANEL_OF_FIVE for a genuinely separate in-process
seat driven by a different session, this one for the ordinary case.
"""


class ResolvedSeat:
    """A seat with its credential resolved. The credential never appears in
    repr(), str(), or a formatted log line."""

    __slots__ = ("_secret", "in_process", "model", "seat_id")

    def __init__(self, seat_id: str, model: str | None,
                 secret: str | None, in_process: bool = False):
        self.seat_id = seat_id
        self.model = model
        self._secret = secret
        self.in_process = in_process

    def credential(self) -> str | None:
        """Explicit accessor. Reading a secret should look like reading a
        secret at the call site."""
        return self._secret

    def __repr__(self) -> str:
        held = "in-process" if self.in_process else (
            "set" if self._secret else "MISSING")
        return (f"ResolvedSeat(seat_id={self.seat_id!r}, "
                f"model={self.model!r}, credential=<{held}>)")

    __str__ = __repr__


def load_panel(
    specs: Sequence[SeatSpec] = PANEL_OF_FIVE,
    env: dict[str, str] | None = None,
) -> list[ResolvedSeat]:
    """
    Resolve every seat's credential from the environment.

    FAIL CLOSED: a missing or blank credential raises MissingSeatCredential.
    The panel does not quietly run short. Seat count is an input to
    effective_seats, to the Chao1 estimate, and to what the residual
    extrapolation means, so a four-seat run reported as a five-seat run
    misstates every downstream number.

    env defaults to os.environ; pass a dict to test without touching the
    process environment.
    """
    source = os.environ if env is None else env
    resolved: list[ResolvedSeat] = []
    missing: list[str] = []

    for spec in specs:
        model = source.get(spec.model_env) if spec.model_env else None
        if spec.api_key_env is None:
            resolved.append(ResolvedSeat(spec.seat_id, model, None, in_process=True))
            continue
        secret = source.get(spec.api_key_env, "")
        if not secret.strip():
            missing.append(spec.api_key_env)
            continue
        resolved.append(ResolvedSeat(spec.seat_id, model, secret))

    if missing:
        raise MissingSeatCredential(
            "seat credentials absent from the environment: "
            + ", ".join(sorted(missing))
        )
    return resolved


# ---------------------------------------------------------------------------
# Divergence: disagreement is the expected state, not a failure
# ---------------------------------------------------------------------------

@dataclass
class PassDivergence:
    pass_id: str
    pass_name: str
    n_seats: int
    seats_responding: list[str]
    seats_errored: list[str]
    distinct_claim_sets: int
    mean_pairwise_jaccard: float
    unanimous: bool
    all_seats_silent: bool = False
    collapse_warning: str | None = None
    seat_errors: dict[str, str] = field(default_factory=dict)
    """{seat_id: failure message} for every seat that errored on this pass.

    seats_errored records WHICH seats failed; this records WHY. Without it the
    run destroys its own evidence: a 400 on a rejected parameter, a 401 on a
    bad credential, and a 200 whose reply text sat somewhere the configured
    text_path does not reach are three different operator errors with three
    different fixes, and "seat_1 failed" cannot distinguish them. Recovering
    the distinction otherwise costs a second paid run.
    """


def measure_divergence(p: Pass, responses: Sequence[SeatResponse]) -> PassDivergence:
    """
    Quantify how much the blinded seats disagreed on one pass.

    Claims are compared on CONTENT -- (kind, warrant) -- not on seat-assigned
    labels, so two seats making the same substantive claim register as
    agreement regardless of wording.

    READING IT: on a non-trivial artifact, unanimity is the alarming result.
    Independent seats examining custom code through the same lens will not
    produce identical claim sets; if they do, they are not failing
    independently, and the whole ensemble is worth roughly one seat. See
    seat_independence.effective_seats for what that costs.

    SILENCE IS NOT COLLAPSE. If every seat returned an EMPTY claim set the
    sets are trivially identical, but that is the marginal-yield signal --
    this pass found nothing -- not a monoculture signal. all_seats_silent
    records it and collapse_warning is suppressed, because a warning that
    fires on every empty pass is a warning operators learn to ignore.
    """
    responding = [r for r in responses if r.error is None]
    errored = [r.seat_id for r in responses if r.error is not None]
    seat_errors = {r.seat_id: r.error for r in responses if r.error is not None}
    sets = [frozenset((c.kind.value, (c.warrant or c.text).strip()) for c in r.claims)
            for r in responding]

    silent = bool(sets) and all(len(s) == 0 for s in sets)

    if len(sets) < 2:
        return PassDivergence(
            p.id, p.name, len(responses), [r.seat_id for r in responding], errored,
            len(set(sets)), float("nan"), False, silent, None, seat_errors,
        )

    jaccards = []
    for a, b in itertools.combinations(sets, 2):
        union = a | b
        jaccards.append(1.0 if not union else len(a & b) / len(union))
    mean_j = sum(jaccards) / len(jaccards)
    unanimous = len(set(sets)) == 1

    warning = None
    if unanimous and not silent:
        warning = (
            f"All {len(sets)} seats returned an IDENTICAL claim set on "
            f"'{p.name}'. On a non-trivial artifact this is a monoculture "
            f"signal, not a confirmation: independently-failing seats do not "
            f"agree exactly. Treat the agreement as evidence the seats share a "
            f"failure mode and the panel is worth ~1 effective seat."
        )
    return PassDivergence(
        p.id, p.name, len(responses), [r.seat_id for r in responding], errored,
        len(set(sets)), mean_j, unanimous, silent, warning, seat_errors,
    )


@dataclass
class SequentialPassResult:
    pass_id: str
    pass_name: str
    record: PassRecord
    divergence: PassDivergence
    responses: list[SeatResponse] = field(default_factory=list)
    carried_from_round: int | None = None
    """Which round's comprised answer this round was shown, if any.

    None means the round saw the artifact alone and its seats shared no input
    beyond it -- true of round 1 always, and of every round when the panel is
    run with carry_forward=False. An integer means the seats of this round
    were handed what rounds 1..k established, so their agreement is partly
    explained by that shared text rather than by independent checking. The
    report reads this rather than assuming; a number here is the difference
    between corroboration and a common cause."""


# ===========================================================================
# 4. CONVERGENCE AND STOPPING
# ===========================================================================

def fit_decay(yields: Sequence[float]) -> tuple[float, float] | None:
    """
    Fit VCY_k = a * exp(-b*k) by least squares on log(yield).
    Returns (a, b) or None if fewer than two positive observations.
    """
    pts = [(k + 1, y) for k, y in enumerate(yields) if y > 0]
    if len(pts) < 2:
        return None
    n = len(pts)
    xs = [p[0] for p in pts]
    ys = [math.log(p[1]) for p in pts]
    mx, my = sum(xs) / n, sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / denom
    intercept = my - slope * mx
    return math.exp(intercept), -slope


def residual_estimate(yields: Sequence[float]) -> float | None:
    """
    Expected number of verified catches still to come after the passes run:
        R = a * e^(-b(K+1)) / (1 - e^(-b))
    This converts 'there was nothing left to find' from an impression into an
    extrapolation. Requires b > 0 (an actually decaying series).
    """
    fit = fit_decay(yields)
    if fit is None:
        return None
    a, b = fit
    if b <= 0:
        return None  # yields not decaying: do NOT stop
    K = len(yields)
    return a * math.exp(-b * (K + 1)) / (1 - math.exp(-b))


def chao1_lower_bound(
    detections_by_seat: Mapping[str, set[str]],
) -> dict[str, float]:
    """
    Capture-recapture lower bound on errors NO seat caught.

    A high singleton fraction is exactly what 'each seat caught what others
    missed' feels like from inside, AND is the signal that more errors remain.
    Positive error correlation biases this DOWNWARD: it is a LOWER BOUND.
    """
    counts: Counter[str] = Counter()
    for caught in detections_by_seat.values():
        for e in caught:
            counts[e] += 1
    s_obs = len(counts)
    f1 = sum(1 for c in counts.values() if c == 1)
    f2 = sum(1 for c in counts.values() if c == 2)
    n_hat = s_obs + (f1 ** 2) / (2 * f2) if f2 else s_obs + f1 * (f1 - 1) / 2
    return {
        "observed": float(s_obs),
        "f1_singletons": float(f1),
        "f2_doubletons": float(f2),
        "estimated_total_lower_bound": float(n_hat),
        "estimated_missed": float(n_hat - s_obs),
        "singleton_fraction": float(f1 / s_obs) if s_obs else float("nan"),
    }


# ===========================================================================
# 5. ORCHESTRATOR
# ===========================================================================

@dataclass
class PassRecord:
    pass_id: str
    proposed: int
    auto_accepted: int
    auto_rejected: int
    escalated: int
    warrant_only: int = 0
    """Claims whose warrant checked out but does not establish the claim.

    Counted separately from ordinary escalations because they are a different
    finding: an ordinary escalation had no mechanical warrant at all, while
    these had one that passed and simply is not about the proposition. A run
    with many of these is a run where seats are attaching true evidence to
    unrelated assertions, which is the specific failure mode this system exists to
    stop.
    """
    repeats: int = 0
    """Claims re-proposed after being adjudicated in an earlier pass.

    Without this the pass counts read as "N proposed, 0 resolved" on a later
    round, which looks exactly like the gates having stopped working."""
    repeated_failures: int = 0
    """Re-proposed claims whose STANDING verdict is FAIL.

    The one that matters. A speaker restating something the gates already
    refuted is asserting a known falsehood, and counting only fresh rulings
    made that invisible after the first occurrence."""
    eliminated_candidates: list[str] = field(default_factory=list)
    blocked: int = 0
    """Claims whose check could not be performed. Never a finding, never a kill.

    Kept apart from escalated because they are different facts: escalated
    means no gate applied, blocked means a gate applied and could not reach
    its evidence. Merging them would let an outage read as "nothing to check
    here".
    """


@dataclass(frozen=True)
class ClaimVerdict:
    """
    The adjudicated outcome of ONE claim, retained for the whole run.

    PassRecord counts outcomes; it does not say WHICH claim got which verdict.
    That is enough to fit the decay curve and nothing else. The independence
    diagnostics need per-claim ground truth -- whether the proposition a seat
    asserted turned out to be true -- so the verdict is kept here rather than
    reduced to a tally at the moment it is produced.

    status is None for an ESCALATED claim: no gate applied, so the run has no
    mechanical opinion about it. That is not a soft "unknown" to be filled in
    with a default. It is the absence of a measurement, and correctness_matrix
    excludes such claims unless a human adjudication is supplied.
    """
    claim_id: str
    pass_id: str
    status: GateStatus | None
    gate: str | None = None
    detail: str = ""

    @property
    def verified_true(self) -> bool | None:
        """True, False, or None -- and None is a THIRD answer, not a default.

        PASS      -> True    the check ran and the claim held
        FAIL      -> False   the check ran and refuted it
        anything else -> None

        BLOCKED AND INAPPLICABLE ARE NOT False. They were, and that turned
        "the check could not run" into ground truth that the claim is untrue.
        Downstream this was consumed as a resolved fact: a run whose only claim
        was BLOCKED reported resolved=True with that claim recorded false, so
        a paywall or a timeout became a finding and the run declared itself
        complete on the strength of a check that never happened.

        This is the same tri-state the rest of the system runs on, at the one
        place it was silently collapsed back into a boolean.
        """
        if self.status is GateStatus.PASS:
            return True
        if self.status is GateStatus.FAIL:
            return False
        return None


class Orchestrator:
    """
    Sequential, gate-first adjudication. The orchestrator is CODE, not a model.

    Contract:
      - A claim with an applicable gate is decided by the gate. No LLM vote.
      - A claim with no applicable gate is ESCALATED. It is never auto-accepted.
      - A candidate is eliminated only by a FAILED gate on an eliminative pass.
      - Stopping is decided by the decay extrapolation, not by 'it looks done'.
    """

    def __init__(
        self,
        gates: Sequence[Gate],
        passes: Sequence[Pass] = tuple(DEFAULT_PASSES),
        max_candidates_at_stop: int = 2,
        residual_tolerance: float = 0.5,
        singleton_alarm: float | None = None,
    ):
        self.gates = list(gates)
        self.passes = list(passes)
        self.max_candidates_at_stop = max_candidates_at_stop
        self.residual_tolerance = residual_tolerance
        # SOP 9.2 lists 'singleton fraction very high' as an abort signal but
        # names no number, and SOP 8.4 requires operators to set their own
        # thresholds. None means UNCALIBRATED: the check is not applied and
        # the report says so, rather than this module inventing a cutoff.
        self.singleton_alarm = singleton_alarm

        self.escalation_queue: list[Claim] = []
        self.history: list[PassRecord] = []
        self.detections_by_seat: dict[str, set[str]] = {}
        self._seen_claims: set[str] = set()
        self.divergence_by_pass: dict[str, PassDivergence] = {}
        # claim_id -> ClaimVerdict, one entry per DISTINCT claim. A claim is
        # adjudicated once, in the pass that first saw it; later re-proposals
        # by other seats do not re-run the gates and do not overwrite this.
        self.verdicts: dict[str, ClaimVerdict] = {}
        self.unsupported_claims: dict[str, str] = {}
        """claim_id -> why, for claims whose supporting quote proved absent."""
        self._proposed_index: dict[str, Claim] = {}

    # -- verification -------------------------------------------------------

    def _route(self, claim: Claim) -> GateResult | None:
        """
        Every applicable gate must pass. The first FAIL decides.

        Conjunctive rather than first-match-wins: a citation is subject to both
        SourceAdmissibilityGate (is this class of evidence allowed at all?) and
        CitationResolutionGate (does it actually resolve?), and passing one is
        not passing the other. Returns None only when NO gate applies, which
        routes the claim to the human escalation queue.
        """
        applicable = [g for g in self.gates if g.applies_to(claim)]
        if not applicable:
            return None  # no mechanical warrant -> escalate
        results = [g.check(claim) for g in applicable]
        # FAIL OUTRANKS BLOCKED, and this is a correction. The original
        # reasoning was that an unreachable gate means "not fully examined",
        # so BLOCKED should win -- but that is wrong, and two independent
        # reviewers caught it. False AND unknown is false: if any applicable
        # gate definitively refuted the claim, a second gate timing out does
        # not make the refutation provisional. The earlier order let a proven
        # falsehood survive whenever any other gate happened to be blocked.
        #
        # BLOCKED still outranks PASS, which is the half that was right: a
        # claim is not verified while one of its checks did not happen.
        for r in results:
            if r.status is GateStatus.FAIL:
                return r
        for r in results:
            if r.status is GateStatus.BLOCKED:
                return r
        for r in results:
            if r.status is not GateStatus.PASS:
                return r
        return results[0]

    def gate_candidate_claims(self, candidates: list[Candidate]) -> list[str]:
        """
        Rule on the claims the CANDIDATES themselves assert, before any pass.

        WHY THIS EXISTS. Elimination in run_pass fires only when a SEAT
        independently proposes a claim whose content-addressed id collides with
        one a candidate carries. A candidate standing on a falsehood that no
        seat happened to raise was therefore never examined at all -- and the
        report listed it beside a genuinely scrutinised survivor with no way to
        tell the two apart. Observed on run-003: two of three survivors each
        carried a false arithmetic claim, and neither had been tested.

        That is a fail-open in a system built to fail closed, so it is closed
        here. A candidate that contradicts arithmetic is wrong whether or not a
        seat noticed; requiring rediscovery made scrutiny depend on luck.

        Blinding is unaffected -- gates are code, not seats. The verdicts land
        in the same self.verdicts map, so a claim adjudicated here is not
        re-gated when a seat later proposes it, exactly as a claim first seen
        in pass 1 is not re-gated in pass 2.

        THIS METHOD DOES NOT ELIMINATE ANYTHING. It only rules on claims and
        records the verdicts. Removal stays where the design puts it: on an
        eliminative pass, via _sweep_standing_verdicts. Eliminating here would
        have removed candidates outside an eliminative pass, which is the one
        rule this module states about how an answer may be discarded, and a
        fail-open is not worth buying with a broken invariant.

        Returns the ids of claims newly adjudicated here.
        """
        ruled: list[str] = []
        for cand in candidates:
            for claim in cand.claims:
                if claim.id in self.verdicts or claim.id in self._seen_claims:
                    continue
                result = self._route(claim)
                if result is None:
                    # No applicable gate: escalate like any other unwarranted
                    # claim rather than letting it count as passed.
                    self.escalation_queue.append(claim)
                    self._seen_claims.add(claim.id)
                    continue
                self._seen_claims.add(claim.id)
                # THE SAME WARRANT-TO-PROPOSITION TEST AS run_pass.
                #
                # This path recorded result.status directly, so a candidate
                # whose claim carried a valid warrant beside unrelated prose
                # was marked PASS at intake and never reconsidered -- the one
                # place a candidate's own assertions are ruled on, applying a
                # weaker rule than the one seats are held to.
                if result.status is GateStatus.PASS:
                    unsupported = warrant_supports(claim)
                    if unsupported is not None:
                        self.verdicts[claim.id] = ClaimVerdict(
                            claim.id, "intake", None, result.gate,
                            f"{unsupported} (the warrant itself checked out: "
                            f"{result.detail})",
                        )
                        self.escalation_queue.append(claim)
                        continue
                self.verdicts[claim.id] = ClaimVerdict(
                    claim.id, "intake", result.status, result.gate, result.detail
                )
                ruled.append(claim.id)
        return ruled

    def apply_quote_cascade(self, candidates: list[Candidate],
                            p: Pass, rec: PassRecord) -> None:
        """A fabricated quote takes down what it was offered to support.

        A quote_verification claim ruled FAIL does not merely drop itself:
        every claim listed in its `supports` has lost its stated evidentiary
        basis, so it leaves the working answer and any candidate resting on it
        is eliminated. The severity is deliberate -- a claim whose supporting
        quote does not exist is worse off than one with no quote, because the
        quote actively misrepresented the state of the evidence.

        A BLOCKED quote cascades nothing. The check did not happen, so the
        supported claim is exactly as well evidenced as it was before.
        """
        from quote_gate import cascade_unsupported

        by_id = {c.id: c for cand in candidates for c in cand.claims}
        by_id.update({c.id: c for c in self.escalation_queue})
        # Direct, not getattr-with-a-default: _proposed_index is set in
        # __init__, so a default here could only ever mask a rename, and it
        # would mask it by silently cascading nothing -- a quote shown not to
        # exist would leave every claim it supported standing.
        by_id.update(self._proposed_index)

        unsupported = cascade_unsupported(self.verdicts, by_id)
        if not unsupported:
            return
        # Keep the human-readable half in the public record; the edge itself
        # stays structured for anything that must reason about ownership.
        self.unsupported_claims.update(
            {cid: why for cid, (_qid, why) in unsupported.items()})
        for cand in candidates:
            if cand.eliminated:
                continue
            # SUPPORT EDGES ARE CANDIDATE-SCOPED. A quote may only undermine
            # claims carried by the SAME candidate that offered it. Globally
            # scoped edges let a candidate name a rival's independently
            # verified claim in its own `supports` and take the rival down
            # with it when its own quote proved fabricated -- a candidate
            # eliminating a competitor by lying about it.
            own = {c.id for c in cand.claims}
            for claim in cand.claims:
                edge = unsupported.get(claim.id)
                if edge and not _edge_is_own(claim.id, unsupported, own):
                    continue
                if edge:
                    _quote_id, why = edge
                    cand.eliminated = True
                    cand.elimination_reason = f"{p.name}: {why}"
                    cand.elimination_kind = "earned"
                    rec.eliminated_candidates.append(cand.id)
                    break

    def _sweep_standing_verdicts(
        self, candidates: list[Candidate], p: Pass, rec: PassRecord
    ) -> None:
        """Remove any candidate leaning on a claim already ruled FAIL.

        run_pass eliminates on claims proposed IN THAT PASS. That leaves two
        gaps, both of which let a false candidate through: a claim ruled at
        intake and never re-proposed by a seat, and a claim ruled in an earlier
        pass whose candidate was not checked against it. Claim ids are
        content-addressed, so a standing FAIL is a fact about the claim itself
        and applies to every candidate carrying it, whenever it was ruled.
        """
        for cand in candidates:
            if cand.eliminated:
                continue
            for claim in cand.claims:
                v = self.verdicts.get(claim.id)
                # ONLY a FAIL eliminates. A BLOCKED claim means the check did
                # not happen -- a firewall, a rate limit, a paywall -- and
                # letting that remove a candidate would make a network outage
                # indistinguishable from a refutation.
                if v is not None and v.status is GateStatus.FAIL:
                    cand.eliminated = True
                    cand.elimination_reason = (
                        f"{p.name}: {v.gate} failed -- {v.detail}"
                    )
                    cand.elimination_kind = "earned"
                    rec.eliminated_candidates.append(cand.id)
                    break

    def claim_coverage(self, cand: Candidate) -> tuple[int, int]:
        """How many of a candidate's own claims actually reached a gate.

        (tested, total). A survivor with 1 of 6 tested survived by not being
        looked at, which is a different fact from surviving scrutiny, and the
        report should not print them identically.
        """
        total = len(cand.claims)
        # A BLOCKED claim was NOT tested. It has a verdict object, but the
        # verdict says the check did not happen, and counting it as coverage
        # let a survivor report "3/3 claims tested" when one of them was never
        # actually checked.
        tested = sum(
            1 for c in cand.claims
            if (v := self.verdicts.get(c.id)) is not None
            and v.status in (GateStatus.PASS, GateStatus.FAIL)
        )
        return tested, total

    def claim_by_id(self, claim_id: str) -> Claim | None:
        """The claim behind a verdict, or None if it was never proposed here.

        Public because callers legitimately need it: a verdict carries a gate's
        message but not the assertion the gate ruled on, and a report that
        shows only the message tells a reader that something held without
        saying what. Reaching into the private index from outside was the
        alternative, and it would break silently on any rename.
        """
        return self._proposed_index.get(claim_id)

    def run_pass(
        self,
        p: Pass,
        candidates: list[Candidate],
        proposed_claims: list[Claim],
    ) -> PassRecord:
        rec = PassRecord(p.id, len(proposed_claims), 0, 0, 0)

        for claim in proposed_claims:
            if not claim.id:
                # Unreachable via __post_init__, which fills an empty id. Kept
                # because the consequence of an empty id is silent: it aliases
                # to every other empty id, so the first claim is gated and the
                # rest vanish without appearing in any count. A loud failure
                # here costs one traceback; the alternative costs a run whose
                # report looks complete.
                raise ValueError(
                    f"claim with no id: {claim.text!r}. An empty id aliases to "
                    f"every other empty id, so this claim and all later ones "
                    f"would be dropped without being adjudicated."
                )
            self._proposed_index[claim.id] = claim
            if claim.source_seat:
                self.detections_by_seat.setdefault(claim.source_seat, set()).add(claim.id)

            if claim.id in self._seen_claims:
                # Already adjudicated in an earlier pass. Re-gating a
                # content-addressed claim would recompute a verdict that
                # cannot have changed, so the skip is right -- but it is
                # counted, because "not ruled on THIS pass" and "not ruled on
                # at all" are different facts and a consumer that conflates
                # them stops seeing repeat offences. A closer that restates a
                # refuted claim in every round was flagged only in the round
                # where the claim was new.
                rec.repeats += 1
                if self.verdicts.get(claim.id, None) is not None:
                    v = self.verdicts[claim.id]
                    if v.status is GateStatus.FAIL:
                        rec.repeated_failures += 1
                continue
            self._seen_claims.add(claim.id)

            result = self._route(claim)

            if result is None:
                self.escalation_queue.append(claim)
                rec.escalated += 1
                self.verdicts[claim.id] = ClaimVerdict(claim.id, p.id, None)
                continue

            self.verdicts[claim.id] = ClaimVerdict(
                claim.id, p.id, result.status, result.gate, result.detail
            )

            if result.status is GateStatus.PASS:
                # THE GATE CHECKED THE WARRANT. Does the warrant bear on the
                # PROPOSITION? If that cannot be established, the claim is not
                # accepted -- it escalates. Not eliminated either: an
                # unestablished claim could still be true, and killing it here
                # would break the rule this whole system runs on.
                unsupported = warrant_supports(claim)
                if unsupported is not None:
                    self.verdicts[claim.id] = ClaimVerdict(
                        claim.id, p.id, None, result.gate,
                        f"{unsupported} (the warrant itself checked out: "
                        f"{result.detail})",
                    )
                    self.escalation_queue.append(claim)
                    rec.escalated += 1
                    rec.warrant_only += 1
                    continue
                rec.auto_accepted += 1
                continue

            if result.status is GateStatus.BLOCKED:
                # Not a rejection and not an acceptance. Counted on its own so
                # a blocked check can never be read as a finding.
                rec.blocked += 1
                continue

            rec.auto_rejected += 1
            if p.eliminative:
                for cand in candidates:
                    if cand.eliminated:
                        continue
                    if any(c.id == claim.id for c in cand.claims):
                        cand.eliminated = True
                        cand.elimination_reason = (
                            f"{p.name}: {result.gate} failed -- {result.detail}"
                        )
                        cand.elimination_kind = "earned"
                        rec.eliminated_candidates.append(cand.id)

        # Candidates can also lean on claims ruled at intake or in an earlier
        # pass that no seat re-proposed here. Those are just as decided.
        if p.eliminative:
            self.apply_quote_cascade(candidates, p, rec)
            self._sweep_standing_verdicts(candidates, p, rec)

        self.history.append(rec)
        return rec

    # -- sequential, blinded execution --------------------------------------

    # -- the round-to-round carry ------------------------------------------

    CARRY_HEADER = "=== WHAT THE EARLIER ROUNDS ESTABLISHED ==="

    def compose_carry_forward(
        self,
        artifact: str,
        candidates: Sequence[Candidate],
        through_pass: int,
    ) -> str:
        """Build the input for the NEXT round: the artifact plus what the
        rounds so far comprised.

        THIS IS THE ITERATIVE LOOP, AND IT COSTS INDEPENDENCE ON PURPOSE.
        Round k+1 is meant to refine round k rather than re-examine the same
        text through a new lens, so the comprised answer travels forward. The
        price is stated here rather than buried: everything in this section is
        a COMMON INPUT to all five seats of the next round. An error that
        survives into it is inherited by every seat at once, and they will
        then agree about it for that reason and not because they checked it
        independently. Cross-round agreement is therefore evidence of shared
        input, not of corroboration, and `carry_forward_rounds` on the result
        records which rounds were affected so a reader is never left to assume
        an independence the run did not have.

        Two properties are preserved, because losing them would make the
        round's five answers incomparable rather than merely dependent:

        * NO SEAT IS NAMED. The section is aggregate; `source_seat` is never
          written out. A seat that could tell which analyst said what could
          model the others and start agreeing with a particular one, which is
          seat-to-seat leakage wearing the carry's clothes.
        * EVERY SEAT IN A ROUND SEES THE SAME TEXT. The carry is composed once
          per round, before any seat of that round is prompted, so within the
          round the panel is still blind and still symmetric.

        Ordering is by claim id throughout: replay mode forbids nondeterminism,
        and a section whose order drifted between runs would change the prompt
        and therefore the answers.
        """
        verified: list[str] = []
        refuted: list[str] = []
        open_q: list[str] = []

        for claim_id in sorted(self.verdicts):
            v = self.verdicts[claim_id]
            claim = self._proposed_index.get(claim_id)
            if claim is None:
                continue
            line = f"  - {claim.text}"
            if claim.warrant:
                line += f"   [warrant: {claim.warrant}]"
            # status is a GateStatus, never a bool. Comparing it to True/False
            # silently sorted EVERY adjudicated claim into `open_q`, so a
            # refuted claim -- which this section tells the next round to
            # treat as settled -- was carried forward as still unresolved, and
            # a verified one lost its verification. The section still rendered
            # perfectly well formed. Compare against the enum.
            if v.status is GateStatus.PASS:
                verified.append(line)
            elif v.status is GateStatus.FAIL:
                refuted.append(line)
            else:
                # None (escalated: no gate applied), INAPPLICABLE, or BLOCKED.
                # In none of those does the run hold a mechanical opinion, so
                # the claim travels as an open question and never as a finding.
                open_q.append(line)

        parts = [
            artifact,
            "",
            self.CARRY_HEADER,
            f"(Composed by the adjudicator after round {through_pass}, from "
            f"what survived mechanical gates. Not any analyst's opinion, and "
            f"no analyst is identified. Treat REFUTED as settled and do not "
            f"re-assert it; treat OPEN as still needing work.)",
            "",
        ]
        if verified:
            parts += ["VERIFIED -- a gate confirmed these:", *verified, ""]
        if refuted:
            parts += ["REFUTED -- a gate disproved these:", *refuted, ""]
        if open_q:
            parts += ["OPEN -- no gate applied; still unresolved:",
                      *open_q, ""]

        remaining = [c.id for c in candidates if not c.eliminated]
        gone = [(c.id, c.elimination_reason or "")
                for c in candidates if c.eliminated]
        if remaining or gone:
            parts.append("CANDIDATES:")
            if remaining:
                parts.append(f"  still standing: {', '.join(sorted(remaining))}")
            for cid, why in sorted(gone):
                parts.append(f"  removed: {cid} -- {why}")
            parts.append("")

        if not (verified or refuted or open_q or remaining or gone):
            # Nothing was comprised, so nothing is carried. Appending an empty
            # header would still change the prompt and would tell the next
            # round that a round had run, which is a leak that buys nothing.
            return artifact

        return "\n".join(parts).rstrip() + "\n"

    def run_sequential(  # noqa: PLR0913
        # Six arguments, two of them keyword-only switches. Collapsing them
        # into a config object would hide that `carry_forward` exists, and it
        # is the switch that decides whether the rounds are independent -- the
        # single most consequential choice a caller makes here.
        self,
        artifact: str,
        candidates: list[Candidate],
        runner: BlindedSeatRunner,
        passes: Sequence[Pass] | None = None,
        *,
        audit: Any = None,
        carry_forward: bool = True,
    ) -> list[SequentialPassResult]:
        """
        Run the five rounds ONE AT A TIME, each round refining the last.

        Within a round: every seat is prompted in isolation via
        build_blinded_prompt (see BLINDING_CONTRACT), each answers alone, and
        only once ALL of them have answered are the claims gated mechanically
        and the disagreement measured. No seat sees another seat's answer, and
        every seat of a round is handed identical text.

        Between rounds (carry_forward=True, the default): the comprised answer
        of rounds 1..k -- what the gates verified, what they refuted, what is
        still open, and which candidates remain -- is appended to the artifact
        and becomes the input to round k+1. Round k+1 therefore REFINES round
        k rather than re-examining the same text through a new lens, which is
        the iterative loop this tool is built around.

        WHAT THAT COSTS, STATED PLAINLY. The carried section is a COMMON INPUT
        to all five seats of every later round. An error that survives into it
        is inherited by the whole panel at once, and the panel will then agree
        about it because it was handed to them, not because five analysts
        checked it independently. So agreement in rounds 2..5 is NOT evidence
        of independent corroboration, and any rho computed across those rounds
        is measuring a panel that shares an input by design. The rounds that
        received carried content are recorded on each SequentialPassResult
        (`carried_from_round`) and surfaced in the report, so no reader has to
        assume an independence the run did not have. Round 1 alone is
        uncontaminated.

        carry_forward=False restores fully information-independent rounds:
        five lenses over one fixed artifact, all consolidation in code at the
        end. Nothing else about the run changes.

        Returns one SequentialPassResult per round, in order.
        """
        chosen = list(passes) if passes is not None else list(self.passes)
        results: list[SequentialPassResult] = []

        # SOP 8.5: every run writes an audit record. The artifact is committed
        # by digest before any seat sees it, so the log proves WHICH artifact
        # was adjudicated without copying its contents into the record.
        if audit is not None:
            audit.record_artifact(artifact)

        # The text this round's seats actually see. Round 1 is the artifact as
        # given; later rounds get the artifact plus what earlier rounds
        # comprised. It is composed ONCE per round, before any seat of that
        # round is prompted, so the panel stays symmetric and blind within the
        # round even while the rounds themselves build on one another.
        round_input = artifact
        carried_from: int | None = None

        for index, p in enumerate(chosen, start=1):
            responses = runner.run(p, round_input)
            divergence = measure_divergence(p, responses)
            self.divergence_by_pass[p.id] = divergence

            claims: list[Claim] = []
            for r in responses:
                claims.extend(r.claims)

            record = self.run_pass(p, candidates, claims)
            result = SequentialPassResult(
                p.id, p.name, record, divergence, responses,
                carried_from_round=carried_from,
            )
            results.append(result)
            if audit is not None:
                audit.record_pass(result)

            # Compose the next round's input from everything comprised so far.
            # Built after this round is gated, so it can only ever contain
            # adjudicated material -- never a raw seat response in flight.
            if carry_forward and index < len(chosen):
                nxt = self.compose_carry_forward(artifact, candidates, index)
                if nxt != round_input:
                    round_input = nxt
                    carried_from = index

        if audit is not None:
            audit.record_stop_decision(self.should_stop(candidates))

        return results

    # -- convergence --------------------------------------------------------

    def survivors(self, candidates: list[Candidate]) -> list[Candidate]:
        return [c for c in candidates if not c.eliminated]

    def should_stop(self, candidates: list[Candidate]) -> dict[str, Any]:
        """
        SOP Manual v1.0 sections 6.3, 9.1 step 8, and 9.2.

        The manual's stop rule is a CONJUNCTION, and the queue is part of it:

            "STOP when R_hat < tolerance AND your judgment queue is empty"   (6.3)
            "Commit ONLY if the queue is empty AND the residual is below
             tolerance"                                                      (9.1)

        This method previously returned stop=True whenever EITHER the candidate
        set had shrunk OR the residual was low, and ignored the escalation queue
        entirely -- the queue produced an advisory WARNING string that nothing
        acted on. SOP section 10 lists "you will not work the escalation queue"
        as a do-not-build condition, because unworked judgment claims are
        exactly the unverified-ensemble topology this system exists to avoid.
        A stop decision that ignores the queue is therefore not a weaker
        version of the rule; it is the failure mode.

        VCY. Section 6.3 defines VCY_k as "verified CORRECTIONS found in round
        k". A correction is a claim the gates found wrong -- auto_rejected. An
        auto-accepted claim is a confirmation, not a correction. Feeding
        accepted claims into the decay fit made a pass that found nothing look
        maximally productive and kept the residual from ever decaying.
        """
        # VCY_k: verified corrections, i.e. gate REJECTIONS (SOP 6.3)
        yields = [float(r.auto_rejected) for r in self.history]
        residual = residual_estimate(yields)
        alive = len(self.survivors(candidates))
        queued = len(self.escalation_queue)

        capture = (chao1_lower_bound(self.detections_by_seat)
                   if self.detections_by_seat else None)
        singleton = capture["singleton_fraction"] if capture else float("nan")

        blockers: list[str] = []
        if queued:
            blockers.append(
                f"{queued} unresolved item(s) in the judgment queue (SOP 9.1 step 8)"
            )
        if residual is None:
            blockers.append(
                "yields are not decaying; convergence not established (SOP 9.2)"
            )
        elif residual >= self.residual_tolerance:
            blockers.append(
                f"extrapolated residual {residual:.2f} >= tolerance "
                f"{self.residual_tolerance}"
            )
        if (self.singleton_alarm is not None
                and not math.isnan(singleton)
                and singleton > self.singleton_alarm):
            blockers.append(
                f"singleton fraction {singleton:.2f} > {self.singleton_alarm}: "
                f"seats are not overlapping, more errors likely remain (SOP 9.2)"
            )

        return {
            "stop": not blockers,
            "blockers": blockers,
            "surviving_candidates": alive,
            "extrapolated_residual": residual,
            "escalations_pending": queued,
            "singleton_fraction": singleton,
            "singleton_alarm_calibrated": self.singleton_alarm is not None,
            "capture_recapture": capture,
            "WARNING": (
                "Pending escalations are claims with NO mechanical warrant. "
                "Committing while the queue is non-empty converts this run into "
                "the independent topology (17.2x error amplification)."
            ) if self.escalation_queue else None,
        }

    def report(self) -> dict[str, Any]:
        return {
            "passes": [vars(r) for r in self.history],
            "divergence_by_pass": {
                pid: dict(vars(d)) for pid, d in self.divergence_by_pass.items()
            },
            "escalation_queue": [
                {"id": c.id, "text": c.text, "kind": c.kind.value} for c in self.escalation_queue
            ],
        }


# ===========================================================================
# 6. DEMO — synthetic, illustrative only
# ===========================================================================

if __name__ == "__main__":
    verdict = preflight(single_agent_baseline=0.31, task_is_decomposable=True, requested_seats=5)
    print(f"PREFLIGHT: run_ensemble={verdict.run_ensemble} seats={verdict.recommended_seats}")
    print(f"  {verdict.reason}\n")

    gates: list[Gate] = [
        ArithmeticGate(),
        CitationResolutionGate(resolver_fn=lambda ident: ident.startswith("10.1038")),
        SchemaGate(required_keys=["id", "value"]),
    ]
    orch = Orchestrator(gates)

    candidates = [
        Candidate("A", "Answer A"),
        Candidate("B", "Answer B"),
        Candidate("C", "Answer C"),
    ]

    batches = {
        "p1": [
            Claim("c1", "Total is 47", ClaimKind.ARITHMETIC, "12 + 35 = 47", "p1", "seat1"),
            Claim("c2", "Total is 50", ClaimKind.ARITHMETIC, "12 + 35 = 50", "p1", "seat2"),
            Claim("c3", "Framing is sound", ClaimKind.JUDGMENT, None, "p1", "seat1"),
        ],
        "p2": [
            Claim("c4", "Source supports claim", ClaimKind.CITATION, "10.1038/s42256-026-01268-y", "p2", "seat2"),
            Claim("c5", "Source supports claim", ClaimKind.CITATION, "10.9999/fabricated", "p2", "seat3"),
        ],
    }
    candidates[1].claims.append(batches["p1"][1])   # B carries the bad arithmetic
    candidates[2].claims.append(batches["p2"][1])   # C carries the bad citation

    for p in DEFAULT_PASSES[:2]:
        rec = orch.run_pass(p, candidates, batches[p.id])
        print(f"{p.name}: proposed={rec.proposed} accepted={rec.auto_accepted} "
              f"rejected={rec.auto_rejected} escalated={rec.escalated} "
              f"eliminated={rec.eliminated_candidates}")

    print("\nSTOP CHECK:")
    for k, v in orch.should_stop(candidates).items():
        if v is not None:
            print(f"  {k}: {v}")
