"""The Full Council Decision Log: the only place a success percentage may come from.

WHY THIS EXISTS. The operator asked for the highest statistical probability of
success, in percentages. The Council protocol, the governance rules, and this
repository's own history agree on what that requires: a dataset, an outcome
variable, and a base rate. Before logged, scored outcomes exist, the posterior
equals the prior and any percentage is fabrication. This file is how the
percentages get earned instead of asserted.

WHAT IT RECORDS. Two events per decision, never more:

    decision   written at decision time: the pre-committed answer, the
               Council's recommendation, the confidence and its cap, and the
               EX ANTE decision-quality score, locked before any outcome exists
    review     written at or after the review date: the outcome, the EX POST
               score, the attribution, and the implementation score

Keeping the two scores in separate, ordered, hash-chained entries is the
safeguard against hindsight bias that the protocol's FMEA names. The ex ante
score cannot be revised once the outcome is known: there is no edit command, a
second decision entry for the same id is refused, and rewriting an entry
breaks the chain (audit_log.DurableAuditLog).

WHAT THE CHAIN PROVES AND DOES NOT. It detects an edited, reordered, spliced,
or deleted entry, and tail truncation against the head sidecar. It is not
signed: someone who rewrites the file AND recomputes every hash AND the sidecar
is not detected. That is the same limit audit_log.py documents.

WHAT A PERCENTAGE HERE MEANS. A track record over n reviewed decisions, shown
with its Wilson interval: never a forecast for the next decision, never a bare
point estimate. Success is an ex post score of 4 or 5 (met or mostly met the
target). N/A outcomes are excluded, not counted as failures. An interval wider
than 30 points is labelled PROVISIONAL. Both thresholds are conventions chosen
here, not derived; they are named so a disagreement is about a number in the
open.

WHERE THE LOG LIVES. adjudication/decisions/decision-log.jsonl by default, and
gitignored: operator records can quote sensitive material, the same reason run
audit logs are not repository content. A cloud container is ephemeral, so
keeping the log (copied out, or committed as GREEN-only material) is a choice
the operator makes deliberately.

    python decision_log.py template
    python decision_log.py record --json filled-record.json
    python decision_log.py review --json filled-review.json
    python decision_log.py stats [--today YYYY-MM-DD] [--json]
    python decision_log.py verify

Exit codes: 0 done; 1 refused (the input or the request was not valid); 2 the
log failed its integrity check, so nothing was computed from it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))

from audit_log import AuditChainError, AuditEntry, DurableAuditLog  # noqa: E402
from stage_zero import wilson  # noqa: E402

DEFAULT_LOG = os.path.join(HERE, "decisions", "decision-log.jsonl")
LOG_ID = "full-council-decision-log"
PLACEHOLDER = "FILL-IN"

SUCCESS_SCORES = frozenset({4, 5})
PROVISIONAL_WIDTH = 0.30
"""An interval wider than this is PROVISIONAL. A convention, not a derivation."""

DECISION_TYPES = ("factual", "causal", "predictive", "strategic", "legal_regulatory", "tax",
                  "compliance", "ethical", "financial", "technical", "medical", "interpersonal")
DECISION_CLASSES = ("PROCEED", "PROCEED WITH CONDITIONS", "RUN A REVERSIBLE TEST",
                    "GATHER EVIDENCE THEN DECIDE", "DO NOT PROCEED")
CONFIDENCE = ("Low", "Medium", "High")
DELTAS = ("No change", "Strengthened", "Weakened", "Reversed", "Insufficient fresh evidence")
WARRANTED = ("Yes", "No", "Unsure")
FOLLOWED = ("Yes", "No", "Partially")
ATTRIBUTION = ("High", "Medium", "Low", "Unknown")
DRIVERS = ("validated reasoning", "luck", "execution", "external shock", "unknown")

PLAN_FIELDS = ("key_assumption", "fastest_test", "owner", "deadline", "pass_condition",
               "fail_condition", "decision_change_if_failed")
RECORD_TEXT = ("decision", "stakes", "operator_precommitted_answer", "base_rate",
               "expected_without_council", "council_recommendation", "cap_applied",
               "strongest_dissent", "immediate_action", "trigger_next_time", "ex_ante_reason",
               "outcome_metric")
RECORD_ENUMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("decision_class", DECISION_CLASSES),
    ("fresh_evidence_delta", DELTAS),
    ("confidence", CONFIDENCE),
    ("full_council_warranted", WARRANTED),
    ("recommendation_followed", FOLLOWED),
)
RECORD_FIELDS = frozenset({
    *RECORD_TEXT, *(name for name, _ in RECORD_ENUMS),
    "id", "date", "review_date", "decision_types", "load_bearing_premises",
    "assumption_test_plan", "ex_ante_score", "if_not_followed_what_changed",
})
REVIEW_TEXT = ("actual_outcome", "outcome_vs_base_rate", "ex_post_reason", "lesson")
REVIEW_FIELDS = frozenset({
    *REVIEW_TEXT, "id", "reviewed_on", "ex_post_score", "result_driver", "attribution",
    "implementation_score",
})

ID_RE = re.compile(r"^D-\d{8}-[a-z0-9][a-z0-9-]{0,39}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Refused(ValueError):
    """The input or request is not valid. Nothing was written."""

    def __init__(self, problems: Sequence[str]):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


class IntegrityError(RuntimeError):
    """The log does not verify. Nothing may be computed from it."""


# ---------------------------------------------------------------- validation

def _is_text(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _iso(v: Any) -> dt.date | None:
    if not (isinstance(v, str) and DATE_RE.match(v)):
        return None
    try:
        return dt.date.fromisoformat(v)
    except ValueError:
        return None


def _date(v: Any, name: str, problems: list[str]) -> dt.date | None:
    day = _iso(v)
    if day is None:
        problems.append(f"{name} must be a real date written YYYY-MM-DD")
    return day


def _score(v: Any, name: str, problems: list[str], allow_na: bool) -> None:
    # bool is an int in Python; True must not pass as a score of 1.
    if isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 5:
        return
    if allow_na and v == "N/A":
        return
    problems.append(f"{name} must be a whole number 1 to 5" + (' or "N/A"' if allow_na else ""))


def _enum(v: Any, name: str, allowed: Sequence[str], problems: list[str]) -> None:
    if v not in allowed:
        problems.append(f"{name} must be one of: {', '.join(allowed)}")


def _placeholders(v: Any, path: str = "") -> list[str]:
    if isinstance(v, str):
        return [f"{path or 'value'} still contains {PLACEHOLDER}"] if PLACEHOLDER in v else []
    if isinstance(v, Mapping):
        return [p for k, sub in v.items() for p in _placeholders(sub, f"{path}.{k}" if path else str(k))]
    if isinstance(v, list):
        return [p for i, sub in enumerate(v) for p in _placeholders(sub, f"{path}[{i}]")]
    return []


def _shape(p: Any, fields: frozenset[str], what: str) -> list[str]:
    if not isinstance(p, Mapping):
        return [f"the {what} must be a JSON object"]
    missing = sorted(fields - set(p))
    unknown = sorted(set(p) - fields)
    problems = [f"missing field: {f}" for f in missing]
    problems += [f"unknown field: {f} (a misspelled field is refused, not ignored)" for f in unknown]
    return problems


def validate_record(p: Any) -> list[str]:
    """Every problem with a decision record. An empty list means it may be written."""
    problems = _shape(p, RECORD_FIELDS, "record")
    if problems:
        return problems
    problems += _placeholders(p)
    if not (isinstance(p["id"], str) and ID_RE.match(p["id"])):
        problems.append("id must look like D-20260926-short-slug (lowercase letters, digits, hyphens)")
    day = _date(p["date"], "date", problems)
    due = _date(p["review_date"], "review_date", problems)
    if day and due and due < day:
        problems.append("review_date is before the decision date")
    problems += [f"{f} must be non-empty text" for f in RECORD_TEXT if not _is_text(p[f])]
    for name, allowed in RECORD_ENUMS:
        _enum(p[name], name, allowed, problems)
    types = p["decision_types"]
    if not (isinstance(types, list) and types and all(t in DECISION_TYPES for t in types)):
        problems.append(f"decision_types must be a non-empty list from: {', '.join(DECISION_TYPES)}")
    premises = p["load_bearing_premises"]
    if not (isinstance(premises, list) and 1 <= len(premises) <= 3 and all(_is_text(x) for x in premises)):
        problems.append("load_bearing_premises must list one to three non-empty premises")
    plan = p["assumption_test_plan"]
    if not (isinstance(plan, Mapping) and set(plan) == set(PLAN_FIELDS) and all(_is_text(plan[f]) for f in PLAN_FIELDS)):
        problems.append(f"assumption_test_plan must hold exactly these non-empty fields: {', '.join(PLAN_FIELDS)}")
    _score(p["ex_ante_score"], "ex_ante_score", problems, allow_na=False)
    why = p["if_not_followed_what_changed"]
    if p["recommendation_followed"] in ("No", "Partially") and not _is_text(why):
        problems.append("if_not_followed_what_changed is required when the recommendation was not fully followed")
    elif not isinstance(why, str):
        problems.append("if_not_followed_what_changed must be text (empty is allowed when followed)")
    return problems


def validate_review(p: Any, decision: Mapping[str, Any]) -> list[str]:
    """Every problem with a review of `decision`. Empty means it may be written."""
    problems = _shape(p, REVIEW_FIELDS, "review")
    if problems:
        return problems
    problems += _placeholders(p)
    on = _date(p["reviewed_on"], "reviewed_on", problems)
    day = dt.date.fromisoformat(decision["date"])
    if on and on < day:
        problems.append("reviewed_on is before the decision date")
    problems += [f"{f} must be non-empty text" for f in REVIEW_TEXT if not _is_text(p[f])]
    _score(p["ex_post_score"], "ex_post_score", problems, allow_na=True)
    _score(p["implementation_score"], "implementation_score", problems, allow_na=True)
    _enum(p["result_driver"], "result_driver", DRIVERS, problems)
    _enum(p["attribution"], "attribution", ATTRIBUTION, problems)
    return problems


# ---------------------------------------------------------------- the log

def _exists(path: str) -> bool:
    return os.path.exists(path) and os.path.getsize(path) > 0


def _open_or_create(path: str) -> DurableAuditLog:
    """The log at `path`, verified on open; created with its genesis if absent."""
    try:
        if not _exists(path):
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        return DurableAuditLog(path, run_id=LOG_ID)
    except (AuditChainError, ValueError, OSError) as exc:
        # ValueError covers a line that is not JSON. Every one of these means
        # the record cannot be trusted, so nothing is computed from it.
        raise IntegrityError(f"{path}: {exc}") from exc


def _open_existing(path: str) -> DurableAuditLog | None:
    """The log at `path`, verified on open, or None when nothing is recorded yet."""
    return _open_or_create(path) if _exists(path) else None


def replay(entries: Sequence[AuditEntry]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Decisions and reviews by id, re-validated. Any violation fails closed."""
    decisions: dict[str, dict[str, Any]] = {}
    reviews: dict[str, dict[str, Any]] = {}
    for e in entries[1:]:
        pid = e.payload.get("id")
        if not isinstance(pid, str):
            raise IntegrityError(f"entry {e.seq}: id is not text: {pid!r}")
        if e.kind == "decision":
            if pid in decisions:
                raise IntegrityError(f"entry {e.seq}: decision {pid!r} recorded twice; an ex ante record may have been rewritten")
            bad = validate_record(e.payload)
            if bad:
                raise IntegrityError(f"entry {e.seq}: decision {pid!r} does not validate: {bad[0]}")
            decisions[pid] = dict(e.payload)
        elif e.kind == "review":
            if pid not in decisions:
                raise IntegrityError(f"entry {e.seq}: review of {pid!r} has no earlier decision")
            if pid in reviews:
                raise IntegrityError(f"entry {e.seq}: decision {pid!r} reviewed twice")
            bad = validate_review(e.payload, decisions[pid])
            if bad:
                raise IntegrityError(f"entry {e.seq}: review of {pid!r} does not validate: {bad[0]}")
            reviews[pid] = dict(e.payload)
        else:
            raise IntegrityError(f"entry {e.seq}: unexpected entry kind {e.kind!r}")
    return decisions, reviews


def load(path: str) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Decisions and reviews from the log at `path`; empty when no log exists yet."""
    log = _open_existing(path)
    return ({}, {}) if log is None else replay(log.entries)


def record(path: str, payload: Any) -> AuditEntry:
    """Write a decision and lock its ex ante score. Refuses before touching disk."""
    problems = validate_record(payload)
    if problems:
        raise Refused(problems)
    log = _open_or_create(path)
    decisions, _ = replay(log.entries)
    if payload["id"] in decisions:
        raise Refused([f"decision {payload['id']} is already recorded; the ex ante record is locked"])
    return log.append("decision", dict(payload))


def review(path: str, payload: Any) -> AuditEntry:
    """Write the ex post review of a recorded decision, once."""
    log = _open_existing(path)
    if log is None:
        raise Refused([f"no decision log at {path}: record the decision before reviewing it"])
    decisions, reviews = replay(log.entries)
    pid = payload.get("id") if isinstance(payload, Mapping) else None
    if not isinstance(pid, str) or pid not in decisions:
        raise Refused([f"no recorded decision with id {pid!r}"])
    if pid in reviews:
        raise Refused([f"decision {pid} is already reviewed; a review is written once"])
    problems = validate_review(payload, decisions[pid])
    if problems:
        raise Refused(problems)
    return log.append("review", dict(payload))


# ---------------------------------------------------------------- statistics

@dataclass(frozen=True)
class Rate:
    """k successes in n scored decisions, always carried with its interval."""

    label: str
    k: int
    n: int

    @property
    def interval(self) -> tuple[float, float] | None:
        return None if self.n == 0 else wilson(self.k, self.n)

    @property
    def provisional(self) -> bool:
        iv = self.interval
        return iv is None or (iv[1] - iv[0]) > PROVISIONAL_WIDTH

    def line(self) -> str:
        iv = self.interval
        if iv is None:
            return f"{self.label:<32} NO DATA (n = 0)"
        text = (f"{self.label:<32} {self.k}/{self.n} = {100 * self.k / self.n:.1f}%"
                f"  Wilson 95% [{100 * iv[0]:.1f}%, {100 * iv[1]:.1f}%]")
        return text + ("  PROVISIONAL" if self.provisional else "")

    def as_dict(self) -> dict[str, Any]:
        iv = self.interval
        return {"label": self.label, "k": self.k, "n": self.n,
                "rate": None if iv is None else self.k / self.n,
                "wilson_95": None if iv is None else list(iv),
                "provisional": self.provisional}


@dataclass(frozen=True)
class Stats:
    recorded: int
    reviewed: int
    awaiting: int
    overdue: list[str] | None
    not_observable: int
    early_reviews: int
    overall: Rate
    by_confidence: list[Rate]
    by_followed: list[Rate]
    ex_ante_vs_outcome: list[tuple[int, int, float | None]]
    attribution: dict[str, int]
    drivers: dict[str, int]
    warranted: dict[str, int]


def _rate(label: str, pairs: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]]) -> Rate:
    return Rate(label, sum(1 for _, r in pairs if r["ex_post_score"] in SUCCESS_SCORES), len(pairs))


def _tally(values: Sequence[str], keys: Sequence[str]) -> dict[str, int]:
    return {k: sum(1 for v in values if v == k) for k in keys}


def compute(decisions: Mapping[str, Mapping[str, Any]], reviews: Mapping[str, Mapping[str, Any]],
            today: dt.date | None = None) -> Stats:
    scored = [(decisions[i], r) for i, r in reviews.items() if r["ex_post_score"] != "N/A"]
    overdue = None if today is None else sorted(
        i for i, d in decisions.items()
        if i not in reviews and dt.date.fromisoformat(d["review_date"]) < today)
    ex_ante = []
    for score in (5, 4, 3, 2, 1):
        outcomes = [int(r["ex_post_score"]) for d, r in scored if d["ex_ante_score"] == score]
        ex_ante.append((score, len(outcomes), sum(outcomes) / len(outcomes) if outcomes else None))
    return Stats(
        recorded=len(decisions),
        reviewed=len(reviews),
        awaiting=len(decisions) - len(reviews),
        overdue=overdue,
        not_observable=len(reviews) - len(scored),
        early_reviews=sum(1 for i, r in reviews.items()
                          if r["reviewed_on"] < decisions[i]["review_date"]),
        overall=_rate("all reviewed decisions", scored),
        by_confidence=[_rate(f"confidence {c}", [(d, r) for d, r in scored if d["confidence"] == c])
                       for c in reversed(CONFIDENCE)],
        by_followed=[
            _rate("recommendation followed", [(d, r) for d, r in scored if d["recommendation_followed"] == "Yes"]),
            _rate("not or partially followed", [(d, r) for d, r in scored if d["recommendation_followed"] != "Yes"]),
        ],
        ex_ante_vs_outcome=ex_ante,
        attribution=_tally([r["attribution"] for r in reviews.values()], ATTRIBUTION),
        drivers=_tally([r["result_driver"] for r in reviews.values()], DRIVERS),
        warranted=_tally([d["full_council_warranted"] for d in decisions.values()], WARRANTED),
    )


def _counts(d: Mapping[str, int]) -> str:
    return ", ".join(f"{k} {v}" for k, v in d.items())


def render(s: Stats, path: str, today: dt.date | None = None) -> list[str]:
    out = ["FULL COUNCIL DECISION TRACK RECORD", f"  log: {path}"]
    if s.recorded == 0:
        return [*out, "  NO DECISIONS RECORDED.",
                "  With an empty outcome dataset the posterior equals the prior:",
                "  no success rate can be stated until decisions are recorded and reviewed."]
    head = f"  decisions recorded {s.recorded}, reviewed {s.reviewed}, awaiting review {s.awaiting}"
    if s.overdue is not None and today is not None:
        head += f"; overdue as of {today.isoformat()}: {', '.join(s.overdue) or 'none'}"
    out += [head,
            f"  success = ex post score 4 or 5 (met or mostly met the target); "
            f"N/A outcomes excluded: {s.not_observable}; reviewed before the review date: {s.early_reviews}",
            "", "  " + s.overall.line(), "  by confidence at decision time:"]
    out += ["    " + r.line() for r in s.by_confidence]
    out += ["  by whether the recommendation was followed:"]
    out += ["    " + r.line() for r in s.by_followed]
    out += ["  ex ante decision quality against outcome (n scored, mean ex post score):"]
    out += [f"    ex ante {score}: n {n}" + ("" if mean is None else f", mean {mean:.2f}")
            for score, n, mean in s.ex_ante_vs_outcome]
    out += [f"  attribution to the Council: {_counts(s.attribution)}",
            f"  what drove each result: {_counts(s.drivers)}",
            f"  Full Council warranted: {_counts(s.warranted)}",
            "",
            "  Each rate is a track record over n reviewed decisions, not a forecast for the",
            "  next one. Read the interval, not the midpoint. PROVISIONAL marks an interval",
            "  wider than 30 points (a convention, not a derivation)."]
    return out


def as_json(s: Stats) -> dict[str, Any]:
    return {
        "recorded": s.recorded, "reviewed": s.reviewed, "awaiting": s.awaiting,
        "overdue": s.overdue, "not_observable": s.not_observable, "early_reviews": s.early_reviews,
        "success_definition": "ex post score 4 or 5; N/A excluded",
        "overall": s.overall.as_dict(),
        "by_confidence": [r.as_dict() for r in s.by_confidence],
        "by_followed": [r.as_dict() for r in s.by_followed],
        "ex_ante_vs_outcome": [{"ex_ante": a, "n": n, "mean_ex_post": m} for a, n, m in s.ex_ante_vs_outcome],
        "attribution": s.attribution, "drivers": s.drivers, "warranted": s.warranted,
    }


def template() -> dict[str, Any]:
    """Fill-in templates. They fail validation until every placeholder is replaced."""
    rec: dict[str, Any] = dict.fromkeys(sorted(RECORD_FIELDS), PLACEHOLDER)
    rec.update({
        "id": f"D-YYYYMMDD-{PLACEHOLDER}", "date": f"YYYY-MM-DD {PLACEHOLDER}",
        "review_date": f"YYYY-MM-DD {PLACEHOLDER}",
        "decision_types": [PLACEHOLDER], "load_bearing_premises": [PLACEHOLDER],
        "assumption_test_plan": dict.fromkeys(PLAN_FIELDS, PLACEHOLDER),
    })
    rev: dict[str, Any] = dict.fromkeys(sorted(REVIEW_FIELDS), PLACEHOLDER)
    rev["reviewed_on"] = f"YYYY-MM-DD {PLACEHOLDER}"
    allowed = {"decision_types": DECISION_TYPES, **dict(RECORD_ENUMS),
               "ex_ante_score": "whole number 1 to 5, scored now, locked once written",
               "ex_post_score": 'whole number 1 to 5, or "N/A"',
               "implementation_score": 'whole number 1 to 5, or "N/A"',
               "result_driver": DRIVERS, "attribution": ATTRIBUTION}
    return {"record": rec, "review": rev, "allowed_values": allowed}


# ---------------------------------------------------------------- command line

def _read_json(source: str) -> Any:
    try:
        text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
        return json.loads(text)
    except (OSError, ValueError) as exc:
        raise Refused([f"cannot read JSON from {source}: {exc}"]) from exc


def _parse_today(v: str | None) -> dt.date | None:
    if v is None:
        return None
    problems: list[str] = []
    day = _date(v, "--today", problems)
    if day is None:
        raise Refused(problems)
    return day


def _cmd_template(_: argparse.Namespace) -> int:
    print(json.dumps(template(), indent=2))
    return 0


def _cmd_record(a: argparse.Namespace) -> int:
    payload = _read_json(a.json_path)
    entry = record(a.log, payload)
    print(f"RECORDED {payload['id']} as entry {entry.seq}. The ex ante score is now locked. "
          f"Review on or after {payload['review_date']}.")
    return 0


def _cmd_review(a: argparse.Namespace) -> int:
    payload = _read_json(a.json_path)
    entry = review(a.log, payload)
    print(f"REVIEWED {payload['id']} as entry {entry.seq}.")
    return 0


def _cmd_stats(a: argparse.Namespace) -> int:
    today = _parse_today(a.today)
    decisions, reviews = load(a.log)
    stats = compute(decisions, reviews, today)
    if a.as_json:
        print(json.dumps(as_json(stats), indent=2))
    else:
        print("\n".join(render(stats, a.log, today)))
    return 0


def _cmd_verify(a: argparse.Namespace) -> int:
    log = _open_existing(a.log)
    if log is None:
        print(f"NO LOG at {a.log}: nothing has been recorded, and an absent log is not a verified one.")
        return 1
    verdict = log.verify()
    decisions, reviews = replay(log.entries)
    print(f"VERIFIED: {verdict.entries_checked} entries, {len(decisions)} decisions, {len(reviews)} reviews.")
    return 0


_COMMANDS: dict[str, Callable[[argparse.Namespace], int]] = {
    "template": _cmd_template, "record": _cmd_record, "review": _cmd_review,
    "stats": _cmd_stats, "verify": _cmd_verify,
}


class _Parser(argparse.ArgumentParser):
    """argparse exits 2 on a usage error, which here means a failed integrity
    check. A mistyped flag is a refusal (1), not a tampered log."""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        raise Refused([message])


def _parser() -> argparse.ArgumentParser:
    p = _Parser(prog="decision_log.py",
                description="The Full Council Decision Log: the only place a success percentage may come from.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("template", help="print the record and review templates")
    for name in ("record", "review"):
        sp = sub.add_parser(name, help=f"write a {name} entry")
        sp.add_argument("--json", dest="json_path", required=True, help="filled JSON file, or - for stdin")
        sp.add_argument("--log", default=DEFAULT_LOG)
    sp = sub.add_parser("stats", help="track record with Wilson intervals")
    sp.add_argument("--log", default=DEFAULT_LOG)
    sp.add_argument("--today", help="YYYY-MM-DD, to list overdue reviews")
    sp.add_argument("--json", dest="as_json", action="store_true")
    sp = sub.add_parser("verify", help="integrity check only")
    sp.add_argument("--log", default=DEFAULT_LOG)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    try:
        a = _parser().parse_args(argv)
        return _COMMANDS[a.cmd](a)
    except Refused as exc:
        print("REFUSED, nothing written:", file=sys.stderr)
        for problem in exc.problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    except IntegrityError as exc:
        print(f"INTEGRITY FAILURE, nothing computed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
