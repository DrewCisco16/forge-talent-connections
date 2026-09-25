"""Tests for Stage 0 -- SOP 8.1, the step that decides whether to build.

WHY THESE ARE STRICTER THAN THEY LOOK. Stage 0's output is a single number
that decides whether months of work continue. Every way it could be wrong is
a way to spend or save the wrong months, so the failure modes worth pinning
are the ones that produce a PLAUSIBLE number rather than an obvious error:
a grader that is too lenient, an interval read as though it decided something
it does not, a call failure scored as a wrong answer.
"""
from __future__ import annotations

import json

import pytest

import stage_zero as S


def _q(**kw):
    base = {"id": "q", "question": "x?", "answer": "1"}
    base.update(kw)
    return S.Question(**base)


# ---------------------------------------------------------------------------
# 1. the refusal that matters most
# ---------------------------------------------------------------------------

class TestItRefusesToInventGroundTruth:

    def test_a_missing_question_set_names_what_is_needed(self, tmp_path):
        """SOP 8.1 step 3 is the operator's own domain data by definition. A
        baseline measured on another task class predicts nothing about this
        one -- SOP 10.1 gives leave-one-domain-out R-squared = -2.09."""
        with pytest.raises(S.QuestionSetError, match="thirty real examples"):
            S.load_questions(str(tmp_path / "nope.json"))

    def test_an_empty_answer_is_refused_rather_than_scored(self, tmp_path):
        p = tmp_path / "q.json"
        p.write_text(json.dumps([{"id": "a", "question": "x?", "answer": ""}]))
        with pytest.raises(S.QuestionSetError, match="answer is empty"):
            S.load_questions(str(p))

    def test_duplicate_ids_are_refused(self, tmp_path):
        p = tmp_path / "q.json"
        p.write_text(json.dumps([
            {"id": "a", "question": "x?", "answer": "1"},
            {"id": "a", "question": "y?", "answer": "2"}]))
        with pytest.raises(S.QuestionSetError, match="duplicate"):
            S.load_questions(str(p))

    def test_the_shipped_template_parses(self):
        """A template nobody can load is a template nobody fills in."""
        qs = S.load_questions("stage-zero-questions.example.json")
        assert len(qs) == 3
        assert {q.kind for q in qs} == {"exact", "numeric", "oneof"}

    def test_an_unreadable_numeric_answer_is_refused_at_load(self):
        with pytest.raises(S.QuestionSetError):
            _q(answer="about seven", kind="numeric")


# ---------------------------------------------------------------------------
# 2. no model ever grades a model
# ---------------------------------------------------------------------------

class TestScoringIsMechanical:

    @pytest.mark.parametrize("given,ok", [
        ("10000.02", True), ("$10,000.02", True), ("10000.04", True),
        ("10000.05", False), ("10001", False), ("nonsense", False),
    ])
    def test_numeric_compares_numbers_within_tolerance(self, given, ok):
        q = _q(answer="10000.02", kind="numeric", tolerance="0.02")
        assert S.score(given, q) is ok

    @pytest.mark.parametrize("given,ok", [
        ("14.3", True), ("  14.3  ", True), ("Clause 14.3", False),
        ("14.4", False),
    ])
    def test_exact_folds_case_and_punctuation_but_not_meaning(self, given, ok):
        assert S.score(given, _q(answer="14.3")) is ok

    def test_oneof_accepts_any_listed_form(self):
        q = _q(answer="yes", kind="oneof", accept=("yes", "y", "affirmative"))
        assert S.score("Y", q) is True
        assert S.score("affirmative!", q) is True
        assert S.score("no", q) is False

    def test_a_paraphrase_scores_wrong_and_that_is_deliberate(self):
        """Nothing here reads for sense. A grader that guesses at intent is a
        grader nobody can check, and the alternative -- a model judging -- is
        the correlated error the baseline exists to measure."""
        assert S.score("fourteen point three", _q(answer="14.3")) is False


# ---------------------------------------------------------------------------
# 3. an unanswered question is not a wrong answer
# ---------------------------------------------------------------------------

class TestUnansweredIsNotWrong:

    def test_no_answer_line_scores_none(self):
        assert S.score(None, _q()) is None

    def test_it_is_excluded_from_the_rate_rather_than_counted_against(self):
        """Counting a missing ANSWER line as wrong UNDERSTATES the baseline,
        which biases the 0.45 gate toward building the ensemble -- the
        expensive direction. The bias has to run the other way."""
        qs = [_q(id=f"q{i}", answer="1", kind="numeric") for i in range(4)]
        replies = ["ANSWER: 1", "ANSWER: 1", "no answer here", "ANSWER: 2"]
        it = iter(replies)
        b = S.measure(qs, lambda _p: next(it))
        assert (b.correct, b.wrong, b.unanswered) == (2, 1, 1)
        assert b.scored == 3
        assert b.rate == pytest.approx(2 / 3)

    def test_a_call_failure_is_not_a_wrong_answer(self):
        """A transport error says nothing about the model's knowledge."""
        def boom(_p):
            raise RuntimeError("connection reset")
        b = S.measure([_q()], boom)
        assert (b.correct, b.wrong, b.unanswered) == (0, 0, 1)

    def test_the_last_answer_line_wins(self):
        """A model that reasons aloud puts its conclusion last; taking the
        first would grade a worked step."""
        assert S.extract_answer("ANSWER: 3\nno wait\nANSWER: 4") == "4"


# ---------------------------------------------------------------------------
# 4. the gate is read on the interval, not the point
# ---------------------------------------------------------------------------

class TestTheGateIsReadOnTheInterval:

    @staticmethod
    def _b(correct, n):
        low, high = S.wilson(correct, n)
        return S.Baseline(n, correct, n - correct, 0, low, high)

    def test_a_point_estimate_near_the_threshold_decides_nothing(self):
        """14/30 is 0.467, just over the 0.45 threshold. Read as a point it
        says do not build. Its interval runs roughly 0.30 to 0.64 and contains
        the threshold, so it settles nothing -- and reading the point as
        though it did is how a coin flip becomes a months-long build."""
        b = self._b(14, 30)
        assert b.rate > 0.45
        assert b.low < 0.45 < b.high
        assert b.verdict == "INCONCLUSIVE"

    def test_a_clearly_strong_model_stops_the_build(self):
        b = self._b(29, 30)
        assert b.verdict == "DO NOT BUILD THE ENSEMBLE"

    def test_a_clearly_weak_model_justifies_the_panel(self):
        b = self._b(2, 30)
        assert b.verdict == "ENSEMBLE JUSTIFIED"

    def test_too_few_questions_cannot_decide_however_clean_the_score(self):
        """Five out of five is a rate of 1.0 and settles nothing. SOP 8.1
        step 3 asks for thirty and the interval shows why."""
        b = self._b(5, 5)
        assert b.rate == 1.0
        assert b.verdict == "INSUFFICIENT"

    def test_wilson_stays_inside_zero_and_one(self):
        """The normal approximation runs outside [0,1] at the extremes, which
        is exactly where a baseline of 0 or 1 lands."""
        for k, n in ((0, 30), (30, 30), (0, 1), (1, 1)):
            low, high = S.wilson(k, n)
            assert 0.0 <= low <= high <= 1.0

    @pytest.mark.parametrize("k,n,low,high", [
        (0, 30, 0.0000, 0.1135),
        (14, 30, 0.3023, 0.6386),
        (15, 30, 0.3315, 0.6685),
        (29, 30, 0.8333, 0.9941),
        (30, 30, 0.8865, 1.0000),
    ])
    def test_it_is_the_wilson_interval_and_not_the_normal_approximation(
            self, k, n, low, high):
        """MUTATION TESTING ADDED THIS. Asserting only that the bounds sit
        inside [0,1] does not distinguish Wilson from the textbook normal
        approximation, because the clamp puts that inside [0,1] too -- so
        replacing the estimator wholesale left every test green.

        The difference is not cosmetic at the sizes Stage 0 runs at. With
        nothing correct out of thirty, the normal approximation gives an upper
        bound near 0.064 and Wilson gives 0.1135 -- nearly double. An interval
        that is too narrow is one that decides the 0.45 gate when the evidence
        cannot."""
        got_low, got_high = S.wilson(k, n)
        assert got_low == pytest.approx(low, abs=5e-4)
        assert got_high == pytest.approx(high, abs=5e-4)

    def test_the_interval_is_asymmetric_near_the_extremes(self):
        """The property that makes Wilson the right choice: at k=0 the whole
        interval sits above the point estimate, because a run of thirty
        failures does not establish that the true rate is zero."""
        low, high = S.wilson(0, 30)
        assert low == 0.0
        assert high > 0.10, "a symmetric interval would collapse this"


# ---------------------------------------------------------------------------
# 5. what the operator actually reads
# ---------------------------------------------------------------------------

class TestTheReport:

    def test_a_sequential_task_is_stopped_before_any_call(self):
        """SOP 8.1 step 2 can end the exercise on its own: a strictly
        sequential task measured -70%. Measuring a baseline for a task the
        manual already refuses is spending money to confirm a stop."""
        text = "\n".join(S.render(S.Baseline(30, 0, 0, 0, 0.0, 1.0),
                                  "x", decomposes=False))
        assert "Do not build this" in text

    def test_the_misses_are_printed_so_the_number_can_be_challenged(self):
        qs = [_q(id=f"q{i}", answer="1", kind="numeric") for i in range(2)]
        it = iter(["ANSWER: 1", "ANSWER: 9"])
        b = S.measure(qs, lambda _p: next(it))
        text = "\n".join(S.render(b, "x", decomposes=True))
        assert "q1" in text and "'9'" in text

    def test_an_undecided_verdict_never_prints_preflight_as_agreement(self):
        """It was doing this. A baseline of 0.567 with an interval straddling
        0.45 came out INCONCLUSIVE, and directly beneath it: "preflight()
        agrees: ... Run one seat plus deterministic gates." preflight decides
        on the POINT estimate and this section decides on the INTERVAL, so
        when the interval settles nothing, printing preflight's firm answer
        under "agrees" hands the reader a decision the evidence cannot carry.
        """
        low, high = S.wilson(17, 30)
        b = S.Baseline(30, 17, 13, 0, low, high)
        assert b.verdict == "INCONCLUSIVE"
        text = "\n".join(S.render(b, "x", decomposes=True))
        assert "preflight() agrees" not in text
        assert "DOES NOT SUPPORT THAT" in text

    def test_a_decided_verdict_does_report_the_agreement(self):
        low, high = S.wilson(29, 30)
        b = S.Baseline(30, 29, 1, 0, low, high)
        assert b.verdict == "DO NOT BUILD THE ENSEMBLE"
        assert "preflight() agrees" in "\n".join(
            S.render(b, "x", decomposes=True))

    def test_it_never_prints_a_baseline_it_did_not_measure(self):
        b = S.Baseline(0, 0, 0, 0, 0.0, 1.0)
        text = "\n".join(S.render(b, "x", decomposes=True))
        assert "NOT MEASURED" in text
