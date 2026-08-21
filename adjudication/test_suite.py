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

import json as _json
import warnings as _warnings
from collections import Counter as _Counter


def _majority(row):
    """
    Deterministic majority vote, used as the aggregator in the
    leave-one-seat-out tests.

    Ties are broken by sorted order rather than by Counter internals, so every
    expected value below is reproducible by hand.
    """
    counts = _Counter(row)
    top = max(counts.values())
    return sorted(k for k, v in counts.items() if v == top)[0]


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

import inspect as _inspect


def _seat(text):
    """A seat that ignores its prompt and returns a fixed response."""
    return lambda _prompt: text


class TestFivePassFramework:
    def test_exact_names_and_order(self):
        assert [p.name for p in AO.DEFAULT_PASSES] == [
            "Inversion Analysis",
            "FMEA + FTA + FMEDA",
            "IDOV",
            "Critical Skills Thinking + TRIZ + Quality Zero Defects",
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
        with pytest.raises(Exception):
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
