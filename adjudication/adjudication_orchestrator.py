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
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence


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
    warrant: Optional[str] = None   # expression, DOI, test command, schema...
    source_pass: Optional[str] = None
    source_seat: Optional[str] = None


@dataclass
class Candidate:
    id: str
    content: str
    claims: List[Claim] = field(default_factory=list)
    eliminated: bool = False
    elimination_reason: Optional[str] = None
    confidence: Optional[float] = None


# ===========================================================================
# 2. DETERMINISTIC GATES — the automated verification bottleneck
# ===========================================================================

class GateStatus(str, Enum):
    PASS = "pass"
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


_SAFE_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _safe_eval(node):
    """Evaluate an arithmetic AST without exec/eval on arbitrary code."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.operand))
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
        try:
            expr, claimed = claim.warrant.rsplit("=", 1)
            actual = _safe_eval(ast.parse(expr.strip(), mode="eval"))
            expected = float(claimed.strip())
        except Exception as exc:
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
        ident = claim.warrant.strip()
        if not (self._DOI.match(ident) or ident.startswith("http")):
            return GateResult(self.name, GateStatus.FAIL, "malformed identifier")
        try:
            ok = self.resolver_fn(ident)
        except Exception as exc:
            return GateResult(self.name, GateStatus.FAIL, f"resolver error: {exc}")
        return GateResult(
            self.name,
            GateStatus.PASS if ok else GateStatus.FAIL,
            "resolved" if ok else "did not resolve",
        )


class TestExecutionGate:
    """Runs the test command that a code claim asserts will pass."""
    name = "test_execution"

    def __init__(self, test_runner_fn: Callable[[str], bool]):
        self.test_runner_fn = test_runner_fn

    def applies_to(self, claim: Claim) -> bool:
        return claim.kind is ClaimKind.CODE_BEHAVIOR and bool(claim.warrant)

    def check(self, claim: Claim) -> GateResult:
        try:
            ok = self.test_runner_fn(claim.warrant)
        except Exception as exc:
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
        try:
            payload = json.loads(claim.warrant)
        except Exception as exc:
            return GateResult(self.name, GateStatus.FAIL, f"invalid JSON: {exc}")
        missing = [k for k in self.required_keys if k not in payload]
        if missing:
            return GateResult(self.name, GateStatus.FAIL, f"missing keys: {missing}")
        return GateResult(self.name, GateStatus.PASS, "schema valid")


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
        "Critical Skills Thinking + TRIZ + Quality Zero Defects",
        "Surface the contradictions, resolve them with TRIZ separation "
        "principles, then run the zero-defects checklist against what remains.",
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
    claims: List["Claim"] = field(default_factory=list)
    error: Optional[str] = None


def content_claim_id(kind: ClaimKind, warrant: Optional[str], text: str) -> str:
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


def line_claim_extractor(raw: str, seat_id: str, pass_id: str) -> List["Claim"]:
    """
    Reference extractor for the documented output format.

    FAIL-CLOSED: a line that announces itself as a CLAIM but does not parse,
    or names a kind that does not exist, becomes a JUDGMENT claim with no
    warrant. JUDGMENT has no applicable gate, so it escalates to a human. A
    malformed claim is never silently dropped -- dropping it would let a model
    smuggle an unverified assertion past the gates by writing it badly.
    """
    claims: List[Claim] = []
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

    def __init__(self, seat_fns: Dict[str, Callable[[str], str]], extractor=line_claim_extractor):
        if not seat_fns:
            raise ValueError("at least one seat is required")
        self.seat_fns = dict(seat_fns)
        self.extractor = extractor
        self.prompt_log: List[SeatPrompt] = []

    def run(self, p: Pass, artifact: str) -> List[SeatResponse]:
        out: List[SeatResponse] = []
        for seat_id, fn in self.seat_fns.items():
            prompt = build_blinded_prompt(p, seat_id, artifact)
            self.prompt_log.append(prompt)
            try:
                raw = fn(prompt.render())
            except Exception as exc:
                # Fail closed: a seat that errors contributes no claims, and
                # the failure is recorded rather than silently swallowed.
                out.append(SeatResponse(seat_id, p.id, "", [], error=str(exc)))
                continue
            out.append(SeatResponse(seat_id, p.id, raw, self.extractor(raw, seat_id, p.id)))
        return out


# ---------------------------------------------------------------------------
# Divergence: disagreement is the expected state, not a failure
# ---------------------------------------------------------------------------

@dataclass
class PassDivergence:
    pass_id: str
    pass_name: str
    n_seats: int
    seats_responding: List[str]
    seats_errored: List[str]
    distinct_claim_sets: int
    mean_pairwise_jaccard: float
    unanimous: bool
    all_seats_silent: bool = False
    collapse_warning: Optional[str] = None


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
    record: "PassRecord"
    divergence: PassDivergence
    responses: List[SeatResponse] = field(default_factory=list)


# ===========================================================================
# 4. CONVERGENCE AND STOPPING
# ===========================================================================

def fit_decay(yields: Sequence[float]) -> Optional[tuple]:
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
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    intercept = my - slope * mx
    return math.exp(intercept), -slope


def residual_estimate(yields: Sequence[float]) -> Optional[float]:
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


def chao1_lower_bound(detections_by_seat: Dict[str, set]) -> Dict[str, float]:
    """
    Capture-recapture lower bound on errors NO seat caught.

    A high singleton fraction is exactly what 'each seat caught what others
    missed' feels like from inside, AND is the signal that more errors remain.
    Positive error correlation biases this DOWNWARD: it is a LOWER BOUND.
    """
    counts = Counter()
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
    eliminated_candidates: List[str] = field(default_factory=list)


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
    ):
        self.gates = list(gates)
        self.passes = list(passes)
        self.max_candidates_at_stop = max_candidates_at_stop
        self.residual_tolerance = residual_tolerance

        self.escalation_queue: List[Claim] = []
        self.history: List[PassRecord] = []
        self.detections_by_seat: Dict[str, set] = {}
        self._seen_claims: set = set()
        self.divergence_by_pass: Dict[str, PassDivergence] = {}

    # -- verification -------------------------------------------------------

    def _route(self, claim: Claim) -> Optional[GateResult]:
        for gate in self.gates:
            if gate.applies_to(claim):
                return gate.check(claim)
        return None  # no mechanical warrant -> escalate

    def run_pass(
        self,
        p: Pass,
        candidates: List[Candidate],
        proposed_claims: List[Claim],
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
                continue

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
        candidates: List[Candidate],
        runner: "BlindedSeatRunner",
        passes: Optional[Sequence[Pass]] = None,
    ) -> List["SequentialPassResult"]:
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
        results: List[SequentialPassResult] = []

        for p in chosen:
            responses = runner.run(p, artifact)
            divergence = measure_divergence(p, responses)
            self.divergence_by_pass[p.id] = divergence

            claims: List[Claim] = []
            for r in responses:
                claims.extend(r.claims)

            record = self.run_pass(p, candidates, claims)
            results.append(SequentialPassResult(p.id, p.name, record, divergence, responses))

        return results

    # -- convergence --------------------------------------------------------

    def survivors(self, candidates: List[Candidate]) -> List[Candidate]:
        return [c for c in candidates if not c.eliminated]

    def should_stop(self, candidates: List[Candidate]) -> Dict[str, Any]:
        yields = [float(r.auto_rejected + r.auto_accepted) for r in self.history]
        residual = residual_estimate(yields)
        alive = len(self.survivors(candidates))

        reasons = []
        if alive <= self.max_candidates_at_stop:
            reasons.append(f"candidate set reduced to {alive}")
        if residual is not None and residual < self.residual_tolerance:
            reasons.append(f"extrapolated residual {residual:.2f} < {self.residual_tolerance}")

        return {
            "stop": bool(reasons),
            "reasons": reasons,
            "surviving_candidates": alive,
            "extrapolated_residual": residual,
            "escalations_pending": len(self.escalation_queue),
            "capture_recapture": chao1_lower_bound(self.detections_by_seat)
            if self.detections_by_seat else None,
            "WARNING": (
                "Pending escalations are claims with NO mechanical warrant. "
                "Committing while the queue is non-empty converts this run into "
                "the independent topology (17.2x error amplification)."
            ) if self.escalation_queue else None,
        }

    def report(self) -> Dict[str, Any]:
        return {
            "passes": [vars(r) for r in self.history],
            "divergence_by_pass": {
                pid: {
                    k: v for k, v in vars(d).items()
                } for pid, d in self.divergence_by_pass.items()
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

    gates = [
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
