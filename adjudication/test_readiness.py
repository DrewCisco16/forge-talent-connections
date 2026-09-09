"""
test_readiness.py -- the build tracker, and the counting it does on live replies.

WHY THIS FILE EXISTS. readiness.py was at 0% coverage. It is the file the
operator reads to learn what has been established, so a defect in it does not
break a run -- it misreports the state of the whole project, which is worse,
because nothing downstream contradicts it.

Its own comments record two rounds of the same error already: a fully
compliant panel counted at 15 of 32, and a passing check reported as failing.
Both were counting bugs on live replies. The tests below are about the third.

NOTHING HERE RUNS THE SUITE OR SHELLS OUT. `checks()` calls `_suite()`, which
runs pytest in a subprocess -- calling it from inside pytest would recurse.
The pure readers and predicates are what is tested; the two subprocess
functions are exercised only by the operator running the tracker.
"""
from __future__ import annotations

import json
import os

import pytest

import readiness as R


def _status(tmp_path, name, rounds):
    """A runs/<name>/status.md shaped the way run_night writes one."""
    d = tmp_path / "runs" / name
    d.mkdir(parents=True)
    (d / "status.md").write_text(
        "# status\n\n```json\n" + json.dumps(rounds) + "\n```\n",
        encoding="utf-8")
    return d


@pytest.fixture
def here(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "HERE", str(tmp_path))
    return tmp_path


class TestWhatItReadsOffDisk:

    def test_no_runs_is_no_rounds_rather_than_an_error(self, here):
        assert R._live_runs() == []
        assert R._corroborated_removals() == 0
        assert R._challenges_seen() == 0
        assert R._compliance() == (0, 0)

    def test_a_round_is_read_from_the_run_record(self, here):
        _status(here, "full-1", [
            {"round": 1, "options_created": 4,
             "options_removed": ["opt_a"], "challenges": 2},
            {"round": 2, "options_created": 0,
             "options_removed": [], "challenges": 0},
        ])
        rounds = R._live_runs()
        assert [r.n for r in rounds] == [1, 2]
        assert sum(r.created for r in rounds) == 4
        assert sum(r.removed for r in rounds) == 1
        assert sum(r.challenges for r in rounds) == 2

    def test_a_status_file_it_cannot_read_is_skipped_not_fatal(self, here):
        d = here / "runs" / "full-broken"
        d.mkdir(parents=True)
        (d / "status.md").write_text("no json fence here", encoding="utf-8")
        assert R._live_runs() == []
        assert R._corroborated_removals() == 0

    def test_only_a_corroborated_failure_counts_as_one(self, here):
        _status(here, "full-1", [{
            "round": 2, "rulings": [
                {"status": "fail", "detail": "agreed by 3 seats"},
                {"status": "fail", "detail": "its own formula gives 4"},
                {"status": "pass", "detail": "agreed by 3 seats"},
            ]}])
        assert R._corroborated_removals() == 1


class TestTheComplianceCountReadsWhatTheEngineReads:
    """The third round of this module's oldest bug.

    _compliance and _challenges_seen anchored on the start of the raw line, so
    a seat that wrote "- OPTION | ..." and "**PREDICATE | ...**" counted as
    having ignored the contract. On a tracker whose whole purpose is to say
    what has been established, that reports a working panel as a broken one --
    and the remedy an operator reaches for is a rewrite of the prompt.
    """

    BARE = "\n".join([
        "OPTION | rent capacity for six months",
        "PREDICATE | total cost | = | 12 dollars",
        "FORMULA | months * per_month",
        "INPUT | months = 6",
    ])
    DECORATED = "\n".join([
        "- **OPTION | rent capacity for six months**",
        "  - PREDICATE | total cost | = | 12 dollars",
        "  - FORMULA | months * per_month",
        "  - INPUT | months = 6",
    ])

    def _reply(self, here, text, run="full-1"):
        d = here / "runs" / run / "round-1"
        d.mkdir(parents=True)
        (d / "thinker-seat_1.md").write_text(text, encoding="utf-8")

    def test_a_bare_reply_counts_as_compliant(self, here):
        self._reply(here, self.BARE)
        assert R._compliance() == (1, 1)

    def test_a_decorated_reply_counts_as_compliant_too(self, here):
        self._reply(here, self.DECORATED)
        assert R._compliance() == (1, 1)

    def test_prose_is_still_counted_as_non_compliant(self, here):
        """The negative control. Undecorating must not turn a paragraph into
        a commitment: a seat that ignored the contract has to keep showing up
        as having ignored it."""
        self._reply(here, "I think renting is wiser, on balance.")
        assert R._compliance() == (0, 1)

    def test_a_decorated_challenge_is_counted(self, here):
        d = here / "runs" / "full-1" / "round-2"
        d.mkdir(parents=True)
        (d / "thinker-seat_2.md").write_text(
            "- **CHALLENGE | pred_abc123 | months = 3**\n"
            "1. CHALLENGE | pred_def456 | months = 4\n",
            encoding="utf-8")
        assert R._challenges_seen() == 2

    def test_only_the_most_recent_run_of_each_kind_is_counted(self, here):
        """Half the replies on disk predate the PREDICATE contract, and
        counting them was what put a compliant panel at 15 of 32."""
        self._reply(here, "old prose that could not comply", run="full-1")
        self._reply(here, self.DECORATED, run="full-2")
        assert R._compliance() == (1, 1)


class TestTheSpecificationChecksReadTheCodeNotAMemory:
    """Four predicates that take no filesystem and no network. Each answers a
    question about the build by reading the modules themselves, which is the
    only form of evidence this tracker accepts."""

    def test_the_fifth_pass_cannot_eliminate_in_either_engine(self):
        ok, detail = R._calibration_pass_is_inert()
        assert ok, detail
        assert "4/5 eliminative" in detail

    def test_the_stop_rule_is_reachable_from_the_engine_that_pays(self):
        ok, detail = R._stop_rule_reaches_a_live_run()
        assert ok, detail

    def test_every_hole_names_what_would_close_it(self):
        ok, detail = R._holes_name_their_remedy()
        assert ok, detail

    def test_the_accuracy_experiment_is_wired_and_refuses_to_spend(self):
        ok, detail = R._the_accuracy_experiment_is_reachable()
        assert ok, detail
        assert "UNRUN" in detail

    def test_the_queue_check_fails_closed_with_no_run_to_replay(self, here):
        ok, detail = R._the_queue_can_be_worked()
        assert not ok
        assert "no full run on disk" in detail


class TestTheMeterCannotReadAboveFull:
    """The weights are not guaranteed to sum to 100 and did not: three added
    checks took the total to 120 and the report printed "120% of 120%", which
    reads as a broken meter rather than a finished build."""

    def test_a_check_carries_its_own_evidence(self):
        c = R.Check("name", 5, "detail", True, "how it was established")
        assert (c.name, c.weight, c.done, c.evidence) == (
            "name", 5, True, "how it was established")

    def test_the_percentage_is_a_share_of_the_weights_that_exist(self):
        got = [R.Check("a", 15, "", True, ""),
               R.Check("b", 5, "", False, ""),
               R.Check("c", 100, "", True, "")]
        earned = sum(c.weight for c in got if c.done)
        total = sum(c.weight for c in got)
        assert total == 120
        assert round(100.0 * earned / total) == 96

    def test_the_module_never_promises_a_correctness_figure(self):
        """The one sentence this file exists to keep true. A tracker that
        drifted into reporting how likely an answer is to be right would be
        the exact failure the design exists to prevent."""
        with open(os.path.join(os.path.dirname(R.__file__), "readiness.py"),
                  encoding="utf-8") as fh:
            text = fh.read()
        assert "THIS IS NOT A CONFIDENCE THAT ANY ANSWER IS CORRECT." in text
        assert "NOT MEASURED, AND NOT MEASURABLE FROM A RUN" in text


class TestTheReportItPrints:
    """`checks()` shells out to pytest and to the three static tools, so the
    assembly and the rendering are tested with those two stubbed. Everything
    else in the list is computed for real from the fixtures above."""

    @pytest.fixture
    def stubbed(self, here, monkeypatch):
        monkeypatch.setattr(R, "_suite", lambda: (1649, 0))
        monkeypatch.setattr(R, "_tool_clean", lambda _cmd: True)
        return here

    def test_every_check_carries_a_name_a_weight_and_its_evidence(self,
                                                                 stubbed):
        """A square with no evidence is a claim, and this file's whole
        contract is that nothing in it is asserted from memory."""
        got = R.checks()
        assert got
        for c in got:
            assert c.name and c.evidence, c.name
            assert c.weight > 0, c.name
            assert isinstance(c.done, bool), c.name

    def test_a_check_with_no_live_run_behind_it_is_not_ticked(self, stubbed):
        """Fail-closed, and the reason this tracker exists: an unticked
        square that could never be ticked reports progress already made as
        progress still owed, and a ticked one with nothing behind it is
        worse."""
        by_name = {c.name: c for c in R.checks()}
        assert by_name["offline suite"].done
        assert not by_name["seats write the contract"].done
        assert not by_name["all five rounds run"].done

    def test_the_meter_never_reads_above_full(self, stubbed, capsys):
        """The weights are not guaranteed to sum to 100 and did not: three
        added checks took the total to 120 and the report printed
        "120% of 120%", which reads as a broken meter rather than a finished
        build."""
        assert R.main() == 0
        out = capsys.readouterr().out
        pct = int(next(line for line in out.splitlines()
                       if "established by evidence" in line).split("%")[0])
        assert 0 <= pct <= 100

    def test_the_report_refuses_to_offer_a_correctness_figure(self, stubbed,
                                                             capsys):
        R.main()
        out = capsys.readouterr().out
        assert "THIS IS NOT A CONFIDENCE THAT ANY ANSWER IS CORRECT." in out
        assert "ANSWER CORRECTNESS: NOT MEASURED" in out

    def test_a_reply_it_cannot_open_is_skipped_rather_than_counted(self,
                                                                  here):
        """A directory where a reply file should be. seen must not count it:
        a file that could not be read is not a seat that said nothing."""
        d = here / "runs" / "probe-1" / "seat_1.md"
        d.mkdir(parents=True)
        assert R._compliance() == (0, 0)
