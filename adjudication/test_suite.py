"""
test_suite.py — comprehensive tests for the adjudication toolchain.

Run:      pytest test_suite.py -v
Coverage: pytest test_suite.py --cov=. --cov-report=term-missing

Organised into six groups:
  1. Independence math      (effective seats, error correlation)
  2. Capture-recapture      (Chao1, Lincoln-Petersen)
  3. Deterministic gates    (arithmetic, citation, schema, tests)
  4. SAFETY                 (expression evaluator must not execute code)
  5. Orchestrator routing   (accept / eliminate / escalate)
  6. Convergence + stopping (decay fit, residual, stop conditions)
"""

import math
import pytest

import seat_independence as SI
import adjudication_orchestrator as AO
from adjudication_orchestrator import TestExecutionGate as ExecGate
from adjudication_orchestrator import (
    Claim, ClaimKind, Candidate, Pass, GateStatus,
    ArithmeticGate, CitationResolutionGate, SchemaGate,
    Orchestrator, preflight, fit_decay, residual_estimate, chao1_lower_bound,
)

import numpy as np


# ===================================================== 1. INDEPENDENCE MATH

class TestEffectiveSeats:
    def test_zero_correlation_gives_full_count(self):
        assert SI.effective_seats(5, 0.0) == pytest.approx(5.0)

    def test_perfect_correlation_collapses_to_one(self):
        assert SI.effective_seats(5, 1.0) == pytest.approx(1.0)

    @pytest.mark.parametrize("rho,expected", [
        (0.2, 2.7778), (0.4, 1.9231), (0.6, 1.4706), (0.8, 1.1905),
    ])
    def test_published_table_values(self, rho, expected):
        """These are the numbers printed in the SOP manual, Section 6.1."""
        assert SI.effective_seats(5, rho) == pytest.approx(expected, abs=1e-3)

    def test_negative_correlation_is_clamped(self):
        """Must never claim MORE independent seats than models present."""
        assert SI.effective_seats(5, -0.5) == pytest.approx(5.0)

    def test_single_seat_is_identity(self):
        assert SI.effective_seats(1, 0.6) == pytest.approx(1.0)

    def test_adding_a_sixth_seat_buys_almost_nothing_at_high_rho(self):
        """The economic argument in the manual: 20% more cost, ~3% more seats."""
        gain = SI.effective_seats(6, 0.6) - SI.effective_seats(5, 0.6)
        assert 0 < gain < 0.10


class TestErrorCorrelation:
    def test_identical_seats_correlate_perfectly(self):
        col = np.array([1, 0, 1, 0, 1, 0, 1, 0])
        X = np.column_stack([col, col, col])
        assert SI.mean_error_correlation(X) == pytest.approx(1.0)

    def test_independent_seats_correlate_near_zero(self):
        rng = np.random.default_rng(0)
        X = (rng.random((4000, 3)) < 0.7).astype(int)
        assert abs(SI.mean_error_correlation(X)) < 0.06

    def test_shared_hard_items_produce_positive_correlation(self):
        rng = np.random.default_rng(1)
        n = 2000
        Z = rng.random(n) < 0.3           # items everyone finds hard
        X = np.column_stack([
            (rng.random(n) < np.where(Z, 0.3, 0.95)).astype(int) for _ in range(3)
        ])
        assert SI.mean_error_correlation(X) > 0.25

    def test_correlation_matrix_is_symmetric_with_unit_diagonal(self):
        rng = np.random.default_rng(2)
        X = (rng.random((300, 4)) < 0.6).astype(int)
        C = SI.pairwise_error_correlation(X)
        assert C.shape == (4, 4)
        assert np.allclose(np.diag(C), 1.0)
        assert np.allclose(C, C.T, equal_nan=True)

    def test_constant_seat_yields_nan_not_crash(self):
        """A seat that never errs has zero variance — must not raise."""
        X = np.column_stack([np.ones(50, dtype=int),
                             (np.arange(50) % 2)])
        C = SI.pairwise_error_correlation(X)
        assert np.isnan(C[0, 1])


class TestConditionalAgreement:
    def test_always_same_wrong_answer_is_one(self):
        answers = [["X", "X"], ["X", "X"]]
        truth = ["A", "A"]
        assert SI.conditional_agreement_given_error(answers, truth) == pytest.approx(1.0)

    def test_always_different_wrong_answers_is_zero(self):
        answers = [["X", "Y"], ["P", "Q"]]
        truth = ["A", "A"]
        assert SI.conditional_agreement_given_error(answers, truth) == pytest.approx(0.0)

    def test_no_double_errors_returns_nan(self):
        answers = [["A", "A"], ["A", "A"]]
        truth = ["A", "A"]
        assert math.isnan(SI.conditional_agreement_given_error(answers, truth))


# ===================================================== 2. CAPTURE-RECAPTURE

class TestChao1:
    def test_hand_computed_case(self):
        """counts: 1->2, 2->1, 3->2, 4->1  =>  S_obs=4, f1=2, f2=2
           Chao1 = 4 + 2^2/(2*2) = 5.0"""
        det = {"a": {1, 2, 3}, "b": {3, 4}, "c": {1}}
        r = chao1_lower_bound(det)
        assert r["observed"] == 4
        assert r["f1_singletons"] == 2
        assert r["f2_doubletons"] == 2
        assert r["estimated_total_lower_bound"] == pytest.approx(5.0)
        assert r["estimated_missed"] == pytest.approx(1.0)

    def test_all_singletons_flags_high_residual(self):
        det = {"a": {1}, "b": {2}, "c": {3}, "d": {4}}
        r = chao1_lower_bound(det)
        assert r["observed"] == 4
        assert r["singleton_fraction"] == pytest.approx(1.0)
        assert r["estimated_missed"] > 0

    def test_full_overlap_implies_nothing_missed(self):
        """Every seat caught every error -> no singletons -> no residual."""
        det = {"a": {1, 2, 3}, "b": {1, 2, 3}, "c": {1, 2, 3}}
        r = chao1_lower_bound(det)
        assert r["estimated_missed"] == pytest.approx(0.0)

    def test_estimate_never_below_observed(self):
        det = {"a": {1, 2}, "b": {2, 3}}
        r = chao1_lower_bound(det)
        assert r["estimated_total_lower_bound"] >= r["observed"]


class TestLincolnPetersen:
    def test_chapman_handles_zero_overlap(self):
        """Plain LP divides by zero here; Chapman must stay finite."""
        assert math.isfinite(SI.lincoln_petersen(10, 10, 0, chapman=True))

    def test_plain_estimator_known_value(self):
        assert SI.lincoln_petersen(10, 20, 5, chapman=False) == pytest.approx(40.0)

    def test_more_overlap_implies_smaller_population(self):
        high = SI.lincoln_petersen(10, 10, 9)
        low = SI.lincoln_petersen(10, 10, 2)
        assert high < low


# ===================================================== 3. GATES

class TestArithmeticGate:
    g = ArithmeticGate()

    def _claim(self, warrant):
        return Claim("c", "t", ClaimKind.ARITHMETIC, warrant)

    def test_correct_arithmetic_passes(self):
        assert self.g.check(self._claim("12 + 35 = 47")).status is GateStatus.PASS

    def test_incorrect_arithmetic_fails(self):
        r = self.g.check(self._claim("12 + 35 = 50"))
        assert r.status is GateStatus.FAIL
        assert "47" in r.detail

    def test_float_tolerance(self):
        assert self.g.check(self._claim("1/3 = 0.3333333333333333")).status is GateStatus.PASS

    def test_malformed_warrant_fails_closed(self):
        """Unparseable input must FAIL, never PASS."""
        assert self.g.check(self._claim("banana")).status is GateStatus.FAIL

    def test_applies_only_to_arithmetic_with_warrant(self):
        assert not self.g.applies_to(Claim("c", "t", ClaimKind.JUDGMENT, "1+1=2"))
        assert not self.g.applies_to(Claim("c", "t", ClaimKind.ARITHMETIC, None))


class TestCitationGate:
    def test_resolving_doi_passes(self):
        g = CitationResolutionGate(lambda i: True)
        c = Claim("c", "t", ClaimKind.CITATION, "10.1038/s42256-026-01268-y")
        assert g.check(c).status is GateStatus.PASS

    def test_nonresolving_doi_fails(self):
        g = CitationResolutionGate(lambda i: False)
        c = Claim("c", "t", ClaimKind.CITATION, "10.9999/fabricated")
        assert g.check(c).status is GateStatus.FAIL

    def test_malformed_identifier_fails_before_network_call(self):
        called = []
        g = CitationResolutionGate(lambda i: called.append(i) or True)
        c = Claim("c", "t", ClaimKind.CITATION, "not-a-doi")
        assert g.check(c).status is GateStatus.FAIL
        assert called == [], "resolver must not be called on malformed input"

    def test_resolver_exception_fails_closed(self):
        def boom(i):
            raise ConnectionError("network down")
        g = CitationResolutionGate(boom)
        c = Claim("c", "t", ClaimKind.CITATION, "10.1000/x")
        assert g.check(c).status is GateStatus.FAIL


class TestSchemaGate:
    def test_valid_payload_passes(self):
        g = SchemaGate(["id", "value"])
        assert g.check(Claim("c", "t", ClaimKind.SCHEMA,
                             '{"id": 1, "value": 2}')).status is GateStatus.PASS

    def test_missing_key_fails(self):
        g = SchemaGate(["id", "value"])
        r = g.check(Claim("c", "t", ClaimKind.SCHEMA, '{"id": 1}'))
        assert r.status is GateStatus.FAIL and "value" in r.detail

    def test_invalid_json_fails(self):
        g = SchemaGate([])
        assert g.check(Claim("c", "t", ClaimKind.SCHEMA, "{bad")).status is GateStatus.FAIL


class TestExecGate:
    def test_passing_suite(self):
        g = ExecGate(lambda cmd: True)
        assert g.check(Claim("c", "t", ClaimKind.CODE_BEHAVIOR, "pytest")).status is GateStatus.PASS

    def test_runner_exception_fails_closed(self):
        def boom(cmd):
            raise OSError("no such command")
        g = ExecGate(boom)
        assert g.check(Claim("c", "t", ClaimKind.CODE_BEHAVIOR, "x")).status is GateStatus.FAIL


# ===================================================== 4. SAFETY

class TestExpressionEvaluatorSafety:
    """
    ArithmeticGate parses model-supplied strings. It must never execute code.
    A model can propose an arbitrary warrant, so this is an injection surface.
    """
    g = ArithmeticGate()

    @pytest.mark.parametrize("payload", [
        "__import__('os').system('echo pwned') = 0",
        "open('/etc/passwd').read() = 1",
        "(lambda: 1)() = 1",
        "[].__class__ = 1",
        "exec('x=1') = 1",
        "globals() = 1",
    ])
    def test_code_execution_attempts_are_rejected(self, payload):
        r = self.g.check(Claim("c", "t", ClaimKind.ARITHMETIC, payload))
        assert r.status is GateStatus.FAIL, f"SECURITY: evaluated {payload!r}"

    def test_no_side_effect_file_is_created(self, tmp_path):
        marker = tmp_path / "pwned.txt"
        payload = f"__import__('pathlib').Path('{marker}').write_text('x') = 1"
        self.g.check(Claim("c", "t", ClaimKind.ARITHMETIC, payload))
        assert not marker.exists()

    def test_legitimate_math_still_works(self):
        assert self.g.check(Claim("c", "t", ClaimKind.ARITHMETIC,
                                  "2 ** 10 = 1024")).status is GateStatus.PASS


# ===================================================== 5. PREFLIGHT

class TestPreflight:
    def test_saturated_baseline_blocks_the_ensemble(self):
        v = preflight(0.62, task_is_decomposable=True)
        assert v.run_ensemble is False and v.recommended_seats == 1

    def test_sequential_task_blocks_the_ensemble(self):
        v = preflight(0.20, task_is_decomposable=False)
        assert v.run_ensemble is False

    def test_low_baseline_decomposable_task_runs(self):
        v = preflight(0.31, task_is_decomposable=True)
        assert v.run_ensemble is True

    def test_seat_count_is_capped_at_three(self):
        v = preflight(0.31, task_is_decomposable=True, requested_seats=9)
        assert v.recommended_seats == AO.MAX_RECOMMENDED_SEATS == 3

    def test_boundary_exactly_at_threshold_still_runs(self):
        v = preflight(AO.CAPABILITY_SATURATION_THRESHOLD, task_is_decomposable=True)
        assert v.run_ensemble is True

    def test_sequential_check_precedes_baseline_check(self):
        """A sequential task is refused regardless of how low the baseline is."""
        assert preflight(0.01, task_is_decomposable=False).run_ensemble is False


# ===================================================== 6. ORCHESTRATOR

def _orch(resolver=lambda i: True):
    return Orchestrator([ArithmeticGate(), CitationResolutionGate(resolver)])


ELIM = Pass("pe", "Eliminative", "x", True)
CALIB = Pass("pc", "Calibration", "x", False)


class TestOrchestratorRouting:
    def test_gate_pass_is_auto_accepted(self):
        o = _orch()
        rec = o.run_pass(ELIM, [], [Claim("c1", "t", ClaimKind.ARITHMETIC, "2+2 = 4")])
        assert (rec.auto_accepted, rec.auto_rejected, rec.escalated) == (1, 0, 0)

    def test_gate_fail_eliminates_the_carrying_candidate(self):
        o = _orch()
        claim = Claim("c1", "t", ClaimKind.ARITHMETIC, "2+2 = 5")
        cand = Candidate("A", "answer", [claim])
        o.run_pass(ELIM, [cand], [claim])
        assert cand.eliminated is True
        assert "arithmetic" in cand.elimination_reason

    def test_judgment_claim_escalates_and_is_never_accepted(self):
        o = _orch()
        rec = o.run_pass(ELIM, [], [Claim("c1", "t", ClaimKind.JUDGMENT, None)])
        assert rec.escalated == 1 and rec.auto_accepted == 0
        assert len(o.escalation_queue) == 1

    def test_non_eliminative_pass_never_eliminates(self):
        """Bayesian calibration reweights; it must not remove candidates."""
        o = _orch()
        claim = Claim("c1", "t", ClaimKind.ARITHMETIC, "2+2 = 5")
        cand = Candidate("A", "answer", [claim])
        o.run_pass(CALIB, [cand], [claim])
        assert cand.eliminated is False

    def test_duplicate_claim_is_adjudicated_once(self):
        o = _orch()
        c = Claim("dup", "t", ClaimKind.ARITHMETIC, "2+2 = 4")
        o.run_pass(ELIM, [], [c])
        rec2 = o.run_pass(ELIM, [], [c])
        assert rec2.auto_accepted == 0

    def test_detections_are_tracked_per_seat(self):
        o = _orch()
        o.run_pass(ELIM, [], [
            Claim("c1", "t", ClaimKind.ARITHMETIC, "1+1 = 2", source_seat="s1"),
            Claim("c2", "t", ClaimKind.ARITHMETIC, "1+1 = 2", source_seat="s2"),
        ])
        assert o.detections_by_seat["s1"] == {"c1"}
        assert o.detections_by_seat["s2"] == {"c2"}

    def test_unaffected_candidate_survives(self):
        o = _orch()
        bad = Claim("bad", "t", ClaimKind.ARITHMETIC, "1+1 = 3")
        a = Candidate("A", "a", [bad])
        b = Candidate("B", "b", [])
        o.run_pass(ELIM, [a, b], [bad])
        assert a.eliminated and not b.eliminated
        assert [c.id for c in o.survivors([a, b])] == ["B"]


# ===================================================== 7. CONVERGENCE

class TestDecayAndStopping:
    def test_fit_recovers_known_decay(self):
        a_true, b_true = 20.0, 0.5
        ys = [a_true * math.exp(-b_true * k) for k in range(1, 7)]
        a, b = fit_decay(ys)
        assert b == pytest.approx(b_true, abs=1e-6)
        assert a == pytest.approx(a_true, abs=1e-6)

    def test_residual_is_positive_and_small_for_fast_decay(self):
        r = residual_estimate([20, 7, 2.5, 0.9])
        assert 0 < r < 1.0

    def test_flat_yields_refuse_to_produce_a_stopping_estimate(self):
        """If nothing is decaying you have NOT converged — must return None."""
        assert residual_estimate([5, 5, 5, 5]) is None

    def test_increasing_yields_refuse_to_stop(self):
        assert residual_estimate([1, 3, 8, 20]) is None

    def test_too_few_points_returns_none(self):
        assert fit_decay([7]) is None

    def test_stop_blocked_while_queue_is_dirty(self):
        o = _orch()
        o.run_pass(ELIM, [], [Claim("j1", "t", ClaimKind.JUDGMENT, None)])
        s = o.should_stop([])
        assert s["escalations_pending"] == 1
        assert s["WARNING"] is not None
        assert "17.2" in s["WARNING"]

    def test_stop_triggers_when_candidates_reduced(self):
        o = _orch()
        bad = Claim("b", "t", ClaimKind.ARITHMETIC, "1+1 = 3")
        a, b = Candidate("A", "a", [bad]), Candidate("B", "b", [])
        o.run_pass(ELIM, [a, b], [bad])
        s = o.should_stop([a, b])
        assert s["stop"] is True and s["surviving_candidates"] == 1

    def test_report_is_serialisable(self):
        import json
        o = _orch()
        o.run_pass(ELIM, [], [Claim("j", "t", ClaimKind.JUDGMENT, None)])
        json.dumps(o.report())


# ===================================================== 8. END TO END

class TestEndToEnd:
    def test_full_run_matches_documented_demo_behaviour(self):
        o = Orchestrator([ArithmeticGate(),
                          CitationResolutionGate(lambda i: i.startswith("10.1038"))])
        cands = [Candidate("A", "A"), Candidate("B", "B"), Candidate("C", "C")]
        p1 = [Claim("c1", "", ClaimKind.ARITHMETIC, "12 + 35 = 47", source_seat="s1"),
              Claim("c2", "", ClaimKind.ARITHMETIC, "12 + 35 = 50", source_seat="s2"),
              Claim("c3", "", ClaimKind.JUDGMENT, None, source_seat="s1")]
        p2 = [Claim("c4", "", ClaimKind.CITATION, "10.1038/real", source_seat="s2"),
              Claim("c5", "", ClaimKind.CITATION, "10.9999/fake", source_seat="s3")]
        cands[1].claims.append(p1[1])
        cands[2].claims.append(p2[1])

        r1 = o.run_pass(AO.DEFAULT_PASSES[0], cands, p1)
        r2 = o.run_pass(AO.DEFAULT_PASSES[1], cands, p2)

        assert r1.eliminated_candidates == ["B"]
        assert r2.eliminated_candidates == ["C"]
        assert len(o.survivors(cands)) == 1
        assert o.survivors(cands)[0].id == "A"
        # one judgment claim remains unresolved -> must warn against committing
        assert o.should_stop(cands)["WARNING"] is not None
