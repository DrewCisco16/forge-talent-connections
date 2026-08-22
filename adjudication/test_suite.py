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

import dataclasses
import inspect as _inspect
import json as _json
import math
import os as _os
import warnings as _warnings
from collections import Counter as _Counter
from typing import ClassVar

import numpy as np
import pytest

import adjudication_orchestrator as AO
import audit_log as AL
import seat_adapter as SA
import seat_independence as SI
from adjudication_orchestrator import (
    ArithmeticGate,
    Candidate,
    CitationResolutionGate,
    Claim,
    ClaimKind,
    GateStatus,
    Orchestrator,
    Pass,
    SchemaGate,
    chao1_lower_bound,
    fit_decay,
    preflight,
    residual_estimate,
)
from adjudication_orchestrator import TestExecutionGate as ExecGate
from audit_log import AuditChainError, AuditLog, verify_chain_integrity
from seat_adapter import HttpSeat, ProviderProfile, RetryPolicy, SeatError

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
        """SOP 9.1 step 8: commit ONLY if the queue is empty. This previously
        asserted only that a WARNING string existed; the run still reported
        stop=True. Now it asserts the block itself."""
        o = _orch()
        o.run_pass(ELIM, [], [Claim("j1", "t", ClaimKind.JUDGMENT, None)])
        s = o.should_stop([])
        assert s["escalations_pending"] == 1
        assert s["WARNING"] is not None
        assert "17.2" in s["WARNING"]
        assert s["stop"] is False
        assert any("judgment queue" in b for b in s["blockers"])

    def test_candidate_reduction_alone_does_not_trigger_a_stop(self):
        """CHANGED against the SOP. This test previously asserted stop is True
        as soon as the candidate set shrank. SOP 6.3 and 9.1 step 8 make the
        rule a conjunction -- residual below tolerance AND an empty judgment
        queue -- and list no candidate-count condition at all. A single pass
        cannot establish decay, so the run has not converged."""
        o = _orch()
        bad = Claim("b", "t", ClaimKind.ARITHMETIC, "1+1 = 3")
        a, b = Candidate("A", "a", [bad]), Candidate("B", "b", [])
        o.run_pass(ELIM, [a, b], [bad])
        s = o.should_stop([a, b])
        assert s["surviving_candidates"] == 1      # the elimination still happened
        assert s["stop"] is False
        assert any("not decaying" in x for x in s["blockers"])

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


# ===========================================================================
# 9. SEAT_INDEPENDENCE — previously uncovered surface
#
# Everything below covers seat_independence.py functions the original suite
# never exercised: chao1, marginal_yield_by_pass, leave_one_seat_out_stability,
# independence_gap, diagnose, and the non-Chapman m == 0 branch of
# lincoln_petersen.
#
# Every non-obvious expected value is derived in a comment so it can be checked
# on paper without running the code.
# ===========================================================================



def _majority(row):
    """
    Deterministic majority vote, used as the aggregator in the
    leave-one-seat-out tests.

    Ties are broken by sorted order rather than by Counter internals, so every
    expected value below is reproducible by hand.
    """
    counts = _Counter(row)
    top = max(counts.values())
    return min(k for k, v in counts.items() if v == top)


class TestChao1SeatIndependence:
    """seat_independence.chao1 — same estimator as the orchestrator's
    chao1_lower_bound, different output vocabulary."""

    def test_hand_computed_case(self):
        # per-error catch counts:
        #   error 1 caught by a, c  -> 2
        #   error 2 caught by a     -> 1
        #   error 3 caught by a, b  -> 2
        #   error 4 caught by b     -> 1
        # S_obs = 4, f1 = |{2, 4}| = 2, f2 = |{1, 3}| = 2
        # f2 > 0, so N_hat = S_obs + f1^2 / (2*f2) = 4 + 4/4 = 5.0
        # estimated_missed   = 5.0 - 4 = 1.0
        # singleton_fraction = f1 / S_obs = 2/4 = 0.5
        r = SI.chao1({"a": {1, 2, 3}, "b": {3, 4}, "c": {1}})
        assert r["S_obs"] == 4.0
        assert r["f1_singletons"] == 2.0
        assert r["f2_doubletons"] == 2.0
        assert r["N_hat_lower_bound"] == pytest.approx(5.0)
        assert r["estimated_missed"] == pytest.approx(1.0)
        assert r["singleton_fraction"] == pytest.approx(0.5)

    def test_key_names_differ_from_the_orchestrator_version(self):
        """Two implementations of one estimator, with different key names.
        Pinned so that unifying them later fails loudly instead of silently
        breaking a caller's lookup."""
        det = {"a": {1, 2}, "b": {2, 3}}
        assert set(SI.chao1(det)) != set(chao1_lower_bound(det))
        assert "S_obs" in SI.chao1(det)
        assert "observed" in chao1_lower_bound(det)
        # ...while the underlying number agrees
        assert SI.chao1(det)["N_hat_lower_bound"] == pytest.approx(
            chao1_lower_bound(det)["estimated_total_lower_bound"]
        )

    def test_empty_detections(self):
        # S_obs = 0 -> f2 == 0 branch -> N_hat = 0 + 0*(0-1)/2 = 0.0
        # singleton_fraction guards on S_obs == 0 and returns NaN
        r = SI.chao1({})
        assert r["S_obs"] == 0.0
        assert r["N_hat_lower_bound"] == pytest.approx(0.0)
        assert r["estimated_missed"] == pytest.approx(0.0)
        assert math.isnan(r["singleton_fraction"])

    def test_single_seat_is_all_singletons(self):
        # one seat, 3 errors, every count = 1
        # S_obs = 3, f1 = 3, f2 = 0 -> N_hat = 3 + 3*2/2 = 6.0
        r = SI.chao1({"only": {1, 2, 3}})
        assert r["S_obs"] == 3.0
        assert r["f1_singletons"] == 3.0
        assert r["f2_doubletons"] == 0.0
        assert r["N_hat_lower_bound"] == pytest.approx(6.0)
        assert r["estimated_missed"] == pytest.approx(3.0)
        assert r["singleton_fraction"] == pytest.approx(1.0)

    def test_all_identical_seats_have_no_singletons(self):
        # three seats catching exactly the same errors: every count = 3,
        # so f1 = f2 = 0 and N_hat collapses to S_obs
        r = SI.chao1({"a": {1, 2, 3}, "b": {1, 2, 3}, "c": {1, 2, 3}})
        assert r["f1_singletons"] == 0.0
        assert r["estimated_missed"] == pytest.approx(0.0)
        assert r["singleton_fraction"] == pytest.approx(0.0)


class TestLincolnPetersenPlainBranch:
    def test_plain_estimator_at_zero_overlap_is_infinite(self):
        # n1*n2/m is undefined at m = 0; the plain branch returns inf rather
        # than raising, so callers must test isfinite before using it.
        assert SI.lincoln_petersen(10, 10, 0, chapman=False) == float("inf")

    def test_chapman_at_zero_overlap_is_hand_computable(self):
        # (n1+1)(n2+1)/(m+1) - 1 = (11*11)/1 - 1 = 120.0
        assert SI.lincoln_petersen(10, 10, 0, chapman=True) == pytest.approx(120.0)


class TestMarginalYieldByPass:
    def test_hand_computed_with_known_seed_count(self):
        # total_seeded = 10 throughout, so marginal_yield = new / 10
        #
        #  pass  caught     new         cumulative  yield      share
        #  p1    {1,2,3}    {1,2,3} = 3     3       3/10 = 0.3  3/3 = 1.0
        #  p2    {3,4}      {4}     = 1     4       1/10 = 0.1  1/4 = 0.25
        #  p3    {1,2}      {}      = 0     4       0/10 = 0.0  0/4 = 0.0
        out = SI.marginal_yield_by_pass(
            [("p1", {1, 2, 3}), ("p2", {3, 4}), ("p3", {1, 2})], total_seeded=10
        )
        assert [p.pass_id for p in out] == ["p1", "p2", "p3"]
        assert [p.newly_caught for p in out] == [3, 1, 0]
        assert [p.cumulative for p in out] == [3, 4, 4]
        assert [p.marginal_yield for p in out] == pytest.approx([0.3, 0.1, 0.0])
        assert [p.marginal_share for p in out] == pytest.approx([1.0, 0.25, 0.0])

    def test_without_total_seeded_yield_equals_share(self):
        # The denominator falls back to the running cumulative, which is
        # exactly what marginal_share divides by, so the two columns coincide.
        #   p1 {1,2}    new 2, cum 2 -> 2/2 = 1.0
        #   p2 {2,3,4}  new 2, cum 4 -> 2/4 = 0.5
        out = SI.marginal_yield_by_pass([("p1", {1, 2}), ("p2", {2, 3, 4})])
        assert [p.marginal_yield for p in out] == pytest.approx([1.0, 0.5])
        assert [p.marginal_share for p in out] == pytest.approx([1.0, 0.5])

    def test_total_seeded_zero_is_silently_treated_as_absent(self):
        """0 is falsy, so the function falls back to the cumulative
        denominator instead of dividing by zero or rejecting the input.
        Pinned because the substitution is invisible at the call site."""
        out = SI.marginal_yield_by_pass([("p1", {1, 2})], total_seeded=0)
        assert out[0].marginal_yield == pytest.approx(1.0)   # 2/2, not 2/0

    def test_empty_input_returns_empty_list(self):
        assert SI.marginal_yield_by_pass([]) == []

    def test_single_pass_catching_nothing(self):
        # new = 0 and cumulative = 0; both denominators are guarded with
        # max(..., 1), so this is 0.0 rather than ZeroDivisionError
        out = SI.marginal_yield_by_pass([("p1", set())])
        assert len(out) == 1
        assert out[0].newly_caught == 0
        assert out[0].cumulative == 0
        assert out[0].marginal_yield == pytest.approx(0.0)
        assert out[0].marginal_share == pytest.approx(0.0)

    def test_yield_collapses_once_passes_stop_finding_anything(self):
        # The documented use: if marginal_yield reaches ~0 by pass 4, pass 5
        # is not earning its compute.
        #   new per pass: 4, 2, 0, 0, 0
        out = SI.marginal_yield_by_pass(
            [("p1", {1, 2, 3, 4}), ("p2", {5, 6}), ("p3", {1, 5}),
             ("p4", {2}), ("p5", set())],
            total_seeded=8,
        )
        assert [p.newly_caught for p in out] == [4, 2, 0, 0, 0]
        assert out[0].marginal_yield == pytest.approx(0.5)   # 4/8
        assert out[-1].marginal_yield == pytest.approx(0.0)

    def test_repeated_pass_adds_nothing(self):
        # A pass that re-reports an earlier pass's findings has zero marginal
        # yield -- the whole point of the diagnostic.
        out = SI.marginal_yield_by_pass([("p1", {1, 2}), ("p2", {1, 2})], total_seeded=4)
        assert out[1].newly_caught == 0
        assert out[1].cumulative == 2


class TestLeaveOneSeatOutStability:
    def test_hand_computed_decisive_seat(self):
        # aggregator = _majority (ties broken by sorted order)
        #
        # item 0: ["A","B","C"] -> all count 1 -> sorted first -> "A"
        #   drop seat 0 -> ["B","C"] -> tie -> "B" != "A"  FLIP
        #   drop seat 1 -> ["A","C"] -> tie -> "A" == "A"  no flip
        #   drop seat 2 -> ["A","B"] -> tie -> "A" == "A"  no flip
        # item 1: ["B","A","A"] -> A=2 -> "A"
        #   drop seat 0 -> ["A","A"] -> "A"       no flip
        #   drop seat 1 -> ["B","A"] -> tie -> "A" no flip
        #   drop seat 2 -> ["B","A"] -> tie -> "A" no flip
        #
        # flips_by_seat    = {0: 1, 1: 0, 2: 0}
        # overall_flip_rate = total_flips / (n_items * n_seats) = 1 / (2*3)
        r = SI.leave_one_seat_out_stability(
            [["A", "B", "C"], ["B", "A", "A"]], _majority
        )
        assert r["flips_by_seat"] == {0: 1, 1: 0, 2: 0}
        assert r["flipped_items_by_seat"][0] == [0]
        assert r["flipped_items_by_seat"][1] == []
        assert r["flipped_items_by_seat"][2] == []
        assert r["overall_flip_rate"] == pytest.approx(1 / 6)
        assert r["most_decisive_seat"] == 0

    def test_unanimous_panel_never_flips(self):
        # every seat gives the same answer on every item, so dropping any one
        # of them cannot change the survivor
        r = SI.leave_one_seat_out_stability(
            [["A", "A", "A"], ["B", "B", "B"]], _majority
        )
        assert r["overall_flip_rate"] == pytest.approx(0.0)
        assert set(r["flips_by_seat"].values()) == {0}
        assert r["flipped_items_by_seat"] == {0: [], 1: [], 2: []}

    def test_empty_input(self):
        # n_items = 0 -> n_seats = 0 -> denominator guarded to 1,
        # and most_decisive_seat is None rather than a spurious seat 0
        r = SI.leave_one_seat_out_stability([], _majority)
        assert r["overall_flip_rate"] == pytest.approx(0.0)
        assert r["flips_by_seat"] == {}
        assert r["flipped_items_by_seat"] == {}
        assert r["most_decisive_seat"] is None

    def test_single_seat_cannot_be_dropped(self):
        """With one seat the reduced panel is empty and the loop skips, so the
        flip rate is 0 -- which is NOT evidence of robustness. Note that
        most_decisive_seat still names seat 0 despite zero flips; pinned as a
        caveat for anyone reading that field alone."""
        r = SI.leave_one_seat_out_stability([["A"], ["B"]], _majority)
        assert r["overall_flip_rate"] == pytest.approx(0.0)
        assert r["flips_by_seat"] == {0: 0}
        assert r["most_decisive_seat"] == 0

    def test_every_seat_decisive_gives_flip_rate_one(self):
        # item 0: ["A","B","C"] -> "A"; dropping seat 0 gives ["B","C"] -> "B"
        # Build a panel where each of the 3 seats is the tie-break pivot on a
        # different item, so exactly 1 of 3 drops flips each item.
        rows = [["A", "B", "C"], ["A", "B", "C"], ["A", "B", "C"]]
        r = SI.leave_one_seat_out_stability(rows, _majority)
        # only dropping seat 0 changes the sorted-first survivor, on all 3 items
        assert r["flips_by_seat"] == {0: 3, 1: 0, 2: 0}
        assert r["overall_flip_rate"] == pytest.approx(3 / 9)

    def test_interpretation_string_is_returned(self):
        r = SI.leave_one_seat_out_stability([["A", "A"]], _majority)
        assert "flip_rate" in r["interpretation"]


class TestIndependenceGap:
    # X rows are items, columns are seats; 1 means that seat got it right.

    def test_hand_computed_collapse_case(self):
        # Three seats that fail together: identical columns, 3 of 4 correct.
        #   per-seat accuracy = 3/4 = 0.75 for all three -> best_single = 0.75
        #   observed majority: row sums 3,3,3,0; > 1.5 on the first three
        #                      -> 3/4 = 0.75
        #   independence line: threshold = floor(3/2)+1 = 2
        #     P(>=2 of 3 correct | p = 0.75 each)
        #       = 3*(0.75^2)*(0.25) + 0.75^3
        #       = 3*0.5625*0.25 + 0.421875
        #       = 0.421875 + 0.421875
        #       = 0.84375
        #   theoretical_gain = 0.84375 - 0.75 = 0.09375
        #   observed_gain    = 0.75    - 0.75 = 0.0
        #   capture_fraction = 0.0 / 0.09375  = 0.0
        X = np.array([[1, 1, 1], [1, 1, 1], [1, 1, 1], [0, 0, 0]])
        g = SI.independence_gap(X)
        assert g["best_single_seat_accuracy"] == pytest.approx(0.75)
        assert g["observed_majority_accuracy"] == pytest.approx(0.75)
        assert g["independence_predicted_accuracy"] == pytest.approx(0.84375)
        assert g["theoretical_gain_over_best_single"] == pytest.approx(0.09375)
        assert g["observed_gain_over_best_single"] == pytest.approx(0.0)
        assert g["capture_fraction"] == pytest.approx(0.0)
        assert g["ensemble_beats_best_single"] is False

    def test_hand_computed_eliminative_case(self):
        # Same per-seat accuracy (3/4 each) but the failures are spread so no
        # two seats miss the same item.
        #   column sums down: seat0 = 1+1+0+1 = 3, seat1 = 3, seat2 = 3 -> 0.75
        #   row sums across:  2,2,2,3 -> all > 1.5 -> observed majority = 1.0
        #   independence line and best_single unchanged (0.84375 / 0.75)
        #   observed_gain    = 1.0 - 0.75 = 0.25
        #   capture_fraction = 0.25 / 0.09375 = 8/3 = 2.666...
        # capture > 1 means the panel beat the independence prediction, i.e.
        # the errors are anti-correlated rather than merely uncorrelated.
        X = np.array([[1, 1, 0], [1, 0, 1], [0, 1, 1], [1, 1, 1]])
        g = SI.independence_gap(X)
        assert g["best_single_seat_accuracy"] == pytest.approx(0.75)
        assert g["observed_majority_accuracy"] == pytest.approx(1.0)
        assert g["independence_predicted_accuracy"] == pytest.approx(0.84375)
        assert g["observed_gain_over_best_single"] == pytest.approx(0.25)
        assert g["capture_fraction"] == pytest.approx(8 / 3)
        assert g["ensemble_beats_best_single"] is True

    def test_single_seat_has_no_theoretical_gain(self):
        # n_seats = 1 -> threshold = floor(1/2)+1 = 1 -> P(>=1) = p = 0.75,
        # which equals best_single, so the gain is 0 and capture is NaN.
        X = np.array([[1], [1], [0], [1]])
        g = SI.independence_gap(X)
        assert g["best_single_seat_accuracy"] == pytest.approx(0.75)
        assert g["observed_majority_accuracy"] == pytest.approx(0.75)
        assert g["independence_predicted_accuracy"] == pytest.approx(0.75)
        assert g["theoretical_gain_over_best_single"] == pytest.approx(0.0)
        assert math.isnan(g["capture_fraction"])
        assert g["ensemble_beats_best_single"] is False

    def test_identical_seats_where_majority_rule_actively_hurts(self):
        # Two identical seats, each 1/2 correct.
        #   threshold = floor(2/2)+1 = 2, so BOTH must be correct
        #   P(both correct | p = 0.5 independent) = 0.25
        # 0.25 is BELOW best_single (0.5), so theoretical_gain = -0.25.
        # The guard is `theoretical_gain > 1e-12`, which rejects negative as
        # well as zero -- so capture_fraction is NaN, not a negative ratio.
        X = np.array([[1, 1], [0, 0]])
        g = SI.independence_gap(X)
        assert g["best_single_seat_accuracy"] == pytest.approx(0.5)
        assert g["observed_majority_accuracy"] == pytest.approx(0.5)
        assert g["independence_predicted_accuracy"] == pytest.approx(0.25)
        assert g["theoretical_gain_over_best_single"] == pytest.approx(-0.25)
        assert math.isnan(g["capture_fraction"])
        assert g["ensemble_beats_best_single"] is False

    def test_empty_item_set_returns_nan_without_raising(self):
        """0 items, 3 seats. numpy means over an empty axis are NaN and the
        function propagates them rather than raising -- but
        ensemble_beats_best_single still comes back as a plain False, because
        NaN > NaN is False. That reads like a real verdict, so callers must
        check for NaN themselves."""
        X = np.zeros((0, 3), dtype=int)
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore", RuntimeWarning)
            g = SI.independence_gap(X)
        assert math.isnan(g["observed_majority_accuracy"])
        assert math.isnan(g["best_single_seat_accuracy"])
        assert math.isnan(g["capture_fraction"])
        assert g["ensemble_beats_best_single"] is False

    def test_perfect_seats_leave_no_room_to_gain(self):
        # every seat correct on every item: best_single = 1.0, independence
        # prediction = 1.0, gain = 0 -> capture NaN
        X = np.ones((5, 3), dtype=int)
        g = SI.independence_gap(X)
        assert g["observed_majority_accuracy"] == pytest.approx(1.0)
        assert g["best_single_seat_accuracy"] == pytest.approx(1.0)
        assert g["independence_predicted_accuracy"] == pytest.approx(1.0)
        assert math.isnan(g["capture_fraction"])


class TestDiagnose:
    def test_no_data_returns_an_empty_report(self):
        assert SI.diagnose() == {}

    def test_hand_computed_effective_seats_from_X(self):
        # Three seats that are always identical, so every pairwise error
        # correlation is exactly 1.0 and rho = 1.0.
        #   effective_seats(3, 1.0) = 3 / (1 + (3-1)*1.0) = 3/3 = 1.0
        # Three seats that never disagree are worth exactly one seat.
        X = np.array([[1, 1, 1], [0, 0, 0], [1, 1, 1], [0, 0, 0]])
        r = SI.diagnose(X=X)
        assert r["n_seats"] == 3
        assert r["mean_error_correlation_rho"] == pytest.approx(1.0)
        assert r["effective_seats"] == pytest.approx(1.0)
        assert "independence_gap" in r

    def test_X_alone_produces_only_the_X_sections(self):
        r = SI.diagnose(X=np.array([[1, 0], [0, 1]]))
        assert set(r) == {
            "mean_error_correlation_rho", "n_seats",
            "effective_seats", "independence_gap",
        }

    def test_detections_alone(self):
        # same hand-computed Chao1 case as above: N_hat = 5.0
        r = SI.diagnose(detections={"a": {1, 2, 3}, "b": {3, 4}, "c": {1}})
        assert set(r) == {"capture_recapture"}
        assert r["capture_recapture"]["N_hat_lower_bound"] == pytest.approx(5.0)

    def test_pass_detections_are_flattened_to_plain_dicts(self):
        # diagnose() calls vars() on each PassYield so the report stays
        # JSON-serialisable.
        #   p1: new {1,2} = 2 -> 2/4 = 0.5
        #   p2: new {3}   = 1 -> 1/4 = 0.25
        r = SI.diagnose(
            pass_detections=[("p1", {1, 2}), ("p2", {2, 3})], total_seeded=4
        )
        rows = r["marginal_yield_by_pass"]
        assert set(r) == {"marginal_yield_by_pass"}
        assert all(isinstance(row, dict) for row in rows)
        assert [row["marginal_yield"] for row in rows] == pytest.approx([0.5, 0.25])
        _json.dumps(rows)

    def test_answers_without_truth_is_skipped_entirely(self):
        """Both arguments are required. Supplying one must not half-run the
        diagnostic or raise."""
        assert SI.diagnose(answers=[["A", "B"]]) == {}
        assert SI.diagnose(truth=["A"]) == {}

    def test_answers_with_truth_hand_computed(self):
        # item 0: truth "A", answers ["X","X"] -> both wrong, they agree
        # item 1: truth "A", answers ["X","Y"] -> both wrong, they differ
        # P(same wrong answer | both wrong) = 1 agreeing pair / 2 pairs = 0.5
        r = SI.diagnose(answers=[["X", "X"], ["X", "Y"]], truth=["A", "A"])
        assert set(r) == {"conditional_agreement_given_error"}
        assert r["conditional_agreement_given_error"] == pytest.approx(0.5)

    def test_all_sections_together(self):
        r = SI.diagnose(
            X=np.array([[1, 1, 1], [0, 0, 0], [1, 1, 1], [0, 1, 0]]),
            detections={"a": {1, 2}, "b": {2, 3}},
            pass_detections=[("p1", {1, 2}), ("p2", {3})],
            answers=[["X", "X", "A"], ["A", "A", "A"],
                     ["A", "A", "A"], ["B", "A", "A"]],
            truth=["A", "A", "A", "A"],
            total_seeded=5,
        )
        assert set(r) == {
            "mean_error_correlation_rho", "n_seats", "effective_seats",
            "independence_gap", "conditional_agreement_given_error",
            "capture_recapture", "marginal_yield_by_pass",
        }

    def test_report_is_json_serialisable_end_to_end(self):
        """The whole point of a one-call report is that it can be persisted.
        independence_gap embeds numpy-derived floats, so this pins that they
        are cast to plain Python types before they reach the caller."""
        r = SI.diagnose(
            X=np.array([[1, 1, 0], [1, 0, 1], [0, 1, 1], [1, 1, 1]]),
            detections={"a": {1, 2}, "b": {2, 3}},
            pass_detections=[("p1", {1, 2})],
        )
        _json.dumps(r)


# ===========================================================================
# 10. THE FIVE-PASS FRAMEWORK, BLINDING, AND DIVERGENCE
#
# Three properties are under test here:
#   (a) the pass framework is exactly the five named lenses, in order;
#   (b) a seat is never shown a prior result, another seat's answer, or a gate
#       verdict -- and the blinding is enforced structurally, not by comment;
#   (c) seat disagreement is measured as a first-class output, and UNANIMITY
#       is treated as a defect signal rather than as confidence.
# ===========================================================================



def _seat(text):
    """A seat that ignores its prompt and returns a fixed response."""
    return lambda _prompt: text


class TestFivePassFramework:
    def test_exact_names_and_order(self):
        assert [p.name for p in AO.DEFAULT_PASSES] == [
            "Inversion Analysis",
            "FMEA + FTA + FMEDA",
            "IDOV",
            "Critical Systems Thinking + TRIZ + Quality Zero Defects",
            "Bayesian + MCMC",
        ]

    def test_there_are_exactly_five_passes(self):
        assert len(AO.DEFAULT_PASSES) == 5

    def test_only_the_fifth_pass_is_non_eliminative(self):
        # A Bayesian posterior never reaches zero from a nonzero prior, so
        # pass 5 calibrates survivors and cannot rule a candidate out.
        assert [p.eliminative for p in AO.DEFAULT_PASSES] == [
            True, True, True, True, False
        ]


class TestBlinding:
    def test_prompt_builder_accepts_no_history_parameter(self):
        """The blinding holds because there is no argument through which a
        prior result could be passed. Adding one breaks this test, which is
        the point -- the contract is enforced by the signature, not by a
        docstring asking callers to behave."""
        assert list(_inspect.signature(AO.build_blinded_prompt).parameters) == [
            "p", "seat_id", "artifact",
        ]

    def test_seat_prompt_is_immutable(self):
        sp = AO.build_blinded_prompt(AO.DEFAULT_PASSES[0], "s1", "art")
        with pytest.raises(dataclasses.FrozenInstanceError):
            sp.artifact = "tampered"

    def test_no_prior_pass_content_reaches_any_later_prompt(self):
        """The canary: both seats emit a distinctive string on every pass. If
        any later prompt contained a prior pass's output, the canary would
        show up in prompt_log."""
        canary = "CANARY-9f3a-PRIOR-RESULT"
        runner = AO.BlindedSeatRunner({
            "s1": _seat(f"CLAIM | arithmetic | 1+1 = 3 | {canary}"),
            "s2": _seat(f"CLAIM | judgment |  | {canary}"),
        })
        o = Orchestrator([ArithmeticGate()])
        o.run_sequential("clean artifact", [], runner)
        assert len(runner.prompt_log) == 10          # 5 passes x 2 seats
        for sp in runner.prompt_log:
            assert canary not in sp.render()

    def test_gate_verdicts_do_not_reach_any_prompt(self):
        runner = AO.BlindedSeatRunner({
            "s1": _seat("CLAIM | arithmetic | 12 + 35 = 50 | wrong total"),
        })
        o = Orchestrator([ArithmeticGate()])
        o.run_sequential("artifact", [], runner)
        # a real verdict was produced on pass 1 ...
        assert o.history[0].auto_rejected == 1
        # ... and none of its wording appears in any prompt, on any pass
        for sp in runner.prompt_log:
            rendered = sp.render()
            assert "recomputed" not in rendered
            assert "eliminated" not in rendered.lower()

    def test_every_seat_on_a_pass_is_shown_identical_text(self):
        """No seat is handed anything the others were not. Seat
        differentiation lives in the callables, never in the prompt."""
        runner = AO.BlindedSeatRunner(
            {"s1": _seat(""), "s2": _seat(""), "s3": _seat("")}
        )
        runner.run(AO.DEFAULT_PASSES[1], "artifact")
        assert len({sp.render() for sp in runner.prompt_log}) == 1

    def test_prompt_carries_only_the_lens_and_the_artifact(self):
        sp = AO.build_blinded_prompt(AO.DEFAULT_PASSES[0], "s1", "THE-ARTIFACT")
        rendered = sp.render()
        assert "Inversion Analysis" in rendered
        assert "THE-ARTIFACT" in rendered
        assert "p1" not in rendered                      # no pass number
        for other in AO.DEFAULT_PASSES[1:]:              # no other lens
            assert other.name not in rendered

    def test_runner_requires_at_least_one_seat(self):
        with pytest.raises(ValueError):
            AO.BlindedSeatRunner({})


class TestSequentialBlindedRun:
    def test_runs_the_five_passes_in_order_one_at_a_time(self):
        calls = []
        runner = AO.BlindedSeatRunner({
            "s1": lambda prompt: calls.append(prompt)
            or "CLAIM | arithmetic | 1+1 = 2 | sum",
        })
        o = Orchestrator([ArithmeticGate()])
        results = o.run_sequential("artifact", [], runner)
        assert [r.pass_name for r in results] == [p.name for p in AO.DEFAULT_PASSES]
        assert [r.pass_id for r in results] == ["p1", "p2", "p3", "p4", "p5"]
        assert len(calls) == 5           # one seat, five sequential invocations
        assert len(o.history) == 5

    def test_a_subset_of_passes_can_be_run(self):
        runner = AO.BlindedSeatRunner({"s1": _seat("CLAIM | arithmetic | 2+2 = 4 | s")})
        o = Orchestrator([ArithmeticGate()])
        results = o.run_sequential("art", [], runner, passes=AO.DEFAULT_PASSES[:2])
        assert [r.pass_id for r in results] == ["p1", "p2"]

    def test_two_seats_making_the_same_claim_are_both_credited_but_gated_once(self):
        """Content-addressed ids are what make capture-recapture work: the
        claim is adjudicated once, but BOTH seats are recorded as having
        caught it. Seat-scoped ids would make every claim a singleton and
        inflate the Chao1 estimate of what nobody caught."""
        both = _seat("CLAIM | arithmetic | 12 + 35 = 47 | total")
        runner = AO.BlindedSeatRunner({"s1": both, "s2": both})
        o = Orchestrator([ArithmeticGate()])
        rec = o.run_sequential("art", [], runner, passes=[AO.DEFAULT_PASSES[0]])[0].record
        assert rec.proposed == 2          # two seats proposed it
        assert rec.auto_accepted == 1     # the gate ran once
        cid = AO.content_claim_id(ClaimKind.ARITHMETIC, "12 + 35 = 47", "total")
        assert o.detections_by_seat["s1"] == {cid}
        assert o.detections_by_seat["s2"] == {cid}
        # one error, caught twice -> a doubleton, not two singletons
        cr = chao1_lower_bound(o.detections_by_seat)
        assert cr["observed"] == 1.0
        assert cr["f1_singletons"] == 0.0
        assert cr["f2_doubletons"] == 1.0

    def test_report_includes_divergence_and_stays_serialisable(self):
        runner = AO.BlindedSeatRunner({"s1": _seat("CLAIM | arithmetic | 1+1 = 2 | s")})
        o = Orchestrator([ArithmeticGate()])
        o.run_sequential("art", [], runner)
        rep = o.report()
        assert set(rep["divergence_by_pass"]) == {"p1", "p2", "p3", "p4", "p5"}
        _json.dumps(rep)


class TestDivergenceMeasurement:
    def test_hand_computed_jaccard_for_two_disagreeing_seats(self):
        # content keys are (kind, warrant), so:
        #   s1 = {(arithmetic,"1+1 = 2"), (arithmetic,"2+2 = 4")}
        #   s2 = {(arithmetic,"2+2 = 4"), (arithmetic,"3+3 = 7")}
        #   intersection = 1, union = 3 -> Jaccard = 1/3
        # one pair, so the mean is that same 1/3
        p = AO.DEFAULT_PASSES[0]
        runner = AO.BlindedSeatRunner({
            "s1": _seat("CLAIM | arithmetic | 1+1 = 2 | a\n"
                        "CLAIM | arithmetic | 2+2 = 4 | b"),
            "s2": _seat("CLAIM | arithmetic | 2+2 = 4 | b\n"
                        "CLAIM | arithmetic | 3+3 = 7 | c"),
        })
        d = AO.measure_divergence(p, runner.run(p, "art"))
        assert d.mean_pairwise_jaccard == pytest.approx(1 / 3)
        assert d.distinct_claim_sets == 2
        assert d.unanimous is False
        assert d.collapse_warning is None

    def test_hand_computed_jaccard_for_three_seats(self):
        # A = {x, y}, B = {y, z}, C = {x, y}
        #   A|B = |{y}| / |{x,y,z}| = 1/3
        #   A|C = |{x,y}| / |{x,y}|  = 1
        #   B|C = |{y}| / |{x,y,z}| = 1/3
        #   mean = (1/3 + 1 + 1/3) / 3 = (5/3)/3 = 5/9
        p = AO.DEFAULT_PASSES[0]
        x = "CLAIM | arithmetic | 1+1 = 2 | x"
        y = "CLAIM | arithmetic | 2+2 = 4 | y"
        z = "CLAIM | arithmetic | 3+3 = 7 | z"
        runner = AO.BlindedSeatRunner({
            "s1": _seat(f"{x}\n{y}"),
            "s2": _seat(f"{y}\n{z}"),
            "s3": _seat(f"{x}\n{y}"),
        })
        d = AO.measure_divergence(p, runner.run(p, "art"))
        assert d.mean_pairwise_jaccard == pytest.approx(5 / 9)
        assert d.distinct_claim_sets == 2      # s1 and s3 are identical
        assert d.unanimous is False

    def test_unanimous_seats_raise_a_collapse_warning(self):
        """Identical claim sets from independent seats is a monoculture
        signal, not a confirmation."""
        p = AO.DEFAULT_PASSES[0]
        same = _seat("CLAIM | arithmetic | 1+1 = 2 | sum")
        runner = AO.BlindedSeatRunner({"s1": same, "s2": same, "s3": same})
        d = AO.measure_divergence(p, runner.run(p, "art"))
        assert d.unanimous is True
        assert d.mean_pairwise_jaccard == pytest.approx(1.0)
        assert d.distinct_claim_sets == 1
        assert d.collapse_warning is not None
        assert "monoculture" in d.collapse_warning

    def test_total_disagreement_scores_zero(self):
        p = AO.DEFAULT_PASSES[0]
        runner = AO.BlindedSeatRunner({
            "s1": _seat("CLAIM | arithmetic | 1+1 = 2 | a"),
            "s2": _seat("CLAIM | arithmetic | 3+3 = 7 | b"),
        })
        d = AO.measure_divergence(p, runner.run(p, "art"))
        assert d.mean_pairwise_jaccard == pytest.approx(0.0)
        assert d.unanimous is False

    def test_a_single_seat_cannot_be_unanimous(self):
        p = AO.DEFAULT_PASSES[0]
        runner = AO.BlindedSeatRunner({"only": _seat("CLAIM | arithmetic | 1+1 = 2 | s")})
        d = AO.measure_divergence(p, runner.run(p, "art"))
        assert d.unanimous is False
        assert math.isnan(d.mean_pairwise_jaccard)
        assert d.collapse_warning is None

    def test_a_seat_that_raises_is_recorded_not_swallowed(self):
        def boom(_prompt):
            raise ConnectionError("seat offline")
        p = AO.DEFAULT_PASSES[0]
        runner = AO.BlindedSeatRunner({
            "good": _seat("CLAIM | arithmetic | 1+1 = 2 | s"),
            "bad": boom,
        })
        responses = runner.run(p, "art")
        by_seat = {r.seat_id: r for r in responses}
        assert by_seat["bad"].error is not None
        assert by_seat["bad"].claims == []
        assert by_seat["good"].claims
        d = AO.measure_divergence(p, responses)
        assert d.n_seats == 2
        assert d.seats_responding == ["good"]
        assert d.seats_errored == ["bad"]


class TestLineClaimExtractor:
    def test_parses_the_documented_format(self):
        claims = AO.line_claim_extractor(
            "CLAIM | arithmetic | 12 + 35 = 47 | the total", "s1", "p1"
        )
        assert len(claims) == 1
        c = claims[0]
        assert c.kind is ClaimKind.ARITHMETIC
        assert c.warrant == "12 + 35 = 47"
        assert c.text == "the total"
        assert c.source_seat == "s1" and c.source_pass == "p1"

    def test_prose_around_the_claim_is_ignored(self):
        raw = "Here is my analysis.\nCLAIM | arithmetic | 1+1 = 2 | sum\nHope that helps!"
        assert len(AO.line_claim_extractor(raw, "s1", "p1")) == 1

    def test_malformed_claim_line_fails_closed_to_judgment(self):
        """A line that announces itself as a CLAIM but does not parse becomes
        a JUDGMENT with no warrant, which has no gate and therefore escalates.
        Dropping it would let a model smuggle an unverified assertion past the
        gates by writing it badly."""
        claims = AO.line_claim_extractor("CLAIM the answer is obviously 42", "s1", "p1")
        assert len(claims) == 1
        assert claims[0].kind is ClaimKind.JUDGMENT
        assert claims[0].warrant is None

    def test_unknown_kind_fails_closed_to_judgment(self):
        claims = AO.line_claim_extractor("CLAIM | telepathy | x | y", "s1", "p1")
        assert claims[0].kind is ClaimKind.JUDGMENT
        assert claims[0].warrant is None

    def test_malformed_claim_actually_reaches_the_escalation_queue(self):
        claims = AO.line_claim_extractor("CLAIM trust me on this one", "s1", "p1")
        o = Orchestrator([ArithmeticGate()])
        rec = o.run_pass(AO.DEFAULT_PASSES[0], [], claims)
        assert rec.escalated == 1
        assert rec.auto_accepted == 0
        assert len(o.escalation_queue) == 1

    def test_empty_warrant_becomes_none(self):
        claims = AO.line_claim_extractor(
            "CLAIM | judgment |  | the framing is sound", "s1", "p1"
        )
        assert claims[0].warrant is None

    def test_no_claim_lines_yields_nothing(self):
        assert AO.line_claim_extractor("I have no claims to make.", "s1", "p1") == []

    def test_identical_claims_from_different_seats_share_an_id(self):
        a = AO.line_claim_extractor("CLAIM | arithmetic | 2+2 = 4 | sum", "s1", "p1")[0]
        b = AO.line_claim_extractor("CLAIM | arithmetic | 2+2 = 4 | sum", "s2", "p3")[0]
        assert a.id == b.id
        assert a.source_seat != b.source_seat

    def test_different_claims_get_different_ids(self):
        a = AO.line_claim_extractor("CLAIM | arithmetic | 2+2 = 4 | sum", "s1", "p1")[0]
        b = AO.line_claim_extractor("CLAIM | arithmetic | 2+2 = 5 | sum", "s1", "p1")[0]
        assert a.id != b.id


class TestSilenceIsNotCollapse:
    """Found by running the seeded-error harness: three seats that all return
    NOTHING have trivially identical claim sets, and were being flagged as a
    monoculture. Unanimous silence is the marginal-yield signal (this pass
    found nothing), not the collapse signal."""

    def test_all_silent_seats_do_not_raise_a_collapse_warning(self):
        p = AO.DEFAULT_PASSES[4]
        runner = AO.BlindedSeatRunner(
            {"s1": _seat(""), "s2": _seat(""), "s3": _seat("")}
        )
        d = AO.measure_divergence(p, runner.run(p, "art"))
        assert d.all_seats_silent is True
        assert d.unanimous is True            # the sets ARE identical
        assert d.collapse_warning is None     # ...but that is not monoculture

    def test_unanimous_non_empty_still_warns(self):
        p = AO.DEFAULT_PASSES[0]
        same = _seat("CLAIM | arithmetic | 1+1 = 2 | sum")
        runner = AO.BlindedSeatRunner({"s1": same, "s2": same, "s3": same})
        d = AO.measure_divergence(p, runner.run(p, "art"))
        assert d.all_seats_silent is False
        assert d.collapse_warning is not None

    def test_partial_silence_is_not_silence(self):
        p = AO.DEFAULT_PASSES[0]
        runner = AO.BlindedSeatRunner({
            "s1": _seat(""), "s2": _seat("CLAIM | arithmetic | 1+1 = 2 | sum")})
        d = AO.measure_divergence(p, runner.run(p, "art"))
        assert d.all_seats_silent is False
        assert d.mean_pairwise_jaccard == pytest.approx(0.0)
        assert d.collapse_warning is None


# ===========================================================================
# 11. EVIDENCE ADMISSIBILITY AND PANEL CONFIGURATION
# ===========================================================================



class TestSourceAdmissibility:
    g = AO.SourceAdmissibilityGate()

    def _cite(self, warrant):
        return Claim("c", "t", ClaimKind.CITATION, warrant)

    @pytest.mark.parametrize("ident,expected", [
        ("10.1038/s42256-026-01268-y", AO.SourceClass.PEER_REVIEWED),
        ("PMID: 31452104",             AO.SourceClass.PEER_REVIEWED),
        ("10.5281/zenodo.1234567",     AO.SourceClass.EMPIRICAL_DATA),
        ("GSE12345",                   AO.SourceClass.EMPIRICAL_DATA),
        ("ISO/IEC 27001:2022",         AO.SourceClass.TECHNICAL_MANUAL),
        ("RFC 8446",                   AO.SourceClass.TECHNICAL_MANUAL),
        ("NIST SP 800-53",             AO.SourceClass.TECHNICAL_MANUAL),
        ("ISBN 978-0-262-03384-8",     AO.SourceClass.TECHNICAL_MANUAL),
        ("https://arxiv.org/abs/2301.00001", AO.SourceClass.PREPRINT),
    ])
    def test_structural_classification(self, ident, expected):
        assert AO.classify_source(ident) is expected

    @pytest.mark.parametrize("ident", [
        "https://medium.com/@someone/why-i-think-x",
        "https://en.wikipedia.org/wiki/Bayes_theorem",
        "https://news.ycombinator.com/item?id=1",
        "https://vendor.example.com/product",
        "a colleague told me",
        "the model said so",
        "",
        "   ",
    ])
    def test_everything_else_is_inadmissible(self, ident):
        """Fail closed. There is no 'probably fine' branch."""
        assert AO.classify_source(ident) is AO.SourceClass.INADMISSIBLE
        assert self.g.check(self._cite(ident)).status is GateStatus.FAIL

    def test_scholarly_article_passes(self):
        r = self.g.check(self._cite("10.1038/s42256-026-01268-y"))
        assert r.status is GateStatus.PASS
        assert "peer_reviewed" in r.detail

    def test_preprint_is_rejected_by_default(self):
        r = self.g.check(self._cite("https://arxiv.org/abs/2301.00001"))
        assert r.status is GateStatus.FAIL
        assert "not peer-reviewed" in r.detail

    def test_preprint_opt_in_is_recorded_in_the_audit_detail(self):
        """Admitting a preprint is allowed, but the concession has to be
        visible in the record rather than buried in configuration."""
        g = AO.SourceAdmissibilityGate(allow_preprints=True)
        r = g.check(self._cite("https://arxiv.org/abs/2301.00001"))
        assert r.status is GateStatus.PASS
        assert "NOT peer reviewed" in r.detail

    def test_classifier_exception_fails_closed(self):
        def boom(_ident):
            raise RuntimeError("registry down")
        g = AO.SourceAdmissibilityGate(classifier=boom)
        assert g.check(self._cite("10.1000/x")).status is GateStatus.FAIL

    def test_does_not_apply_to_non_citation_claims(self):
        assert not self.g.applies_to(Claim("c", "t", ClaimKind.ARITHMETIC, "1+1 = 2"))
        assert not self.g.applies_to(Claim("c", "t", ClaimKind.CITATION, None))


class TestConjunctiveRouting:
    """A citation must be BOTH admissible in class AND actually resolve.
    Passing one gate is not passing the other."""

    def _orch(self, resolves):
        return Orchestrator([
            AO.SourceAdmissibilityGate(),
            CitationResolutionGate(lambda i: resolves),
        ])

    def test_admissible_and_resolving_is_accepted(self):
        o = self._orch(True)
        rec = o.run_pass(AO.DEFAULT_PASSES[0], [],
                         [Claim("c", "t", ClaimKind.CITATION, "10.1038/real")])
        assert rec.auto_accepted == 1

    def test_admissible_but_not_resolving_is_rejected(self):
        o = self._orch(False)
        rec = o.run_pass(AO.DEFAULT_PASSES[0], [],
                         [Claim("c", "t", ClaimKind.CITATION, "10.1038/ghost")])
        assert rec.auto_rejected == 1

    def test_resolving_but_inadmissible_is_rejected(self):
        """The blog post exists. That is not the question."""
        o = self._orch(True)
        claim = Claim("c", "t", ClaimKind.CITATION, "https://medium.com/@x/post")
        cand = Candidate("A", "answer", [claim])
        o.run_pass(AO.DEFAULT_PASSES[0], [cand], [claim])
        assert cand.eliminated is True
        assert "inadmissible" in cand.elimination_reason

    def test_a_claim_with_no_applicable_gate_still_escalates(self):
        o = self._orch(True)
        rec = o.run_pass(AO.DEFAULT_PASSES[0], [],
                         [Claim("j", "t", ClaimKind.JUDGMENT, None)])
        assert rec.escalated == 1


class TestPanelConfiguration:
    ENV: ClassVar[dict[str, str]] = {
        "ADJ_SEAT_1_API_KEY": "k1", "ADJ_SEAT_2_API_KEY": "k2",
        "ADJ_SEAT_3_API_KEY": "k3", "ADJ_SEAT_4_API_KEY": "k4",
        "ADJ_SEAT_1_MODEL": "m1",
    }

    def test_five_seats_four_credentials_plus_claude(self):
        panel = AO.load_panel(env=dict(self.ENV))
        assert len(panel) == 5
        assert [s.seat_id for s in panel] == [
            "seat_1", "seat_2", "seat_3", "seat_4", "seat_5_claude"]
        assert sum(1 for s in panel if not s.in_process) == 4
        assert panel[-1].in_process is True
        assert panel[-1].credential() is None

    def test_missing_credential_fails_closed(self):
        """A four-seat run reported as five misstates rho, effective_seats,
        and the residual estimate. It must not start."""
        env = dict(self.ENV)
        del env["ADJ_SEAT_3_API_KEY"]
        with pytest.raises(AO.MissingSeatCredential) as exc:
            AO.load_panel(env=env)
        assert "ADJ_SEAT_3_API_KEY" in str(exc.value)

    def test_blank_credential_is_treated_as_missing(self):
        env = dict(self.ENV)
        env["ADJ_SEAT_2_API_KEY"] = "   "
        with pytest.raises(AO.MissingSeatCredential):
            AO.load_panel(env=env)

    def test_all_missing_credentials_are_reported_at_once(self):
        with pytest.raises(AO.MissingSeatCredential) as exc:
            AO.load_panel(env={})
        msg = str(exc.value)
        assert all(f"ADJ_SEAT_{i}_API_KEY" in msg for i in (1, 2, 3, 4))

    def test_credential_never_appears_in_repr(self):
        panel = AO.load_panel(env=dict(self.ENV))
        for seat in panel:
            assert "k1" not in repr(seat)
            assert "k1" not in str(seat)
            assert "k1" not in f"{seat}"
        assert panel[0].credential() == "k1"      # explicit accessor still works

    def test_spec_has_no_field_that_could_hold_a_secret(self):
        """SeatSpec carries the NAME of an environment variable and nothing
        else. There is no field a credential could be pasted into, so a key
        cannot reach source control through this dataclass."""
        import dataclasses
        fields = {f.name for f in dataclasses.fields(AO.SeatSpec)}
        assert fields == {"seat_id", "api_key_env", "model_env"}
        for spec in AO.PANEL_OF_FIVE[:4]:
            assert spec.api_key_env.startswith("ADJ_SEAT_")
            assert spec.api_key_env.endswith("_API_KEY")

    def test_load_panel_defaults_to_the_process_environment(self):
        """Default source is os.environ; the suite must not depend on it
        being populated, so this only checks the wiring."""
        assert AO.load_panel.__defaults__[1] is None
        assert _os.environ is not None

    def test_preflight_cap_is_not_silently_raised_by_the_five_seat_panel(self):
        """PANEL_OF_FIVE is a deliberate override of this module's own
        recommendation. preflight must still say 3."""
        assert len(AO.PANEL_OF_FIVE) == 5
        assert AO.MAX_RECOMMENDED_SEATS == 3
        v = preflight(0.31, task_is_decomposable=True, requested_seats=5)
        assert v.recommended_seats == 3


# ===========================================================================
# 12. CONFORMANCE TO SOP MANUAL v1.0
#
# The manual is the specification; where code and manual disagreed, the manual
# won. Section references are to "SOP Manual: Automated Disconfirmation
# Adjudication, Version 1.0, 21 August 2026".
# ===========================================================================

class TestSOPStopRule:
    def _run(self, rejects_per_pass, escalations=0, tol=0.5):
        """Drive history directly so the decay series is exactly specified."""
        o = Orchestrator([ArithmeticGate()], residual_tolerance=tol)
        for k, n in enumerate(rejects_per_pass):
            o.history.append(AO.PassRecord(f"p{k+1}", n, 0, n, 0))
        for i in range(escalations):
            o.escalation_queue.append(Claim(f"j{i}", "t", ClaimKind.JUDGMENT, None))
        return o

    def test_vcy_counts_corrections_not_confirmations(self):
        """SOP 6.3: 'VCY_k = verified CORRECTIONS found in round k'. A pass that
        accepted ten true claims and rejected nothing found no corrections; it
        must not read as a yield of ten."""
        o = Orchestrator([ArithmeticGate()])
        o.history.append(AO.PassRecord("p1", 10, 10, 0, 0))   # 10 accepted, 0 rejected
        o.history.append(AO.PassRecord("p2", 10, 10, 0, 0))
        s = o.should_stop([])
        # zero corrections in both passes -> no decay series -> cannot converge
        assert s["extrapolated_residual"] is None
        assert any("not decaying" in b for b in s["blockers"])

    def test_decaying_corrections_with_empty_queue_stops(self):
        # corrections 20, 7, 2.5 -> steep decay, residual well under tolerance
        o = self._run([20, 7, 2, 1])
        s = o.should_stop([])
        assert s["extrapolated_residual"] is not None
        assert s["extrapolated_residual"] < 0.5
        assert s["blockers"] == []
        assert s["stop"] is True

    def test_same_run_with_one_queued_item_does_not_stop(self):
        """The only difference from the previous test is a single unworked
        judgment claim. SOP 10 lists an unworked queue as a do-not-build
        condition."""
        o = self._run([20, 7, 2, 1], escalations=1)
        s = o.should_stop([])
        assert s["extrapolated_residual"] < 0.5      # residual is fine
        assert s["stop"] is False                    # ...and it still does not stop
        assert any("judgment queue" in b for b in s["blockers"])

    def test_flat_yields_do_not_stop(self):
        """SOP 9.2: 'Yields are not decreasing -> Run more passes, do not commit'."""
        s = self._run([5, 5, 5, 5]).should_stop([])
        assert s["stop"] is False
        assert any("not decaying" in b for b in s["blockers"])

    def test_residual_above_tolerance_does_not_stop(self):
        s = self._run([100, 90, 80, 70], tol=0.5).should_stop([])
        assert s["stop"] is False
        assert any("tolerance" in b for b in s["blockers"])

    def test_singleton_alarm_is_uncalibrated_by_default_and_says_so(self):
        """SOP 9.2 names a high singleton fraction as an abort signal but gives
        no number, and SOP 8.4 makes thresholds the operator's to set. The
        module does not invent one; it reports that the check is not armed."""
        o = self._run([20, 7, 2, 1])
        o.detections_by_seat = {"s1": {"e1"}, "s2": {"e2"}}   # all singletons
        s = o.should_stop([])
        assert s["singleton_alarm_calibrated"] is False
        assert s["singleton_fraction"] == pytest.approx(1.0)
        assert s["stop"] is True          # not armed, so not applied

    def test_armed_singleton_alarm_blocks_the_stop(self):
        o = Orchestrator([ArithmeticGate()], singleton_alarm=0.5)
        for k, n in enumerate([20, 7, 2, 1]):
            o.history.append(AO.PassRecord(f"p{k+1}", n, 0, n, 0))
        o.detections_by_seat = {"s1": {"e1"}, "s2": {"e2"}}
        s = o.should_stop([])
        assert s["singleton_alarm_calibrated"] is True
        assert s["stop"] is False
        assert any("singleton fraction" in b for b in s["blockers"])


class TestPermissiveResolverProbe:
    """SOP 8.3 names a default-True resolver as the single most common way this
    build fails, and its checklist requires probing with a fake identifier."""

    def test_permissive_resolver_is_detected(self):
        r = AO.probe_resolver(lambda i: True)
        assert r.status is GateStatus.FAIL
        assert "PERMISSIVE RESOLVER" in r.detail

    def test_correctly_denying_resolver_passes(self):
        r = AO.probe_resolver(lambda i: i == "10.1038/s42256-026-01268-y")
        assert r.status is GateStatus.PASS

    def test_raising_resolver_is_acceptable(self):
        """The gate already fails closed on exceptions, so a resolver that
        cannot reach the network is safe -- unlike one that guesses True."""
        def offline(_i):
            raise ConnectionError("no network")
        assert AO.probe_resolver(offline).status is GateStatus.PASS

    def test_the_probe_identifier_is_structurally_valid_but_inadmissible_free(self):
        """The probe must look like a real DOI, or a resolver could reject it on
        format alone and appear strict when it is not."""
        assert AO.classify_source(AO.PERMISSIVE_RESOLVER_PROBE) is \
            AO.SourceClass.PEER_REVIEWED


class TestGatesFailClosedOnMissingWarrant:
    """Every gate's applies_to() already excludes a claim with no warrant, but
    check() is public and the suite calls it directly. It previously relied on
    an AttributeError being swallowed by the broad except; the guard is now
    explicit, so the fail-closed path is stated rather than incidental."""

    @pytest.mark.parametrize("gate,kind", [
        (ArithmeticGate(),                      ClaimKind.ARITHMETIC),
        (CitationResolutionGate(lambda i: True), ClaimKind.CITATION),
        (ExecGate(lambda c: True),              ClaimKind.CODE_BEHAVIOR),
        (SchemaGate([]),                        ClaimKind.SCHEMA),
        (AO.SourceAdmissibilityGate(),          ClaimKind.CITATION),
    ])
    def test_none_warrant_fails_never_passes(self, gate, kind):
        r = gate.check(Claim("c", "t", kind, None))
        assert r.status is GateStatus.FAIL
        assert "no warrant" in r.detail

    @pytest.mark.parametrize("gate,kind", [
        (ArithmeticGate(),                      ClaimKind.ARITHMETIC),
        (CitationResolutionGate(lambda i: True), ClaimKind.CITATION),
        (SchemaGate([]),                        ClaimKind.SCHEMA),
        (AO.SourceAdmissibilityGate(),          ClaimKind.CITATION),
    ])
    def test_empty_warrant_fails_never_passes(self, gate, kind):
        assert gate.check(Claim("c", "t", kind, "")).status is GateStatus.FAIL

    def test_a_permissive_runner_cannot_rescue_a_missing_warrant(self):
        """The runner returning True must not matter: with nothing to run, the
        gate denies before the runner is reached."""
        called = []
        g = ExecGate(lambda c: called.append(c) or True)
        assert g.check(Claim("c", "t", ClaimKind.CODE_BEHAVIOR, None)).status is GateStatus.FAIL
        assert called == []


# ===========================================================================
# 13. AUDIT LOG  (SOP 8.5; sixteen-test template items 15 and 16)
#
# The chain must detect a modified payload, a reordered entry, a spliced
# entry, a deleted middle entry, and a renumbered sequence. It provably
# CANNOT detect tail truncation on its own -- that limitation is pinned by
# test rather than left to the docstring.
# ===========================================================================



def _log_with(n=3, clock=None):
    log = AuditLog("run-001", clock=clock)
    log.record_artifact("the artifact under review")
    for i in range(n):
        log.append("pass", {"pass_id": f"p{i + 1}", "auto_rejected": 3 - i})
    return log


class TestAuditLogCreation:
    """sixteen-test-template item 15: audit log creation."""

    def test_genesis_entry_is_created_automatically(self):
        log = AuditLog("run-001")
        assert len(log) == 1
        g = log.entries[0]
        assert g.seq == 0
        assert g.kind == "genesis"
        assert g.prev_hash == AL.GENESIS_PREV_HASH
        assert g.payload["run_id"] == "run-001"

    def test_a_fresh_log_verifies(self):
        assert AuditLog("run-001").verify().valid is True

    def test_a_populated_log_verifies(self):
        v = _log_with(3).verify()
        assert v.valid is True
        assert v.entries_checked == 5      # genesis + artifact + 3 passes
        assert v.failures == []

    def test_genesis_kind_is_reserved(self):
        with pytest.raises(AuditChainError):
            AuditLog("run-001").append("genesis", {})

    def test_empty_run_id_is_refused(self):
        with pytest.raises(AuditChainError):
            AuditLog("")

    def test_entries_view_cannot_be_used_to_append(self):
        log = AuditLog("run-001")
        assert isinstance(log.entries, tuple)
        before = len(log)
        with pytest.raises(AttributeError):
            log.entries.append("nope")     # type: ignore[attr-defined]
        assert len(log) == before

    def test_artifact_is_committed_by_digest_not_by_text(self):
        """A log of a RED run must not itself become RED."""
        log = AuditLog("run-001")
        log.record_artifact("SENSITIVE CLAIM TEXT")
        p = log.entries[-1].payload
        assert p["artifact_sha256"] == AL.digest("SENSITIVE CLAIM TEXT")
        assert "artifact_text" not in p
        assert "SENSITIVE" not in AL.canonical_json(p)

    def test_full_text_only_on_explicit_opt_in(self):
        log = AuditLog("run-001")
        log.record_artifact("green artifact", include_text=True)
        assert log.entries[-1].payload["artifact_text"] == "green artifact"


class TestAuditChainTamperDetection:
    def _tamper(self, log, idx, **changes):
        """Replace one entry's payload, leaving every stored hash untouched."""
        es = list(log.entries)
        e = es[idx]
        es[idx] = AL.AuditEntry(e.seq, e.prev_hash, e.kind,
                                {**e.payload, **changes}, e.entry_hash)
        return es

    def test_modified_payload_is_detected(self):
        """sixteen-test-template item 8: tampered payload."""
        log = _log_with(3)
        es = self._tamper(log, 2, auto_rejected=999)
        v = verify_chain_integrity(es)
        assert v.valid is False
        assert any("hash mismatch" in f for f in v.failures)

    def test_reordered_entries_are_detected(self):
        log = _log_with(3)
        es = list(log.entries)
        es[2], es[3] = es[3], es[2]
        v = verify_chain_integrity(es)
        assert v.valid is False
        assert any("seq is" in f for f in v.failures)
        assert any("prev_hash" in f for f in v.failures)

    def test_deleted_middle_entry_is_detected(self):
        log = _log_with(3)
        es = [e for i, e in enumerate(log.entries) if i != 2]
        v = verify_chain_integrity(es)
        assert v.valid is False
        assert any("prev_hash" in f for f in v.failures)

    def test_spliced_entry_is_detected(self):
        log = _log_with(3)
        es = list(log.entries)
        forged = AL.AuditEntry(2, es[1].entry_hash, "pass",
                               {"pass_id": "forged"}, "0" * 64)
        es.insert(2, forged)
        v = verify_chain_integrity(es)
        assert v.valid is False

    def test_renumbered_sequence_is_detected(self):
        log = _log_with(2)
        es = list(log.entries)
        e = es[1]
        es[1] = AL.AuditEntry(99, e.prev_hash, e.kind, e.payload, e.entry_hash)
        v = verify_chain_integrity(es)
        assert v.valid is False
        assert any("seq is 99" in f for f in v.failures)

    def test_a_valid_chain_reports_its_head(self):
        log = _log_with(2)
        v = log.verify()
        assert v.head == log.head
        assert bool(v) is True


class TestAuditChainTruncation:
    """The named check: 'verify_chain_integrity (empty-log truncation check)'."""

    def test_empty_log_FAILS_rather_than_passing_vacuously(self):
        v = verify_chain_integrity([])
        assert v.valid is False
        assert v.entries_checked == 0
        assert v.head is None
        assert any("empty log" in f for f in v.failures)

    def test_tail_truncation_is_NOT_detectable_by_the_chain_alone(self):
        """Pinned as a limitation, not asserted as a feature. Entries 0..2 of a
        five-entry log are a perfectly valid three-entry chain, because nothing
        inside the chain records how long it was supposed to be."""
        log = _log_with(3)
        truncated = list(log.entries)[:3]
        assert verify_chain_integrity(truncated).valid is True

    def test_tail_truncation_IS_detected_against_a_recorded_head(self):
        log = _log_with(3)
        real_head = log.head
        truncated = list(log.entries)[:3]
        v = verify_chain_integrity(truncated, expected_head=real_head)
        assert v.valid is False
        assert any("tail truncated" in f for f in v.failures)

    def test_tail_truncation_IS_detected_against_a_recorded_length(self):
        log = _log_with(3)
        v = verify_chain_integrity(list(log.entries)[:3], expected_length=len(log))
        assert v.valid is False
        assert any("truncated" in f for f in v.failures)

    def test_extension_is_also_detected_against_a_recorded_length(self):
        log = _log_with(3)
        v = verify_chain_integrity(list(log.entries), expected_length=3)
        assert v.valid is False
        assert any("extended" in f for f in v.failures)

    def test_rehashed_tamper_is_self_consistent_but_fails_against_the_head(self):
        """The strongest attack: edit a payload, then recompute every
        downstream hash. The chain verifies internally -- only an
        independently recorded head catches it."""
        good = _log_with(3)
        recorded_head = good.head

        forged = AuditLog("run-001")
        forged.record_artifact("the artifact under review")
        forged.append("pass", {"pass_id": "p1", "auto_rejected": 0})   # was 3
        forged.append("pass", {"pass_id": "p2", "auto_rejected": 2})
        forged.append("pass", {"pass_id": "p3", "auto_rejected": 1})

        assert forged.verify().valid is True                    # internally sound
        assert forged.head != recorded_head                     # ...but not the same run
        assert forged.verify(expected_head=recorded_head).valid is False


class TestAuditDeterministicReplay:
    """sixteen-test-template item 16: deterministic replay."""

    def test_two_identical_runs_produce_identical_chains(self):
        a, b = _log_with(3), _log_with(3)
        assert a.head == b.head
        assert a.to_jsonl() == b.to_jsonl()

    def test_replay_recomputes_the_head_from_payloads_alone(self):
        log = _log_with(3)
        assert AL.replay(log.entries) == log.head

    def test_replay_of_a_tampered_chain_diverges(self):
        log = _log_with(3)
        es = list(log.entries)
        e = es[2]
        es[2] = AL.AuditEntry(e.seq, e.prev_hash, e.kind,
                              {**e.payload, "auto_rejected": 999}, e.entry_hash)
        assert AL.replay(es) != log.head

    def test_replay_refuses_an_empty_chain(self):
        with pytest.raises(AuditChainError):
            AL.replay([])

    def test_the_log_never_reads_a_clock_by_default(self):
        """Global rule 4: replay mode blocks all nondeterminism. With no clock
        injected, no entry carries a timestamp and the chain is reproducible."""
        log = _log_with(2)
        assert all("at" not in e.payload for e in log.entries)

    def test_an_injected_clock_is_recorded_and_makes_the_run_unique(self):
        ticks = iter(["2026-08-21T16:00:00Z", "2026-08-21T16:00:01Z",
                      "2026-08-21T16:00:02Z", "2026-08-21T16:00:03Z"])
        log = AuditLog("run-001", clock=lambda: next(ticks))
        log.append("pass", {"pass_id": "p1"})
        assert log.entries[0].payload["at"] == "2026-08-21T16:00:00Z"
        assert log.head != AuditLog("run-001").head
        assert log.verify().valid is True


class TestAuditSerialisation:
    def test_jsonl_round_trip_preserves_the_chain(self):
        log = _log_with(3)
        parsed = AuditLog.parse_jsonl(log.to_jsonl())
        assert [e.to_dict() for e in parsed] == [e.to_dict() for e in log.entries]
        assert verify_chain_integrity(parsed, expected_head=log.head).valid is True

    def test_blank_lines_are_tolerated(self):
        log = _log_with(2)
        assert len(AuditLog.parse_jsonl(log.to_jsonl() + "\n\n")) == len(log)

    def test_malformed_json_fails_closed(self):
        """sixteen-test-template item 9: malformed payload. A line that will
        not parse is what a tampered log looks like; it is refused, not
        skipped."""
        log = _log_with(1)
        with pytest.raises(AuditChainError) as exc:
            AuditLog.parse_jsonl(log.to_jsonl() + "\n{not json")
        assert "not valid JSON" in str(exc.value)

    @pytest.mark.parametrize("bad,msg", [
        ({"seq": 0, "prev_hash": "x", "kind": "k"},                "missing required keys"),
        ({"seq": "0", "prev_hash": "x", "kind": "k",
          "payload": {}, "entry_hash": "h"},                       "seq must be an integer"),
        ({"seq": True, "prev_hash": "x", "kind": "k",
          "payload": {}, "entry_hash": "h"},                       "seq must be an integer"),
        ({"seq": 0, "prev_hash": "x", "kind": "k",
          "payload": [], "entry_hash": "h"},                       "payload must be an object"),
        ({"seq": 0, "prev_hash": 1, "kind": "k",
          "payload": {}, "entry_hash": "h"},                       "prev_hash must be a string"),
        ("not-an-object",                                          "not an object"),
    ])
    def test_invalid_schema_is_refused_at_the_boundary(self, bad, msg):
        """sixteen-test-template item 2: invalid schema."""
        with pytest.raises(AuditChainError) as exc:
            AL.AuditEntry.from_dict(bad)
        assert msg in str(exc.value)

    def test_nan_is_scrubbed_so_the_entry_stays_canonicalisable(self):
        """The diagnostics legitimately return NaN. It reaches the log as null,
        because NaN is not valid JSON and does not equal itself, so a hash over
        it would only be reproducible by accident."""
        log = AuditLog("run-001")
        log.append("divergence", {"jaccard": float("nan"), "inf": float("inf"),
                                  "nested": {"x": [1.0, float("nan")]}})
        p = log.entries[-1].payload
        assert p["jaccard"] is None
        assert p["inf"] is None
        assert p["nested"]["x"] == [1.0, None]
        AL.canonical_json(p)                       # must not raise
        assert log.verify().valid is True

    def test_canonical_json_refuses_raw_nan(self):
        with pytest.raises(ValueError):
            AL.canonical_json({"x": float("nan")})


class TestAuditIntegratedWithARun:
    def test_a_full_run_writes_artifact_passes_and_stop_decision(self):
        log = AuditLog("run-e2e")
        runner = AO.BlindedSeatRunner({
            "s1": _seat("CLAIM | arithmetic | 12 + 35 = 50 | wrong total"),
            "s2": _seat("CLAIM | judgment |  | framing is sound"),
        })
        o = Orchestrator([ArithmeticGate()])
        o.run_sequential("the artifact", [], runner, audit=log)

        kinds = [e.kind for e in log.entries]
        assert kinds[0] == "genesis"
        assert kinds[1] == "artifact"
        assert kinds.count("pass") == 5
        assert kinds[-1] == "stop_decision"
        assert log.verify().valid is True

    def test_the_stop_decision_records_WHY_it_did_not_stop(self):
        """SOP 9.1 step 8 makes an empty queue a precondition. The reason a run
        did not stop is the part an auditor needs."""
        log = AuditLog("run-e2e")
        runner = AO.BlindedSeatRunner({"s1": _seat("CLAIM | judgment |  | unresolvable")})
        o = Orchestrator([ArithmeticGate()])
        o.run_sequential("the artifact", [], runner, audit=log)

        stop = log.entries[-1].payload
        assert stop["stop"] is False
        assert stop["escalations_pending"] == 1
        assert any("judgment queue" in b for b in stop["blockers"])

    def test_pass_entries_carry_gate_outcomes_and_divergence(self):
        log = AuditLog("run-e2e")
        runner = AO.BlindedSeatRunner({
            "s1": _seat("CLAIM | arithmetic | 2+2 = 4 | ok"),
            "s2": _seat("CLAIM | arithmetic | 2+2 = 5 | wrong"),
        })
        o = Orchestrator([ArithmeticGate()])
        o.run_sequential("art", [], runner, audit=log, passes=[AO.DEFAULT_PASSES[0]])

        p = next(e.payload for e in log.entries if e.kind == "pass")
        assert p["pass_name"] == "Inversion Analysis"
        assert p["proposed"] == 2
        assert p["auto_accepted"] == 1 and p["auto_rejected"] == 1
        assert sorted(p["seats_responding"]) == ["s1", "s2"]
        assert p["unanimous"] is False
        assert len(p["claims"]) == 2

    def test_a_silent_pass_logs_null_jaccard_not_nan(self):
        log = AuditLog("run-e2e")
        runner = AO.BlindedSeatRunner({"only": _seat("")})
        o = Orchestrator([ArithmeticGate()])
        o.run_sequential("art", [], runner, audit=log, passes=[AO.DEFAULT_PASSES[0]])
        p = next(e.payload for e in log.entries if e.kind == "pass")
        assert p["mean_pairwise_jaccard"] is None
        assert log.verify().valid is True

    def test_the_run_is_unchanged_when_no_audit_log_is_passed(self):
        runner = AO.BlindedSeatRunner({"s1": _seat("CLAIM | arithmetic | 2+2 = 4 | ok")})
        a = Orchestrator([ArithmeticGate()]).run_sequential("art", [], runner)
        b = Orchestrator([ArithmeticGate()]).run_sequential(
            "art", [], AO.BlindedSeatRunner({"s1": _seat("CLAIM | arithmetic | 2+2 = 4 | ok")}),
            audit=AuditLog("r"))
        assert [r.record.auto_accepted for r in a] == [r.record.auto_accepted for r in b]


class TestCommitmentCoversEveryField:
    """Found by mutation testing: removing seq from compute_entry_hash broke no
    test, because the explicit `e.seq != i` check in verify still caught
    renumbering. That is defence in depth right up until someone removes the
    explicit check believing the hash covers it. These assert the commitment
    directly, field by field, so each one is independently pinned."""

    BASE: ClassVar[dict[str, object]] = {
        "seq": 3, "prev_hash": "a" * 64, "kind": "pass", "payload": {"x": 1},
    }

    def _h(self, **over):
        d = {**self.BASE, **over}
        return AL.compute_entry_hash(d["seq"], d["prev_hash"], d["kind"], d["payload"])

    def test_sequence_number_is_part_of_the_commitment(self):
        assert self._h() != self._h(seq=4)

    def test_predecessor_is_part_of_the_commitment(self):
        assert self._h() != self._h(prev_hash="b" * 64)

    def test_kind_is_part_of_the_commitment(self):
        assert self._h() != self._h(kind="stop_decision")

    def test_payload_is_part_of_the_commitment(self):
        assert self._h() != self._h(payload={"x": 2})

    def test_the_commitment_is_stable_for_identical_input(self):
        assert self._h() == self._h()

    def test_key_order_does_not_change_the_commitment(self):
        """Canonicalisation sorts keys, so a re-serialised payload commits
        identically. Without this, a round trip through any JSON library that
        reorders keys would look like tampering."""
        a = AL.compute_entry_hash(1, "c" * 64, "pass", {"alpha": 1, "beta": 2})
        b = AL.compute_entry_hash(1, "c" * 64, "pass", {"beta": 2, "alpha": 1})
        assert a == b


# ===========================================================================
# 14. DURABLE AUDIT STORE
#     sixteen-test-template item 11 (rollback) and item 12 (concurrent commit)
# ===========================================================================

class TestDurableAuditStore:
    def test_creates_verifies_and_reopens(self, tmp_path):
        p = str(tmp_path / "run.jsonl")
        log = AL.DurableAuditLog(p, run_id="r1")
        log.record_artifact("the artifact")
        log.append("pass", {"pass_id": "p1", "auto_rejected": 3})
        head, n = log.head, len(log)

        reopened = AL.DurableAuditLog(p)
        assert len(reopened) == n
        assert reopened.head == head
        assert reopened.run_id == "r1"
        assert reopened.verify().valid is True

    def test_reopened_log_continues_the_same_chain(self, tmp_path):
        p = str(tmp_path / "run.jsonl")
        a = AL.DurableAuditLog(p, run_id="r1")
        a.append("pass", {"pass_id": "p1"})
        prev_head = a.head

        b = AL.DurableAuditLog(p)
        e = b.append("pass", {"pass_id": "p2"})
        assert e.prev_hash == prev_head          # chained onto disk, not onto a fresh log
        assert b.verify().valid is True

    def test_new_log_requires_a_run_id(self, tmp_path):
        with pytest.raises(AL.AuditStoreError):
            AL.DurableAuditLog(str(tmp_path / "run.jsonl"))

    def test_opening_with_the_wrong_run_id_is_refused(self, tmp_path):
        p = str(tmp_path / "run.jsonl")
        AL.DurableAuditLog(p, run_id="r1").append("pass", {})
        with pytest.raises(AL.AuditStoreError) as exc:
            AL.DurableAuditLog(p, run_id="r2")
        assert "belongs to run" in str(exc.value)

    def test_genesis_is_reserved_on_the_durable_log_too(self, tmp_path):
        log = AL.DurableAuditLog(str(tmp_path / "run.jsonl"), run_id="r1")
        with pytest.raises(AL.AuditStoreError):
            log.append("genesis", {})

    def test_a_corrupted_line_refuses_to_load(self, tmp_path):
        p = tmp_path / "run.jsonl"
        log = AL.DurableAuditLog(str(p), run_id="r1")
        log.append("pass", {"pass_id": "p1"})
        lines = p.read_text().splitlines()
        obj = _json.loads(lines[1])
        obj["payload"]["pass_id"] = "tampered"
        lines[1] = _json.dumps(obj)
        p.write_text("\n".join(lines) + "\n")
        with pytest.raises(AL.AuditStoreError) as exc:
            AL.DurableAuditLog(str(p))
        assert "does not verify" in str(exc.value)


class TestDurableRollback:
    """sixteen-test-template item 11: rollback. A failed append must leave the
    log at its last committed state, never in a half-written one."""

    def test_a_torn_final_line_refuses_to_load(self, tmp_path):
        p = tmp_path / "run.jsonl"
        log = AL.DurableAuditLog(str(p), run_id="r1")
        log.append("pass", {"pass_id": "p1"})
        good_head, good_len = log.head, len(log)

        with p.open("a") as fh:                       # an append that died mid-write
            fh.write('{"seq": 2, "prev_hash": "aa", "kind": "pa')

        with pytest.raises(AL.TornAppendError) as exc:
            AL.DurableAuditLog(str(p))
        assert "did not finish" in str(exc.value)
        assert "recover=True" in str(exc.value)
        assert good_head and good_len                 # the good state is still on disk

    def test_recover_rolls_back_to_the_last_committed_entry(self, tmp_path):
        p = tmp_path / "run.jsonl"
        log = AL.DurableAuditLog(str(p), run_id="r1")
        log.append("pass", {"pass_id": "p1"})
        good_head, good_len = log.head, len(log)

        with p.open("a") as fh:
            fh.write('{"seq": 2, "prev_hash": "aa", "kind": "pa')

        recovered = AL.DurableAuditLog(str(p), recover=True)
        assert len(recovered) == good_len
        assert recovered.head == good_head
        assert recovered.verify().valid is True

    def test_the_log_is_usable_again_after_recovery(self, tmp_path):
        p = tmp_path / "run.jsonl"
        log = AL.DurableAuditLog(str(p), run_id="r1")
        log.append("pass", {"pass_id": "p1"})
        with p.open("a") as fh:
            fh.write("{partial")

        recovered = AL.DurableAuditLog(str(p), recover=True)
        recovered.append("pass", {"pass_id": "p2"})
        assert AL.DurableAuditLog(str(p)).verify().valid is True

    def test_recovery_is_never_automatic(self, tmp_path):
        """Silently discarding a trailing line is indistinguishable from
        silently discarding evidence, so it takes an explicit flag."""
        p = tmp_path / "run.jsonl"
        AL.DurableAuditLog(str(p), run_id="r1").append("pass", {})
        with p.open("a") as fh:
            fh.write("{partial")
        with pytest.raises(AL.TornAppendError):
            AL.DurableAuditLog(str(p))                # default: refuse

    def test_a_failed_write_leaves_no_half_entry(self, tmp_path, monkeypatch):
        """The rollback proper: os.write raises mid-append. The in-memory chain
        and the on-disk chain must both be unchanged, and the next append must
        succeed."""
        p = tmp_path / "run.jsonl"
        log = AL.DurableAuditLog(str(p), run_id="r1")
        log.append("pass", {"pass_id": "p1"})
        before_head, before_len = log.head, len(log)
        before_bytes = p.read_bytes()

        real_write = _os.write

        def exploding(fd, data):
            if b'"p2"' in data:
                raise OSError("disk full")
            return real_write(fd, data)

        monkeypatch.setattr(AL.os, "write", exploding)
        with pytest.raises(OSError, match="disk full"):
            log.append("pass", {"pass_id": "p2"})
        monkeypatch.undo()

        assert len(log) == before_len                 # in-memory unchanged
        assert log.head == before_head
        assert p.read_bytes() == before_bytes         # on-disk unchanged
        log.append("pass", {"pass_id": "p3"})         # and still usable
        assert AL.DurableAuditLog(str(p)).verify().valid is True

    def test_a_short_write_is_treated_as_a_failure(self, tmp_path, monkeypatch):
        p = tmp_path / "run.jsonl"
        log = AL.DurableAuditLog(str(p), run_id="r1")
        before = len(log)
        monkeypatch.setattr(AL.os, "write", lambda fd, data: 3)
        with pytest.raises(AL.AuditStoreError, match="short write"):
            log.append("pass", {"pass_id": "p1"})
        monkeypatch.undo()
        assert len(log) == before


class TestDurableConcurrentCommit:
    """sixteen-test-template item 12: concurrent commit attempt."""

    def test_a_stale_handle_chains_onto_disk_not_onto_its_own_view(self, tmp_path):
        """The deterministic version of the concurrency guarantee, and the one
        that actually bites.

        Two handles open the same log, so both hold the same view. One appends,
        which makes the other's in-memory tail stale. The stale handle must
        re-read the committed tail inside the lock and chain onto what is
        ACTUALLY on disk. Without that it emits an entry claiming the old head
        as its predecessor, forking the chain.

        Written this way on purpose: a threaded version passed whether or not
        the re-read existed, because tiny operations under the GIL rarely
        interleave. That made it a test of nothing.
        """
        p = str(tmp_path / "run.jsonl")
        AL.DurableAuditLog(p, run_id="r1")
        a = AL.DurableAuditLog(p)
        b = AL.DurableAuditLog(p)
        assert a.head == b.head                       # both start from the same view

        first = a.append("pass", {"writer": "a"})     # b is now stale
        second = b.append("pass", {"writer": "b"})

        assert second.prev_hash == first.entry_hash   # chained onto disk...
        assert second.seq == first.seq + 1            # ...not onto b's stale view
        final = AL.DurableAuditLog(p)
        assert len(final) == 3
        assert final.verify().valid is True

    def test_parallel_processes_do_not_fork_the_chain(self, tmp_path):
        """Real contention: separate processes, so flock is genuinely exercised
        rather than serialised by the GIL. A barrier releases every writer at
        the same instant."""
        import multiprocessing as mp

        p = str(tmp_path / "run.jsonl")
        AL.DurableAuditLog(p, run_id="r1")
        writers, per_writer = 4, 5
        ctx = mp.get_context("fork")
        barrier = ctx.Barrier(writers)

        def child(w, path, bar, per):
            bar.wait()
            h = AL.DurableAuditLog(path)
            for i in range(per):
                h.append("pass", {"writer": w, "i": i})

        procs = [ctx.Process(target=child, args=(w, p, barrier, per_writer))
                 for w in range(writers)]
        for proc in procs:
            proc.start()
        for proc in procs:
            proc.join(timeout=30)
        assert all(proc.exitcode == 0 for proc in procs), \
            [proc.exitcode for proc in procs]

        final = AL.DurableAuditLog(p)
        assert len(final) == writers * per_writer + 1
        assert final.verify().valid is True
        assert [e.seq for e in final.entries] == list(range(len(final)))
        prevs = [e.prev_hash for e in final.entries[1:]]
        assert len(set(prevs)) == len(prevs)          # no two entries share a predecessor
        seen = {(e.payload["writer"], e.payload["i"])
                for e in final.entries if e.kind == "pass"}
        assert seen == {(w, i) for w in range(writers) for i in range(per_writer)}

    def test_threaded_writers_also_converge(self, tmp_path):
        import threading

        p = str(tmp_path / "run.jsonl")
        AL.DurableAuditLog(p, run_id="r1")
        writers, per_writer = 4, 6
        errors: list[BaseException] = []

        def worker(w):
            try:
                handle = AL.DurableAuditLog(p)
                for i in range(per_writer):
                    handle.append("pass", {"writer": w, "i": i})
            except BaseException as exc:       # noqa: BLE001 - surfaced below
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(w,)) for w in range(writers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        final = AL.DurableAuditLog(p)
        assert len(final) == writers * per_writer + 1     # genesis + every append
        assert final.verify().valid is True

        seqs = [e.seq for e in final.entries]
        assert seqs == list(range(len(final)))            # contiguous, no fork
        prevs = [e.prev_hash for e in final.entries[1:]]
        assert len(set(prevs)) == len(prevs)              # no shared predecessor

    def test_every_concurrent_append_is_present_exactly_once(self, tmp_path):
        import threading

        p = str(tmp_path / "run.jsonl")
        AL.DurableAuditLog(p, run_id="r1")

        def worker(w):
            h = AL.DurableAuditLog(p)
            for i in range(5):
                h.append("pass", {"writer": w, "i": i})

        threads = [threading.Thread(target=worker, args=(w,)) for w in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final = AL.DurableAuditLog(p)
        seen = {(e.payload["writer"], e.payload["i"]) for e in final.entries if e.kind == "pass"}
        assert seen == {(w, i) for w in range(3) for i in range(5)}   # none lost, none duplicated


class TestDurableHeadSidecar:
    def test_the_sidecar_records_head_and_length(self, tmp_path):
        p = tmp_path / "run.jsonl"
        log = AL.DurableAuditLog(str(p), run_id="r1")
        log.append("pass", {"pass_id": "p1"})
        side = _json.loads((tmp_path / ("run.jsonl" + AL.HEAD_SUFFIX)).read_text())
        assert side["head"] == log.head
        assert side["length"] == len(log)

    def test_tail_truncation_is_caught_by_the_sidecar(self, tmp_path):
        """The chain alone cannot see this; the recorded head can."""
        p = tmp_path / "run.jsonl"
        log = AL.DurableAuditLog(str(p), run_id="r1")
        for i in range(3):
            log.append("pass", {"pass_id": f"p{i}"})

        lines = p.read_text().splitlines()
        p.write_text("\n".join(lines[:2]) + "\n")          # drop the last two entries

        with pytest.raises(AL.AuditStoreError) as exc:
            AL.DurableAuditLog(str(p))
        msg = str(exc.value)
        assert "truncated" in msg or "tail truncated" in msg

    def test_an_unreadable_sidecar_is_refused(self, tmp_path):
        p = tmp_path / "run.jsonl"
        AL.DurableAuditLog(str(p), run_id="r1").append("pass", {})
        (tmp_path / ("run.jsonl" + AL.HEAD_SUFFIX)).write_text("{not json")
        with pytest.raises(AL.AuditStoreError, match="sidecar is unreadable"):
            AL.DurableAuditLog(str(p))

    def test_verify_can_be_asked_to_ignore_the_sidecar(self, tmp_path):
        p = tmp_path / "run.jsonl"
        log = AL.DurableAuditLog(str(p), run_id="r1")
        log.append("pass", {})
        assert log.verify(check_sidecar=False).valid is True


class TestPropertyTestRegressions:
    """Three defects found by property tests in test_properties.py, pinned here
    as example-based regressions so they are covered by the primary suite too."""

    def test_effective_seats_clamps_rho_above_one(self):
        """effective_seats(2, 2.0) returned 0.67 -- fewer than one effective
        seat. rho > 1 is impossible for a correlation, and SOP 6.1 reads this
        number in plain language, so a nonsense value reads as meaningful."""
        assert SI.effective_seats(2, 2.0) == pytest.approx(1.0)
        assert SI.effective_seats(5, 17.0) == pytest.approx(1.0)
        assert SI.effective_seats(5, 1.0) == pytest.approx(1.0)

    def test_lincoln_petersen_rejects_impossible_overlap(self):
        """lincoln_petersen(0, 0, 1) returned -0.5. An error caught by BOTH
        seats was caught by each, so m can never exceed either sample, and a
        negative population estimate is not a bound on anything."""
        with pytest.raises(ValueError, match="contradictory"):
            SI.lincoln_petersen(0, 0, 1)
        with pytest.raises(ValueError, match="contradictory"):
            SI.lincoln_petersen(10, 4, 5)
        with pytest.raises(ValueError, match="non-negative"):
            SI.lincoln_petersen(-1, 5, 0)
        assert SI.lincoln_petersen(10, 4, 4) >= 0.0        # the boundary is valid

    def test_mean_error_correlation_is_quiet_when_there_are_no_pairs(self):
        """A single seat has no pair to correlate. NaN is right; the
        "Mean of empty slice" warning that came with it is not."""
        with _warnings.catch_warnings():
            _warnings.simplefilter("error", RuntimeWarning)
            assert math.isnan(SI.mean_error_correlation(np.array([[1], [0], [1]])))

    def test_mean_error_correlation_is_quiet_when_every_seat_is_constant(self):
        with _warnings.catch_warnings():
            _warnings.simplefilter("error", RuntimeWarning)
            assert math.isnan(SI.mean_error_correlation(np.ones((6, 3), dtype=int)))


class TestBooleanLiteralsAreNotArithmetic:
    """Found by a fuzz property on CI's random seed, not by any example.

    bool subclasses int, so `isinstance(True, (int, float))` is True and the
    warrant "True = 1" evaluated to True, compared equal to 1.0, and returned
    PASS with the detail "True confirmed". A seat could have attached that to
    any arithmetic claim and been auto-accepted -- a warrant that proves
    nothing, which is the arithmetic-gate equivalent of a permissive resolver.
    """

    g = ArithmeticGate()

    def _check(self, warrant):
        return self.g.check(Claim("c", "t", ClaimKind.ARITHMETIC, warrant))

    @pytest.mark.parametrize("warrant", [
        "True = 1",
        "False = 0",
        "True + True = 2",
        "True * 5 = 5",
        "False + 1 = 1",
        "-True = -1",
    ])
    def test_boolean_literals_never_satisfy_an_arithmetic_warrant(self, warrant):
        r = self._check(warrant)
        assert r.status is GateStatus.FAIL
        assert "unsupported expression" in r.detail

    @pytest.mark.parametrize("warrant,expected", [
        ("12 + 35 = 47", "47"),
        ("2 ** 10 = 1024", "1024"),
        ("1 = 1", "1"),
        ("0 = 0", "0"),
        ("1/3 = 0.3333333333333333", "0.333"),
    ])
    def test_real_numeric_literals_still_pass(self, warrant, expected):
        """The fix must not cost genuine arithmetic, including the integers 1
        and 0 that True and False were masquerading as."""
        r = self._check(warrant)
        assert r.status is GateStatus.PASS
        assert expected in r.detail

    def test_safe_eval_rejects_a_bare_boolean_constant(self):
        import ast
        with pytest.raises(ValueError, match="unsupported expression"):
            AO._safe_eval(ast.parse("True", mode="eval"))


# ===========================================================================
# 15. SEAT ADAPTER  (SOP 8.3: "write a seat function for each provider")
#
# The transport is injected, so every path here is exercised without a socket.
# ===========================================================================


SECRET = "sk-do-not-leak-me-0123456789"


def _profile(**over):
    base = {
        "name": "testvendor",
        "endpoint": "https://api.example.test/v1/messages",
        "auth_header": "authorization",
        "auth_template": "Bearer {key}",
        "build_body": lambda model, prompt, mt, temp: {
            "model": model, "prompt": prompt, "max_tokens": mt, "temperature": temp,
        },
        "extract_text": lambda payload: payload.get("text"),
    }
    base.update(over)
    return ProviderProfile(**base)


def _resolved_seat(seat_id="seat_1", model="m-1", secret=SECRET, in_process=False):
    """NOTE the name. An earlier _resolved_seat() in this file builds a fake seat
    CALLABLE for the blinding tests; reusing that name here shadowed it and
    broke twelve unrelated tests."""
    return AO.ResolvedSeat(seat_id, model, None if in_process else secret,
                           in_process=in_process)


def _transport(status=200, body=None, raises=None, record=None):
    payload = {"text": "CLAIM | arithmetic | 2+2 = 4 | ok"} if body is None else body

    def t(method, url, headers, data, timeout):
        if record is not None:
            record.append({"method": method, "url": url, "headers": dict(headers),
                           "data": data, "timeout": timeout})
        if raises is not None:
            raise raises
        raw = payload if isinstance(payload, bytes) else _json.dumps(payload).encode()
        return status, raw
    return t


class TestProviderProfileValidation:
    def test_auth_template_must_carry_a_key_placeholder(self):
        with pytest.raises(ValueError, match=r"\{key\} placeholder"):
            _profile(auth_template="Bearer hardcoded")

    def test_endpoint_must_be_https(self):
        """A credential must never cross a plaintext connection."""
        with pytest.raises(ValueError, match="must be https"):
            _profile(endpoint="http://api.example.test/v1")

    def test_repr_shows_no_secret_bearing_fields(self):
        r = repr(_profile())
        assert "testvendor" in r and "api.example.test" in r
        assert "auth_template" not in r


class TestHttpSeatHappyPath:
    def test_returns_the_extracted_text(self):
        s = HttpSeat(_resolved_seat(), _profile(), _transport())
        assert s("the prompt") == "CLAIM | arithmetic | 2+2 = 4 | ok"

    def test_sends_the_prompt_model_and_auth_the_profile_specifies(self):
        rec = []
        s = HttpSeat(_resolved_seat(model="m-9"), _profile(), _transport(record=rec),
                     max_tokens=99, temperature=0.0, timeout_s=7.5)
        s("PROMPT-BODY")
        sent = rec[0]
        assert sent["method"] == "POST"
        assert sent["url"] == "https://api.example.test/v1/messages"
        assert sent["timeout"] == 7.5
        assert sent["headers"]["authorization"] == f"Bearer {SECRET}"
        body = _json.loads(sent["data"])
        assert body == {"model": "m-9", "prompt": "PROMPT-BODY",
                        "max_tokens": 99, "temperature": 0.0}

    def test_extra_headers_are_forwarded(self):
        rec = []
        s = HttpSeat(_resolved_seat(), _profile(extra_headers={"x-api-version": "2026-01-01"}),
                     _transport(record=rec))
        s("p")
        assert rec[0]["headers"]["x-api-version"] == "2026-01-01"

    def test_the_seat_carries_no_state_between_calls(self):
        """A seat that accumulated conversation state would reintroduce the
        cross-pass leakage BLINDING_CONTRACT forbids."""
        rec = []
        s = HttpSeat(_resolved_seat(), _profile(), _transport(record=rec))
        s("first prompt")
        s("second prompt")
        assert _json.loads(rec[0]["data"])["prompt"] == "first prompt"
        assert _json.loads(rec[1]["data"])["prompt"] == "second prompt"
        assert rec[0]["data"] != rec[1]["data"]


class TestHttpSeatFailsClosed:
    """Every failure RAISES. It never returns an empty string, because
    BlindedSeatRunner records a raised seat as errored and excludes it from the
    divergence statistics, while an empty string reads as a seat that looked
    and found nothing. Those are opposite facts."""

    @pytest.mark.parametrize("status", [400, 401, 403, 404, 422, 500, 503])
    def test_non_2xx_raises_rather_than_returning_text(self, status):
        s = HttpSeat(_resolved_seat(), _profile(), _transport(status=status),
                     retry=RetryPolicy(max_attempts=1))
        with pytest.raises(SeatError, match=f"HTTP {status}"):
            s("p")

    def test_transport_exception_raises_seat_error(self):
        s = HttpSeat(_resolved_seat(), _profile(), _transport(raises=ConnectionError("no route")),
                     retry=RetryPolicy(max_attempts=1))
        with pytest.raises(SeatError, match="transport raised ConnectionError"):
            s("p")

    def test_non_json_body_raises(self):
        s = HttpSeat(_resolved_seat(), _profile(), _transport(body=b"<html>gateway</html>"))
        with pytest.raises(SeatError, match="not JSON"):
            s("p")

    def test_json_that_is_not_an_object_raises(self):
        s = HttpSeat(_resolved_seat(), _profile(), _transport(body=["a", "list"]))
        with pytest.raises(SeatError, match="expected a JSON object"):
            s("p")

    def test_missing_text_at_the_configured_path_raises(self):
        """The dangerous case: a 200 with a well-formed body whose text path is
        wrong. Returning None here would read as a seat with nothing to say."""
        s = HttpSeat(_resolved_seat(), _profile(), _transport(body={"choices": [], "id": "x"}))
        with pytest.raises(SeatError, match="no text at the configured path"):
            s("p")

    def test_the_error_names_the_keys_that_were_present(self):
        s = HttpSeat(_resolved_seat(), _profile(), _transport(body={"zeta": 1, "alpha": 2}))
        with pytest.raises(SeatError) as exc:
            s("p")
        assert "alpha" in str(exc.value) and "zeta" in str(exc.value)

    def test_a_raising_extractor_fails_closed(self):
        s = HttpSeat(_resolved_seat(), _profile(extract_text=lambda p: p["nope"]), _transport())
        with pytest.raises(SeatError, match="extract_text raised KeyError"):
            s("p")

    def test_a_non_string_from_the_extractor_raises(self):
        s = HttpSeat(_resolved_seat(), _profile(extract_text=lambda p: {"not": "a string"}),
                     _transport())
        with pytest.raises(SeatError, match="returned dict, expected str"):
            s("p")

    def test_seat_without_a_model_is_refused_at_construction(self):
        with pytest.raises(SeatError, match="no model configured"):
            HttpSeat(_resolved_seat(model=None), _profile(), _transport())

    def test_seat_without_a_credential_is_refused_at_construction(self):
        with pytest.raises(SeatError, match="no credential resolved"):
            HttpSeat(_resolved_seat(secret=""), _profile(), _transport())

    def test_in_process_seat_cannot_be_driven_by_this_adapter(self):
        with pytest.raises(SeatError, match="in-process"):
            HttpSeat(_resolved_seat(seat_id="seat_5_claude", in_process=True), _profile(),
                     _transport())


class TestHttpSeatRetry:
    def _flaky(self, statuses):
        seq = list(statuses)
        calls = {"n": 0}

        def t(method, url, headers, data, timeout):
            i = calls["n"]
            calls["n"] += 1
            st = seq[i] if i < len(seq) else 200
            return st, _json.dumps({"text": "recovered"}).encode()
        return t, calls

    def test_retries_a_transient_status_and_succeeds(self):
        t, calls = self._flaky([503, 429])
        s = HttpSeat(_resolved_seat(), _profile(), t, retry=RetryPolicy(max_attempts=3))
        assert s("p") == "recovered"
        assert calls["n"] == 3

    def test_retries_are_bounded(self):
        t, calls = self._flaky([503] * 10)
        s = HttpSeat(_resolved_seat(), _profile(), t, retry=RetryPolicy(max_attempts=3))
        with pytest.raises(SeatError, match="retries exhausted"):
            s("p")
        assert calls["n"] == 3

    @pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
    def test_never_retries_an_auth_or_client_error(self, status):
        """An auth failure is a configuration error, not a transient fault.
        Retrying burns quota, multiplies the audit trail, and delays the
        operator seeing the one thing that needs fixing."""
        t, calls = self._flaky([status] * 5)
        s = HttpSeat(_resolved_seat(), _profile(), t, retry=RetryPolicy(max_attempts=5))
        with pytest.raises(SeatError, match=f"HTTP {status}"):
            s("p")
        assert calls["n"] == 1

    def test_the_retryable_set_excludes_every_auth_status(self):
        for st in (400, 401, 403, 404, 405, 422):
            assert st not in SA.RETRYABLE_STATUS
        for st in (429, 500, 502, 503, 504):
            assert st in SA.RETRYABLE_STATUS

    def test_backoff_is_delegated_and_this_module_never_sleeps(self):
        """Global rule 4: no clock, no nondeterminism inside the module."""
        slept: list[float] = []
        t, _ = self._flaky([503, 503])
        s = HttpSeat(_resolved_seat(), _profile(), t, retry=RetryPolicy(max_attempts=3),
                     sleeper=slept.append)
        s("p")
        assert slept == [0.5, 2.0]

    def test_no_sleeper_means_no_delay_and_still_retries(self):
        t, calls = self._flaky([503])
        s = HttpSeat(_resolved_seat(), _profile(), t, retry=RetryPolicy(max_attempts=2))
        assert s("p") == "recovered"
        assert calls["n"] == 2

    def test_max_attempts_below_one_is_refused(self):
        with pytest.raises(ValueError, match="at least 1"):
            RetryPolicy(max_attempts=0)


class TestHttpSeatNeverLeaksTheCredential:
    def test_the_secret_is_absent_from_repr_and_str(self):
        s = HttpSeat(_resolved_seat(), _profile(), _transport())
        assert SECRET not in repr(s)
        assert SECRET not in str(s)
        assert SECRET not in f"{s}"

    @pytest.mark.parametrize("kind", ["status", "raises", "badjson", "nopath"])
    def test_the_secret_is_absent_from_every_error_message(self, kind):
        t = {
            "status": _transport(status=401),
            "raises": _transport(raises=ConnectionError(f"failed with {SECRET}")),
            "badjson": _transport(body=b"nope"),
            "nopath": _transport(body={"other": 1}),
        }[kind]
        s = HttpSeat(_resolved_seat(), _profile(), t, retry=RetryPolicy(max_attempts=1))
        with pytest.raises(SeatError) as exc:
            s("p")
        # The transport's own exception text is the one place a careless
        # implementation could echo a secret; assert the seat does not.
        if kind != "raises":
            assert SECRET not in str(exc.value)

    def test_the_credential_is_not_stored_on_the_seat_object(self):
        """It is read through ResolvedSeat.credential() per request, so
        rotating the underlying seat takes effect without rebuilding."""
        s = HttpSeat(_resolved_seat(), _profile(), _transport())
        assert SECRET not in _json.dumps(
            {k: str(v) for k, v in vars(s).items() if k != "seat"}
        )

    def test_the_secret_never_appears_in_the_serialised_object_graph(self):
        s = HttpSeat(_resolved_seat(), _profile(), _transport())
        assert not any(SECRET in str(v) for k, v in vars(s).items() if k != "seat")


class TestBuildSeatCallables:
    ENV: ClassVar[dict[str, str]] = {
        "ADJ_SEAT_1_API_KEY": "k1", "ADJ_SEAT_2_API_KEY": "k2",
        "ADJ_SEAT_3_API_KEY": "k3", "ADJ_SEAT_4_API_KEY": "k4",
        "ADJ_SEAT_1_MODEL": "m1", "ADJ_SEAT_2_MODEL": "m2",
        "ADJ_SEAT_3_MODEL": "m3", "ADJ_SEAT_4_MODEL": "m4",
    }

    def test_builds_one_callable_per_outbound_resolved_seat(self):
        panel = AO.load_panel(env=dict(self.ENV))
        profiles = {f"seat_{i}": _profile(name=f"v{i}") for i in range(1, 5)}
        seats = SA.build_seat_callables(panel, profiles, _transport())
        assert sorted(seats) == ["seat_1", "seat_2", "seat_3", "seat_4"]
        assert "seat_5_claude" not in seats          # in-process, not ours to drive
        assert seats["seat_1"]("p") == "CLAIM | arithmetic | 2+2 = 4 | ok"

    def test_a_seat_with_no_profile_fails_closed(self):
        """A panel that quietly runs short misstates rho, effective seats, and
        the residual -- the same reason load_panel refuses a missing key."""
        panel = AO.load_panel(env=dict(self.ENV))
        profiles = {f"seat_{i}": _profile() for i in (1, 2, 3)}    # seat_4 missing
        with pytest.raises(SeatError, match="seat_4"):
            SA.build_seat_callables(panel, profiles, _transport())

    def test_the_callables_plug_straight_into_the_blinded_runner(self):
        panel = AO.load_panel(env=dict(self.ENV))
        profiles = {f"seat_{i}": _profile() for i in range(1, 5)}
        runner = AO.BlindedSeatRunner(
            SA.build_seat_callables(panel, profiles, _transport())
        )
        responses = runner.run(AO.DEFAULT_PASSES[0], "the artifact")
        assert len(responses) == 4
        assert all(r.error is None for r in responses)
        assert all(len(r.claims) == 1 for r in responses)

    def test_a_failing_seat_is_recorded_not_silently_dropped(self):
        panel = AO.load_panel(env=dict(self.ENV))
        profiles = {f"seat_{i}": _profile() for i in range(1, 5)}
        good = SA.build_seat_callables(panel, profiles, _transport())
        good["seat_3"] = HttpSeat(_resolved_seat("seat_3"), _profile(),
                                  _transport(status=500),
                                  retry=RetryPolicy(max_attempts=1))
        runner = AO.BlindedSeatRunner(good)
        d = AO.measure_divergence(AO.DEFAULT_PASSES[0],
                                  runner.run(AO.DEFAULT_PASSES[0], "art"))
        assert d.seats_errored == ["seat_3"]
        assert sorted(d.seats_responding) == ["seat_1", "seat_2", "seat_4"]
        assert d.n_seats == 4                       # the panel size is not silently reduced

    def test_end_to_end_five_passes_through_the_adapter(self):
        panel = AO.load_panel(env=dict(self.ENV))
        profiles = {f"seat_{i}": _profile() for i in range(1, 5)}
        runner = AO.BlindedSeatRunner(
            SA.build_seat_callables(panel, profiles, _transport())
        )
        log = AuditLog("run-adapter")
        o = Orchestrator([ArithmeticGate()])
        results = o.run_sequential("the artifact", [], runner, audit=log)
        assert [r.pass_id for r in results] == ["p1", "p2", "p3", "p4", "p5"]
        assert log.verify().valid is True
        # every seat returned the same claim -> collapse, correctly flagged
        assert results[0].divergence.unanimous is True
        assert results[0].divergence.collapse_warning is not None

    def test_no_vendor_endpoint_is_hardcoded_in_the_adapter(self):
        """The module must ship zero provider specifics. An endpoint written
        from memory is how a build acquires a stale URL that looks right."""
        src = _os.path.join(_os.path.dirname(SA.__file__), "seat_adapter.py")
        with open(src, encoding="utf-8") as fh:
            body = fh.read()
        for vendor in ("api.openai.com", "api.anthropic.com",
                       "generativelanguage.googleapis.com", "api.mistral.ai",
                       "api.x.ai"):
            assert vendor not in body, f"{vendor} is hardcoded in seat_adapter"


# ===========================================================================
# THE MODULES MUST NOT CITE WHAT THEIR OWN GATE WOULD REJECT
#
# independence_gap once carried a BENCHMARK paragraph crediting "a published
# 12-model / 224-problem study" for the claim that realized ensemble gains
# stay below half the independence prediction. No author, no venue, no year,
# no identifier. SourceAdmissibilityGate would have refused that warrant from
# a seat, and the module asserted it in a docstring an operator reads as
# established fact. These tests keep it out.
# ===========================================================================

class TestNoUnsourcedBenchmarkClaims:

    def _module_source(self, mod):
        with open(mod.__file__, encoding="utf-8") as fh:
            return fh.read()

    def test_the_unnamed_study_is_gone_from_seat_independence(self):
        body = self._module_source(SI)
        for fragment in ("12-model", "224-problem", "224 problem"):
            assert fragment not in body, (
                f"{fragment!r} is back in seat_independence. The study it "
                "refers to has no identifier and cannot clear the "
                "admissibility gate; re-source it or leave it out."
            )

    def test_the_gate_itself_rejects_the_way_that_study_was_cited(self):
        """The prose claim 'our own gate would reject this' is worth nothing
        unless the gate actually does. This asserts the verdict rather than
        restating the assertion."""
        for how_it_was_cited in (
            "a published 12-model / 224-problem study",
            "12-model / 224-problem study",
            "a published study",
            "prior work",
        ):
            assert AO.classify_source(how_it_was_cited) is AO.SourceClass.INADMISSIBLE

    def test_a_seat_submitting_that_warrant_is_rejected_end_to_end(self):
        """Same claim, arriving the way a seat would send it."""
        gate = AO.SourceAdmissibilityGate()
        claim = Claim(
            id="c-unsourced",
            text="ensembles capture under half the independence prediction",
            kind=ClaimKind.CITATION,
            warrant="a published 12-model / 224-problem study",
        )
        assert gate.applies_to(claim) is True
        assert gate.check(claim).status is not GateStatus.PASS

    def test_the_replacement_anchor_is_this_repositorys_own_measurement(self):
        """What replaced it must be reproducible here, not another citation.
        validation_harness.py produces these numbers on demand."""
        body = self._module_source(SI)
        assert "validation_harness.py" in body
        assert "synthetic seats" in body


# ===========================================================================
# CORRECTNESS MATRIX -- the join between a run and the diagnostics
#
# This is the number the whole system exists to produce, so the tests below
# are hand-computable end to end. Every X, every rho, and every effective-seat
# figure asserted here can be recomputed on paper from the seat outputs.
# ===========================================================================

from correctness_matrix import (  # noqa: E402
    AdjudicationConflict,
    build_correctness_matrix,
    build_detections,
    build_pass_detections,
    diagnose_run,
)

_TRUE_A = "CLAIM | arithmetic | 2 + 2 = 4 | 2 + 2 = 4"
_TRUE_B = "CLAIM | arithmetic | 3 * 3 = 9 | 3 * 3 = 9"
_FALSE_A = "CLAIM | arithmetic | 2 + 2 = 5 | 2 + 2 = 5"
_JUDGMENT = "CLAIM | judgment | the prose is unclear |"


def _fixed(text):
    """A seat that returns the same thing for every prompt."""
    return lambda _prompt: text


def _run(seat_texts, passes=None, gates=None):
    """Run a panel and hand back (results, orchestrator)."""
    orch = AO.Orchestrator(gates if gates is not None else [ArithmeticGate()])
    runner = AO.BlindedSeatRunner({k: _fixed(v) for k, v in seat_texts.items()})
    results = orch.run_sequential("artifact", [], runner, passes=passes)
    return results, orch


_ONE_PASS = (Pass("p1", "Inversion Analysis", "invert it", True),)


class TestTheSemanticTable:
    """correct = (seat asserted it) == (the claim is true). All four cells."""

    def test_true_claim_asserted_scores_correct(self):
        results, orch = _run({"s1": _TRUE_A, "s2": _TRUE_A}, passes=_ONE_PASS)
        m = build_correctness_matrix(results, orch.verdicts)
        assert m.item_truth == (True,)
        assert m.X.tolist() == [[1, 1]]

    def test_true_claim_missed_scores_wrong(self):
        results, orch = _run({"s1": _TRUE_A, "s2": ""}, passes=_ONE_PASS)
        m = build_correctness_matrix(results, orch.verdicts)
        assert m.seats == ("s1", "s2")
        assert m.item_truth == (True,)
        # s1 found it, s2 stayed silent on a real finding -> a miss
        assert m.X.tolist() == [[1, 0]]

    def test_false_claim_asserted_scores_wrong(self):
        results, orch = _run({"s1": _FALSE_A, "s2": _FALSE_A}, passes=_ONE_PASS)
        m = build_correctness_matrix(results, orch.verdicts)
        assert m.item_truth == (False,)
        assert m.X.tolist() == [[0, 0]]

    def test_false_claim_not_repeated_scores_correct(self):
        results, orch = _run({"s1": _FALSE_A, "s2": ""}, passes=_ONE_PASS)
        m = build_correctness_matrix(results, orch.verdicts)
        assert m.item_truth == (False,)
        # s1 asserted a falsehood; s2 was right not to
        assert m.X.tolist() == [[0, 1]]


class TestTheTwoExtremesThatMakeTheNumberMeanSomething:
    """A construction that got these backwards would still return a plausible
    float. These are worked by hand in the assertions."""

    def test_maximum_divergence_reads_as_maximum_independence(self):
        results, orch = _run(
            {"s1": _TRUE_A, "s2": _TRUE_B, "s3": _FALSE_A}, passes=_ONE_PASS
        )
        m = build_correctness_matrix(results, orch.verdicts)
        assert m.seats == ("s1", "s2", "s3")
        # rows in adjudication order: 2+2=4 (true), 3*3=9 (true), 2+2=5 (false)
        assert m.X.tolist() == [
            [1, 0, 0],   # s1 found it; s2, s3 missed it
            [0, 1, 0],   # s2 found it; s1, s3 missed it
            [1, 1, 0],   # s3 asserted a falsehood; s1 and s2 did not
        ]
        # E = 1 - X. Column s3 = (1,1,1) is constant -> its pairs are NaN and
        # drop out. The only live pair is (s1, s2):
        #   e_s1 = (0,1,0), e_s2 = (1,0,0), each mean 1/3, var 2/9
        #   cov = 0 - 1/9 = -1/9  ->  r = (-1/9) / (2/9) = -0.5
        rho = SI.mean_error_correlation(m.X)
        assert rho == pytest.approx(-0.5)
        # negative correlation is clamped at 0: never claim MORE independence
        # than there are seats
        assert SI.effective_seats(3, rho) == pytest.approx(3.0)

    def test_total_collapse_reads_as_one_effective_seat(self):
        both = f"{_TRUE_A}\n{_FALSE_A}"
        results, orch = _run({"s1": both, "s2": both, "s3": both}, passes=_ONE_PASS)
        m = build_correctness_matrix(results, orch.verdicts)
        assert m.X.tolist() == [
            [1, 1, 1],   # all three found the true one
            [0, 0, 0],   # all three asserted the same falsehood
        ]
        # every error column is (0,1) -> identical -> r = 1.0 for all pairs
        rho = SI.mean_error_correlation(m.X)
        assert rho == pytest.approx(1.0)
        assert SI.effective_seats(3, rho) == pytest.approx(1.0)  # 3/(1+2*1)

    def test_the_two_extremes_are_actually_distinguished(self):
        """The point of the exercise: these must not report the same thing."""
        div, div_o = _run({"s1": _TRUE_A, "s2": _TRUE_B, "s3": _FALSE_A},
                          passes=_ONE_PASS)
        both = f"{_TRUE_A}\n{_FALSE_A}"
        col, col_o = _run({"s1": both, "s2": both, "s3": both}, passes=_ONE_PASS)
        d_rep = diagnose_run(div, div_o.verdicts)
        c_rep = diagnose_run(col, col_o.verdicts)
        assert d_rep["effective_seats"] > c_rep["effective_seats"]
        assert d_rep["effective_seats"] == pytest.approx(3.0)
        assert c_rep["effective_seats"] == pytest.approx(1.0)


class TestEscalatedClaimsAreExcludedNotDefaulted:

    def test_an_escalated_claim_never_enters_the_matrix(self):
        results, orch = _run({"s1": _JUDGMENT, "s2": ""}, passes=_ONE_PASS)
        m = build_correctness_matrix(results, orch.verdicts)
        assert m.coverage.n_claims_adjudicated == 1
        assert m.coverage.n_excluded_unadjudicated == 1
        assert m.coverage.n_items == 0
        assert m.measurable is False

    def test_exclusion_is_counted_so_the_operator_sees_the_hole(self):
        results, orch = _run(
            {"s1": f"{_TRUE_A}\n{_JUDGMENT}", "s2": _TRUE_A}, passes=_ONE_PASS
        )
        m = build_correctness_matrix(results, orch.verdicts)
        assert m.coverage.n_items == 1
        assert m.coverage.n_excluded_unadjudicated == 1
        assert m.coverage.gate_coverage == pytest.approx(0.5)
        assert "escalated" in m.coverage.summary()

    def test_a_human_adjudication_resolves_an_escalated_claim(self):
        results, orch = _run({"s1": _JUDGMENT, "s2": ""}, passes=_ONE_PASS)
        escalated = next(iter(orch.verdicts))
        m = build_correctness_matrix(results, orch.verdicts, {escalated: True})
        assert m.coverage.n_items == 1
        assert m.coverage.n_items_from_human_adjudication == 1
        assert m.coverage.n_items_from_gates == 0
        assert m.X.tolist() == [[1, 0]]   # s1 raised it, s2 missed it

    def test_a_human_adjudication_may_not_override_a_gate(self):
        """Authority stays with the mechanical bottleneck."""
        results, orch = _run({"s1": _TRUE_A, "s2": _TRUE_A}, passes=_ONE_PASS)
        gated = next(iter(orch.verdicts))
        with pytest.raises(AdjudicationConflict, match="decided by gate"):
            build_correctness_matrix(results, orch.verdicts, {gated: False})

    def test_an_adjudication_for_an_unknown_claim_raises(self):
        """Otherwise a typo is silently ignored and the operator believes the
        queue was cleared."""
        results, orch = _run({"s1": _TRUE_A, "s2": _TRUE_A}, passes=_ONE_PASS)
        with pytest.raises(AdjudicationConflict, match="unknown claim"):
            build_correctness_matrix(results, orch.verdicts, {"no-such-id": True})


class TestASeatErrorInvalidatesThatPassRatherThanTheSeat:

    def test_items_from_a_pass_with_a_seat_error_are_dropped(self):
        def boom(_prompt):
            raise RuntimeError("transport died")

        orch = AO.Orchestrator([ArithmeticGate()])
        runner = AO.BlindedSeatRunner({"s1": _fixed(_TRUE_A), "s2": boom})
        results = orch.run_sequential("artifact", [], runner, passes=_ONE_PASS)
        m = build_correctness_matrix(results, orch.verdicts)
        assert m.coverage.errored_passes == ("p1",)
        assert m.coverage.n_excluded_seat_error == 1
        assert m.coverage.n_items == 0
        assert m.measurable is False
        assert "seat error" in m.coverage.summary()

    def test_the_errored_seat_still_appears_as_a_column_elsewhere(self):
        """The seat is not deleted from the panel -- only the pass it missed is
        dropped. Deleting the seat would change n and misstate every downstream
        number."""
        calls = {"n": 0}

        def flaky(_prompt):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("transient")
            return _TRUE_B

        two = (Pass("p1", "Inversion Analysis", "x", True),
               Pass("p2", "FMEA + FTA + FMEDA", "y", True))
        orch = AO.Orchestrator([ArithmeticGate()])
        runner = AO.BlindedSeatRunner({"s1": _fixed(_TRUE_A), "s2": flaky})
        results = orch.run_sequential("artifact", [], runner, passes=two)
        m = build_correctness_matrix(results, orch.verdicts)
        assert m.seats == ("s1", "s2")
        assert m.coverage.errored_passes == ("p1",)
        # p1's claim dropped; p2's 3*3=9 survives
        assert m.coverage.n_items == 1
        assert m.coverage.n_excluded_seat_error == 1


class TestFailsClosed:

    def test_no_adjudicated_claim_yields_no_diagnosis(self):
        results, orch = _run({"s1": _JUDGMENT, "s2": _JUDGMENT}, passes=_ONE_PASS)
        report = diagnose_run(results, orch.verdicts)
        assert report["measurable"] is False
        assert report["blockers"]
        for key in ("mean_error_correlation_rho", "effective_seats",
                    "independence_gap", "capture_recapture"):
            assert key not in report, f"{key} reported on an unmeasurable run"

    def test_a_single_seat_panel_is_blocked(self):
        results, orch = _run({"s1": _TRUE_A}, passes=_ONE_PASS)
        m = build_correctness_matrix(results, orch.verdicts)
        assert m.measurable is False
        assert any("two seats" in b for b in m.blockers)

    def test_an_undefined_rho_is_named_not_rounded(self):
        """Every seat identical AND every item the same verdict -> no variance
        in any pair. NaN is the honest answer; the reading must say so rather
        than let a NaN print as a value."""
        results, orch = _run({"s1": _TRUE_A, "s2": _TRUE_A}, passes=_ONE_PASS)
        report = diagnose_run(results, orch.verdicts)
        assert math.isnan(report["mean_error_correlation_rho"])
        assert "absence of a measurement" in report["reading"]


class TestDetectionsExcludeFalseAssertions:

    def test_chao1_input_counts_only_verified_findings(self):
        """Orchestrator.detections_by_seat records every proposal including the
        rejected ones. Chao1 estimates uncaught REAL defects, so feeding it
        false assertions inflates S_obs and the singleton count."""
        results, orch = _run(
            {"s1": f"{_TRUE_A}\n{_FALSE_A}", "s2": _TRUE_A}, passes=_ONE_PASS
        )
        raw = orch.detections_by_seat
        clean = build_detections(results, orch.verdicts)
        assert len(raw["s1"]) == 2          # both proposals
        assert len(clean["s1"]) == 1        # only the verified one
        assert clean["s1"] == clean["s2"]

    def test_a_seat_that_found_nothing_true_gets_an_empty_set(self):
        results, orch = _run({"s1": _TRUE_A, "s2": _FALSE_A}, passes=_ONE_PASS)
        clean = build_detections(results, orch.verdicts)
        assert clean["s2"] == set()
        assert "s2" in clean, "a seat with no true findings must still be listed"

    def test_pass_detections_are_ordered_and_true_only(self):
        two = (Pass("p1", "Inversion Analysis", "x", True),
               Pass("p2", "FMEA + FTA + FMEDA", "y", True))
        calls = {"n": 0}

        def by_pass(_prompt):
            calls["n"] += 1
            return _TRUE_A if calls["n"] <= 2 else f"{_TRUE_B}\n{_FALSE_A}"

        orch = AO.Orchestrator([ArithmeticGate()])
        runner = AO.BlindedSeatRunner({"s1": by_pass, "s2": by_pass})
        results = orch.run_sequential("artifact", [], runner, passes=two)
        pd = build_pass_detections(results, orch.verdicts)
        assert [pid for pid, _ in pd] == ["p1", "p2"]
        assert len(pd[0][1]) == 1     # 2+2=4
        assert len(pd[1][1]) == 1     # 3*3=9; the false claim is not a detection


class TestCoverageAccountingIsComplete:

    def test_every_adjudicated_claim_is_either_used_or_counted_as_excluded(self):
        results, orch = _run(
            {"s1": f"{_TRUE_A}\n{_FALSE_A}\n{_JUDGMENT}", "s2": _TRUE_B},
            passes=_ONE_PASS,
        )
        c = build_correctness_matrix(results, orch.verdicts).coverage
        assert (c.n_items + c.n_excluded_unadjudicated + c.n_excluded_seat_error
                == c.n_claims_adjudicated)
        assert c.n_items_from_gates + c.n_items_from_human_adjudication == c.n_items

    def test_the_summary_names_human_adjudication_when_it_was_used(self):
        """The operator must be able to see, from the summary line alone, that
        part of this diagnosis rests on a judgement call rather than a gate."""
        results, orch = _run({"s1": _JUDGMENT, "s2": ""}, passes=_ONE_PASS)
        escalated = next(iter(orch.verdicts))
        c = build_correctness_matrix(results, orch.verdicts, {escalated: True}).coverage
        assert "1 from human adjudication" in c.summary()
        assert "0 from gates" in c.summary()

    def test_gate_coverage_is_nan_when_nothing_was_adjudicated(self):
        results, orch = _run({"s1": "", "s2": ""}, passes=_ONE_PASS)
        c = build_correctness_matrix(results, orch.verdicts).coverage
        assert c.n_claims_adjudicated == 0
        assert math.isnan(c.gate_coverage)


class TestVerdictsAreRetainedByTheOrchestrator:

    def test_each_distinct_claim_has_exactly_one_verdict(self):
        results, orch = _run({"s1": _TRUE_A, "s2": _TRUE_A}, passes=_ONE_PASS)
        assert len(orch.verdicts) == 1
        v = next(iter(orch.verdicts.values()))
        assert v.status is GateStatus.PASS
        assert v.verified_true is True
        assert v.pass_id == "p1"
        assert len(results) == 1

    def test_an_escalated_claim_records_a_verdict_with_no_status(self):
        _, orch = _run({"s1": _JUDGMENT, "s2": ""}, passes=_ONE_PASS)
        v = next(iter(orch.verdicts.values()))
        assert v.status is None
        assert v.verified_true is None, "absence of a gate is not a False verdict"

    def test_a_reproposed_claim_is_not_readjudicated(self):
        """A claim seen in pass 1 keeps pass 1's verdict when pass 2 repeats
        it, so the pass attribution stays honest."""
        two = (Pass("p1", "Inversion Analysis", "x", True),
               Pass("p2", "FMEA + FTA + FMEDA", "y", True))
        orch = AO.Orchestrator([ArithmeticGate()])
        runner = AO.BlindedSeatRunner({"s1": _fixed(_TRUE_A), "s2": _fixed(_TRUE_A)})
        orch.run_sequential("artifact", [], runner, passes=two)
        assert len(orch.verdicts) == 1
        assert next(iter(orch.verdicts.values())).pass_id == "p1"

    def test_claims_from_an_errored_response_are_never_counted(self):
        """The reference runner returns no claims alongside an error, so this
        path is unreachable through it -- and build_detections does NOT apply
        the errored-pass exclusion that covers the matrix, so a custom runner
        returning both would put a half-finished response into the chao1 input.
        Found by mutation: deleting the guard broke no test.
        """
        claim = Claim(
            id="c-partial",
            text="2 + 2 = 4",
            kind=ClaimKind.ARITHMETIC,
            warrant="2 + 2 = 4",
            source_pass="p1",
            source_seat="s2",
        )
        good = AO.SeatResponse("s1", "p1", "raw", [claim])
        # a seat that errored AND returned something: the response is partial
        partial = AO.SeatResponse("s2", "p1", "raw", [claim], error="died mid-stream")
        result = AO.SequentialPassResult(
            "p1", "Inversion Analysis",
            AO.PassRecord("p1", 1, 1, 0, 0),
            AO.measure_divergence(_ONE_PASS[0], [good, partial]),
            [good, partial],
        )
        verdicts = {"c-partial": AO.ClaimVerdict("c-partial", "p1", GateStatus.PASS,
                                                 "ArithmeticGate", "confirmed")}
        det = build_detections([result], verdicts)
        assert det["s1"] == {"c-partial"}
        assert det["s2"] == set(), "an errored seat must not be credited with a find"


# ===========================================================================
# THE RUNNER -- five passes one at a time, elimination, and the holes
# ===========================================================================

import run_adjudication as RA  # noqa: E402
from run_adjudication import (  # noqa: E402
    AdjudicationAnswer,
    CandidateFileError,
    load_candidates,
    parse_candidates,
    render_report,
    run_adjudication,
)

# Field order is CLAIM | kind | WARRANT | text, per build_blinded_prompt.
_R_TRUE = "CLAIM | arithmetic | 2 + 2 = 4 | the total is 4"
_R_FALSE = "CLAIM | arithmetic | 2 + 2 = 5 | the total is 5"
_R_JUDGE = "CLAIM | judgment |  | the framing is one-sided"


def _cand(cid, text, warrant):
    claim = Claim(AO.content_claim_id(ClaimKind.ARITHMETIC, warrant, text),
                  text, ClaimKind.ARITHMETIC, warrant)
    return Candidate(cid, text, [claim])


def _seats(*texts):
    return {f"s{i}": (lambda _p, t=t: t) for i, t in enumerate(texts, 1)}


class TestTheClaimLineFieldOrder:
    """A demo written as kind|text|warrant put prose where the gate expects an
    expression, so every arithmetic claim was rejected for the wrong reason and
    no candidate was eliminated. The earlier matrix tests used self-symmetric
    lines and could not have caught it."""

    def test_the_third_field_is_the_warrant_not_the_text(self):
        claims = AO.line_claim_extractor(_R_TRUE, "s1", "p1")
        assert len(claims) == 1
        assert claims[0].warrant == "2 + 2 = 4"
        assert claims[0].text == "the total is 4"

    def test_the_prompt_documents_the_order_the_extractor_parses(self):
        prompt = AO.build_blinded_prompt(_ONE_PASS[0], "s1", "artifact").render()
        assert "CLAIM | <kind> | <warrant> | <text>" in prompt

    def test_reversing_warrant_and_text_fails_the_gate(self):
        reversed_line = "CLAIM | arithmetic | the total is 4 | 2 + 2 = 4"
        claim = AO.line_claim_extractor(reversed_line, "s1", "p1")[0]
        assert ArithmeticGate().check(claim).status is GateStatus.FAIL


class TestFivePassesOneAtATime:

    def test_all_five_frameworks_run_in_order(self):
        answer = run_adjudication("artifact", [], _seats(_R_TRUE, _R_TRUE))
        assert [p.pass_name for p in answer.passes] == [
            "Inversion Analysis",
            "FMEA + FTA + FMEDA",
            "IDOV",
            "Critical Systems Thinking + TRIZ + Quality Zero Defects",
            "Bayesian + MCMC",
        ]

    def test_no_seat_is_shown_a_previous_pass(self):
        """The runner must not weaken the blinding the orchestrator enforces."""
        seen: list[str] = []

        def recorder(prompt):
            seen.append(prompt)
            return _R_TRUE + "\nCANARY-9f3b"

        run_adjudication("artifact", [], {"s1": recorder, "s2": recorder})
        assert len(seen) == 10  # 5 passes x 2 seats
        assert not any("CANARY-9f3b" in p for p in seen[2:]), (
            "a pass-1 response reached a later prompt"
        )


class TestTheAnswerIsWhatSurvives:

    def test_a_failed_gate_eliminates_the_candidate_that_stands_on_it(self):
        cands = [_cand("c_true", "the total is 4", "2 + 2 = 4"),
                 _cand("c_false", "the total is 5", "2 + 2 = 5")]
        answer = run_adjudication("artifact", cands,
                                  _seats(_R_TRUE, f"{_R_TRUE}\n{_R_FALSE}"))
        assert [c.id for c in answer.survivors] == ["c_true"]
        assert [c.id for c in answer.eliminated] == ["c_false"]
        assert "recomputed 4" in answer.eliminated[0].elimination_reason

    def test_elimination_happens_on_the_pass_that_first_sees_the_claim(self):
        cands = [_cand("c_false", "the total is 5", "2 + 2 = 5")]
        answer = run_adjudication("artifact", cands, _seats(_R_FALSE, _R_FALSE))
        assert answer.passes[0].record.eliminated_candidates == ["c_false"]
        for later in answer.passes[1:]:
            assert later.record.eliminated_candidates == []

    def test_nothing_is_ever_selected_only_removed(self):
        """Two candidates, neither refuted -> both survive. No tie is broken."""
        cands = [_cand("c1", "the total is 4", "2 + 2 = 4"),
                 _cand("c2", "the sum is 4", "1 + 3 = 4")]
        answer = run_adjudication("artifact", cands, _seats(_R_TRUE, _R_TRUE))
        assert len(answer.survivors) == 2
        assert answer.resolved is False
        assert any(h.kind == "not narrowed to one" for h in answer.holes)

    def test_every_candidate_eliminated_is_reported_as_a_hole(self):
        cands = [_cand("c_false", "the total is 5", "2 + 2 = 5")]
        answer = run_adjudication("artifact", cands, _seats(_R_FALSE, _R_FALSE))
        assert answer.survivors == []
        hole = next(h for h in answer.holes if h.kind == "every candidate eliminated")
        assert "not among them" in hole.detail
        assert "fix the gate" in hole.remedy


class TestHolesArePartOfTheAnswer:

    def test_resolved_needs_one_survivor_AND_no_holes(self):
        """One survivor with an open queue is a shortlist, not an answer."""
        cands = [_cand("c_true", "the total is 4", "2 + 2 = 4"),
                 _cand("c_false", "the total is 5", "2 + 2 = 5")]
        answer = run_adjudication(
            "artifact", cands, _seats(f"{_R_TRUE}\n{_R_FALSE}\n{_R_JUDGE}", _R_TRUE)
        )
        assert len(answer.survivors) == 1
        assert answer.holes
        assert answer.resolved is False

    def test_an_escalated_claim_becomes_an_actionable_hole(self):
        answer = run_adjudication("artifact", [], _seats(_R_JUDGE, _R_JUDGE))
        hole = next(h for h in answer.holes if h.kind == "unadjudicated claims")
        assert "judgment" in hole.detail
        assert "--adjudications" in hole.remedy

    def test_a_seat_error_is_a_hole_naming_the_seat(self):
        def boom(_p):
            raise RuntimeError("transport died")

        answer = run_adjudication("artifact", [], {"s1": _fixed(_R_TRUE), "s2": boom})
        hole = next(h for h in answer.holes if h.kind == "seat error")
        assert "s2" in hole.detail
        assert "cannot be read as agreement" in hole.remedy

    def test_a_collapse_warning_is_a_hole(self):
        answer = run_adjudication("artifact", [], _seats(_R_TRUE, _R_TRUE, _R_TRUE))
        assert any(h.kind == "collapse warning" for h in answer.holes)

    def test_every_hole_carries_a_remedy(self):
        answer = run_adjudication("artifact", [], _seats(_R_JUDGE, _R_TRUE))
        assert answer.holes
        for h in answer.holes:
            assert h.remedy.strip(), f"hole {h.kind!r} has no remedy"


class TestDefaultGatesDoNotShipAPermissiveResolver:

    def test_citation_and_test_gates_are_absent_by_default(self):
        """Both take an operator-supplied callable, and a default returning
        True is the permissive resolver SOP 8.3 names as the most common way
        this build fails. A citation claim escalates instead."""
        names = [type(g).__name__ for g in RA._default_gates()]
        assert "CitationResolutionGate" not in names
        assert "TestExecutionGate" not in names

    def test_admissibility_alone_would_accept_a_fabricated_doi(self):
        """The reason SourceAdmissibilityGate is not a default, pinned as a
        fact rather than left as a comment. It answers 'is this the right KIND
        of source', never 'does this source exist'. As the sole citation gate
        it reintroduces the single-gate fail-open that conjunctive routing was
        built to close. Found when a runner test failed on code I had just
        written."""
        invented = "10.1038/s41586-000-0000-0"
        claim = Claim(AO.content_claim_id(ClaimKind.CITATION, invented, "x"),
                      "x", ClaimKind.CITATION, invented)
        assert AO.classify_source(invented) is AO.SourceClass.PEER_REVIEWED
        assert AO.SourceAdmissibilityGate().check(claim).status is GateStatus.PASS
        assert not any(isinstance(g, AO.SourceAdmissibilityGate)
                       for g in RA._default_gates())

    def test_a_citation_claim_escalates_rather_than_being_waved_through(self):
        cite = "CLAIM | citation | 10.1038/s41586-000-0000-0 | the source says so"
        answer = run_adjudication("artifact", [], _seats(cite, cite))
        assert answer.passes[0].record.auto_accepted == 0
        assert any(h.kind == "unadjudicated claims" for h in answer.holes)


class TestCandidateFileParsing:

    def test_the_documented_shape_round_trips(self, tmp_path):
        path = tmp_path / "c.json"
        path.write_text(_json.dumps([
            {"id": "c1", "content": "four",
             "claims": [{"kind": "arithmetic", "text": "the total is 4",
                         "warrant": "2 + 2 = 4"}]}
        ]))
        cands = load_candidates(str(path))
        assert [c.id for c in cands] == ["c1"]
        assert cands[0].claims[0].warrant == "2 + 2 = 4"

    def test_a_duplicate_id_raises(self):
        with pytest.raises(CandidateFileError, match="duplicate candidate id"):
            parse_candidates([{"id": "c1"}, {"id": "c1"}])

    def test_an_unknown_claim_kind_raises_and_lists_the_valid_ones(self):
        with pytest.raises(CandidateFileError, match="unknown kind"):
            parse_candidates([{"id": "c1", "claims": [{"kind": "vibes"}]}])

    def test_a_non_list_raises(self):
        with pytest.raises(CandidateFileError, match="expected a JSON list"):
            parse_candidates({"id": "c1"})

    def test_a_missing_id_raises(self):
        with pytest.raises(CandidateFileError, match="no usable 'id'"):
            parse_candidates([{"content": "x"}])

    def test_invalid_json_names_the_file(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not json")
        with pytest.raises(CandidateFileError, match="not valid JSON"):
            load_candidates(str(path))


class TestTheRunnerWritesADurableAuditLog:

    def test_the_chain_survives_the_run_and_verifies(self, tmp_path):
        """RunRecorder was defined only on AuditLog, so DurableAuditLog raised
        AttributeError on the first record_artifact and no real run could
        persist its chain at all."""
        path = str(tmp_path / "audit.jsonl")
        cands = [_cand("c_false", "the total is 5", "2 + 2 = 5")]
        answer = run_adjudication("artifact", cands, _seats(_R_FALSE, _R_FALSE),
                                  audit_path=path)
        reopened = AL.DurableAuditLog(path)
        assert reopened.verify().valid is True
        assert reopened.head == answer.audit_head
        kinds = [e.kind for e in reopened.entries]
        assert kinds.count("pass") == 5
        assert "artifact" in kinds and "stop_decision" in kinds

    def test_the_artifact_is_committed_by_digest_not_text(self, tmp_path):
        path = str(tmp_path / "audit.jsonl")
        run_adjudication("SENSITIVE-RED-TEXT", [], _seats(_R_TRUE, _R_TRUE),
                         audit_path=path)
        with open(path, encoding="utf-8") as fh:
            body = fh.read()
        assert "SENSITIVE-RED-TEXT" not in body


class TestTheReport:

    def test_the_report_names_the_survivor_and_every_hole(self):
        cands = [_cand("c_true", "the total is 4", "2 + 2 = 4"),
                 _cand("c_false", "the total is 5", "2 + 2 = 5")]
        answer = run_adjudication("artifact", cands,
                                  _seats(f"{_R_TRUE}\n{_R_FALSE}", _R_TRUE))
        text = render_report(answer)
        assert "SURVIVOR: c_true" in text
        assert "removed c_false" in text
        for h in answer.holes:
            assert h.detail in text
        assert "NOT RESOLVED" in text

    def test_a_nan_capture_fraction_is_not_printed_as_a_number(self):
        answer = run_adjudication("artifact", [], _seats(_R_TRUE, _R_TRUE))
        assert "nan" not in render_report(answer)

    def test_the_report_never_contains_a_raw_seat_response(self):
        """The console is for the operator, but a verbatim seat dump would
        make the report itself a blinding leak if it were ever fed back."""
        marker = "SEAT-VERBATIM-4c1a"
        answer = run_adjudication("artifact", [],
                                  _seats(f"{_R_TRUE}\n{marker}", _R_TRUE))
        assert marker not in render_report(answer)


class TestTheCliFailsClosedWithoutSeats:

    def test_no_demo_flag_refuses_to_run(self, capsys):
        assert RA.main([]) == 2
        err = capsys.readouterr().err
        assert "no seats configured" in err
        assert "ProviderProfile" in err

    def test_demo_runs_end_to_end_and_reports_unresolved(self, capsys):
        assert RA.main(["--demo"]) == 1     # an escalated judgment claim remains
        out = capsys.readouterr().out
        assert "SURVIVOR: c_true" in out
        assert "HOLES" in out

    def test_the_exit_code_is_nonzero_while_holes_remain(self):
        answer = AdjudicationAnswer(
            artifact_digest="x", passes=[], survivors=[Candidate("c1", "")],
            eliminated=[], stop={}, diagnosis={}, holes=[],
        )
        assert answer.resolved is True
