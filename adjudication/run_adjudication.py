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
    MissingSeatCredential,
    Orchestrator,
    Pass,
    SchemaGate,
    SequentialPassResult,
    content_claim_id,
    load_panel,
)
from audit_log import AuditLog, DurableAuditLog, digest
from correctness_matrix import diagnose_run
from seat_adapter import SeatError, build_seat_callables
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
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
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
            adjudications = {k: bool(v) for k, v in json.load(fh).items()}

    if args.profiles:
        print(f"env: {load_env_file(args.env)}", file=sys.stderr)
        try:
            seat_fns = live_seats(
                args.profiles,
                specs=(PANEL_OF_FIVE if args.seat5 == "in-process"
                       else PANEL_OF_FIVE_EXTERNAL),
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

    answer = run_adjudication(
        artifact, candidates, seat_fns,
        audit_path=args.audit, run_id=args.run_id, adjudications=adjudications,
    )
    print(render_report(answer))
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
