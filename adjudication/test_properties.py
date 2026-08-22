"""
test_properties.py
==================
Property-based tests and fuzz targets.

SOP Manual v1.1 section 8.4 requires a verification layer whose failures are
uncorrelated with the models, and the sixteen-test template is explicit about
why this file exists: "tests prove bugs exist, never their absence, so fuzz +
property tests are mandatory."

The example-based suite in test_suite.py asserts what specific inputs do. This
file asserts what must hold for EVERY input, and throws adversarial garbage at
the two surfaces a model can reach directly: the arithmetic evaluator and the
claim extractor.

Run: pytest test_properties.py
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

import adjudication_orchestrator as AO
import audit_log as AL
import seat_independence as SI

# Deadlines off: numpy work and the audit chain's fsync-free hashing are fast
# but variable under CI load, and a flaky timing failure teaches nothing.
SETTINGS = settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

# ---------------------------------------------------------------------------
# strategies
# ---------------------------------------------------------------------------

finite = st.floats(allow_nan=False, allow_infinity=False, width=64)
rho_values = st.floats(min_value=-2.0, max_value=2.0, allow_nan=False, allow_infinity=False)
seat_counts = st.integers(min_value=0, max_value=12)


@st.composite
def correctness_matrix(draw, min_items=1, max_items=40, min_seats=1, max_seats=6):
    """(n_items, n_seats) of 0/1 -- the shape seat_independence documents."""
    n_items = draw(st.integers(min_value=min_items, max_value=max_items))
    n_seats = draw(st.integers(min_value=min_seats, max_value=max_seats))
    rows = draw(
        st.lists(
            st.lists(st.integers(min_value=0, max_value=1), min_size=n_seats, max_size=n_seats),
            min_size=n_items,
            max_size=n_items,
        )
    )
    return np.array(rows, dtype=int)


detections = st.dictionaries(
    st.text(min_size=1, max_size=6),
    st.sets(st.integers(min_value=0, max_value=30), max_size=15),
    max_size=6,
)

json_scalars = st.one_of(
    st.none(), st.booleans(), st.integers(min_value=-10**9, max_value=10**9),
    finite, st.text(max_size=40),
)
json_payload = st.dictionaries(
    st.text(min_size=1, max_size=12),
    st.recursive(json_scalars, lambda c: st.lists(c, max_size=4), max_leaves=8),
    max_size=6,
)


# ===========================================================================
# 1. effective_seats -- the Kish design effect
# ===========================================================================

class TestEffectiveSeatsProperties:
    @given(n=st.integers(min_value=1, max_value=50), rho=rho_values)
    @SETTINGS
    def test_result_is_always_between_one_and_n(self, n, rho):
        """The whole point of the statistic: you never have more independent
        seats than seats, and never fewer than one."""
        got = SI.effective_seats(n, rho)
        assert 1.0 - 1e-9 <= got <= n + 1e-9

    @given(n=st.integers(min_value=2, max_value=50),
           a=st.floats(min_value=0.0, max_value=1.0),
           b=st.floats(min_value=0.0, max_value=1.0))
    @SETTINGS
    def test_monotone_decreasing_in_rho(self, n, a, b):
        lo, hi = min(a, b), max(a, b)
        assert SI.effective_seats(n, lo) >= SI.effective_seats(n, hi) - 1e-9

    @given(n=st.integers(min_value=1, max_value=50))
    @SETTINGS
    def test_endpoints(self, n):
        assert SI.effective_seats(n, 0.0) == pytest.approx(float(n))
        assert SI.effective_seats(n, 1.0) == pytest.approx(1.0)

    @given(n=st.integers(min_value=1, max_value=50),
           rho=st.floats(min_value=-50.0, max_value=0.0))
    @SETTINGS
    def test_negative_rho_never_manufactures_seats(self, n, rho):
        """Negative correlation would imply n_eff > n. The function clamps
        instead, and must never claim more independence than it can evidence."""
        assert SI.effective_seats(n, rho) == pytest.approx(float(n))


# ===========================================================================
# 2. correlation
# ===========================================================================

class TestCorrelationProperties:
    @given(X=correctness_matrix())
    @SETTINGS
    def test_matrix_is_square_symmetric_with_unit_diagonal(self, X):
        C = SI.pairwise_error_correlation(X)
        n = X.shape[1]
        assert C.shape == (n, n)
        assert np.allclose(np.diag(C), 1.0)
        assert np.allclose(C, C.T, equal_nan=True)

    @given(X=correctness_matrix())
    @SETTINGS
    def test_every_correlation_is_in_range_or_nan(self, X):
        C = SI.pairwise_error_correlation(X)
        finite_vals = C[~np.isnan(C)]
        assert np.all(finite_vals >= -1.0 - 1e-9)
        assert np.all(finite_vals <= 1.0 + 1e-9)

    @given(X=correctness_matrix())
    @SETTINGS
    def test_mean_correlation_is_in_range_or_nan(self, X):
        rho = SI.mean_error_correlation(X)
        assert math.isnan(rho) or (-1.0 - 1e-9 <= rho <= 1.0 + 1e-9)

    @given(col=st.lists(st.integers(min_value=0, max_value=1), min_size=4, max_size=30),
           k=st.integers(min_value=2, max_value=5))
    @SETTINGS
    def test_identical_seats_correlate_at_one(self, col, k):
        assume(len(set(col)) > 1)          # a constant column has no variance
        X = np.column_stack([col] * k)
        assert SI.mean_error_correlation(X) == pytest.approx(1.0)


# ===========================================================================
# 3. capture-recapture
# ===========================================================================

class TestChao1Properties:
    @given(det=detections)
    @SETTINGS
    def test_estimate_never_below_observed(self, det):
        r = SI.chao1(det)
        assert r["N_hat_lower_bound"] >= r["S_obs"] - 1e-9
        assert r["estimated_missed"] >= -1e-9

    @given(det=detections)
    @SETTINGS
    def test_singleton_fraction_is_a_fraction_or_nan(self, det):
        f = SI.chao1(det)["singleton_fraction"]
        assert math.isnan(f) or 0.0 <= f <= 1.0 + 1e-9

    @given(det=detections)
    @SETTINGS
    def test_counts_are_consistent(self, det):
        r = SI.chao1(det)
        union = set().union(*det.values()) if det else set()
        assert r["S_obs"] == float(len(union))
        assert r["f1_singletons"] + r["f2_doubletons"] <= r["S_obs"] + 1e-9

    @given(n1=st.integers(min_value=0, max_value=500),
           n2=st.integers(min_value=0, max_value=500),
           data=st.data())
    @SETTINGS
    def test_chapman_is_always_finite_and_non_negative(self, n1, n2, data):
        m = data.draw(st.integers(min_value=0, max_value=min(n1, n2)))
        v = SI.lincoln_petersen(n1, n2, m, chapman=True)
        assert math.isfinite(v)
        assert v >= -1e-9

    @given(n1=st.integers(min_value=0, max_value=200),
           n2=st.integers(min_value=0, max_value=200),
           excess=st.integers(min_value=1, max_value=50))
    @SETTINGS
    def test_contradictory_overlap_is_rejected_not_estimated(self, n1, n2, excess):
        """An overlap larger than either sample is impossible. It must raise
        rather than return a negative population estimate."""
        with pytest.raises(ValueError, match="contradictory"):
            SI.lincoln_petersen(n1, n2, min(n1, n2) + excess, chapman=True)

    @given(n1=st.integers(min_value=1, max_value=200),
           n2=st.integers(min_value=1, max_value=200),
           data=st.data())
    @SETTINGS
    def test_chapman_decreases_as_overlap_grows(self, n1, n2, data):
        cap = min(n1, n2)
        a = data.draw(st.integers(min_value=0, max_value=cap))
        b = data.draw(st.integers(min_value=0, max_value=cap))
        lo, hi = min(a, b), max(a, b)
        assert (SI.lincoln_petersen(n1, n2, lo, True)
                >= SI.lincoln_petersen(n1, n2, hi, True) - 1e-9)


# ===========================================================================
# 4. marginal yield
# ===========================================================================

class TestMarginalYieldProperties:
    @given(passes=st.lists(st.sets(st.integers(0, 20), max_size=10), max_size=8),
           seeded=st.one_of(st.none(), st.integers(min_value=1, max_value=60)))
    @SETTINGS
    def test_cumulative_is_non_decreasing_and_totals_correctly(self, passes, seeded):
        out = SI.marginal_yield_by_pass(
            [(f"p{i}", s) for i, s in enumerate(passes)], total_seeded=seeded
        )
        assert len(out) == len(passes)
        cums = [p.cumulative for p in out]
        assert cums == sorted(cums)
        assert sum(p.newly_caught for p in out) == (cums[-1] if cums else 0)
        union = set().union(*passes) if passes else set()
        assert (cums[-1] if cums else 0) == len(union)

    @given(passes=st.lists(st.sets(st.integers(0, 20), max_size=10), min_size=1, max_size=8),
           seeded=st.one_of(st.none(), st.integers(min_value=1, max_value=60)))
    @SETTINGS
    def test_shares_and_yields_are_never_negative(self, passes, seeded):
        for p in SI.marginal_yield_by_pass(
            [(f"p{i}", s) for i, s in enumerate(passes)], total_seeded=seeded
        ):
            assert p.marginal_yield >= 0.0
            assert 0.0 <= p.marginal_share <= 1.0 + 1e-9
            assert p.newly_caught <= p.cumulative

    @given(passes=st.lists(st.sets(st.integers(0, 20), max_size=10), min_size=1, max_size=6))
    @SETTINGS
    def test_replaying_a_pass_yields_nothing_new(self, passes):
        """Order matters, but a repeat never adds. The diagnostic would be
        meaningless if it did."""
        seq = [(f"p{i}", s) for i, s in enumerate(passes)]
        out = SI.marginal_yield_by_pass([*seq, ("repeat", passes[0])])
        assert out[-1].newly_caught == 0


# ===========================================================================
# 5. independence gap
# ===========================================================================

class TestIndependenceGapProperties:
    @given(X=correctness_matrix(min_items=1, max_items=25, min_seats=1, max_seats=5))
    @SETTINGS
    def test_every_reported_accuracy_is_a_probability(self, X):
        g = SI.independence_gap(X)
        for key in ("observed_majority_accuracy",
                    "independence_predicted_accuracy",
                    "best_single_seat_accuracy"):
            v = g[key]
            assert 0.0 - 1e-9 <= v <= 1.0 + 1e-9, f"{key} = {v}"

    @given(X=correctness_matrix(min_items=1, max_items=25, min_seats=1, max_seats=5))
    @SETTINGS
    def test_gains_are_consistent_with_the_accuracies(self, X):
        g = SI.independence_gap(X)
        assert g["theoretical_gain_over_best_single"] == pytest.approx(
            g["independence_predicted_accuracy"] - g["best_single_seat_accuracy"]
        )
        assert g["observed_gain_over_best_single"] == pytest.approx(
            g["observed_majority_accuracy"] - g["best_single_seat_accuracy"]
        )

    @given(X=correctness_matrix(min_items=1, max_items=25, min_seats=1, max_seats=5))
    @SETTINGS
    def test_beats_best_single_agrees_with_the_numbers(self, X):
        g = SI.independence_gap(X)
        assert g["ensemble_beats_best_single"] == (
            g["observed_majority_accuracy"] > g["best_single_seat_accuracy"]
        )


# ===========================================================================
# 6. FUZZ -- the arithmetic evaluator is an injection surface
# ===========================================================================

class TestArithmeticGateFuzz:
    """A seat supplies the warrant string, so this parser eats adversarial
    input by design. It must never execute, never hang, and never raise."""

    gate = AO.ArithmeticGate()

    @given(warrant=st.text(max_size=200))
    @SETTINGS
    def test_never_raises_on_arbitrary_text(self, warrant):
        r = self.gate.check(AO.Claim("c", "t", AO.ClaimKind.ARITHMETIC, warrant))
        assert r.status in (AO.GateStatus.PASS, AO.GateStatus.FAIL)

    @given(warrant=st.text(max_size=200))
    @SETTINGS
    def test_never_passes_without_a_real_equality(self, warrant):
        """A PASS must mean the left side genuinely recomputes to the right."""
        r = self.gate.check(AO.Claim("c", "t", AO.ClaimKind.ARITHMETIC, warrant))
        if r.status is AO.GateStatus.PASS:
            expr, claimed = warrant.rsplit("=", 1)
            import ast
            actual = AO._safe_eval(ast.parse(expr.strip(), mode="eval"))
            assert math.isclose(actual, float(claimed.strip()),
                                rel_tol=1e-9, abs_tol=1e-9)

    @given(a=st.integers(min_value=-10**6, max_value=10**6),
           b=st.integers(min_value=-10**6, max_value=10**6))
    @SETTINGS
    def test_correct_integer_arithmetic_always_passes(self, a, b):
        w = f"{a} + {b} = {a + b}"
        assert self.gate.check(
            AO.Claim("c", "t", AO.ClaimKind.ARITHMETIC, w)
        ).status is AO.GateStatus.PASS

    @given(a=st.integers(min_value=-10**6, max_value=10**6),
           b=st.integers(min_value=-10**6, max_value=10**6),
           wrong=st.integers(min_value=1, max_value=10**6))
    @SETTINGS
    def test_incorrect_integer_arithmetic_always_fails(self, a, b, wrong):
        w = f"{a} + {b} = {a + b + wrong}"
        assert self.gate.check(
            AO.Claim("c", "t", AO.ClaimKind.ARITHMETIC, w)
        ).status is AO.GateStatus.FAIL

    @given(name=st.text(alphabet=st.characters(whitelist_categories=("Ll", "Lu")),
                        min_size=1, max_size=12),
           arg=st.text(max_size=12).filter(lambda t: "=" not in t))
    @SETTINGS
    def test_no_call_or_attribute_access_ever_evaluates(self, name, arg):
        """Constructed rather than filtered: every shape that would need a
        call, an attribute, a subscript, or a name lookup to evaluate."""
        for expr in (f"{name}({arg!r})", f"{name}.{name}", f"[{arg!r}].{name}",
                     f"{name}", "(lambda: 1)()", "{}.get"):
            r = self.gate.check(AO.Claim("c", "t", AO.ClaimKind.ARITHMETIC, f"{expr} = 1"))
            assert r.status is AO.GateStatus.FAIL, expr


class TestClassifySourceFuzz:
    @given(ident=st.text(max_size=200))
    @SETTINGS
    def test_is_total_and_fails_closed(self, ident):
        """classify_source must be total, and anything it cannot positively
        place is inadmissible. There is no crash path and no permissive path."""
        cls = AO.classify_source(ident)
        assert isinstance(cls, AO.SourceClass)

    @given(ident=st.text(max_size=200))
    @SETTINGS
    def test_gate_verdict_follows_the_classification(self, ident):
        gate = AO.SourceAdmissibilityGate()
        cls = AO.classify_source(ident)
        r = gate.check(AO.Claim("c", "t", AO.ClaimKind.CITATION, ident))
        if not ident.strip():
            assert r.status is AO.GateStatus.FAIL
        elif cls in AO.ADMISSIBLE_CLASSES:
            assert r.status is AO.GateStatus.PASS
        else:
            assert r.status is AO.GateStatus.FAIL


class TestClaimExtractorFuzz:
    @given(raw=st.text(max_size=400))
    @SETTINGS
    def test_never_raises_on_arbitrary_model_output(self, raw):
        for c in AO.line_claim_extractor(raw, "s1", "p1"):
            assert isinstance(c, AO.Claim)
            assert c.source_seat == "s1" and c.source_pass == "p1"

    @given(raw=st.text(max_size=400))
    @SETTINGS
    def test_a_claim_line_is_never_silently_dropped(self, raw):
        """Every line announcing itself as a CLAIM produces exactly one claim.
        Dropping one would let a model smuggle an assertion past the gates by
        writing it badly."""
        announced = sum(
            1 for ln in raw.splitlines() if ln.strip().upper().startswith("CLAIM")
        )
        assert len(AO.line_claim_extractor(raw, "s1", "p1")) == announced

    @given(raw=st.text(max_size=400))
    @SETTINGS
    def test_an_unparseable_claim_always_escalates(self, raw):
        """A claim the extractor could not understand must reach a human, not
        a gate that might accept it."""
        claims = AO.line_claim_extractor(raw, "s1", "p1")
        o = AO.Orchestrator([AO.ArithmeticGate(), AO.SourceAdmissibilityGate()])
        rec = o.run_pass(AO.DEFAULT_PASSES[0], [], claims)
        assert rec.auto_accepted + rec.auto_rejected + rec.escalated <= len(claims)
        for c in claims:
            if c.kind is AO.ClaimKind.JUDGMENT:
                assert c.warrant is None


# ===========================================================================
# 7. audit chain
# ===========================================================================

class TestAuditChainProperties:
    @given(payloads=st.lists(json_payload, min_size=0, max_size=8))
    @SETTINGS
    def test_any_sequence_of_appends_verifies(self, payloads):
        log = AL.AuditLog("run")
        for p in payloads:
            log.append("pass", p)
        assert log.verify().valid is True
        assert len(log) == len(payloads) + 1

    @given(payloads=st.lists(json_payload, min_size=0, max_size=8))
    @SETTINGS
    def test_replay_always_reproduces_the_head(self, payloads):
        log = AL.AuditLog("run")
        for p in payloads:
            log.append("pass", p)
        assert AL.replay(log.entries) == log.head

    @given(payloads=st.lists(json_payload, min_size=0, max_size=6))
    @SETTINGS
    def test_identical_inputs_produce_identical_chains(self, payloads):
        """Global rule 4: deterministic replay. No clock, no randomness."""
        def build():
            log = AL.AuditLog("run")
            for p in payloads:
                log.append("pass", p)
            return log
        assert build().to_jsonl() == build().to_jsonl()

    @given(payloads=st.lists(json_payload, min_size=1, max_size=6),
           idx=st.integers(min_value=0, max_value=20),
           extra=st.text(min_size=1, max_size=8))
    @SETTINGS
    def test_tampering_with_any_entry_always_breaks_verification(self, payloads, idx, extra):
        log = AL.AuditLog("run")
        for p in payloads:
            log.append("pass", p)
        es = list(log.entries)
        i = idx % len(es)
        e = es[i]
        es[i] = AL.AuditEntry(e.seq, e.prev_hash, e.kind,
                              {**e.payload, "__tamper__": extra}, e.entry_hash)
        assert AL.verify_chain_integrity(es).valid is False

    @given(payloads=st.lists(json_payload, min_size=2, max_size=8),
           cut=st.integers(min_value=1, max_value=20))
    @SETTINGS
    def test_truncation_is_always_caught_against_the_recorded_head(self, payloads, cut):
        log = AL.AuditLog("run")
        for p in payloads:
            log.append("pass", p)
        k = 1 + (cut % (len(log) - 1))
        truncated = list(log.entries)[:k]
        assume(len(truncated) < len(log))
        v = AL.verify_chain_integrity(truncated, expected_head=log.head,
                                      expected_length=len(log))
        assert v.valid is False

    @given(payload=json_payload)
    @SETTINGS
    def test_scrubbed_payloads_are_always_canonicalisable(self, payload):
        AL.canonical_json(AL.scrub_nan(payload))

    @given(obj=st.recursive(
        st.one_of(json_scalars, st.just(float("nan")), st.just(float("inf"))),
        lambda c: st.one_of(st.lists(c, max_size=4),
                            st.dictionaries(st.text(min_size=1, max_size=6), c, max_size=4)),
        max_leaves=10))
    @SETTINGS
    def test_scrub_nan_removes_every_non_finite_float(self, obj):
        AL.canonical_json(AL.scrub_nan(obj))

    @given(keys=st.lists(st.text(min_size=1, max_size=6), min_size=2, max_size=6, unique=True),
           vals=st.lists(st.integers(), min_size=2, max_size=6))
    @SETTINGS
    def test_key_order_never_changes_the_commitment(self, keys, vals):
        n = min(len(keys), len(vals))
        assume(n >= 2)
        pairs = list(zip(keys[:n], vals[:n], strict=True))
        a = AL.compute_entry_hash(1, "0" * 64, "pass", dict(pairs))
        b = AL.compute_entry_hash(1, "0" * 64, "pass", dict(reversed(pairs)))
        assert a == b


# ===========================================================================
# 8. divergence
# ===========================================================================

class TestDivergenceProperties:
    @given(responses=st.lists(st.lists(st.text(min_size=1, max_size=5), max_size=5), max_size=5))
    @SETTINGS
    def test_jaccard_is_a_fraction_or_nan(self, responses):
        runner = AO.BlindedSeatRunner({
            f"s{i}": (lambda _p, r=r: "\n".join(
                f"CLAIM | arithmetic | {w} | t" for w in r))
            for i, r in enumerate(responses)
        } or {"s0": lambda _p: ""})
        p = AO.DEFAULT_PASSES[0]
        d = AO.measure_divergence(p, runner.run(p, "art"))
        j = d.mean_pairwise_jaccard
        assert math.isnan(j) or 0.0 - 1e-9 <= j <= 1.0 + 1e-9

    @given(responses=st.lists(st.lists(st.text(min_size=1, max_size=5), max_size=5),
                              min_size=2, max_size=5))
    @SETTINGS
    def test_a_collapse_warning_implies_unanimous_and_not_silent(self, responses):
        runner = AO.BlindedSeatRunner({
            f"s{i}": (lambda _p, r=r: "\n".join(
                f"CLAIM | arithmetic | {w} | t" for w in r))
            for i, r in enumerate(responses)
        })
        p = AO.DEFAULT_PASSES[0]
        d = AO.measure_divergence(p, runner.run(p, "art"))
        if d.collapse_warning is not None:
            assert d.unanimous is True
            assert d.all_seats_silent is False
            assert d.mean_pairwise_jaccard == pytest.approx(1.0)
