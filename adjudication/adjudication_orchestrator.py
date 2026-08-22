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
from enum import Enum
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
    JUDGMENT = "judgment"          # no mechanical warrant -> always escalates


@dataclass
class Claim:
    id: str
    text: str
    kind: ClaimKind
    warrant: str | None = None   # expression, DOI, test command, schema...
    source_pass: str | None = None
    source_seat: str | None = None


@dataclass
class Candidate:
    id: str
    content: str
    claims: list[Claim] = field(default_factory=list)
    eliminated: bool = False
    elimination_reason: str | None = None
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
_BINARY_OPS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_UNARY_OPS: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> float:
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
        return _safe_eval(node.body)
    if (isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
        return _BINARY_OPS[type(node.op)](
            _safe_eval(node.left), _safe_eval(node.right)
        )
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("unsupported expression")


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
        try:
            expr, claimed = warrant.rsplit("=", 1)
            actual = _safe_eval(ast.parse(expr.strip(), mode="eval"))
            expected = float(claimed.strip())
        except Exception as exc:  # noqa: BLE001 - fail-closed: any error denies
            return GateResult(self.name, GateStatus.FAIL, f"unparseable warrant: {exc}")

        if math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9):
            return GateResult(self.name, GateStatus.PASS, f"{actual} confirmed")
        return GateResult(
            self.name, GateStatus.FAIL, f"claimed {expected}, recomputed {actual}"
        )


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
        except Exception as exc:  # noqa: BLE001 - fail-closed: any error denies
            return GateResult(self.name, GateStatus.FAIL, f"resolver error: {exc}")
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
    except Exception as exc:  # noqa: BLE001 - fail-closed: any error denies
        return GateResult("resolver_probe", GateStatus.PASS,
                          f"resolver raised rather than confirming: {exc}")
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
        except Exception as exc:  # noqa: BLE001 - fail-closed: any error denies
            return GateResult(self.name, GateStatus.FAIL, f"invalid JSON: {exc}")
        missing = [k for k in self.required_keys if k not in payload]
        if missing:
            return GateResult(self.name, GateStatus.FAIL, f"missing keys: {missing}")
        return GateResult(self.name, GateStatus.PASS, "schema valid")


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

  - any other seat's response, on this pass or any earlier one
  - any gate verdict (accepted / rejected / escalated)
  - any candidate's elimination status
  - the pass number, or which passes have already run

WHY. Showing results is what turns a panel of adversaries into a panel of
agreers. A seat that sees a prior verdict anchors on it, and the errors it
makes stop being independent of the errors already in the record. That is the
mechanism behind the amplification numbers at the top of this module: seats
that see each other converge, and convergence without independence is
COLLAPSE, not corroboration.

HOW IT IS ENFORCED. build_blinded_prompt() is the only constructor of seat
input, and its signature accepts no history parameter of any kind. There is no
argument through which a prior result could be passed, so the leak cannot be
introduced by a caller mistake -- only by editing this function, which the
test suite asserts against.

WHAT THIS COSTS. Blinded seats cannot build on each other. Pass 2 does not
refine pass 1; it re-examines the same artifact through a different lens. The
orchestrator -- code, not a model -- is the only component that sees
everything, and it decides by mechanical gate rather than by vote.
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


def content_claim_id(kind: ClaimKind, warrant: str | None, text: str) -> str:
    """
    Content-addressed claim id: two seats that independently make the SAME
    claim produce the SAME id.

    This is what makes the capture-recapture statistics work. Orchestrator.
    run_pass registers a detection against the seat BEFORE its duplicate check,
    so both seats are credited with the catch while the claim is gated once.
    Seat-scoped ids would make every claim a singleton and inflate the Chao1
    estimate of what nobody caught.
    """
    material = f"{kind.value}|{(warrant or text).strip()}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


_CLAIM_LINE = re.compile(r"^\s*CLAIM\s*\|([^|]*)\|([^|]*)\|(.*)$", re.IGNORECASE)


def line_claim_extractor(raw: str, seat_id: str, pass_id: str) -> list[Claim]:
    """
    Reference extractor for the documented output format.

    FAIL-CLOSED: a line that announces itself as a CLAIM but does not parse,
    or names a kind that does not exist, becomes a JUDGMENT claim with no
    warrant. JUDGMENT has no applicable gate, so it escalates to a human. A
    malformed claim is never silently dropped -- dropping it would let a model
    smuggle an unverified assertion past the gates by writing it badly.
    """
    claims: list[Claim] = []
    for line in raw.splitlines():
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
        claims.append(Claim(
            content_claim_id(kind, warrant, text),
            text, kind, warrant, pass_id, seat_id,
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
    sets = [frozenset((c.kind.value, (c.warrant or c.text).strip()) for c in r.claims)
            for r in responding]

    silent = bool(sets) and all(len(s) == 0 for s in sets)

    if len(sets) < 2:
        return PassDivergence(
            p.id, p.name, len(responses), [r.seat_id for r in responding], errored,
            len(set(sets)), float("nan"), False, silent, None,
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
        len(set(sets)), mean_j, unanimous, silent, warning,
    )


@dataclass
class SequentialPassResult:
    pass_id: str
    pass_name: str
    record: PassRecord
    divergence: PassDivergence
    responses: list[SeatResponse] = field(default_factory=list)


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
    eliminated_candidates: list[str] = field(default_factory=list)


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
        """True/False for a gated claim, None when nothing adjudicated it."""
        if self.status is None:
            return None
        return self.status is GateStatus.PASS


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
        for r in results:
            if r.status is not GateStatus.PASS:
                return r
        return results[0]

    def run_pass(
        self,
        p: Pass,
        candidates: list[Candidate],
        proposed_claims: list[Claim],
    ) -> PassRecord:
        rec = PassRecord(p.id, len(proposed_claims), 0, 0, 0)

        for claim in proposed_claims:
            if claim.source_seat:
                self.detections_by_seat.setdefault(claim.source_seat, set()).add(claim.id)

            if claim.id in self._seen_claims:
                continue  # already adjudicated in an earlier pass
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
                rec.auto_accepted += 1
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
                        rec.eliminated_candidates.append(cand.id)

        self.history.append(rec)
        return rec

    # -- sequential, blinded execution --------------------------------------

    def run_sequential(
        self,
        artifact: str,
        candidates: list[Candidate],
        runner: BlindedSeatRunner,
        passes: Sequence[Pass] | None = None,
        audit: Any = None,
    ) -> list[SequentialPassResult]:
        """
        Run the five passes ONE AT A TIME against a single artifact.

        Each pass: every seat is prompted in isolation via build_blinded_prompt
        (see BLINDING_CONTRACT), the claims that come back are gated
        mechanically, and the seats' disagreement is measured and recorded.

        No seat is shown the previous pass's claims, verdicts, eliminations, or
        the other seats' answers. The passes are sequential in TIME only; they
        are independent in INFORMATION. That is deliberate -- a relay where
        pass k+1 reads pass k's conclusions is the topology this module exists
        to avoid.

        Returns one SequentialPassResult per pass, in order.
        """
        chosen = list(passes) if passes is not None else list(self.passes)
        results: list[SequentialPassResult] = []

        # SOP 8.5: every run writes an audit record. The artifact is committed
        # by digest before any seat sees it, so the log proves WHICH artifact
        # was adjudicated without copying its contents into the record.
        if audit is not None:
            audit.record_artifact(artifact)

        for p in chosen:
            responses = runner.run(p, artifact)
            divergence = measure_divergence(p, responses)
            self.divergence_by_pass[p.id] = divergence

            claims: list[Claim] = []
            for r in responses:
                claims.extend(r.claims)

            record = self.run_pass(p, candidates, claims)
            result = SequentialPassResult(p.id, p.name, record, divergence, responses)
            results.append(result)
            if audit is not None:
                audit.record_pass(result)

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
