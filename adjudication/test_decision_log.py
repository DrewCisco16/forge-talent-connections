"""Tests for decision_log.py: the track record percentages are earned from.

Every refusal path is exercised, every integrity failure is planted and must be
caught, and every rate must travel with its interval.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

import pytest

import decision_log as dl
from audit_log import HEAD_SUFFIX, ChainVerdict, DurableAuditLog
from stage_zero import wilson


def good_record(**over: Any) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "id": "D-20260926-sponsor-tier",
        "date": "2026-09-26",
        "decision": "Open a paid sponsor tier as a bounded pilot",
        "decision_types": ["strategic", "financial"],
        "stakes": "Public pricing commitment",
        "operator_precommitted_answer": "Proceed with a pilot",
        "load_bearing_premises": ["Sponsors pay for verified collaboration"],
        "base_rate": "Unknown",
        "expected_without_council": "Modest uptake",
        "council_recommendation": "Run a reversible pilot with three sponsors",
        "decision_class": "RUN A REVERSIBLE TEST",
        "fresh_evidence_delta": "Strengthened",
        "confidence": "Medium",
        "cap_applied": "Single model family",
        "strongest_dissent": "Demand may be thin",
        "assumption_test_plan": dict.fromkeys(dl.PLAN_FIELDS, "x"),
        "immediate_action": "Offer the tier to three sponsors",
        "full_council_warranted": "Yes",
        "trigger_next_time": "Any public pricing change",
        "ex_ante_score": 4,
        "ex_ante_reason": "Direct evidence, dissent engaged",
        "recommendation_followed": "Yes",
        "if_not_followed_what_changed": "",
        "outcome_metric": "Two of three sponsors accept",
        "review_date": "2026-11-30",
    }
    rec.update(over)
    return rec


def good_review(**over: Any) -> dict[str, Any]:
    rev: dict[str, Any] = {
        "id": "D-20260926-sponsor-tier",
        "reviewed_on": "2026-11-30",
        "actual_outcome": "Two sponsors accepted",
        "outcome_vs_base_rate": "No base rate",
        "ex_post_score": 5,
        "ex_post_reason": "Target met",
        "result_driver": "validated reasoning",
        "attribution": "Medium",
        "implementation_score": 4,
        "lesson": "Pilot first",
    }
    rev.update(over)
    return rev


@pytest.fixture
def log(tmp_path: Path) -> str:
    return str(tmp_path / "decisions" / "decision-log.jsonl")


def run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = dl.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


def write_json(tmp_path: Path, name: str, obj: Any) -> str:
    p = tmp_path / name
    p.write_text(json.dumps(obj), encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------- templates

def test_shipped_template_fails_validation_until_filled() -> None:
    t = dl.template()
    rec_problems = dl.validate_record(t["record"])
    assert rec_problems
    assert any("placeholder" in p for p in rec_problems)
    rev_problems = dl.validate_review(t["review"], good_record())
    assert rev_problems
    assert any("placeholder" in p for p in rev_problems)
    assert set(t["record"]) == dl.RECORD_FIELDS
    assert set(t["review"]) == dl.REVIEW_FIELDS


def test_good_fixtures_validate() -> None:
    assert dl.validate_record(good_record()) == []
    assert dl.validate_review(good_review(), good_record()) == []


# ---------------------------------------------------------------- record validation

@pytest.mark.parametrize(("over", "pattern"), [
    ({"confidence": "95%"}, r"confidence must be one of"),
    ({"confidence": "Very High"}, r"confidence must be one of"),
    ({"decision_class": "MAYBE"}, r"decision_class must be one of"),
    ({"fresh_evidence_delta": "Up"}, r"fresh_evidence_delta must be one of"),
    ({"full_council_warranted": "Probably"}, r"full_council_warranted must be one of"),
    ({"recommendation_followed": "Mostly"}, r"recommendation_followed must be one of"),
    ({"ex_ante_score": True}, r"ex_ante_score must be a whole number"),
    ({"ex_ante_score": 0}, r"ex_ante_score"),
    ({"ex_ante_score": 6}, r"ex_ante_score"),
    ({"ex_ante_score": "5"}, r"ex_ante_score"),
    ({"ex_ante_score": 4.5}, r"ex_ante_score"),
    ({"ex_ante_score": "N/A"}, r"ex_ante_score"),
    ({"load_bearing_premises": []}, r"one to three"),
    ({"load_bearing_premises": ["a", "b", "c", "d"]}, r"one to three"),
    ({"load_bearing_premises": ["a", " "]}, r"one to three"),
    ({"decision_types": []}, r"decision_types"),
    ({"decision_types": ["vibes"]}, r"decision_types"),
    ({"decision_types": "strategic"}, r"decision_types"),
    ({"id": "sponsor-tier"}, r"id must look like"),
    ({"id": "D-2026926-x"}, r"id must look like"),
    ({"id": "D-20260926-Upper"}, r"id must look like"),
    ({"date": "2026-02-30"}, r"date must be a real date"),
    ({"date": "26/09/2026"}, r"date must be a real date"),
    ({"date": 20260926}, r"date must be a real date"),
    ({"review_date": "2026-09-01"}, r"review_date is before the decision date"),
    ({"decision": "  "}, r"decision must be non-empty text"),
    ({"stakes": None}, r"stakes must be non-empty text"),
    ({"assumption_test_plan": {"key_assumption": "x"}}, r"assumption_test_plan"),
    ({"assumption_test_plan": {**dict.fromkeys(dl.PLAN_FIELDS, "x"), "owner": ""}}, r"assumption_test_plan"),
    ({"recommendation_followed": "No", "if_not_followed_what_changed": ""}, r"required when"),
    ({"recommendation_followed": "Partially", "if_not_followed_what_changed": " "}, r"required when"),
    ({"if_not_followed_what_changed": None}, r"must be text"),
    ({"cap_applied": "FILL-IN later"}, r"still contains placeholder text"),
    ({"cap_applied": "fill in"}, r"still contains placeholder text"),
    ({"stakes": "TBD"}, r"still contains placeholder text"),
    ({"stakes": "todo: write this"}, r"still contains placeholder text"),
    ({"stakes": "<your stakes here>"}, r"still contains placeholder text"),
    ({"stakes": "..."}, r"still contains placeholder text"),
    ({"stakes": "\u2026"}, r"still contains placeholder text"),
    ({"id": "D-20260926-sponsor-tier\n"}, r"id must look like"),
    ({"id": "D-\uff12\uff10\uff12\uff16\uff10\uff19\uff12\uff16-sponsor-tier"}, r"id must look like"),
    ({"date": "2026-09-26\n"}, r"date must be a real date"),
    ({"date": "\uff12\uff10\uff12\uff16-09-26"}, r"date must be a real date"),
])
def test_record_refusals(over: dict[str, Any], pattern: str) -> None:
    problems = dl.validate_record(good_record(**over))
    assert any(re.search(pattern, p) for p in problems), problems


def test_missing_and_unknown_fields_are_refused() -> None:
    rec = good_record()
    del rec["stakes"]
    rec["ex_ante_scor"] = 4
    problems = dl.validate_record(rec)
    assert "missing field: stakes" in problems
    assert any(p.startswith("unknown field: ex_ante_scor") for p in problems)


def test_non_object_is_refused() -> None:
    assert dl.validate_record([1, 2]) == ["the record must be a JSON object"]
    assert dl.validate_review("x", good_record()) == ["the review must be a JSON object"]


def test_placeholder_found_inside_nested_values() -> None:
    rec = good_record(assumption_test_plan={**dict.fromkeys(dl.PLAN_FIELDS, "x"), "owner": "FILL-IN"},
                      load_bearing_premises=["a", "FILL-IN"])
    problems = dl.validate_record(rec)
    assert "assumption_test_plan.owner still contains placeholder text" in problems
    assert "load_bearing_premises[1] still contains placeholder text" in problems


def test_ordinary_words_are_not_placeholders() -> None:
    rec = good_record(stakes="Fulfilling the contract", decision="Refilling the pipeline",
                      strongest_dissent="revenue < cost > margin")
    assert dl.validate_record(rec) == []


def test_deeply_nested_input_is_refused_not_crashed() -> None:
    deep: Any = "x"
    for _ in range(5000):
        deep = [deep]
    problems = dl.validate_record(good_record(stakes=deep))
    assert "stakes must be non-empty text" in problems


def test_followed_with_note_is_fine() -> None:
    assert dl.validate_record(good_record(if_not_followed_what_changed="n/a")) == []
    assert dl.validate_record(good_record(recommendation_followed="No",
                                          if_not_followed_what_changed="Budget moved")) == []


# ---------------------------------------------------------------- review validation

@pytest.mark.parametrize(("over", "pattern"), [
    ({"ex_post_score": 0}, r"ex_post_score must be a whole number 1 to 5 or \"N/A\""),
    ({"ex_post_score": False}, r"ex_post_score"),
    ({"implementation_score": "n/a"}, r"implementation_score"),
    ({"result_driver": "fate"}, r"result_driver must be one of"),
    ({"attribution": "Total"}, r"attribution must be one of"),
    ({"reviewed_on": "2026-09-25"}, r"reviewed_on is before the decision date"),
    ({"reviewed_on": "soon"}, r"reviewed_on must be a real date"),
    ({"lesson": ""}, r"lesson must be non-empty text"),
])
def test_review_refusals(over: dict[str, Any], pattern: str) -> None:
    problems = dl.validate_review(good_review(**over), good_record())
    assert any(re.search(pattern, p) for p in problems), problems


def test_na_scores_are_allowed_on_review() -> None:
    assert dl.validate_review(good_review(ex_post_score="N/A", implementation_score="N/A"), good_record()) == []


# ---------------------------------------------------------------- writing

def test_refused_record_creates_no_log(log: str) -> None:
    with pytest.raises(dl.Refused):
        dl.record(log, good_record(confidence="95%"))
    assert not os.path.exists(log)


def test_record_creates_log_and_locks_the_id(log: str) -> None:
    entry = dl.record(log, good_record())
    assert entry.seq == 1
    with pytest.raises(dl.Refused, match="already recorded"):
        dl.record(log, good_record(ex_ante_score=5))
    decisions, reviews = dl.load(log)
    assert decisions["D-20260926-sponsor-tier"]["ex_ante_score"] == 4
    assert reviews == {}


def test_review_needs_a_log_and_a_recorded_decision(log: str) -> None:
    with pytest.raises(dl.Refused, match="no decision log"):
        dl.review(log, good_review())
    dl.record(log, good_record())
    with pytest.raises(dl.Refused, match="no recorded decision"):
        dl.review(log, good_review(id="D-20260926-other"))
    with pytest.raises(dl.Refused, match="no recorded decision"):
        dl.review(log, good_review(id=["D-20260926-sponsor-tier"]))
    with pytest.raises(dl.Refused, match="no recorded decision"):
        dl.review(log, "not an object")


def test_review_is_written_once(log: str) -> None:
    dl.record(log, good_record())
    dl.review(log, good_review())
    with pytest.raises(dl.Refused, match="already reviewed"):
        dl.review(log, good_review(ex_post_score=1))


def test_invalid_review_is_refused(log: str) -> None:
    dl.record(log, good_record())
    with pytest.raises(dl.Refused, match="attribution"):
        dl.review(log, good_review(attribution="Total"))


# ---------------------------------------------------------------- integrity

def test_rewritten_ex_ante_score_is_detected(log: str) -> None:
    dl.record(log, good_record())
    text = Path(log).read_text(encoding="utf-8")
    assert '"ex_ante_score":4' in text
    Path(log).write_text(text.replace('"ex_ante_score":4', '"ex_ante_score":5'), encoding="utf-8")
    with pytest.raises(dl.IntegrityError, match="hash mismatch"):
        dl.load(log)


def test_truncated_tail_is_detected(log: str) -> None:
    dl.record(log, good_record())
    dl.record(log, good_record(id="D-20260926-second"))
    lines = Path(log).read_text(encoding="utf-8").splitlines(keepends=True)
    Path(log).write_text("".join(lines[:-1]), encoding="utf-8")
    with pytest.raises(dl.IntegrityError, match="truncated"):
        dl.load(log)


def test_non_json_line_is_an_integrity_failure(log: str) -> None:
    dl.record(log, good_record())
    with open(log, "a", encoding="utf-8") as fh:
        fh.write("not json\n")
    with pytest.raises(dl.IntegrityError):
        dl.load(log)


def test_a_foreign_audit_log_is_refused(log: str) -> None:
    os.makedirs(os.path.dirname(log))
    DurableAuditLog(log, run_id="run-001")
    with pytest.raises(dl.IntegrityError, match="belongs to run"):
        dl.record(log, good_record())


@pytest.mark.parametrize(("entries", "pattern"), [
    ([("decision", good_record()), ("decision", good_record(ex_ante_score=5))], "recorded twice"),
    ([("review", good_review())], "no earlier decision"),
    ([("decision", good_record()), ("review", good_review()), ("review", good_review())], "reviewed twice"),
    ([("decision", good_record(confidence="95%"))], "does not validate"),
    ([("decision", good_record()), ("review", good_review(attribution="Total"))], "does not validate"),
    ([("note", {"id": "D-20260926-sponsor-tier"})], "unexpected entry kind"),
    ([("decision", {**good_record(), "id": ["x"]})], "id is not text"),
])
def test_replay_fails_closed_on_entries_written_around_the_api(
        log: str, entries: list[tuple[str, dict[str, Any]]], pattern: str) -> None:
    os.makedirs(os.path.dirname(log))
    raw = DurableAuditLog(log, run_id=dl.LOG_ID)
    for kind, payload in entries:
        raw.append(kind, payload)
    with pytest.raises(dl.IntegrityError, match=pattern):
        dl.load(log)


# ---------------------------------------------------------------- statistics

def _seed(log: str) -> None:
    dl.record(log, good_record(id="D-20260901-a", date="2026-09-01", confidence="High",
                               ex_ante_score=5, review_date="2026-10-01"))
    dl.record(log, good_record(id="D-20260902-b", date="2026-09-02", confidence="Medium",
                               ex_ante_score=3, review_date="2026-10-02",
                               recommendation_followed="No", if_not_followed_what_changed="Budget"))
    dl.record(log, good_record(id="D-20260903-c", date="2026-09-03", confidence="Medium",
                               ex_ante_score=4, review_date="2026-10-03"))
    dl.record(log, good_record(id="D-20260904-d", date="2026-09-04", review_date="2026-10-04",
                               full_council_warranted="No"))
    dl.review(log, good_review(id="D-20260901-a", reviewed_on="2026-10-01", ex_post_score=5))
    dl.review(log, good_review(id="D-20260902-b", reviewed_on="2026-09-20", ex_post_score=2,
                               attribution="Low", result_driver="execution"))
    dl.review(log, good_review(id="D-20260903-c", reviewed_on="2026-10-03", ex_post_score="N/A",
                               attribution="Unknown", result_driver="unknown"))


def test_rates_carry_wilson_intervals_and_exclude_na(log: str) -> None:
    _seed(log)
    s = dl.compute(*dl.load(log), today=dt.date(2026, 10, 5))
    assert (s.recorded, s.reviewed, s.awaiting, s.not_observable) == (4, 3, 1, 1)
    assert (s.overall.k, s.overall.n) == (1, 2)
    assert s.overall.interval == wilson(1, 2)
    by_conf = {r.label: (r.k, r.n) for r in s.by_confidence}
    assert by_conf == {"confidence High": (1, 1), "confidence Medium": (0, 1), "confidence Low": (0, 0)}
    by_followed = {r.label: (r.k, r.n) for r in s.by_followed}
    assert by_followed == {"recommendation followed": (1, 1), "not or partially followed": (0, 1)}
    assert s.overdue == ["D-20260904-d"]
    assert s.early_reviews == 1
    assert s.attribution == {"High": 0, "Medium": 1, "Low": 1, "Unknown": 1}
    assert s.warranted == {"Yes": 3, "No": 1, "Unsure": 0}
    assert (5, 1, 5.0) in s.ex_ante_vs_outcome
    assert (1, 0, None) in s.ex_ante_vs_outcome


def test_success_boundary_is_four_mixed_three_is_not_success(log: str) -> None:
    # The definition every percentage rests on: 4 ("mostly met target") counts,
    # 3 ("mixed result") does not.
    for day, score in (("01", 3), ("02", 4)):
        dl.record(log, good_record(id=f"D-202609{day}-b{score}", date=f"2026-09-{day}"))
        dl.review(log, good_review(id=f"D-202609{day}-b{score}", ex_post_score=score))
    s = dl.compute(*dl.load(log))
    assert (s.overall.k, s.overall.n) == (1, 2)


def test_overdue_needs_a_date_and_respects_it(log: str) -> None:
    _seed(log)
    decisions, reviews = dl.load(log)
    assert dl.compute(decisions, reviews).overdue is None
    assert dl.compute(decisions, reviews, today=dt.date(2026, 10, 4)).overdue == []


def test_no_percentage_is_ever_printed_without_its_interval(log: str) -> None:
    _seed(log)
    decisions, reviews = dl.load(log)
    lines = dl.render(dl.compute(decisions, reviews, dt.date(2026, 10, 5)), log, dt.date(2026, 10, 5))
    pct_lines = [ln for ln in lines if re.search(r"\d%", ln)]
    assert pct_lines
    for ln in pct_lines:
        assert "Wilson 95%" in ln, ln


def test_empty_log_states_no_percentage(log: str) -> None:
    lines = dl.render(dl.compute(*dl.load(log)), log)
    text = "\n".join(lines)
    assert "posterior equals the prior" in text
    assert not re.search(r"\d\s*%", text)
    assert not os.path.exists(log)


def test_provisional_tracks_interval_width() -> None:
    assert dl.Rate("x", 0, 0).provisional
    assert dl.Rate("x", 1, 2).provisional
    narrow = dl.Rate("x", 90, 100)
    low, high = wilson(90, 100)
    assert high - low < dl.PROVISIONAL_WIDTH
    assert not narrow.provisional
    assert "PROVISIONAL" not in narrow.line()
    assert "PROVISIONAL" in dl.Rate("x", 1, 2).line()
    assert dl.Rate("x", 0, 0).line().endswith("NO DATA (n = 0)")
    assert dl.Rate("x", 0, 0).as_dict()["rate"] is None


def test_json_output_matches(log: str) -> None:
    _seed(log)
    j = dl.as_json(dl.compute(*dl.load(log)))
    assert j["overall"]["k"] == 1
    assert j["overall"]["wilson_95"] == list(wilson(1, 2))
    assert j["success_definition"].startswith("ex post score 4 or 5")


# ---------------------------------------------------------------- command line

def test_cli_end_to_end(tmp_path: Path, log: str, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(["template"], capsys)
    assert code == 0
    assert set(json.loads(out)) == {"record", "review", "allowed_values"}

    # The command line stamps writes with the real clock and refuses future
    # dates, so this test dates everything today to hold on any run date.
    today = dt.datetime.now(dt.UTC).date().isoformat()
    rec = write_json(tmp_path, "rec.json", good_record(date=today, review_date=today))
    code, out, _ = run(["record", "--json", rec, "--log", log], capsys)
    assert code == 0
    assert "ex ante score is now locked" in out

    code, _, err = run(["record", "--json", rec, "--log", log], capsys)
    assert code == 1
    assert "already recorded" in err

    rev = write_json(tmp_path, "rev.json", good_review(reviewed_on=today))
    code, out, _ = run(["review", "--json", rev, "--log", log], capsys)
    assert code == 0
    assert out.startswith("REVIEWED")

    code, out, _ = run(["stats", "--log", log, "--today", "2026-12-01"], capsys)
    assert code == 0
    assert "1/1 = 100.0%  Wilson 95%" in out

    code, out, _ = run(["stats", "--log", log, "--json"], capsys)
    assert code == 0
    assert json.loads(out)["reviewed"] == 1

    code, out, _ = run(["verify", "--log", log], capsys)
    assert code == 0
    assert out.startswith("VERIFIED: 3 entries, 1 decisions, 1 reviews")


def test_cli_refusals_exit_1(tmp_path: Path, log: str, capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = run(["record", "--json", str(tmp_path / "missing.json"), "--log", log], capsys)
    assert code == 1
    assert "cannot read JSON" in err
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert run(["record", "--json", str(bad), "--log", log], capsys)[0] == 1
    assert run(["stats", "--log", log, "--today", "tomorrow"], capsys)[0] == 1
    code, out, _ = run(["verify", "--log", log], capsys)
    assert code == 1
    assert "not a verified one" in out


def test_cli_usage_error_is_a_refusal_not_an_integrity_failure(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = run(["stats", "--no-such-flag"], capsys)
    assert code == 1
    assert "REFUSED" in err
    assert run([], capsys)[0] == 1


def test_cli_integrity_failure_exits_2(log: str, capsys: pytest.CaptureFixture[str]) -> None:
    dl.record(log, good_record())
    text = Path(log).read_text(encoding="utf-8")
    Path(log).write_text(text.replace('"confidence":"Medium"', '"confidence":"High"'), encoding="utf-8")
    code, _, err = run(["stats", "--log", log], capsys)
    assert code == 2
    assert "INTEGRITY FAILURE" in err
    assert run(["verify", "--log", log], capsys)[0] == 2


def test_cli_reads_stdin(tmp_path: Path, log: str, capsys: pytest.CaptureFixture[str],
                         monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(good_record())))
    assert run(["record", "--json", "-", "--log", log], capsys)[0] == 0


def test_default_log_directory_is_gitignored() -> None:
    root = Path(dl.HERE).parent
    ignored = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "adjudication/decisions/" in ignored
    assert os.path.dirname(dl.DEFAULT_LOG).endswith(os.path.join("adjudication", "decisions"))


# ---------------------------------------------------------------- the sidecar and the anchor

def _two_decisions(log: str) -> None:
    dl.record(log, good_record(id="D-20260901-a", date="2026-09-01"))
    dl.record(log, good_record(id="D-20260902-b", date="2026-09-02"))


def test_a_missing_sidecar_is_an_integrity_failure_not_a_fresh_start(log: str) -> None:
    _two_decisions(log)
    os.remove(log + HEAD_SUFFIX)
    lines = Path(log).read_text(encoding="utf-8").splitlines(keepends=True)
    Path(log).write_text("".join(lines[:-1]), encoding="utf-8")
    with pytest.raises(dl.IntegrityError, match="sidecar"):
        dl.load(log)
    with pytest.raises(dl.IntegrityError, match="sidecar"):
        dl.record(log, good_record(id="D-20260902-b", date="2026-09-02", ex_ante_score=5))


def test_a_log_emptied_to_zero_bytes_is_not_an_empty_record(log: str) -> None:
    _two_decisions(log)
    Path(log).write_text("", encoding="utf-8")
    with pytest.raises(dl.IntegrityError, match="empty"):
        dl.load(log)
    with pytest.raises(dl.IntegrityError, match="empty"):
        dl.record(log, good_record(id="D-20260901-a", date="2026-09-01", ex_ante_score=5))


def test_a_sidecar_without_its_log_is_an_integrity_failure(log: str) -> None:
    _two_decisions(log)
    os.remove(log)
    with pytest.raises(dl.IntegrityError, match="missing"):
        dl.load(log)
    with pytest.raises(dl.IntegrityError, match="missing"):
        dl.review(log, good_review(id="D-20260901-a"))


def test_the_anchor_catches_a_truncation_with_a_forged_sidecar(log: str) -> None:
    _two_decisions(log)
    log_obj = dl._open(log)
    head, length = log_obj.head, len(log_obj)
    assert dl.load(log, head, length)[0].keys() == {"D-20260901-a", "D-20260902-b"}
    # Truncate and forge a sidecar for the survivor: the documented limit of an
    # unsigned chain, invisible without an anchor ...
    lines = Path(log).read_text(encoding="utf-8").splitlines(keepends=True)
    Path(log).write_text("".join(lines[:-1]), encoding="utf-8")
    survivor = json.loads(lines[-2])["entry_hash"]
    Path(log + HEAD_SUFFIX).write_text(json.dumps({"head": survivor, "length": length - 1}), encoding="utf-8")
    assert "D-20260902-b" not in dl.load(log)[0]
    # ... and caught by the anchor recorded before it.
    with pytest.raises(dl.IntegrityError, match="anchor says"):
        dl.load(log, None, length)
    with pytest.raises(dl.IntegrityError, match="truncated or rewritten"):
        dl.load(log, head, None)


def test_an_anchor_for_an_absent_log_fails(log: str) -> None:
    with pytest.raises(dl.IntegrityError, match="no log exists"):
        dl.load(log, "abc", 3)


def test_a_deeply_nested_line_in_the_log_is_an_integrity_failure(log: str) -> None:
    os.makedirs(os.path.dirname(log))
    Path(log).write_text("[" * 100000 + "]" * 100000 + "\n", encoding="utf-8")
    Path(log + HEAD_SUFFIX).write_text(json.dumps({"head": "x", "length": 1}), encoding="utf-8")
    with pytest.raises(dl.IntegrityError):
        dl.load(log)


# ---------------------------------------------------------------- one writer at a time

def test_two_writers_cannot_both_record_one_id(log: str, monkeypatch: pytest.MonkeyPatch) -> None:
    dl.record(log, good_record(id="D-20260901-seed", date="2026-09-01"))
    real_replay = dl.replay
    paused, release = threading.Event(), threading.Event()
    calls = {"n": 0}

    def slow_replay(entries: Any) -> Any:
        out = real_replay(entries)
        calls["n"] += 1
        if calls["n"] == 1:          # the first writer stops after its duplicate check
            paused.set()
            release.wait(timeout=10)
        return out

    monkeypatch.setattr(dl, "replay", slow_replay)
    results: list[str] = []

    def writer() -> None:
        try:
            dl.record(log, good_record())
            results.append("recorded")
        except dl.Refused:
            results.append("refused")

    first = threading.Thread(target=writer)
    first.start()
    assert paused.wait(timeout=10)
    second = threading.Thread(target=writer)
    second.start()
    time.sleep(0.3)                  # without the lock, the second writer finishes here
    release.set()
    first.join(timeout=10)
    second.join(timeout=10)
    monkeypatch.undo()
    assert sorted(results) == ["recorded", "refused"]
    assert "D-20260926-sponsor-tier" in dl.load(log)[0]


def test_the_lock_and_the_directory_fail_as_refusals(log: str, monkeypatch: pytest.MonkeyPatch) -> None:
    os.makedirs(log + ".lock")       # a directory where the lock file must go
    with pytest.raises(dl.Refused, match="writer lock"):
        dl.record(log, good_record())

    def no_dirs(*_: Any, **__: Any) -> None:
        raise PermissionError("denied")

    monkeypatch.setattr(dl.os, "makedirs", no_dirs)
    with pytest.raises(dl.Refused, match="cannot create the directory"):
        dl.record(log + "-other", good_record())


def test_a_log_that_cannot_be_created_is_a_refusal(log: str, monkeypatch: pytest.MonkeyPatch) -> None:
    def cannot_write(*_: Any, **__: Any) -> None:
        raise PermissionError("read-only")

    monkeypatch.setattr(dl, "DurableAuditLog", cannot_write)
    with pytest.raises(dl.Refused, match="cannot create the log"):
        dl.record(log, good_record())


# ---------------------------------------------------------------- write stamps

def _clock(stamp: str) -> Any:
    return lambda: stamp


def test_entries_carry_their_write_time_and_late_records_are_counted(log: str) -> None:
    dl.record(log, good_record(id="D-20260901-ontime", date="2026-09-01"), clock=_clock("2026-09-02T10:00:00+00:00"))
    dl.record(log, good_record(id="D-20260901-late", date="2026-09-01"), clock=_clock("2026-09-10T10:00:00+00:00"))
    dl.record(log, good_record(id="D-20260901-nostamp", date="2026-09-01"))
    text = Path(log).read_text(encoding="utf-8")
    assert '"at":"2026-09-10T10:00:00+00:00"' in text
    decisions, reviews = dl.load(log)
    assert decisions["D-20260901-late"][dl.WRITTEN_AT] == "2026-09-10T10:00:00+00:00"
    s = dl.compute(decisions, reviews)
    assert s.late == ["D-20260901-late"]
    assert s.unstamped == 1
    assert "hindsight risk): D-20260901-late" in "\n".join(dl.render(s, log))
    assert dl.as_json(s)["late"] == ["D-20260901-late"]


def test_future_dated_decisions_and_reviews_are_refused(log: str) -> None:
    with pytest.raises(dl.Refused, match="after the write date"):
        dl.record(log, good_record(), clock=_clock("2026-09-25T23:59:00+00:00"))
    dl.record(log, good_record(), clock=_clock("2026-09-26T08:00:00+00:00"))
    with pytest.raises(dl.Refused, match="after the write date"):
        dl.review(log, good_review(reviewed_on="2026-11-30"), clock=_clock("2026-10-01T08:00:00+00:00"))
    dl.review(log, good_review(reviewed_on="2026-10-01"), clock=_clock("2026-10-01T08:00:00+00:00"))


def test_a_write_stamp_cannot_be_supplied_as_input(log: str) -> None:
    assert any("unknown field: at" in p for p in dl.validate_record({**good_record(), "at": "2020-01-01"}))
    assert any("unknown field: _written_at" in p for p in dl.validate_record({**good_record(), dl.WRITTEN_AT: "x"}))


# ---------------------------------------------------------------- verify and the command line

def test_verify_prints_an_anchor_and_honours_it(tmp_path: Path, log: str, capsys: pytest.CaptureFixture[str]) -> None:
    rec = write_json(tmp_path, "rec.json", good_record())
    code, out, _ = run(["record", "--json", rec, "--log", log], capsys)
    assert code == 0
    assert "ANCHOR: --expect-head " in out
    code, out, _ = run(["verify", "--log", log], capsys)
    assert code == 0
    anchor_args = out.split("ANCHOR: ", 1)[1].split("  (", 1)[0].split()
    assert run(["verify", "--log", log, *anchor_args], capsys)[0] == 0
    assert run(["stats", "--log", log, *anchor_args], capsys)[0] == 0
    rec2 = write_json(tmp_path, "rec2.json", good_record(id="D-20260926-second"))
    assert run(["record", "--json", rec2, "--log", log], capsys)[0] == 0
    code, _, err = run(["verify", "--log", log, *anchor_args], capsys)
    assert code == 2
    assert "anchor" in err
    code, _, err = run(["verify", "--log", str(tmp_path / "none.jsonl"), "--expect-length", "2"], capsys)
    assert code == 2
    assert "no log exists" in err


def test_verify_refuses_a_verdict_that_failed(log: str, capsys: pytest.CaptureFixture[str],
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    dl.record(log, good_record())
    monkeypatch.setattr(DurableAuditLog, "verify",
                        lambda self, check_sidecar=True: ChainVerdict(False, 2, None, ["planted failure"]))
    code, _, err = run(["verify", "--log", log], capsys)
    assert code == 2
    assert "planted failure" in err


def test_cli_stamps_writes_with_the_current_time(tmp_path: Path, log: str, capsys: pytest.CaptureFixture[str]) -> None:
    today = dt.datetime.now(dt.UTC).date().isoformat()
    rec = write_json(tmp_path, "rec.json", good_record(id="D-20260926-today", date=today, review_date=today))
    assert run(["record", "--json", rec, "--log", log], capsys)[0] == 0
    assert f'"at":"{today}T' in Path(log).read_text(encoding="utf-8")
    rev = write_json(tmp_path, "rev.json", good_review(id="D-20260926-today", reviewed_on=today))
    code, out, _ = run(["review", "--json", rev, "--log", log], capsys)
    assert code == 0
    assert "ANCHOR:" in out


def test_cli_deeply_nested_json_input_is_a_refusal(tmp_path: Path, log: str, capsys: pytest.CaptureFixture[str]) -> None:
    deep = tmp_path / "deep.json"
    deep.write_text("[" * 100000 + "]" * 100000, encoding="utf-8")
    code, _, err = run(["record", "--json", str(deep), "--log", log], capsys)
    assert code == 1
    assert "RecursionError" in err
