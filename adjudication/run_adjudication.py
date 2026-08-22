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
import json
import math
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from adjudication_orchestrator import (
    DEFAULT_PASSES,
    ArithmeticGate,
    BlindedSeatRunner,
    Candidate,
    Claim,
    ClaimKind,
    Gate,
    Orchestrator,
    Pass,
    SchemaGate,
    SequentialPassResult,
    content_claim_id,
)
from audit_log import AuditLog, DurableAuditLog, digest
from correctness_matrix import diagnose_run


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

    @property
    def resolved(self) -> bool:
        """Exactly one candidate survives AND nothing is outstanding.

        Both halves are required. One survivor with an unadjudicated queue is
        a leading candidate, not an answer, and calling it one is how a
        shortlist gets shipped as a conclusion.
        """
        return len(self.survivors) == 1 and not self.holes


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
            claims.append(
                Claim(content_claim_id(kind, warrant, text), text, kind, warrant)
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
    results = orch.run_sequential(artifact, cands, runner, passes=chosen, audit=audit)

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
    )


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
    return [ArithmeticGate(), SchemaGate()]


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def render_report(answer: AdjudicationAnswer) -> str:
    L: list[str] = []
    add = L.append

    add("=" * 72)
    add("ADJUDICATION RUN")
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
            f"rejected {rec.auto_rejected} | escalated {rec.escalated}")
        if rec.eliminated_candidates:
            add(f"     eliminated: {', '.join(rec.eliminated_candidates)}")
        jac = div.mean_pairwise_jaccard
        overlap = "n/a" if jac is None else f"{jac:.2f}"
        add(f"     seat overlap {overlap}"
            + (f"  [{div.collapse_warning}]" if div.collapse_warning else ""))
        if div.seats_errored:
            add(f"     SEAT ERROR: {', '.join(div.seats_errored)}")
    add("")

    add("-" * 72)
    add("ANSWER, BY ELIMINATION")
    add("-" * 72)
    if not answer.survivors:
        add("  NONE SURVIVED. Every candidate failed a gate.")
    elif len(answer.survivors) == 1:
        add(f"  SURVIVOR: {answer.survivors[0].id}")
        content = answer.survivors[0].content
        if content:
            add(f"    {content}")
    else:
        add(f"  {len(answer.survivors)} SURVIVE -- not narrowed to one:")
        for c in answer.survivors:
            add(f"    {c.id}")
    for c in answer.eliminated:
        add(f"  removed {c.id}: {c.elimination_reason}")
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
    ap.add_argument("--demo", action="store_true",
                    help="run with three scripted synthetic seats and no credentials")
    args = ap.parse_args(argv)

    if not args.demo:
        # FAIL CLOSED. A real panel needs configured seats, and this tool will
        # not invent one. seat_adapter.build_seat_callables takes the provider
        # profiles the operator supplies from vendor API documentation.
        print(
            "no seats configured.\n"
            "  --demo runs three scripted synthetic seats end to end.\n"
            "  For a real panel: set ADJ_SEAT_1..4_API_KEY, build a "
            "ProviderProfile per seat\n"
            "  from that vendor's API reference, and pass "
            "seat_adapter.build_seat_callables(...)\n"
            "  into run_adjudication(). Nothing here ships a vendor endpoint.",
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
            adjudications = {k: bool(v) for k, v in json.load(fh).items()}

    answer = run_adjudication(
        artifact, candidates, _demo_seats(),
        audit_path=args.audit, run_id=args.run_id, adjudications=adjudications,
    )
    print(render_report(answer))
    # 0 only when one candidate survives with nothing outstanding.
    return 0 if answer.resolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
