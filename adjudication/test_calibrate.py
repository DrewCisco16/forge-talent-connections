"""
test_calibrate.py
=================
Tests for the live seat-independence calibration.

The load-bearing test in this file is
TestTheClaimLineSurvivesTheRelevanceGuard. The first build of calibrate.py put
the bare item id in the claim text field, the orchestrator's relevance guard
escalated every TRUE item as "warrant does not bear on the claim", and the run
still printed a confident rho -- computed over 5 items instead of 17, from the
false items alone. Nothing raised. The only visible trace was a coverage line
an operator had no reason to distrust.

That is the shape of failure this module has to be tested against: not a
crash, but a number that is still produced after most of the evidence has
silently fallen out.
"""

import pytest

import adjudication_orchestrator as AO
import calibrate as CB
from correctness_matrix import SHARED_DETECTION

# ---------------------------------------------------------------------------
# the item set
# ---------------------------------------------------------------------------

class TestTheItemSetIsBalancedAndReproducible:

    def test_half_the_items_are_true_and_half_are_false(self):
        items = CB.build_items(24, seed=1)
        assert sum(1 for i in items if i.is_true) == 12
        assert sum(1 for i in items if not i.is_true) == 12

    def test_the_truth_flag_matches_the_actual_arithmetic(self):
        """The flag is the answer key. If it ever disagreed with the
        expression, every score computed from it would be wrong in a way no
        gate could catch -- the gate would be right and the key wrong."""
        for it in CB.build_items(40, seed=7):
            lhs, _, rhs = it.expression.rpartition("=")
            a, _, b = lhs.partition("+")
            assert (int(a) + int(b) == int(rhs)) is it.is_true, it

    def test_the_same_seed_gives_the_same_items(self):
        assert CB.build_items(12, seed=99) == CB.build_items(12, seed=99)

    def test_a_different_seed_gives_different_items(self):
        assert CB.build_items(12, seed=1) != CB.build_items(12, seed=2)

    def test_false_items_are_wrong_by_a_small_margin(self):
        """An answer off by an order of magnitude is caught by inspection and
        measures nothing. The probe only has signal if the wrong answers are
        plausible."""
        for it in CB.build_items(40, seed=3):
            if it.is_true:
                continue
            lhs, _, rhs = it.expression.rpartition("=")
            a, _, b = lhs.partition("+")
            assert 0 < abs((int(a) + int(b)) - int(rhs)) <= 2

    def test_an_odd_item_count_is_refused(self):
        with pytest.raises(ValueError, match="even"):
            CB.build_items(7)

    def test_too_few_items_is_refused(self):
        with pytest.raises(ValueError, match="at least 2"):
            CB.build_items(0)


# ---------------------------------------------------------------------------
# the regression this module exists to not repeat
# ---------------------------------------------------------------------------

class TestTheClaimLineSurvivesTheRelevanceGuard:

    def test_a_confirmed_true_item_is_ruled_true_not_escalated(self):
        """The bug: text='S03' does not mention 324, so the guard escalated,
        verified_true became None, and correctness_matrix excluded the item."""
        item = next(i for i in CB.build_items(24, seed=5) if i.is_true)
        orch = AO.Orchestrator(gates=[AO.ArithmeticGate()],
                               passes=[CB.CALIBRATION_PASS])
        claim = AO.Claim(id="", kind=AO.ClaimKind.ARITHMETIC,
                         text=item.expression, warrant=item.expression)
        orch.run_pass(CB.CALIBRATION_PASS, [], [claim])
        verdict = next(iter(orch.verdicts.values()))
        assert verdict.verified_true is True, verdict.detail

    def test_the_bare_item_id_form_would_have_escalated(self):
        """Pins WHY the format is what it is. If a future edit puts the id
        back in the text field, this test says what breaks."""
        item = next(i for i in CB.build_items(24, seed=5) if i.is_true)
        orch = AO.Orchestrator(gates=[AO.ArithmeticGate()],
                               passes=[CB.CALIBRATION_PASS])
        claim = AO.Claim(id="", kind=AO.ClaimKind.ARITHMETIC,
                         text=item.item_id, warrant=item.expression)
        orch.run_pass(CB.CALIBRATION_PASS, [], [claim])
        verdict = next(iter(orch.verdicts.values()))
        assert verdict.verified_true is None

    def test_no_item_escalates_in_a_well_formed_run(self):
        """The end-to-end guard. Escalated items are silently EXCLUDED from
        the matrix, so this is the assertion that catches the whole class of
        regression rather than one instance of it."""
        items = CB.build_items(24, seed=11)
        res = CB.run_calibration(CB._demo_seats(items), items)
        cov = res.report["coverage"]
        assert cov.n_excluded_unadjudicated == 0
        assert cov.n_items_from_gates == cov.n_items
        assert cov.n_items >= 12

    def test_two_seats_confirming_one_statement_produce_one_item(self):
        """If the ids did not collide, every item would be a singleton and the
        correlation would be measured over nothing."""
        item = next(i for i in CB.build_items(24, seed=5) if i.is_true)
        line = f"CLAIM | arithmetic | {item.expression} | {item.expression}"
        seats = {"seat_a": lambda _p: line, "seat_b": lambda _p: line}
        res = CB.run_calibration(seats, [item])
        assert res.report["coverage"].n_items == 1
        assert res.report["coverage"].n_seats == 2


# ---------------------------------------------------------------------------
# the measurement itself
# ---------------------------------------------------------------------------

class TestTheMeasurementSeparatesIndependenceFromCollapse:

    def test_seats_that_slip_on_different_items_read_as_independent(self):
        items = CB.build_items(24, seed=11)
        res = CB.run_calibration(CB._demo_seats(items), items)
        assert res.report["measurable"] is True
        assert res.rho is not None and res.rho <= 0.2
        assert res.effective_seats > 4.0

    def test_seats_that_slip_on_the_same_items_read_as_collapsed(self):
        items = CB.build_items(24, seed=11)
        res = CB.run_calibration(CB._collapsed_demo_seats(items), items)
        assert res.rho == pytest.approx(1.0)
        assert res.effective_seats == pytest.approx(1.0)

    def test_the_regime_is_shared_detection_not_open_ended(self):
        """OPEN_ENDED returns no diagnostic keys at all. If this module ever
        stopped declaring its regime it would silently measure nothing."""
        items = CB.build_items(12, seed=4)
        res = CB.run_calibration(CB._demo_seats(items), items)
        assert res.report["task_kind"] == SHARED_DETECTION

    def test_a_single_seat_cannot_produce_a_correlation(self):
        items = CB.build_items(12, seed=4)
        one = {"seat_1": CB._demo_seats(items)["seat_1"]}
        res = CB.run_calibration(one, items)
        assert res.report["measurable"] is False
        assert any("two seats" in b for b in res.report["blockers"])


# ---------------------------------------------------------------------------
# what the operator is told when it goes wrong
# ---------------------------------------------------------------------------

class TestFailuresAreReportedRatherThanAbsorbed:

    def test_a_seat_that_raises_is_recorded_by_name(self):
        items = CB.build_items(12, seed=4)
        seats = dict(CB._demo_seats(items))

        def broken(_p):
            raise RuntimeError("connection reset")

        seats["seat_3"] = broken
        res = CB.run_calibration(seats, items)
        assert "seat_3" in res.seat_errors
        assert "connection reset" in res.seat_errors["seat_3"]

    def test_the_report_says_a_failed_seat_changes_what_was_measured(self):
        items = CB.build_items(12, seed=4)
        seats = dict(CB._demo_seats(items))
        seats["seat_2"] = lambda _p: (_ for _ in ()).throw(RuntimeError("429"))
        text = CB.render_calibration(CB.run_calibration(seats, items))
        assert "SEAT ERRORS" in text
        assert "not of the five you intended" in text

    def test_a_paraphrasing_seat_is_flagged_not_scored_as_silence(self):
        """A seat that reworded the statement made a claim the matrix cannot
        attribute. Reading that as 'did not confirm' understates its agreement
        and biases rho downward -- toward looking MORE independent, which is
        the flattering direction and so the dangerous one."""
        items = CB.build_items(12, seed=4)
        seats = dict(CB._demo_seats(items))
        seats["seat_4"] = lambda _p: "CLAIM | arithmetic | 1 + 1 = 2 | 1 + 1 = 2"
        res = CB.run_calibration(seats, items)
        assert "seat_4" in res.unmatched_claims
        assert "UNDERSTATES" in CB.render_calibration(res)

    def test_a_run_that_measured_nothing_is_not_reported_as_a_number(self):
        items = CB.build_items(12, seed=4)
        silent = {f"seat_{i}": (lambda _p: "") for i in range(1, 6)}
        res = CB.run_calibration(silent, items)
        text = CB.render_calibration(res)
        assert res.report["measurable"] is False
        assert "NOT MEASURABLE" in text
        assert "NO VERDICT" in text


# ---------------------------------------------------------------------------
# blinding still holds on this path
# ---------------------------------------------------------------------------

class TestCalibrationDoesNotBreakBlinding:

    def test_every_seat_is_shown_the_same_artifact(self):
        items = CB.build_items(12, seed=4)
        seen: dict[str, str] = {}

        def spy(seat_id):
            def fn(prompt):
                seen[seat_id] = prompt
                return ""
            return fn

        CB.run_calibration({f"seat_{i}": spy(f"seat_{i}")
                            for i in range(1, 6)}, items)
        bodies = set(seen.values())
        assert len(seen) == 5
        assert len(bodies) == 1, "seats were shown different artifacts"

    def test_no_seat_is_shown_another_seats_answer(self):
        items = CB.build_items(12, seed=4)
        canary = "CANARY-c0ffee-DO-NOT-PROPAGATE"
        prompts: list[str] = []

        def loud(_p):
            prompts.append(_p)
            return f"CLAIM | arithmetic | 2 + 2 = 4 | {canary}"

        def quiet(p):
            prompts.append(p)
            return ""

        CB.run_calibration({"seat_1": loud, "seat_2": quiet, "seat_3": quiet},
                           items)
        assert not any(canary in p for p in prompts)


# ---------------------------------------------------------------------------
# the advice attached to the number
# ---------------------------------------------------------------------------

class TestTheVerdictSaysWhatToDo:

    def test_low_correlation_says_keep_five(self):
        assert "KEEP FIVE" in CB.verdict_line(0.05, 5)

    def test_high_correlation_says_cut(self):
        assert "CUT SEATS" in CB.verdict_line(0.9, 5)

    def test_the_middle_is_called_marginal_rather_than_rounded(self):
        assert "MARGINAL" in CB.verdict_line(0.35, 5)

    def test_no_rho_yields_no_recommendation(self):
        """A missing measurement must not become advice. Defaulting either way
        would let a run that measured nothing justify a spending decision."""
        line = CB.verdict_line(None, 5)
        assert "NO VERDICT" in line
        assert "KEEP" not in line and "CUT" not in line


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestTheCommandFailsClosed:

    def test_demo_exits_zero_and_needs_no_network(self):
        assert CB.main(["--demo", "--n-items", "12"]) == 0

    def test_an_odd_item_count_exits_two_without_running(self):
        assert CB.main(["--demo", "--n-items", "9"]) == 2

    def test_missing_credentials_exit_two_and_send_nothing(self, monkeypatch):
        for i in range(1, 6):
            monkeypatch.delenv(f"ADJ_SEAT_{i}_API_KEY", raising=False)
        assert CB.main(["--profiles", "profiles.example.json"]) == 2

    def test_an_unmeasurable_run_does_not_exit_zero(self, monkeypatch):
        """Exit 0 is what a CI job and a phone-triggered workflow read as
        'calibrated'. A run that produced no rho must not hand back one."""
        monkeypatch.setattr(CB, "_demo_seats",
                            lambda items: {"only": lambda _p: ""})
        assert CB.main(["--demo", "--n-items", "12"]) == 1

    def test_the_json_report_records_the_seed_that_made_the_items(self, tmp_path):
        """Without the seed the numbers cannot be reproduced or compared
        across runs, which is the whole point of recording them."""
        import json
        out = tmp_path / "calib.json"
        CB.main(["--demo", "--n-items", "12", "--seed", "4321",
                 "--json", str(out)])
        payload = json.loads(out.read_text())
        assert payload["seed"] == 4321
        assert payload["n_items"] == 12
        assert payload["measurable"] is True
