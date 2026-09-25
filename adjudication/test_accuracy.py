"""Tests for the accuracy experiment -- SOP 8.4, the seeded-truth run.

WHY THIS FILE IS THE STRICTEST HERE. Its output is the answer to the question
asked from the first day: is the panel right? A wrong number here does not
cost a run, it costs the decision the whole tool exists to support. Every
failure mode worth pinning is one that would flatter the panel.
"""
from __future__ import annotations

from typing import ClassVar

import pytest

import accuracy as A
from stage_zero import Question


def _q(**kw):
    base = {"id": "q", "question": "which?", "answer": "alpha"}
    base.update(kw)
    return Question(**base)


class TestTheThreeOutcomes:

    def test_one_survivor_that_matches_is_resolved_correct(self):
        assert A.judge(["alpha"], _q())[0] == A.RESOLVED_CORRECT

    def test_one_survivor_that_does_not_match_is_resolved_wrong(self):
        assert A.judge(["beta"], _q())[0] == A.RESOLVED_WRONG

    def test_nothing_surviving_is_not_resolved_rather_than_wrong(self):
        """Every answer refuted is a real finding about the answers that were
        proposed. It is not the panel committing to something false, and
        scoring it as wrong would report a refusal to answer as an error."""
        outcome, note = A.judge([], _q())
        assert outcome == A.NOT_RESOLVED
        assert "nothing survived" in note

    def test_several_survivors_are_not_resolved_even_if_one_is_right(self):
        """THE ONE THAT WOULD FLATTER THE PANEL MOST. SOP 9.3: "the tool will
        not break the tie." Picking the survivor that happens to match the key
        would measure this scorer's generosity, not the panel's accuracy, and
        it would do it in the direction that makes the panel look good."""
        outcome, note = A.judge(["alpha", "beta"], _q())
        assert outcome == A.NOT_RESOLVED
        assert "not the same as the panel choosing one" in note

    def test_it_says_when_a_right_answer_was_among_the_survivors(self):
        """Recorded, because it is genuinely different from a tie in which
        none of the survivors was right -- and an operator needs to know
        which."""
        _, note = A.judge(["alpha", "beta"], _q())
        assert "1 of them would have scored correct" in note


class TestTheTwoRatesAreBothReported:

    @staticmethod
    def _acc(*results):
        a = A.Accuracy()
        for i, r in enumerate(results):
            a.outcomes.append(A.Outcome(f"q{i}", r))
        return a

    def test_accuracy_is_over_resolved_and_end_to_end_is_over_all(self):
        """A panel right every time it commits, committing twice in thirty,
        scores 1.000 and 0.067. Reporting only the first would be true and
        profoundly misleading."""
        a = self._acc(A.RESOLVED_CORRECT, A.RESOLVED_CORRECT,
                      *[A.NOT_RESOLVED] * 28)
        assert a.accuracy == pytest.approx(1.0)
        assert a.end_to_end == pytest.approx(2 / 30)
        text = "\n".join(A.render(a))
        assert "1.000" in text and "0.067" in text

    def test_resolving_nothing_gives_an_undefined_accuracy_not_zero(self):
        """THE CASE THE LAST REAL RUN PRODUCED: twelve answers standing, none
        chosen. A score of zero would mean it committed and was wrong. It did
        not commit."""
        a = self._acc(*[A.NOT_RESOLVED] * 5)
        text = "\n".join(A.render(a))
        assert "ACCURACY: UNDEFINED" in text
        assert "It did not commit" in text

    def test_a_thin_set_says_so(self):
        a = self._acc(A.RESOLVED_CORRECT)
        assert "THIN" in "\n".join(A.render(a))


class TestTheComparisonWithOneModel:

    @staticmethod
    def _acc(correct, n, baseline):
        a = A.Accuracy(baseline=baseline)
        for i in range(correct):
            a.outcomes.append(A.Outcome(f"c{i}", A.RESOLVED_CORRECT))
        for i in range(n - correct):
            a.outcomes.append(A.Outcome(f"w{i}", A.RESOLVED_WRONG))
        return a

    def test_it_says_plainly_when_the_panel_is_behind_one_model(self):
        """SOP 7.1 found exactly this across six benchmarks. If it happens
        here the report must say it, not bury it."""
        a = self._acc(10, 30, {"rate": 0.80, "low": 0.6, "high": 0.9})
        text = "\n".join(A.render(a))
        assert "BEHIND one model" in text
        assert "0.0%" in text

    def test_it_says_when_the_panel_is_ahead(self):
        a = self._acc(27, 30, {"rate": 0.30, "low": 0.2, "high": 0.5})
        assert "ahead by" in "\n".join(A.render(a))

    def test_it_tells_the_reader_to_compare_intervals_not_points(self):
        a = self._acc(16, 30, {"rate": 0.50, "low": 0.3, "high": 0.7})
        assert "Compare the INTERVALS" in "\n".join(A.render(a))

    def test_with_no_baseline_it_refuses_to_imply_a_comparison(self):
        a = self._acc(20, 30, None)
        text = "\n".join(A.render(a))
        assert "NO STAGE 0 BASELINE" in text
        assert "cannot say whether five seats beat one" in text


class TestFailuresAreNeverScoredAsWrongAnswers:

    def test_survivors_come_from_the_last_round_that_actually_looked(self):
        """A round whose closer failed never reaches the option bookkeeping,
        so its options_alive keeps the empty default. Reading that as "nothing
        survived" would score a transport failure as the panel refuting every
        answer."""
        class R:
            def __init__(self, observed, alive, texts):
                self.options_observed = observed
                self.options_alive = alive
                self.option_text = texts
        rounds = [R(True, ["o1"], {"o1": "alpha"}), R(False, [], {})]
        assert A._survivors(rounds) == ["alpha"]

    def test_no_round_ever_looked_gives_no_survivors(self):
        class R:
            options_observed = False
            options_alive: ClassVar[list[str]] = []
            option_text: ClassVar[dict[str, str]] = {}
        assert A._survivors([R()]) == []

    def test_an_id_with_no_recorded_text_falls_back_to_the_id(self):
        """Never a crash and never a silent drop: an unnamed survivor is still
        a survivor, and losing it would understate what stood."""
        class R:
            options_observed = True
            options_alive: ClassVar[list[str]] = ["o9"]
            option_text: ClassVar[dict[str, str]] = {}
        assert A._survivors([R()]) == ["o9"]


class TestItRefusesToSpendByAccident:

    def test_the_confirmation_is_required(self, monkeypatch, capsys):
        monkeypatch.setattr(A, "CONFIRM", "")
        assert A.main() == 2
        out = capsys.readouterr().out
        assert "ACCURACY_CONFIRM" in out
        # EVERY COST FIGURE, not one of them. The refusal exists so the price
        # is seen before it is paid, and a reader needs all three to judge:
        # what one run measured, what one run is bounded at, and what the
        # whole set comes to. Pinning only the total let a mutant strip the
        # per-run figures and stay green.
        for figure in ("$4.96", "$16.82", "$150", "$500"):
            assert figure in out, f"the refusal must state {figure}"

    def test_the_refusal_offers_a_cheap_first_step(self, monkeypatch, capsys):
        monkeypatch.setattr(A, "CONFIRM", "no")
        A.main()
        assert "ACCURACY_LIMIT=2" in capsys.readouterr().out
