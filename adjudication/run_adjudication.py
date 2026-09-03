"""
run_adjudication.py
===================
The entry point. Runs the five passes ONE AT A TIME against one artifact and
returns the process-of-elimination answer, with every hole it could not close
named explicitly.

WHAT THIS DOES THAT THE LIBRARY DID NOT
---------------------------------------
Every module here was reachable only from a demo block with hardcoded data.
This is the command: point it at an artifact and a candidate set, and it runs
pass 1 through pass 5 in order, gates every claim mechanically, eliminates
candidates on failed gates, writes the audit chain, and reports what survived.

THE ANSWER IS WHAT SURVIVES, NOT WHAT SCORED HIGHEST. No candidate is ever
selected, ranked, or preferred. Candidates are only ever REMOVED, and only by a
gate that failed on an eliminative pass. If two survive, the run says two
survived; it does not break the tie. A tie broken by anything other than
evidence is the vote this architecture exists to avoid.

HOLES ARE PART OF THE ANSWER, NOT AN APPENDIX. A run that eliminates four of
five candidates while escalating thirty claims nobody adjudicated has not
found the answer -- it has found a shortlist and a pile of unfinished work.
Every hole below carries what would close it, because a hole an operator
cannot act on is just a disclaimer.

BLINDING IS NOT AFFECTED BY THIS FILE. Seats are prompted through
BlindedSeatRunner, which builds each prompt from the artifact and the pass lens
alone. The console report is written for the human running the tool. If that
human is also seat 5 -- the conflict PANEL_OF_FIVE documents -- reading this
report breaks their blinding, and seat 5 must be a separate session.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from adjudication_orchestrator import (
    DEFAULT_PASSES,
    PANEL_OF_FIVE,
    PANEL_OF_FIVE_EXTERNAL,
    ArithmeticGate,
    BlindedSeatRunner,
    Candidate,
    Claim,
    ClaimKind,
    Gate,
    GateStatus,
    MissingSeatCredential,
    Orchestrator,
    Pass,
    SchemaGate,
    SequentialPassResult,
    UnitGate,
    content_claim_id,
    load_panel,
)
from audit_log import AuditLog, DurableAuditLog, digest
from correctness_matrix import diagnose_run
from cost_ledger import CeilingReached, CostLedger, rates_from_config
from seat_adapter import SeatError, build_seat_callables
from seat_conduct import ConductLedger
from seat_profiles import ProfileConfigError, describe, load_profiles


class CandidateFileError(ValueError):
    """The candidate file is not something this run can proceed from."""


@dataclass(frozen=True)
class Hole:
    """Something this run could not close, and what would close it."""
    kind: str
    detail: str
    remedy: str


@dataclass
class AdjudicationAnswer:
    artifact_digest: str
    passes: list[SequentialPassResult]
    survivors: list[Candidate]
    eliminated: list[Candidate]
    stop: dict[str, Any]
    diagnosis: dict[str, Any]
    holes: list[Hole] = field(default_factory=list)
    audit_head: str | None = None
    audit_path: str | None = None
    conduct: Any = None
    """ConductLedger: which seat asserted what that a gate ruled false."""
    escalated: list[Claim] = field(default_factory=list)
    """Claims that reached no applicable gate. The SOP makes an empty queue a
    precondition for commit, so the run has to hand them back in a form an
    operator can actually answer."""
    claim_coverage: dict[str, tuple[int, int]] = field(default_factory=dict)
    """{candidate_id: (claims tested, claims carried)}.

    A survivor with 1 of 6 claims tested survived by not being looked at,
    which is a different fact from surviving scrutiny. Printing the two
    identically is how run-003 reported three survivors when only one had
    actually been examined.
    """

    @property
    def resolved(self) -> bool:
        """Exactly one candidate survives AND nothing is outstanding.

        Both halves are required. One survivor with an unadjudicated queue is
        a leading candidate, not an answer, and calling it one is how a
        shortlist gets shipped as a conclusion.
        """
        return len(self.survivors) == 1 and not self.holes



# ---------------------------------------------------------------------------
# transport
# ---------------------------------------------------------------------------

def urllib_transport(
    method: str, url: str, headers: Mapping[str, str], body: bytes, timeout: float
) -> tuple[int, bytes]:
    """
    The one place this tool touches the network. Standard library only.

    HttpSeat takes the transport as an argument precisely so the 400+ tests
    can drive it without a socket; this is the production implementation and
    nothing else in the codebase performs I/O.

    A non-2xx response is RETURNED with its body, not raised: HttpSeat decides
    what is retryable, and it needs the status to do that. Only a transport
    failure -- DNS, TLS, connection, timeout -- raises, and HttpSeat treats
    that as a failed attempt.
    """
    import urllib.error
    import urllib.request

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        """Refuse every 3xx instead of following it.

        urllib follows redirects by default AND carries the request headers to
        the new location -- verified against a local server: a 302 from an
        authenticated POST arrived at another origin, over plaintext HTTP,
        still carrying Authorization and x-api-key. That is a credential leak
        to whatever the Location header names, and constraint 4 says a key
        never crosses a plaintext connection.

        A redirect from a vendor API endpoint is a configuration error, not a
        thing to follow: the correct endpoint does not redirect. Raising here
        turns it into a visible seat failure with the status attached.
        """

        def redirect_request(
            self, req: Any, fp: Any, code: int, msg: str, headers: Any,
            newurl: str,
        ) -> None:
            raise urllib.error.HTTPError(
                req.full_url, code,
                f"refusing to follow a {code} redirect to {newurl!r}: the "
                f"request carries a credential and urllib would forward it to "
                f"the new origin. Fix the endpoint in profiles.json.",
                headers, fp,
            )

    # DEFENCE IN DEPTH against B310. urlopen honours file:// and ftp://, so a
    # profile whose endpoint slipped past validation would read a local file
    # and hand its bytes back as a seat's answer. ProviderProfile already
    # refuses a non-https endpoint and so does validate_config, but this is the
    # call that would actually do the damage, so it checks for itself rather
    # than trusting two layers above it.
    if not url.startswith("https://"):
        raise ValueError(
            f"refusing a non-https endpoint: {url!r}. A credential must never "
            f"cross a plaintext connection, and urlopen would honour file:// "
            f"or ftp:// here."
        )

    req = urllib.request.Request(url, data=body, headers=dict(headers), method=method)
    try:
        # The https scheme is enforced immediately above; nosec is on the next
        # line because bandit reads everything after it as test ids.
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(req, timeout=timeout) as resp:  # nosec B310
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


# ---------------------------------------------------------------------------
# candidates
# ---------------------------------------------------------------------------

def parse_candidates(raw: Any) -> list[Candidate]:
    """
    Build candidates from the documented JSON shape:

        [{"id": "c1",
          "content": "the answer this candidate asserts",
          "claims": [{"kind": "arithmetic", "text": "...", "warrant": "2+2=4"}]}]

    A candidate's claims are the assertions it stands on. Claim ids are
    content-addressed, so a claim a SEAT proposes and a claim a CANDIDATE
    carries collide exactly when they are the same proposition -- which is
    what lets a failed gate eliminate the candidate that depends on it.
    """
    if not isinstance(raw, list):
        raise CandidateFileError(
            f"expected a JSON list of candidates, got {type(raw).__name__}"
        )
    out: list[Candidate] = []
    seen: set[str] = set()
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise CandidateFileError(f"candidate {i} is {type(item).__name__}, not an object")
        cid = item.get("id")
        if not isinstance(cid, str) or not cid.strip():
            raise CandidateFileError(f"candidate {i} has no usable 'id'")
        if cid in seen:
            raise CandidateFileError(
                f"duplicate candidate id {cid!r}: eliminating one would silently "
                "eliminate the other"
            )
        seen.add(cid)
        claims: list[Claim] = []
        for j, c in enumerate(item.get("claims", []) or []):
            if not isinstance(c, dict):
                raise CandidateFileError(f"candidate {cid!r} claim {j} is not an object")
            kind_raw = str(c.get("kind", "judgment")).lower()
            try:
                kind = ClaimKind(kind_raw)
            except ValueError as exc:
                raise CandidateFileError(
                    f"candidate {cid!r} claim {j} has unknown kind {kind_raw!r}; "
                    f"valid kinds are {', '.join(k.value for k in ClaimKind)}"
                ) from exc
            warrant = c.get("warrant")
            text = str(c.get("text", ""))
            supports = c.get("supports") or []
            if not isinstance(supports, list) or any(
                    not isinstance(x, str) for x in supports):
                raise CandidateFileError(
                    f"candidate {cid!r} claim {j}: 'supports' must be a list of "
                    f"claim ids"
                )
            claims.append(
                Claim(content_claim_id(kind, warrant, text), text, kind, warrant,
                      supports=list(supports))
            )
        out.append(Candidate(cid, str(item.get("content", "")), claims))
    return out


def load_candidates(path: str) -> list[Candidate]:
    with open(path, encoding="utf-8") as fh:
        try:
            raw = json.load(fh)
        except json.JSONDecodeError as exc:
            raise CandidateFileError(f"{path} is not valid JSON: {exc}") from exc
    return parse_candidates(raw)


class AdjudicationFileError(ValueError):
    """The answered escalation queue is not in a shape this will act on."""


def parse_adjudications(raw: Any) -> dict[str, bool]:
    """Read an answered escalation queue, in the shape --export-queue writes.

    IT COULD NOT READ ITS OWN OUTPUT. --export-queue emits
    {"_README": [...], "claims": [{"id": ..., "verdict": null}, ...]} and the
    reader expected a flat {id: value} mapping, so feeding the exported file
    straight back -- which the file's own instructions tell the operator to do
    -- raised AdjudicationConflict on the key "_README".

    It also applied bool() to every value, which is wrong in both directions:
    null became False, silently answering a question the operator had left
    open, and the string "false" became True, because every non-empty string
    is truthy. A human verdict is the one input here that no gate checks, so
    coercing it is the one place a typo becomes a fact.

    Only real booleans resolve a claim. null stays open, which is the honest
    state, and anything else is refused by name.
    """
    if isinstance(raw, dict) and isinstance(raw.get("claims"), list):
        entries = raw["claims"]           # the exported shape
    elif isinstance(raw, list):
        entries = raw
    elif isinstance(raw, dict):
        # A flat {id: verdict} mapping, hand-written. Underscore keys are
        # comments, matching every other config file in this tool.
        entries = [{"id": k, "verdict": v} for k, v in raw.items()
                   if not str(k).startswith("_")]
    else:
        raise AdjudicationFileError(
            f"expected the file written by --export-queue, or a flat "
            f"{{id: true|false}} object; got {type(raw).__name__}")

    out: dict[str, bool] = {}
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise AdjudicationFileError(f"entry {i} is not an object")
        cid = entry.get("id")
        if not isinstance(cid, str) or not cid.strip():
            raise AdjudicationFileError(f"entry {i} has no usable 'id'")
        verdict = entry.get("verdict")
        if verdict is None:
            continue                      # unanswered; stays in the queue
        if not isinstance(verdict, bool):
            raise AdjudicationFileError(
                f"claim {cid!r} has verdict {verdict!r}. Use true or false, "
                f"not a string or a number: bool(\"false\") is True, and a "
                f"human verdict is the one input here that no gate checks."
            )
        out[cid] = verdict
    return out


# ---------------------------------------------------------------------------
# holes
# ---------------------------------------------------------------------------

def collect_holes(
    passes: Sequence[SequentialPassResult],
    orch: Orchestrator,
    survivors: Sequence[Candidate],
    candidates: Sequence[Candidate],
    stop: Mapping[str, Any],
    diagnosis: Mapping[str, Any],
) -> list[Hole]:
    """Everything this run could not close. Ordered most-blocking first."""
    holes: list[Hole] = []

    if not candidates:
        holes.append(Hole(
            "no candidates",
            "nothing was supplied to eliminate, so the run adjudicated claims "
            "without narrowing to an answer",
            "supply a candidate set with --candidates",
        ))
    elif not survivors:
        holes.append(Hole(
            "every candidate eliminated",
            f"all {len(candidates)} candidate(s) failed a gate; the true answer "
            "was not among them, or a gate is wrong",
            "review the elimination reasons below; if a gate misfired, fix the "
            "gate rather than reinstating the candidate",
        ))
    elif len(survivors) > 1:
        holes.append(Hole(
            "not narrowed to one",
            f"{len(survivors)} candidates survive: "
            f"{', '.join(c.id for c in survivors)}",
            "no tie is broken here by design; supply claims that distinguish "
            "them, or accept the set as the honest result",
        ))

    # BLOCKED CLAIMS ARE UNFINISHED WORK AND WERE NOT COUNTED AS ANY.
    #
    # A blocked check did not happen. It is not a pass, not a failure, and not
    # an escalation, so it appeared in no hole and in no stop condition -- a
    # run whose only claim was BLOCKED reported resolved=True and printed no
    # outstanding work. The whole reason BLOCKED exists as its own state is
    # that the check is still owed; leaving it out of the holes list is the
    # same as pretending it was performed.
    blocked = [cid for cid, v in orch.verdicts.items()
               if v.status is GateStatus.BLOCKED]
    if blocked:
        gates = sorted({orch.verdicts[c].gate or "?" for c in blocked})
        holes.append(Hole(
            "checks that could not run",
            f"{len(blocked)} claim(s) were BLOCKED -- a paywall, a timeout, a "
            f"rate limit, or an unreachable service (gate(s): "
            f"{', '.join(gates)}). These are neither verified nor refuted, and "
            f"the run is not complete while any remain",
            "restore access and re-run those checks, or adjudicate them by "
            "hand; do not read a blocked check as a finding either way",
        ))

    queued = len(orch.escalation_queue)
    if queued:
        kinds = sorted({c.kind.value for c in orch.escalation_queue})
        holes.append(Hole(
            "unadjudicated claims",
            f"{queued} claim(s) reached no applicable gate and escalated "
            f"(kinds: {', '.join(kinds)}); SOP 9.1 step 8 makes an empty queue "
            "a precondition for commit",
            "adjudicate them, then re-run with --adjudications to fold the "
            "decisions into the diagnosis",
        ))

    for res in passes:
        div = res.divergence
        if div.seats_errored:
            holes.append(Hole(
                "seat error",
                f"{res.pass_name}: seat(s) {', '.join(div.seats_errored)} failed; "
                "every claim first adjudicated in this pass is excluded from the "
                "independence diagnosis",
                "fix the seat and re-run that pass; its silence cannot be read "
                "as agreement or as a miss",
            ))
        if div.collapse_warning:
            holes.append(Hole(
                "collapse warning",
                f"{res.pass_name}: {div.collapse_warning}",
                "the seats agreed completely, which is what a shared failure "
                "mode looks like; change seat composition and re-run this pass",
            ))

    if not diagnosis.get("measurable", False):
        holes.append(Hole(
            "convergence not measurable",
            "; ".join(diagnosis.get("blockers", [])) or "no diagnosis available",
            "the run cannot tell eliminative convergence from collapse; treat "
            "the surviving answer as unverified until it can",
        ))

    for blocker in stop.get("blockers", []):
        holes.append(Hole("stop rule", str(blocker),
                          "the run is not complete by SOP 6.3 while this holds"))

    return holes


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------

def run_adjudication(
    artifact: str,
    candidates: Sequence[Candidate],
    seat_fns: Mapping[str, Callable[[str], str]],
    gates: Sequence[Gate] | None = None,
    passes: Sequence[Pass] | None = None,
    audit_path: str | None = None,
    run_id: str = "adjudication",
    adjudications: Mapping[str, bool] | None = None,
    total_seeded: int | None = None,
) -> AdjudicationAnswer:
    """
    Run the five passes one at a time and return what survived.

    Nothing here selects an answer. The passes run in order, the gates rule,
    candidates are removed, and whatever is left is the result -- including
    'none' and including 'more than one'.
    """
    chosen = list(passes) if passes is not None else list(DEFAULT_PASSES)
    orch = Orchestrator(list(gates) if gates is not None else _default_gates())
    runner = BlindedSeatRunner(dict(seat_fns))

    audit: Any
    audit = DurableAuditLog(audit_path, run_id) if audit_path else AuditLog(run_id)

    cands = list(candidates)
    # Rule on what the candidates themselves assert BEFORE any seat is asked.
    # Without this a candidate standing on a falsehood no seat happened to
    # raise is never examined, and survives looking exactly like one that was.
    intake_ruled = orch.gate_candidate_claims(cands)
    if intake_ruled:
        audit.append("intake", {"claims_ruled": len(intake_ruled)})
    results = orch.run_sequential(artifact, cands, runner, passes=chosen, audit=audit)

    conduct = ConductLedger.from_run(orch.detections_by_seat, orch.verdicts,
                                     all_seat_ids=list(seat_fns))
    if conduct.total_findings():
        audit.append("seat_conduct", conduct.as_payload())

    stop = orch.should_stop(cands)
    diagnosis = diagnose_run(results, orch.verdicts, adjudications, total_seeded)
    survivors = orch.survivors(cands)
    eliminated = [c for c in cands if c.eliminated]

    return AdjudicationAnswer(
        artifact_digest=digest(artifact),
        passes=results,
        survivors=survivors,
        eliminated=eliminated,
        stop=stop,
        diagnosis=diagnosis,
        holes=collect_holes(results, orch, survivors, cands, stop, diagnosis),
        audit_head=audit.head,
        audit_path=audit_path,
        claim_coverage={c.id: orch.claim_coverage(c) for c in cands},
        escalated=list(orch.escalation_queue),
        conduct=conduct,
    )


def _quote_gate() -> Gate:
    from quote_gate import QuoteVerificationGate
    return QuoteVerificationGate()


def _citation_field_gate() -> Gate:
    from citation_gate import CitationFieldMatchGate
    return CitationFieldMatchGate()


def _approved_test_gate() -> Gate:
    from approved_test_gate import ApprovedTestGate
    return ApprovedTestGate()


_SELECTABLE_GATES: dict[str, Callable[[], Gate]] = {
    "arithmetic": ArithmeticGate,
    "schema": SchemaGate,
    "unit": UnitGate,
    "quote": _quote_gate,
    "citation_fields": _citation_field_gate,
    "code_behavior": _approved_test_gate,
}
"""Gates an operator may switch on from the command line.

CitationResolutionGate and TestExecutionGate are deliberately absent: each
needs a callable the operator must supply -- a real resolver, a real test
runner -- and there is no honest default for either. SourceAdmissibilityGate
is absent because alone it answers "is this the right KIND of source" and
auto-accepted an invented DOI; it is safe only conjoined with a resolver.
Offering any of them here as a name with nothing behind it would be the
fail-open this module exists to prevent.
"""


def gates_from_names(spec: str) -> list[Gate]:
    """Build the gate list named on the command line. Raises on an unknown
    name rather than silently running with fewer gates than the operator
    asked for -- a quietly missing gate is a claim quietly unchecked."""
    names = [n.strip().lower() for n in spec.split(",") if n.strip()]
    if not names:
        raise ValueError("--gates was given no gate names")
    unknown = [n for n in names if n not in _SELECTABLE_GATES]
    if unknown:
        raise ValueError(
            f"unknown gate(s): {', '.join(unknown)}. "
            f"Available: {', '.join(sorted(_SELECTABLE_GATES))}"
        )
    return [_SELECTABLE_GATES[n]() for n in names]


def night_gates() -> list[Gate]:
    """The gates the guided night run uses.

    THE DEFAULTS LEFT CITATIONS UNCHECKED. _default_gates carries arithmetic,
    schema, unit and quote only, so a citation claim on the console night path
    -- the path an operator actually uses -- reached no citation gate at all
    and escalated with no gate applied. The tool advertises DOI resolution and
    citation-field matching as central to its value, and the paid run did
    neither unless a different caller supplied them.

    They are added here rather than to _default_gates because they make
    network requests to Crossref and doi.org. Those are free and take no
    credential, but a default that quietly reaches the network is not a
    default: this is the mode where an operator has already accepted that
    lookups happen, and the console prints the gate list before asking them to
    spend.
    """
    from adjudication_orchestrator import CitationResolutionGate
    from citation_gate import CitationFieldMatchGate
    from doi_resolver import build_resolver

    return [
        *_default_gates(),
        CitationResolutionGate(build_resolver()),
        CitationFieldMatchGate(),
    ]


def _default_gates() -> list[Gate]:
    """Gates that are safe with NO operator configuration. Deliberately few.

    CitationResolutionGate and TestExecutionGate are absent because each takes
    a callable the operator must supply, and a default returning True is the
    permissive resolver SOP 8.3 names as the most common way this build fails.

    SourceAdmissibilityGate is absent for a subtler reason, and it was in this
    list until a test caught it. That gate answers "is this the right KIND of
    source"; it never answers "does this source EXIST". Alone, it auto-accepted
    the invented DOI 10.1038/s41586-000-0000-0 as "admissible: peer_reviewed" --
    a seat could fabricate any well-formed identifier and be believed. It is
    safe only CONJOINED with a resolver, which is exactly why _route requires
    every applicable gate to pass; shipping it as the sole citation gate
    reintroduced the single-gate fail-open that routing was built to close.

    So a citation claim escalates by default and surfaces as a hole. Supply
    both gates together via the `gates` argument once you have a resolver.
    """
    from quote_gate import QuoteVerificationGate
    return [ArithmeticGate(), SchemaGate(), UnitGate(),
            QuoteVerificationGate()]



DEFAULT_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def load_env_file(path: str | None = None) -> str:
    """
    Read .env into the process environment, and SAY what happened.

    python-dotenv was a pinned dependency that nothing ever called, so
    load_panel read os.environ and a filled-in .env was silently ignored: the
    operator got "credential missing" for a file sitting right there with the
    key in it. The fix is this function; the reason it reports rather than
    returning None is that "which .env did you actually read" is the first
    question anyone asks when a key does not take.

    A real environment variable WINS over the file. A shell export or a CI
    secret is deliberate and current; a .env line may be a stale leftover, and
    silently overriding the deliberate one with the stale one is the wrong way
    round.
    """
    target = path or DEFAULT_ENV_FILE
    if not os.path.exists(target):
        return f"no .env found at {target} (using the shell environment only)"
    try:
        from dotenv import load_dotenv
    except ImportError:
        return (f"found {target} but python-dotenv is not installed, so it was "
                f"NOT read. Run: pip install -r requirements.txt")
    load_dotenv(target, override=False)
    return f"loaded {target}"


DEFAULT_RATES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "rates.json")
DAY_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              ".spend-by-day.json")


def build_ledger(per_run: float | None, per_stage: float | None,
                 per_day: float | None,
                 rates_path: str | None = None) -> CostLedger | None:
    """A ledger, or None when no ceiling was asked for.

    Returns None rather than an unenforcing ledger when every ceiling is
    unset: a ledger that bounds nothing but appears in the report reads as
    protection that is not there.
    """
    # EVERY SUPPLIED CEILING MUST BE A REAL LIMIT.
    #
    # NaN fails every comparison, so `spent + would_add > nan` is False
    # forever and a NaN ceiling authorises everything while printing back a
    # figure that looks like a limit. Infinity is a limit that cannot be
    # reached. Zero or negative is not a budget. All three were accepted.
    for label, value in (("--max-cost", per_run),
                         ("--max-cost-per-stage", per_stage),
                         ("--max-cost-per-day", per_day)):
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(float(value)) or float(value) <= 0:
            raise ValueError(
                f"{label}={value!r} is not a finite positive number of "
                f"dollars. A ceiling that cannot be reached is not a ceiling, "
                f"and NaN compares False against every total, so it would "
                f"authorise every call while looking like a limit."
            )
    if per_run is None and per_stage is None and per_day is None:
        return None
    # Resolved at CALL time, not bound at definition time. A module-level
    # default captured in the signature cannot be redirected afterwards, which
    # makes the rates file impossible to point elsewhere for a test or for an
    # operator keeping prices outside the repository.
    rates_path = rates_path or DEFAULT_RATES_FILE
    if not os.path.exists(rates_path):
        raise ValueError(
            f"a ceiling was requested but {rates_path} does not exist. A limit "
            f"computed from absent prices bounds nothing."
        )
    with open(rates_path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return CostLedger(rates=rates_from_config(raw), per_run=per_run,
                      per_stage=per_stage, per_day=per_day,
                      day_state_path=DAY_STATE_FILE)


def live_seats(
    profiles_path: str,
    env: Mapping[str, str] | None = None,
    transport: Any = None,
    specs: Any = None,
    **kwargs: Any,
) -> dict[str, Callable[[str], str]]:
    """
    The real panel: credentials from the environment, request shapes from the
    profile file, and one callable per external seat.

    FAILS CLOSED at each step and says which one. A missing credential, a
    malformed profile, and a seat with no profile are three different
    operator errors with three different fixes, and collapsing them into
    "could not start" costs an hour.

    Defaults to PANEL_OF_FIVE_EXTERNAL: all five seats reached by API key,
    including Claude. That is the recommended shape, because it removes the
    in-process hazard rather than documenting it -- a seat driven by the same
    session as the orchestrator can see gate verdicts, is therefore not blind,
    and its errors correlate with the adjudication itself.

    Pass specs=PANEL_OF_FIVE for the in-process arrangement, where seat 5 is
    NOT returned here and the caller must supply it from a genuinely separate
    session.
    """
    panel = load_panel(specs=specs or PANEL_OF_FIVE_EXTERNAL,
                       env=dict(env) if env is not None else None)
    profiles = load_profiles(profiles_path)
    # WIRE THE BACKOFF. RetryPolicy carries backoff_seconds, but HttpSeat
    # only sleeps if a sleeper is injected -- seat_adapter deliberately never
    # reads a clock, so it stays deterministic under test. Nothing injected
    # one on the live path, so _backoff returned immediately and a 429 fired
    # all three attempts back to back with no delay: the rate limit could not
    # clear, and the seat cost three calls instead of one to arrive at the
    # same "retries exhausted". The CLI is the right place to supply real
    # time; tests keep passing their own sleeper or none.
    kwargs.setdefault("sleeper", time.sleep)
    return build_seat_callables(
        panel, profiles, transport or urllib_transport, **kwargs
    )


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def kill_provenance(answer: AdjudicationAnswer) -> dict[str, int]:
    """Split eliminations into EARNED and STRUCTURAL.

    EARNED means a gate recomputed, resolved, or parsed the claim and it did
    not hold. STRUCTURAL means the candidate went because models found it less
    persuasive.

    This architecture cannot produce a structural kill: nothing here removes a
    candidate on preference, and elimination_reason always names the gate that
    failed. The count is reported anyway, and reported as zero, because a
    reader cannot otherwise tell "the design forbids it" from "it did not
    happen this time" -- and if a future change ever introduces one, this
    number moves and someone notices.

    ZERO EARNED KILLS IS THE ALARM. A run that narrows the field without a
    single mechanical refutation has produced agreement, not elimination.
    Convergence is what this architecture yields whether or not the answer is
    right, so a clean-looking answer with nothing earned behind it is the case
    most likely to be believed and least likely to deserve it.
    """
    earned = structural = 0
    for c in answer.eliminated:
        # Read the field, do not re-derive it from the reason text. Inferring
        # provenance from wording is how the quote cascade got reported as
        # consensus.
        if c.elimination_kind == "earned":
            earned += 1
        else:
            structural += 1
    return {"earned": earned, "structural": structural}


def verdict_header(answer: AdjudicationAnswer) -> str:
    """One line at the top saying how much the run actually established."""
    prov = kill_provenance(answer)
    if answer.eliminated and prov["earned"] == 0:
        return ("CONSENSUS ONLY -- candidates were narrowed without a single "
                "mechanical refutation")
    if not answer.eliminated:
        return ("CONSENSUS ONLY -- nothing was eliminated; no candidate was "
                "mechanically refuted")
    if answer.resolved:
        return "RESOLVED -- one candidate survives and nothing is outstanding"
    if len(answer.survivors) > 1:
        return (f"PROVISIONAL -- {len(answer.survivors)} candidates survive; "
                f"the evidence does not separate them")
    return "PROVISIONAL -- one candidate survives but holes remain"


def _cov(answer: AdjudicationAnswer, cand_id: str) -> str:
    """Claim coverage suffix for a survivor line.

    Silent when every claim was tested; loud when it was not. A survivor
    nobody examined must not read like one that withstood examination.
    """
    tested, total = answer.claim_coverage.get(cand_id, (0, 0))
    if total == 0:
        return "   [carries no claims -- nothing could test it]"
    if tested == total:
        return f"   [{tested}/{total} claims tested]"
    return (f"   [ONLY {tested}/{total} claims tested -- "
            f"{total - tested} never reached a gate]")


def render_report(answer: AdjudicationAnswer) -> str:
    L: list[str] = []
    add = L.append

    add("=" * 72)
    add("ADJUDICATION RUN")
    add(verdict_header(answer))
    add("=" * 72)
    add(f"artifact sha256 : {answer.artifact_digest}")
    if answer.audit_path:
        add(f"audit log       : {answer.audit_path}")
    add(f"audit head      : {answer.audit_head}")
    add("")

    add("-" * 72)
    add(f"PASSES, ONE AT A TIME ({len(answer.passes)})")
    add("-" * 72)
    for i, res in enumerate(answer.passes, 1):
        rec, div = res.record, res.divergence
        add(f"{i}. {res.pass_name}")
        add(f"     proposed {rec.proposed} | accepted {rec.auto_accepted} | "
            f"rejected {rec.auto_rejected} | escalated {rec.escalated}"
            + (f" | blocked {rec.blocked}" if rec.blocked else ""))
        if rec.repeats:
            # Stated explicitly, because otherwise the line above stops adding
            # up and the reader is left to guess where the difference went.
            note = f"     {rec.repeats} already ruled in an earlier pass"
            if rec.repeated_failures:
                note += (f", of which {rec.repeated_failures} had ALREADY "
                         f"BEEN REFUTED and were asserted again")
            add(note)
        if rec.eliminated_candidates:
            add(f"     eliminated: {', '.join(rec.eliminated_candidates)}")
        jac = div.mean_pairwise_jaccard
        overlap = "n/a" if jac is None else f"{jac:.2f}"
        add(f"     seat overlap {overlap}"
            + (f"  [{div.collapse_warning}]" if div.collapse_warning else ""))
        if div.seats_errored:
            add(f"     SEAT ERROR: {', '.join(div.seats_errored)}")
            # WHY, not just WHICH. Printing only the seat ids destroyed the
            # run's own evidence: a rejected parameter, a bad credential, and a
            # reply the text_path could not reach all read as "seat_1 failed",
            # and telling them apart cost a second paid run. The message comes
            # from SeatError, which is built to carry the status and the
            # provider name but never the request -- the request holds the
            # credential.
            for seat_id in div.seats_errored:
                why = div.seat_errors.get(seat_id)
                if why:
                    add(f"       {seat_id}: {why}")
    add("")

    add("-" * 72)
    add("ANSWER, BY ELIMINATION")
    add("-" * 72)
    if not answer.survivors:
        add("  NONE SURVIVED. Every candidate failed a gate.")
    elif len(answer.survivors) == 1:
        add(f"  SURVIVOR: {answer.survivors[0].id}{_cov(answer, answer.survivors[0].id)}")
        content = answer.survivors[0].content
        if content:
            add(f"    {content}")
    else:
        add(f"  {len(answer.survivors)} SURVIVE -- not narrowed to one:")
        for c in answer.survivors:
            add(f"    {c.id}{_cov(answer, c.id)}")
    for c in answer.eliminated:
        reason = c.elimination_reason or ""
        tag = ("EARNED" if c.elimination_kind == "earned"
               else "STRUCTURAL")
        add(f"  removed {c.id} [{tag}]: {reason}")
    prov = kill_provenance(answer)
    add(f"  kills: {prov['earned']} earned, {prov['structural']} structural")
    if answer.eliminated and prov["earned"] == 0:
        add("  NOTHING WAS EARNED. This run produced consensus, not elimination.")
    add("")

    if answer.conduct is not None and answer.conduct.seats:
        for ln in answer.conduct.render():
            add(ln)
        add("")

    add("-" * 72)
    add("CONVERGENCE: ELIMINATIVE, OR COLLAPSE?")
    add("-" * 72)
    d = answer.diagnosis
    add(f"  coverage: {d.get('coverage_summary', 'n/a')}")
    if d.get("measurable"):
        add(f"  {d.get('reading')}")
        cap = d.get("independence_gap", {}).get("capture_fraction")
        # NaN means the independence line offered no gain to capture, so
        # there is no fraction to report. Printing "captured nan" invites it
        # to be read as a low number rather than as no measurement.
        if cap is not None and not math.isnan(cap):
            add(f"  captured {cap:.2f} of the theoretical gain over the best "
                "single seat")
    else:
        for b in d.get("blockers", []):
            add(f"  NOT MEASURABLE: {b}")
    add("")

    add("-" * 72)
    add(f"HOLES ({len(answer.holes)}) -- what this run could NOT close")
    add("-" * 72)
    if not answer.holes:
        add("  none")
    for h in answer.holes:
        add(f"  [{h.kind}] {h.detail}")
        add(f"      -> {h.remedy}")
    add("")

    verdict = ("RESOLVED" if answer.resolved
               else "NOT RESOLVED -- see holes above")
    add("=" * 72)
    add(f"{verdict}")
    add("=" * 72)
    return "\n".join(L)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _demo_seats() -> dict[str, Callable[[str], str]]:
    """Three synthetic seats, so --demo runs with no credentials.

    They are scripted, not intelligent. They demonstrate the machinery end to
    end and say NOTHING about how a real model behaves.
    """
    # Field order is CLAIM | kind | WARRANT | text, exactly as
    # build_blinded_prompt tells the seats. Reversing warrant and text puts
    # prose where the gate expects an expression, and every arithmetic claim
    # is then correctly rejected for the wrong reason -- which is how this
    # demo first ran.
    a = "CLAIM | arithmetic | 2 + 2 = 4 | the total is 4"
    b = "CLAIM | arithmetic | 2 + 2 = 5 | the total is 5"
    c = "CLAIM | judgment |  | the framing is one-sided"
    return {
        "seat_1": lambda _p: f"{a}\n{c}",
        "seat_2": lambda _p: f"{a}\n{b}",
        "seat_3": lambda _p: a,
    }


def _demo_candidate(cid: str, text: str, warrant: str) -> Candidate:
    """A candidate standing on one arithmetic claim."""
    claim = Claim(content_claim_id(ClaimKind.ARITHMETIC, warrant, text),
                  text, ClaimKind.ARITHMETIC, warrant)
    return Candidate(cid, text, [claim])


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Run the blinded five-pass adjudication over one artifact."
    )
    ap.add_argument("artifact", nargs="?", help="path to the artifact to adjudicate")
    ap.add_argument("--candidates", help="path to the candidates JSON file")
    ap.add_argument("--audit", help="path to the durable audit log (JSONL)")
    ap.add_argument("--run-id", default="adjudication")
    ap.add_argument("--adjudications",
                    help="JSON file of {claim_id: true|false} for escalated claims")
    ap.add_argument("--gates", metavar="LIST",
                    help="comma-separated gates to run: arithmetic, schema, "
                         "unit. Default: all three. Citation and code_behavior "
                         "gates need a resolver and a test runner and are not "
                         "selectable here -- see CONNECTING.md")
    ap.add_argument("--max-cost", type=float, metavar="USD",
                    help="hard per-run spend ceiling. The run aborts mid-run "
                         "and writes a partial result rather than crossing it. "
                         "Checked BEFORE each call.")
    ap.add_argument("--max-cost-per-stage", type=float, metavar="USD")
    ap.add_argument("--max-cost-per-day", type=float, metavar="USD")
    ap.add_argument("--resolve-dois", action="store_true",
                    help="switch on the citation gates: every cited DOI must "
                         "actually resolve. Uses Crossref and doi.org, which "
                         "are free and take no credential -- no model is "
                         "called and nothing is billed. The resolver is probed "
                         "first and the run aborts if it is permissive.")
    ap.add_argument("--export-queue", metavar="PATH",
                    help="write the escalated claims to PATH as JSON, ready to "
                         "answer and feed back with --adjudications")
    ap.add_argument("--demo", action="store_true",
                    help="run with three scripted synthetic seats and no credentials")
    ap.add_argument("--profiles",
                    help="path to profiles.json -- runs the REAL panel")
    ap.add_argument("--check-profiles", metavar="PATH",
                    help="validate a profiles file offline and exit; spends nothing")
    ap.add_argument("--seat5", choices=("external", "in-process"),
                    default="external",
                    help="how Claude is reached. 'external' (default) gives it "
                         "its own API key so all five seats are blinded "
                         "identically; 'in-process' expects a separate session "
                         "to supply it.")
    ap.add_argument("--env", metavar="PATH",
                    help=f"path to the .env holding your keys (default: {DEFAULT_ENV_FILE})")
    args = ap.parse_args(argv)

    if args.check_profiles:
        try:
            with open(args.check_profiles, encoding="utf-8") as fh:
                cfg = json.load(fh)
        except OSError as exc:
            print(f"cannot read {args.check_profiles}: {exc}", file=sys.stderr)
            return 2
        except json.JSONDecodeError as exc:
            print(f"{args.check_profiles} is not valid JSON: {exc}", file=sys.stderr)
            return 2
        from seat_profiles import validate_config
        print(describe(cfg))
        return 0 if not validate_config(cfg) else 1

    if args.profiles and args.demo:
        print("--demo and --profiles are mutually exclusive: one runs scripted "
              "seats, the other spends real quota.", file=sys.stderr)
        return 2

    if not args.demo and not args.profiles:
        # FAIL CLOSED. A real panel needs configured seats, and this tool will
        # not invent one. seat_adapter.build_seat_callables takes the provider
        # profiles the operator supplies from vendor API documentation.
        print(
            "no seats configured.\n\n"
            "  --demo                     three scripted synthetic seats, no "
            "credentials, spends nothing\n"
            "  --check-profiles PATH      validate a profiles file offline, "
            "spends nothing\n"
            "  --profiles PATH            run the REAL five-seat panel\n\n"
            "To connect the panel:\n"
            "  1. cp .env.example .env            and fill in "
            "ADJ_SEAT_1..4_API_KEY and the model ids\n"
            "  2. cp profiles.example.json profiles.json\n"
            "  3. fill every FILL-IN from that vendor's own API reference "
            "-- never from memory\n"
            "  4. python run_adjudication.py --check-profiles profiles.json\n"
            "  5. python run_adjudication.py ARTIFACT --profiles profiles.json "
            "--candidates c.json\n\n"
            "Nothing in this codebase ships a vendor endpoint, request shape, "
            "or response path.",
            file=sys.stderr,
        )
        return 2

    artifact = "2 + 2 = 4 and the framing is neutral."
    if args.artifact:
        with open(args.artifact, encoding="utf-8") as fh:
            artifact = fh.read()

    candidates = load_candidates(args.candidates) if args.candidates else [
        _demo_candidate("c_true", "the total is 4", "2 + 2 = 4"),
        _demo_candidate("c_false", "the total is 5", "2 + 2 = 5"),
    ]

    adjudications = None
    if args.adjudications:
        with open(args.adjudications, encoding="utf-8") as fh:
            adjudications = parse_adjudications(json.load(fh))

    try:
        ledger = build_ledger(args.max_cost, args.max_cost_per_stage,
                              args.max_cost_per_day)
    except ValueError as exc:
        print(f"cost ceiling: {exc}", file=sys.stderr)
        return 2
    if ledger is not None:
        stale = ledger.stale_rates()
        if stale:
            print(f"rates unverified or stale for {', '.join(stale)}. "
                  f"A ceiling computed from unchecked prices does not bound "
                  f"anything.", file=sys.stderr)

    if args.profiles:
        # A PAID PANEL WITHOUT A LEDGER IS AN UNBOUNDED PANEL.
        #
        # build_ledger returns None when no ceiling was asked for, and the
        # real-panel path accepted that and called five vendors with nothing
        # counting. The demo has no ledger because it spends nothing; a run
        # against --profiles spends on every call.
        if ledger is None:
            print(
                "refusing to run a real panel with no spend ceiling. Pass "
                "--max-cost (and optionally --max-cost-per-stage or "
                "--max-cost-per-day). A run against --profiles calls five "
                "vendors on every pass; without a ledger nothing counts what "
                "it costs and nothing can stop it.",
                file=sys.stderr)
            return 2
        unusable = sorted(set(ledger.stale_rates()))
        if unusable:
            # WARNING WAS NOT ENOUGH. A zero price means every call is free,
            # so no ceiling can ever be crossed and the limit is decorative --
            # and the run continued past the warning. A ceiling computed from
            # a price nobody checked bounds nothing.
            print(
                f"refusing to run: the price for {', '.join(unusable)} is "
                f"missing, zero, or unverified. A ceiling computed from an "
                f"unchecked price bounds nothing. Fix rates.json and stamp "
                f"verified_on from the vendor's own page.",
                file=sys.stderr)
            return 2
        print(f"env: {load_env_file(args.env)}", file=sys.stderr)
        try:
            seat_fns = live_seats(
                args.profiles,
                specs=(PANEL_OF_FIVE if args.seat5 == "in-process"
                       else PANEL_OF_FIVE_EXTERNAL),
                ledger=ledger,
            )
        except MissingSeatCredential as exc:
            print(f"credential missing: {exc}\n"
                  f"Looked for a .env at: {args.env or DEFAULT_ENV_FILE}\n"
                  f"Put the key there (copy .env.example to .env), or export it "
                  f"in your shell. load_panel refuses to run a short panel "
                  f"because it would misstate every statistic.",
                  file=sys.stderr)
            return 2
        except ProfileConfigError as exc:
            print(f"profiles unusable:\n{exc}\n\n"
                  f"Run --check-profiles {args.profiles} to see every problem at once.",
                  file=sys.stderr)
            return 2
        except SeatError as exc:
            print(f"panel incomplete: {exc}", file=sys.stderr)
            return 2
        if not seat_fns:
            print("no external seats resolved; a panel of one in-process seat "
                  "cannot produce an error correlation.", file=sys.stderr)
            return 2
    else:
        seat_fns = _demo_seats()

    chosen_gates = None
    if args.resolve_dois:
        from adjudication_orchestrator import (
            CitationResolutionGate,
            SourceAdmissibilityGate,
            probe_resolver,
        )
        from doi_resolver import build_resolver
        resolver = build_resolver()
        # SOP 8.3: verify the resolver denies an identifier that cannot exist
        # BEFORE trusting it. A permissive resolver passes every citation and
        # turns a verified system back into an unverified one while the report
        # still reads green, so this aborts rather than warns.
        probe = probe_resolver(resolver)
        print(f"resolver probe: {probe.status.value.upper()} -- {probe.detail}",
              file=sys.stderr)
        if probe.status.value != "pass":
            print("refusing to run with a permissive citation resolver.",
                  file=sys.stderr)
            return 2
        # Conjoined, never alone: admissibility answers "is this the right KIND
        # of source", resolution answers "does it exist". Either one by itself
        # is a fail-open.
        chosen_gates = [*_default_gates(),
                        SourceAdmissibilityGate(), CitationResolutionGate(resolver)]
    if args.gates:
        try:
            named = gates_from_names(args.gates)
            # MERGE, never overwrite. --resolve-dois builds the conjoined
            # citation pair; assigning the named list on top silently dropped
            # them, so an invented DOI became BLOCKED and the candidate
            # resting on it survived. The console passes both options for the
            # doctorate and patent workflows, so this was the normal path.
            if chosen_gates:
                have = {type(g) for g in named}
                named += [g for g in chosen_gates if type(g) not in have]
            chosen_gates = named
        except ValueError as exc:
            print(f"--gates: {exc}", file=sys.stderr)
            return 2

    try:
        answer = run_adjudication(
            artifact, candidates, seat_fns, gates=chosen_gates,
            audit_path=args.audit, run_id=args.run_id,
            adjudications=adjudications,
        )
    except CeilingReached as exc:
        # PARTIAL, not a crash. The operator paid for the calls that were made
        # and is owed the record of them.
        print(f"\nPARTIAL RUN -- {exc}", file=sys.stderr)
        if ledger is not None:
            ledger.persist_day()
            print("\n".join(ledger.render()), file=sys.stderr)
        print(f"audit log: {args.audit}", file=sys.stderr)
        return 3
    print(render_report(answer))
    if ledger is not None:
        ledger.persist_day()
        print("\n".join(ledger.render()))

    if args.export_queue:
        # Shape it so answering is editing one field per entry: set "verdict"
        # to true or false, then feed the file straight back in with
        # --adjudications. Handing back bare ids would make the operator
        # reconstruct what each one said.
        payload = {
            "_README": [
                "Set \"verdict\" on each entry to true or false, then re-run with",
                "--adjudications pointing at this file. Entries left null stay in",
                "the queue and the run stays incomplete, which is the honest state.",
            ],
            "claims": [
                {"id": c.id, "kind": c.kind.value, "text": c.text,
                 "warrant": c.warrant, "first_seen_pass": c.source_pass,
                 "verdict": None}
                for c in answer.escalated
            ],
        }
        with open(args.export_queue, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"escalation queue written: {args.export_queue} "
              f"({len(answer.escalated)} claim(s) to answer)", file=sys.stderr)
    # 0 only when one candidate survives with nothing outstanding.
    return 0 if answer.resolved else 1


def _cli() -> int:
    """Entry point that survives a closed pipe.

    `run_adjudication.py --demo | head` is ordinary usage, and without this it
    ends in a BrokenPipeError traceback: the reader is gone before the report
    finishes printing. Python also flushes stdout at interpreter exit, which
    raises a SECOND time on the way out, so stdout is redirected to devnull
    before returning -- the standard remedy, and the reason a bare
    `except BrokenPipeError: pass` is not enough.
    """
    try:
        return main()
    except BrokenPipeError:
        # Redirecting is best-effort hygiene, not correctness: it suppresses
        # the SECOND raise from Python's exit-time stdout flush. stdout is not
        # always a real file descriptor -- under a test harness or any embedded
        # runner it may be an in-memory object with no fileno -- and failing to
        # redirect must not turn a handled broken pipe into an unhandled error.
        devnull = None
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
        except (OSError, ValueError, AttributeError):
            pass
        finally:
            # dup2 DUPLICATES the descriptor, so the original stays open.
            # Leaking one per broken pipe is harmless in a one-shot CLI and
            # wrong in anything that calls _cli more than once.
            if devnull is not None:
                with contextlib.suppress(OSError):
                    os.close(devnull)
        return 141  # 128 + SIGPIPE, what a shell reports for this
    except KeyboardInterrupt:
        print("\ninterrupted; no audit entry was written for the current pass.",
              file=sys.stderr)
        return 130  # 128 + SIGINT


if __name__ == "__main__":
    raise SystemExit(_cli())
