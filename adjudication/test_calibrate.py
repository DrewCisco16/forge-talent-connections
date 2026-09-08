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

from unittest import mock

import pytest

import adjudication_orchestrator as AO
import calibrate as CB
from correctness_matrix import SHARED_DETECTION


def _arith(lhs: str) -> int:
    """Evaluate an item's left-hand side without reusing the module under
    test, so a bug in build_items cannot validate itself."""
    for sym, fn in (("*", lambda x, y: x * y), ("+", lambda x, y: x + y)):
        if sym in lhs:
            a, _, b = lhs.partition(sym)
            return fn(int(a.strip()), int(b.strip()))
    raise AssertionError(f"unrecognised expression: {lhs!r}")

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
        gate could catch -- the gate would be right and the key wrong.

        Evaluated generically rather than by splitting on '+', so that adding
        an operator to build_items cannot quietly stop this from checking the
        items it was meant to check."""
        for it in CB.build_items(60, seed=7):
            lhs, _, rhs = it.expression.rpartition("=")
            assert (_arith(lhs) == int(rhs)) is it.is_true, it

    def test_the_answer_key_agrees_with_the_gate_that_scores_it(self):
        """The independent check: this module's is_true and the gate's verdict
        are computed by different code, and the whole measurement is void if
        they ever disagree."""
        gate = AO.ArithmeticGate()
        for it in CB.build_items(30, seed=13):
            res = gate.check(AO.Claim(id="", kind=AO.ClaimKind.ARITHMETIC,
                                      text=it.expression,
                                      warrant=it.expression))
            ruled_true = res.status is AO.GateStatus.PASS
            assert ruled_true is it.is_true, (it, res.status, res.detail)

    def test_the_probe_is_not_only_addition(self):
        """Three-digit addition alone produced NO variation between real-model
        seats, so rho came back NaN and the run measured nothing. The mix is
        the fix, and this pins it."""
        ops = {("*" if "*" in i.expression else "+")
               for i in CB.build_items(24, seed=7)}
        assert ops == {"+", "*"}

    def test_the_same_seed_gives_the_same_items(self):
        assert CB.build_items(12, seed=99) == CB.build_items(12, seed=99)

    def test_a_different_seed_gives_different_items(self):
        assert CB.build_items(12, seed=1) != CB.build_items(12, seed=2)

    def test_false_items_are_wrong_by_a_small_margin(self):
        """An answer off by an order of magnitude is caught by inspection and
        measures nothing. The probe only has signal if the wrong answers are
        plausible."""
        for it in CB.build_items(42, seed=3):
            if it.is_true:
                continue
            lhs, _, rhs = it.expression.rpartition("=")
            assert 0 < abs(_arith(lhs) - int(rhs)) <= 9

    def test_a_count_that_would_unbalance_a_band_is_refused(self):
        """With three bands, n must be a multiple of six or some band ends up
        with more true items than false -- and a band whose polarity is skewed
        rewards guessing in one direction."""
        with pytest.raises(ValueError, match="multiple of 6"):
            CB.build_items(20)

    def test_too_few_items_to_fill_the_bands_is_refused(self):
        with pytest.raises(ValueError, match="at least 6"):
            CB.build_items(4)

    def test_every_band_gets_both_polarities_equally(self):
        items = CB.build_items(60, seed=5)
        for band in CB.BANDS:
            in_band = [i for i in items if i.band == band]
            assert len(in_band) == 20, band
            assert sum(1 for i in in_band if i.is_true) == 10, band

    def test_the_polarity_rule_does_not_depend_on_the_band_count(self):
        """Truth alternates by CYCLE, not by index, and the difference is
        invisible at three bands -- index parity balances there because three
        is odd. It is a coincidence, not an equivalence: at four bands index
        parity pins band 0 to true and band 1 to false permanently, and a band
        with fixed polarity rewards guessing in one direction.

        Exercised against build_items itself with a FOUR-band set, because at
        three bands the two rules are behaviourally identical and a test at
        that size cannot fail whichever is implemented. Caught by mutation."""
        four = ("easy", "medium", "hard", "harder")
        with mock.patch.object(CB, "BANDS", four):
            items = CB.build_items(8 * len(four), seed=5)
        for band in four:
            in_band = [i for i in items if i.band == band]
            assert in_band, band
            n_true = sum(1 for i in in_band if i.is_true)
            assert n_true * 2 == len(in_band), (band, n_true, len(in_band))

    def test_the_probe_spans_a_range_rather_than_picking_one_difficulty(self):
        """A single difficulty can only be wrong in one of two directions and
        cannot tell you which. Both earlier sets failed that way."""
        assert {i.band for i in CB.build_items(60, seed=5)} == set(CB.BANDS)


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

    def test_the_report_says_how_many_seats_the_number_describes(self):
        """The old text claimed rho was "computed over the seats that
        answered". It was not: one errored seat voided the whole run and
        nothing was computed at all. The report must state the size of the
        panel actually measured."""
        items = CB.build_items(12, seed=4)
        seats = dict(CB._demo_seats(items))
        seats["seat_2"] = lambda _p: (_ for _ in ()).throw(RuntimeError("429"))
        text = CB.render_calibration(CB.run_calibration(seats, items))
        assert "SEATS EXCLUDED FROM THE MEASUREMENT (1 of 5)" in text
        assert "describes 4 seat(s), NOT the 5 you are paying for" in text

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

    def test_one_flaky_seat_does_not_void_the_whole_run(self):
        """THE EXPENSIVE ONE. correctness_matrix drops every claim first
        adjudicated in a pass where ANY seat errored -- correct for a
        five-pass run, catastrophic for a one-pass calibration, because no
        other pass carries the items. One flaky seat produced a zero-item
        matrix and a wasted paid run."""
        items = CB.build_items(24, seed=11)
        seats = dict(CB._demo_seats(items))
        seats["seat_3"] = lambda _p: (_ for _ in ()).throw(RuntimeError("reset"))
        res = CB.run_calibration(seats, items)
        assert res.report["measurable"] is True
        assert res.report["coverage"].n_items >= 12
        assert res.rho is not None
        assert len(res.scored_seats) == 4

    def test_an_empty_reply_is_an_absence_not_an_all_false_verdict(self):
        """A refusal, a safety filter, or an empty body behind a 200 all
        arrive as "". Scoring that as "this seat judged every statement false"
        puts a fabricated decisive row into the correlation."""
        items = CB.build_items(24, seed=11)
        seats = dict(CB._demo_seats(items))
        seats["seat_4"] = lambda _p: ""
        res = CB.run_calibration(seats, items)
        assert "seat_4" in res.excluded_seats
        assert "seat_4" not in res.scored_seats
        assert len(res.scored_seats) == 4
        assert res.rho is not None

    def test_the_confirmation_count_is_reported_for_every_seat(self):
        """A truncated reply and a decisive one are identical from the text.
        The count is the only thing that exposes the difference."""
        items = CB.build_items(24, seed=11)
        seats = dict(CB._demo_seats(items))
        truncated = items[:2]
        seats["seat_5"] = lambda _p: "\n".join(
            f"CLAIM | arithmetic | {i.expression} | {i.expression}"
            for i in truncated if i.is_true)
        res = CB.run_calibration(seats, items)
        assert res.confirmations["seat_5"] < res.confirmations["seat_1"]
        assert "cut off mid-reply" in CB.render_calibration(res)

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
        assert "KEEP FIVE" in CB.verdict_line(CB.RhoReading(rho=0.05, n_seats=5))

    def test_high_correlation_says_cut(self):
        assert "CUT SEATS" in CB.verdict_line(CB.RhoReading(rho=0.9, n_seats=5))

    def test_the_middle_is_called_marginal_rather_than_rounded(self):
        assert "MARGINAL" in CB.verdict_line(CB.RhoReading(rho=0.35, n_seats=5))

    def test_no_rho_yields_no_recommendation(self):
        """A missing measurement must not become advice. Defaulting either way
        would let a run that measured nothing justify a spending decision."""
        line = CB.verdict_line(CB.RhoReading(rho=None, n_seats=5))
        assert "NO VERDICT" in line
        assert "KEEP FIVE" not in line and "CUT SEATS" not in line

    def test_a_nan_rho_yields_no_recommendation(self):
        """THE BUG THIS CLASS EXISTS FOR. NaN fails every comparison, so the
        threshold ladder fell through to its last branch and a run that
        measured NOTHING printed 'CUT SEATS ... the seats mostly fail
        together'. Wrong, expensive, and in the confident direction."""
        line = CB.verdict_line(CB.RhoReading(rho=float("nan"), n_seats=5))
        assert "NO VERDICT" in line
        assert "CUT SEATS" not in line

    def test_nan_is_recognised_as_an_absent_measurement(self):
        assert CB.rho_undefined(float("nan")) is True
        assert CB.rho_undefined(None) is True
        assert CB.rho_undefined(0.0) is False
        assert CB.rho_undefined(1.0) is False


class TestSeatsThatAllScoreIdenticallyAreNotCalledCollapsed:
    """The most likely shape of a first live run: the probe turns out easy
    enough that every seat gets everything right. Nothing is measured, and
    that must not read as a finding in either direction."""

    def _perfect_panel(self):
        items = CB.build_items(24, seed=11)
        return items, {f"seat_{i}": CB._demo_seat(items, set())
                       for i in range(1, 6)}

    def test_the_verdict_refuses_rather_than_recommending_cuts(self):
        items, seats = self._perfect_panel()
        text = CB.render_calibration(CB.run_calibration(seats, items))
        assert "NO VERDICT" in text
        assert "CUT SEATS" not in text

    def test_rho_is_shown_as_undefined_not_as_nan(self):
        items, seats = self._perfect_panel()
        text = CB.render_calibration(CB.run_calibration(seats, items))
        assert "nan" not in text.lower()
        assert "undefined" in text

    def test_the_operator_is_told_the_probe_was_too_easy(self):
        """Without this the operator has a failed run and no next step."""
        items, seats = self._perfect_panel()
        text = CB.render_calibration(CB.run_calibration(seats, items))
        assert "too easy" in text
        assert "--n-items" in text

    def test_it_does_not_exit_zero(self, monkeypatch):
        """Exit 0 is what the phone-triggered workflow reads as 'calibrated'.
        correctness_matrix reports measurable=True here -- the matrix WAS
        built -- so the exit code cannot be derived from that flag alone."""
        monkeypatch.setattr(
            CB, "_demo_seats",
            lambda its: {f"seat_{i}": CB._demo_seat(its, set())
                         for i in range(1, 6)})
        assert CB.main(["--demo", "--n-items", "24", "--seed", "11"]) == 1


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


# ---------------------------------------------------------------------------
# real models do not reproduce a format character for character
# ---------------------------------------------------------------------------

class TestSeatWordingIsSnappedToTheCanonicalItem:
    """Measured against line_claim_extractor before this existed: a leading
    bullet or bold marker made the line vanish entirely (0 claims, scored as
    the seat judging every statement false); dropping the spaces around '*'
    produced a DIFFERENT claim id, so the two spellings became two one-seat
    items and a purely typographical difference manufactured disagreement in
    both directions; and a thousands separator made the gate rule
    INAPPLICABLE, dropping the item from the matrix without a word."""

    def _item(self):
        return CB.build_items(24, seed=11)[1]

    def _id_for(self, raw):
        items = CB.build_items(24, seed=11)
        claims = CB.calibration_extractor(items)(raw, "seat_1", "calib")
        return claims[0].id if claims else None

    @pytest.mark.parametrize("decorate", [
        lambda e: f"CLAIM | arithmetic | {e} | {e}",
        lambda e: f"- CLAIM | arithmetic | {e} | {e}",
        lambda e: f"* CLAIM | arithmetic | {e} | {e}",
        lambda e: f"**CLAIM** | arithmetic | {e} | {e}",
        lambda e: f"> CLAIM | arithmetic | {e} | {e}",
        lambda e: f"```\nCLAIM | arithmetic | {e} | {e}\n```",
        lambda e: f"Here are my answers:\n\nCLAIM | arithmetic | {e} | {e}",
        lambda e: "CLAIM | arithmetic | {0} | {0}".format(e.replace(" ", "")),
        lambda e: f"CLAIM|arithmetic|{e}|{e}",
    ])
    def test_every_plausible_wording_yields_the_same_claim_id(self, decorate):
        e = self._item().expression
        canonical = self._id_for(f"CLAIM | arithmetic | {e} | {e}")
        assert canonical is not None
        assert self._id_for(decorate(e)) == canonical

    def test_a_thousands_separator_still_reaches_the_gate(self):
        """'363,455' is the same number, but the gate cannot parse it and
        rules INAPPLICABLE -- which escalates the item out of the matrix."""
        it = self._item()
        lhs, _, rhs = it.expression.rpartition("= ")
        with_comma = f"{lhs}= {int(rhs):,}"
        assert "," in with_comma
        assert self._id_for(
            f"CLAIM | arithmetic | {with_comma} | {with_comma}"
        ) == self._id_for(f"CLAIM | arithmetic | {it.expression} | {it.expression}")

    def test_a_statement_outside_the_set_is_never_snapped(self):
        """Snapping must normalise spelling, never repair arithmetic."""
        items = CB.build_items(24, seed=11)
        claims = CB.calibration_extractor(items)(
            "CLAIM | arithmetic | 2 + 2 = 5 | 2 + 2 = 5", "seat_1", "calib")
        assert claims[0].warrant == "2 + 2 = 5"

    def test_an_asterisk_inside_the_expression_survives_undecoration(self):
        """Leading decoration is stripped; the multiplication sign is not."""
        e = self._item().expression
        assert "*" in e
        out = CB._undecorate(f"- CLAIM | arithmetic | {e} | {e}")
        assert out.startswith("CLAIM |")
        assert e in out


class TestSaturationIsNotReportedAsCollapse:
    """Both produce rho = 1.0 and they mean opposite things. Seats sharing a
    blind spot score WELL and fail together on a few items -- cutting seats is
    right. Seats drowning in a probe too hard for them fail nearly everything,
    which also correlates perfectly but says nothing about independence."""

    def _panel(self, wrong_ids):
        items = CB.build_items(24, seed=11)
        return items, {f"seat_{k + 1}": CB._demo_seat(items, wrong_ids)
                       for k in range(5)}

    def test_a_few_shared_errors_reads_as_collapse(self):
        items = CB.build_items(24, seed=11)
        ids = {i.item_id for i in items[:3]}
        _, seats = self._panel(ids)
        res = CB.run_calibration(seats, items)
        assert res.rho == pytest.approx(1.0)
        assert res.mean_accuracy > 0.6
        assert "CUT SEATS" in CB.verdict_line(CB.RhoReading.of(res))

    def test_failing_nearly_everything_refuses_a_verdict(self):
        items = CB.build_items(24, seed=11)
        ids = {i.item_id for i in items[:20]}
        _, seats = self._panel(ids)
        res = CB.run_calibration(seats, items)
        line = CB.verdict_line(CB.RhoReading.of(res))
        assert res.rho == pytest.approx(1.0)
        assert res.mean_accuracy < 0.6
        assert "SATURATED" in line
        assert "CUT SEATS" not in line

    def test_accuracy_is_read_off_the_same_matrix_as_rho(self):
        """If the per-seat figures and rho came from different matrices they
        could describe different panels and nobody would notice."""
        items = CB.build_items(24, seed=11)
        res = CB.run_calibration(CB._demo_seats(items), items)
        assert set(res.seat_accuracy) == set(res.report["coverage"].seats)

    def test_the_report_names_which_seats_are_weakest(self):
        """'Cut seats' is unactionable without saying which."""
        items = CB.build_items(24, seed=11)
        text = CB.render_calibration(
            CB.run_calibration(CB._demo_seats(items), items))
        assert "PER SEAT" in text
        assert "accuracy" in text


class TestTheItemSetCannotCollideWithItself:

    def test_no_two_items_share_a_left_hand_side(self):
        """Two items with the same operands collapse into ONE claim id, so the
        run scores fewer items than it asked about while still reporting n --
        and if one were true and the other false, that single id would carry
        two contradictory answer-key entries."""
        for seed in (1, 7, 11, 4321):
            items = CB.build_items(60, seed=seed)
            lhs = [i.expression.rpartition("=")[0].strip() for i in items]
            assert len(lhs) == len(set(lhs)), seed

    def test_no_two_items_share_a_canonical_key(self):
        for seed in (1, 7, 11, 4321):
            keys = [CB._canonical_key(i.expression)
                    for i in CB.build_items(60, seed=seed)]
            assert len(keys) == len(set(keys)), seed

    def test_uniqueness_holds_at_a_scale_where_chance_would_break_it(self):
        """AT n=24 THIS PROVES NOTHING. Removing the uniqueness guard changes
        no outcome for small sets -- measured: zero collisions at n up to 600,
        so a test at that size passes with the guard deleted and is worth
        nothing. Collisions first appear at n=1000, which is where the guard
        has to be tested if the test is to have any force at all."""
        for seed in (1, 7, 11, 4321):
            lhs = [CB._canonical_key(i.expression.rpartition("=")[0])
                   for i in CB.build_items(1002, seed=seed)]
            assert len(lhs) == len(set(lhs)), seed

    def test_run_calibration_actually_uses_the_snapping_extractor(self):
        """WIRING, NOT COMPONENT. Every other test in this class calls
        calibration_extractor directly, so all of them still passed when the
        extractor was removed from run_calibration and the tolerance silently
        vanished from the real path. Caught by mutation, pinned here.

        Two seats confirm the same statements in different wordings. Snapped,
        that is one item with two seats; unsnapped it is two one-seat items,
        and the panel looks more independent than it is."""
        items = CB.build_items(24, seed=11)
        true_items = [i for i in items if i.is_true]

        def plain(_p):
            return "\n".join(
                f"CLAIM | arithmetic | {i.expression} | {i.expression}"
                for i in true_items)

        def decorated(_p):
            return "\n".join(
                "- **CLAIM** | arithmetic | {0} | {0}".format(
                    i.expression.replace(" ", ""))
                for i in true_items)

        res = CB.run_calibration({"seat_a": plain, "seat_b": decorated}, items)
        # The signal is per-seat accuracy, not the item count: every item is
        # seeded into the matrix now, so n_items is n either way. Unwired, the
        # decorated seat's claims land on ids nobody else uses -- it is scored
        # as having confirmed none of the true items and drops to ~50%.
        assert res.seat_accuracy["seat_a"] == 1.0
        assert res.seat_accuracy["seat_b"] == 1.0, (
            "the decorated seat scored differently from the plain one: "
            "wordings did not collide, so the extractor is not wired in")
        assert not res.unmatched_claims


class TestASharedMissIsVisible:
    """THE MOST DANGEROUS BLIND SPOT WAS THE ONE THAT LEFT NO TRACE.

    build_correctness_matrix builds rows from the verdicts, and a statement
    nobody proposed is never gated and never becomes a row. So when all five
    seats MISSED the same true statement -- everyone failing to spot a real
    defect, which is precisely what this tool exists to detect -- the item
    vanished and the run reported nothing. The visible half of the same
    behaviour, all five wrongly ASSERTING a false statement, registered fine.
    calibrate now seeds every item so both halves are measurable."""

    def _panel_missing(self, items, missed_ids):
        return {f"seat_{k + 1}": CB._demo_seat(items, missed_ids)
                for k in range(5)}

    def test_every_item_reaches_the_matrix_even_if_no_seat_spoke_of_it(self):
        """Two seats each confirm ONE item. The other 23 were never proposed
        by anybody -- and before seeding, those 23 simply did not exist as far
        as the measurement was concerned."""
        items = CB.build_items(24, seed=11)
        first = next(i for i in items if i.is_true)
        line = f"CLAIM | arithmetic | {first.expression} | {first.expression}"
        res = CB.run_calibration(
            {"seat_a": lambda _p: line, "seat_b": lambda _p: line}, items)
        assert res.report["coverage"].n_items == len(items)
        assert res.report["coverage"].n_items_from_gates == len(items)

    def test_five_seats_missing_the_same_true_items_is_detected(self):
        items = CB.build_items(24, seed=11)
        missed = {i.item_id for i in items if i.is_true}
        missed = set(list(missed)[:3])
        res = CB.run_calibration(self._panel_missing(items, missed), items)
        assert res.report["coverage"].n_items == len(items)
        assert res.rho == pytest.approx(1.0), (
            "a shared miss produced no signal: items nobody asserted are "
            "missing from the matrix again")

    def test_a_shared_miss_and_a_shared_false_assertion_both_register(self):
        """They are the two halves of one behaviour and must not be measured
        differently."""
        items = CB.build_items(24, seed=11)
        missed = {i.item_id for i in items if i.is_true}
        asserted = {i.item_id for i in items if not i.is_true}
        a = CB.run_calibration(
            self._panel_missing(items, set(list(missed)[:3])), items)
        b = CB.run_calibration(
            self._panel_missing(items, set(list(asserted)[:3])), items)
        assert a.rho == pytest.approx(1.0)
        assert b.rho == pytest.approx(1.0)
        assert a.report["coverage"].n_items == b.report["coverage"].n_items


class TestTheTwoReadingsAreNotCollapsedIntoOne:
    """seat_independence guards a zero-variance SEAT but not a zero-variance
    ITEM. A band every seat fails enters the correlation as perfect agreement
    by construction and drags the headline up. Measured: a panel genuinely
    independent on the band that discriminated it scored rho 0.768 and was
    told to CUT SEATS, because ten hard items nobody got right counted as ten
    instances of failing together."""

    def _bracketed_panel(self):
        items = CB.build_items(60, seed=11)
        hard = {i.item_id for i in items if i.band == "hard"}
        med = [i for i in items if i.band == "medium"]
        seats = {
            f"seat_{k + 1}": CB._demo_seat(
                items, hard | {med[k].item_id, med[(k + 3) % len(med)].item_id})
            for k in range(5)
        }
        return items, seats

    def test_the_discriminating_reading_is_computed_separately(self):
        items, seats = self._bracketed_panel()
        res = CB.run_calibration(seats, items)
        assert res.rho_discriminating is not None
        assert res.n_unanimous_items > 0
        assert res.rho > res.rho_discriminating

    def test_no_single_verdict_when_the_two_readings_disagree(self):
        items, seats = self._bracketed_panel()
        res = CB.run_calibration(seats, items)
        line = CB.verdict_line(CB.RhoReading.of(res))
        assert "NO SINGLE VERDICT" in line
        assert "CUT SEATS" not in line
        assert "KEEP FIVE" not in line

    def test_agreeing_readings_still_produce_a_verdict(self):
        """The refusal must fire on disagreement, not on the mere presence of
        a second number."""
        line = CB.verdict_line(CB.RhoReading(rho=0.05, n_seats=5, mean_accuracy=0.9, rho_discriminating=0.06))
        assert "KEEP FIVE" in line

    def test_a_wide_gap_that_changes_no_decision_is_not_a_conflict(self):
        """This first compared the raw gap and got it wrong. On the shipped
        demo the readings were -0.034 and -0.250 -- a gap of 0.216, and both
        squarely 'keep five'. Refusing there invents a conflict out of two
        numbers that agree about everything the operator must decide, and an
        alarm that fires when nothing is wrong gets ignored when something
        is."""
        line = CB.verdict_line(CB.RhoReading(rho=-0.034, n_seats=5, mean_accuracy=0.9, rho_discriminating=-0.250))
        assert "KEEP FIVE" in line
        assert "NO SINGLE VERDICT" not in line

    def test_a_narrow_gap_across_a_threshold_is_a_conflict(self):
        """The mirror image: a small numeric difference that lands the two
        readings on opposite sides of a recommendation IS a conflict."""
        line = CB.verdict_line(CB.RhoReading(rho=0.55, n_seats=5, mean_accuracy=0.9, rho_discriminating=0.45))
        assert "NO SINGLE VERDICT" in line

    def test_the_demo_panel_still_yields_a_verdict(self):
        """End to end, on the exact panel an operator meets first."""
        items = CB.build_items(60, seed=11)
        res = CB.run_calibration(CB._demo_seats(items), items)
        assert "KEEP FIVE" in CB.verdict_line(CB.RhoReading.of(res))

    def test_too_few_discriminating_items_yields_no_second_reading(self):
        """A correlation over one or two rows is not a measurement, and
        printing it beside the headline would lend it equal weight.

        Built with EXACTLY TWO discriminating rows, and built so those rows
        still carry column variance:
        seat_1 is wrong on one of them and seat_2 on the other. A panel where
        the odd seat is wrong on BOTH leaves every column constant, the
        correlation comes back NaN, and None is returned whatever the
        threshold says -- so that construction cannot test the guard either.
        Both dead ends were found by mutation."""
        items = CB.build_items(24, seed=11)
        seats = {f"seat_{k + 1}": CB._demo_seat(items, set())
                 for k in range(5)}
        seats["seat_1"] = CB._demo_seat(items, {items[0].item_id})
        seats["seat_2"] = CB._demo_seat(items, {items[1].item_id})
        res = CB.run_calibration(seats, items)
        assert res.n_unanimous_items == len(items) - 2
        assert res.rho_discriminating is None


class TestTheDifficultyTableMakesTheProbeLegible:

    def test_a_bracketed_panel_shows_the_gradient(self):
        items = CB.build_items(60, seed=11)
        hard = {i.item_id for i in items if i.band == "hard"}
        seats = {f"seat_{k + 1}": CB._demo_seat(items, hard) for k in range(5)}
        res = CB.run_calibration(seats, items)
        assert res.band_accuracy["easy"][1] == 1.0
        assert res.band_accuracy["hard"][1] < 0.5
        text = CB.render_calibration(res)
        assert "BY DIFFICULTY" in text

    def test_band_accuracy_is_keyed_by_claim_id_not_expression(self):
        """matrix.item_ids holds content-addressed hashes. Keying the lookup
        by expression silently matched nothing and produced an empty table."""
        items = CB.build_items(24, seed=11)
        res = CB.run_calibration(CB._demo_seats(items), items)
        assert set(res.band_accuracy) == set(CB.BANDS)


class TestPreflightPreventsPaidDiscovery:

    def _settings(self, tmp_path, body):
        import json
        p = tmp_path / "profiles.json"
        p.write_text(json.dumps({"seat_5": {
            "name": "Claude",
            "endpoint": "https://api.anthropic.com/v1/messages",
            "auth_header": "x-api-key", "auth_template": "{key}",
            "body": body, "text_path": ["content", 0, "text"]}}))
        return str(p)

    def test_sampling_params_on_an_anthropic_endpoint_are_caught(self, tmp_path):
        path = self._settings(tmp_path, {"model": "{{model}}",
                                         "temperature": "{{temperature}}"})
        problems = CB.preflight_settings(path)
        assert len(problems) == 1
        assert "temperature" in problems[0]

    def test_a_clean_settings_file_passes(self, tmp_path):
        path = self._settings(tmp_path, {"model": "{{model}}",
                                         "max_tokens": "{{max_tokens}}"})
        assert CB.preflight_settings(path) == []

    def test_the_same_key_on_another_vendor_is_not_flagged(self, tmp_path):
        """Only Anthropic endpoints reject these. Flagging every vendor would
        train the operator to ignore the warning."""
        import json
        p = tmp_path / "profiles.json"
        p.write_text(json.dumps({"seat_1": {
            "endpoint": "https://api.example-vendor.invalid/v1/chat",
            "body": {"temperature": "{{temperature}}"}}}))
        assert CB.preflight_settings(str(p)) == []

    def test_the_run_refuses_rather_than_spending(self, tmp_path):
        path = self._settings(tmp_path, {"temperature": "{{temperature}}"})
        assert CB.main(["--profiles", path]) == 2

    def test_an_unreadable_settings_file_is_a_problem_not_a_pass(self, tmp_path):
        assert CB.preflight_settings(str(tmp_path / "nope.json"))


class TestTheReportSpeaksToBothReaders:

    def test_a_high_rho_states_the_backward_looking_implication(self):
        """The report is framed for the budget-holder throughout. That framing
        hides the other reader: whoever relies on an answer this panel already
        produced. Nothing else in the system will tell them."""
        items = CB.build_items(60, seed=11)
        ids = {i.item_id for i in items[:6]}
        seats = {f"seat_{k + 1}": CB._demo_seat(items, ids) for k in range(5)}
        text = CB.render_calibration(CB.run_calibration(seats, items))
        assert "BACKWARD-LOOKING IMPLICATION" in text
        assert "ALREADY COMPLETED" in text

    def test_a_low_rho_does_not_raise_a_false_alarm(self):
        items = CB.build_items(60, seed=11)
        text = CB.render_calibration(
            CB.run_calibration(CB._demo_seats(items), items))
        assert "BACKWARD-LOOKING IMPLICATION" not in text


class TestTheIntervalNotThePointEstimateDecides:
    """rho was a bare number and a spending decision rested on which side of
    0.2 or 0.5 it fell. With 60 items and 5 seats that is a point estimate
    carrying unstated sampling error -- seat_independence's own reading line
    said so ("a small number of items makes rho unstable regardless of its
    value") while nothing in the pipeline did anything about it."""

    def test_a_straddling_interval_refuses_rather_than_recommending(self):
        line = CB.verdict_line(CB.RhoReading(
            rho=0.19, n_seats=5, mean_accuracy=0.9,
            rho_ci=(0.05, 0.34), n_items=60))
        assert "NOT RESOLVED AT THIS SAMPLE SIZE" in line
        assert "KEEP FIVE" not in line
        assert "CUT SEATS" not in line

    def test_an_interval_wholly_one_side_still_decides(self):
        line = CB.verdict_line(CB.RhoReading(
            rho=0.02, n_seats=5, mean_accuracy=0.9,
            rho_ci=(-0.05, 0.12), n_items=60))
        assert "KEEP FIVE" in line

    def test_an_impractical_sample_size_is_not_offered_as_advice(self):
        """rho=0.190 against a 0.2 edge wanted 12,618 items. That figure is
        arithmetically right and useless: it reads as a plan and is not one.
        The honest reading is that the true value may BE the threshold."""
        line = CB.verdict_line(CB.RhoReading(
            rho=0.199, n_seats=5, mean_accuracy=0.9,
            rho_ci=(0.05, 0.35), n_items=60))
        assert "No practical item count" in line
        assert "12618" not in line

    def test_a_reachable_sample_size_is_named(self):
        line = CB.verdict_line(CB.RhoReading(
            rho=0.10, n_seats=5, mean_accuracy=0.9,
            rho_ci=(0.02, 0.26), n_items=60))
        assert "would likely resolve it" in line

    def test_the_suggested_count_is_a_legal_item_count(self):
        """Advice to run a count build_items would refuse is not advice."""
        got = CB._items_to_resolve(0.10, (0.02, 0.26), 0.2, 60)
        assert got is not None
        assert got % (2 * len(CB.BANDS)) == 0
        CB.build_items(got, seed=1)

    def test_the_interval_is_reported_beside_the_estimate(self):
        items = CB.build_items(60, seed=11)
        text = CB.render_calibration(
            CB.run_calibration(CB._demo_seats(items), items, draws=200))
        assert "90% interval" in text
        assert "not the point estimate" in text


class TestTheIntervalIsReproducibleAndHonest:

    def _matrix(self, seats=None, seed=11):
        items = CB.build_items(60, seed=seed)
        res = CB.run_calibration(seats or CB._demo_seats(items), items,
                                 draws=400)
        return res

    def test_the_same_seed_reproduces_the_same_interval(self):
        """Global rule 4 blocks nondeterminism in replay. An interval that
        moved between runs of identical data would make replay meaningless."""
        a = self._matrix().rho_ci
        b = self._matrix().rho_ci
        assert a == b

    def test_the_interval_brackets_the_point_estimate(self):
        res = self._matrix()
        lo, hi = res.rho_ci
        assert lo <= res.rho <= hi

    def test_more_items_do_not_widen_the_interval(self):
        """Sampling error shrinks with n. If it did not, the interval is not
        measuring what it claims to."""
        narrow = CB.run_calibration(
            CB._demo_seats(CB.build_items(120, seed=11)),
            CB.build_items(120, seed=11), draws=400)
        wide = CB.run_calibration(
            CB._demo_seats(CB.build_items(24, seed=11)),
            CB.build_items(24, seed=11), draws=400)
        w_narrow = narrow.rho_ci[1] - narrow.rho_ci[0]
        w_wide = wide.rho_ci[1] - wide.rho_ci[0]
        assert w_narrow < w_wide

    def test_no_interval_when_there_is_nothing_to_resample(self):
        items = CB.build_items(12, seed=4)
        one = {"seat_1": CB._demo_seats(items)["seat_1"]}
        assert CB.run_calibration(one, items, draws=100).rho_ci is None


class TestTheBetaPosteriorMatchesClosedForms:
    """Hand-rolled because scipy is not a dependency. A quantile nobody
    checked would put a wrong interval beside every seat, and the first
    implementation WAS wrong -- a generic Lentz loop that returned f - 1,
    giving Beta(1,1) a 5th percentile of 0.0528 instead of 0.0500."""

    def test_beta_one_one_is_uniform(self):
        for q in (0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99):
            assert CB._beta_quantile(1.0, 1.0, q) == pytest.approx(q, abs=1e-9)

    def test_beta_two_one_is_sqrt(self):
        import math
        for q in (0.1, 0.5, 0.9):
            assert CB._beta_quantile(2.0, 1.0, q) == pytest.approx(
                math.sqrt(q), abs=1e-9)

    def test_beta_one_two_closed_form(self):
        import math
        for q in (0.1, 0.5, 0.9):
            assert CB._beta_quantile(1.0, 2.0, q) == pytest.approx(
                1 - math.sqrt(1 - q), abs=1e-9)

    def test_a_symmetric_beta_has_median_one_half(self):
        for a in (0.5, 2.0, 7.5, 40.0):
            assert CB._beta_quantile(a, a, 0.5) == pytest.approx(0.5, abs=1e-9)

    def test_the_cdf_runs_monotonically_from_zero_to_one(self):
        for a, b in ((0.5, 0.5), (3, 7), (60, 5)):
            xs = [i / 40 for i in range(41)]
            cs = [CB._beta_cdf(x, a, b) for x in xs]
            assert cs == sorted(cs), (a, b)
            assert cs[0] == pytest.approx(0.0, abs=1e-12)
            assert cs[-1] == pytest.approx(1.0, abs=1e-9)


class TestSeatIntervalsGuardTheCutDecision:

    def test_every_scored_seat_gets_an_interval(self):
        items = CB.build_items(60, seed=11)
        res = CB.run_calibration(CB._demo_seats(items), items, draws=200)
        assert set(res.seat_accuracy_ci) == set(res.seat_accuracy)

    def test_each_interval_contains_its_point_estimate(self):
        items = CB.build_items(60, seed=11)
        res = CB.run_calibration(CB._demo_seats(items), items, draws=200)
        for seat, acc in res.seat_accuracy.items():
            lo, hi = res.seat_accuracy_ci[seat]
            assert lo <= acc <= hi, seat

    def test_the_report_warns_against_cutting_on_overlapping_intervals(self):
        """'Cut the lowest-accuracy seats' ranks five numbers that each carry
        sampling error. Two seats a few points apart over 60 items are not
        distinguishable."""
        items = CB.build_items(60, seed=11)
        text = CB.render_calibration(
            CB.run_calibration(CB._demo_seats(items), items, draws=200))
        assert "intervals OVERLAP" in text


# ---------------------------------------------------------------------------
# a run that cost money is worth scoring more than once
# ---------------------------------------------------------------------------

class TestThePaidRepliesSurviveTheRun:
    """Before the transcript existed, the raw seat text was discarded the
    instant it was parsed -- only counts reached the result.

    That put the operator in a bad place on exactly the failure this module
    warns them about. When the report says CONFIRMATIONS THAT MATCHED NO ITEM
    ID -- a seat reworded the statements instead of copying them -- the score
    is biased in the FLATTERING direction, and the only remedy on offer was to
    pay five vendors again to look at it. Every extraction defect found in
    this module (markdown decoration, spacing variance, thousands separators)
    had that same shape: a well-formed report over evidence that had quietly
    fallen out. On synthetic seats they were catchable because the text was
    ours. On paid seats there was nothing to go back to.
    """

    def test_a_rescore_reproduces_the_original_number_exactly(self, tmp_path):
        """The point of the transcript. If replay disagreed with the run it
        came from, it would be a second opinion rather than a record."""
        book = tmp_path / "t.json"
        first = CB.main(["--demo", "--n-items", "12", "--transcript",
                         str(book)])
        items = CB.build_items(12, CB.DEFAULT_SEED)
        live = CB.run_calibration(CB._demo_seats(items), items)

        _, replayed = CB.load_transcript(str(book))
        again = CB.run_calibration(replayed, items)

        assert first == 0
        assert again.rho == pytest.approx(live.rho)
        assert again.effective_seats == pytest.approx(live.effective_seats)
        assert again.seat_accuracy == live.seat_accuracy
        assert again.rho_ci == live.rho_ci

    def test_replay_calls_no_seat_and_needs_no_credentials(self, tmp_path,
                                                           monkeypatch):
        """A re-score must be free. If it could reach a vendor it would be
        another paid run wearing the name of a cheap one."""
        book = tmp_path / "t.json"
        CB.main(["--demo", "--n-items", "12", "--transcript", str(book)])

        for i in range(1, 6):
            monkeypatch.delenv(f"ADJ_SEAT_{i}_API_KEY", raising=False)

        def forbidden(*a, **k):
            raise AssertionError("a re-score reached for live seats")

        monkeypatch.setattr(CB, "_demo_seats", forbidden)
        with mock.patch.dict("sys.modules"):
            assert CB.main(["--rescore", str(book)]) == 0

    def test_a_seat_that_errored_replays_as_errored_not_as_silent(self,
                                                                 tmp_path):
        """A seat that timed out and a seat that judged every statement false
        are different observations. Replaying the first as the second would
        put a fabricated row into the correlation -- the exact defaulting this
        module refuses everywhere else."""
        items = CB.build_items(12, CB.DEFAULT_SEED)
        seats = dict(CB._demo_seats(items))
        broken = min(seats)

        def dies(_prompt):
            raise RuntimeError("HTTP 503 from vendor")

        seats[broken] = dies

        # The seat runner absorbs an ordinary seat error and records it on the
        # response; only a budget ceiling propagates. So the run completes,
        # and the recorder must have captured the failure on the way past.
        captured = {}
        res = CB.run_calibration(CB.recording_seats(seats, captured), items)

        assert captured[broken] == {"error": "HTTP 503 from vendor"}
        assert broken in res.excluded_seats
        assert broken not in res.scored_seats

        book = tmp_path / "t.json"
        CB.write_transcript(str(book), items=items,
                            seed=CB.DEFAULT_SEED, replies=captured)
        _, replayed = CB.load_transcript(str(book))
        with pytest.raises(CB.ReplayedSeatError, match="HTTP 503"):
            replayed[broken]("prompt")

    def test_replies_already_paid_for_survive_a_budget_stop(self, tmp_path):
        """The ceiling propagates by design, so the run dies mid-panel. That
        is precisely the run whose replies are worth keeping: the money is
        already gone and there is no report to show for it."""
        from adjudication_orchestrator import BudgetExceeded

        items = CB.build_items(12, CB.DEFAULT_SEED)
        seats = dict(CB._demo_seats(items))
        order = sorted(seats)
        answered, stops = order[0], order[1]

        def ceiling(_prompt):
            raise BudgetExceeded("max cost reached")

        seats[stops] = ceiling

        captured = {}
        with pytest.raises(BudgetExceeded):
            CB.run_calibration(CB.recording_seats(seats, captured), items)

        assert answered in captured, (
            "the seat that answered before the ceiling was paid for and lost")
        assert captured[answered]["reply"]

    def test_the_cli_writes_a_transcript_even_when_the_run_dies(self,
                                                               tmp_path,
                                                               monkeypatch):
        from adjudication_orchestrator import BudgetExceeded

        items = CB.build_items(12, CB.DEFAULT_SEED)
        real = CB._demo_seats(items)
        order = sorted(real)

        def half_a_panel(_items):
            seats = dict(real)

            def ceiling(_prompt):
                raise BudgetExceeded("max cost reached")

            seats[order[1]] = ceiling
            return seats

        monkeypatch.setattr(CB, "_demo_seats", half_a_panel)
        book = tmp_path / "t.json"
        with pytest.raises(BudgetExceeded):
            CB.main(["--demo", "--n-items", "12", "--transcript", str(book)])

        assert book.exists(), "a run that spent money left nothing behind"


class TestTheTranscriptReaderFailsClosed:
    """Scoring paid replies against the wrong questions would produce a
    confident, wrong rho -- the failure mode this whole module exists to
    refuse. Every unreadable transcript has to stop the run, not degrade it.
    """

    def _book(self, tmp_path, mutate):
        import json
        book = tmp_path / "t.json"
        CB.main(["--demo", "--n-items", "12", "--transcript", str(book)])
        payload = json.loads(book.read_text())
        mutate(payload)
        book.write_text(json.dumps(payload))
        return book

    def test_questions_that_do_not_match_the_seed_are_refused(self, tmp_path):
        def swap(p):
            p["items"][0]["expression"] = "2 + 2 = 4"

        book = self._book(tmp_path, swap)
        with pytest.raises(ValueError, match="not the ones seed"):
            CB.load_transcript(str(book))
        assert CB.main(["--rescore", str(book)]) == 2

    def test_an_unknown_schema_is_refused_rather_than_guessed_at(self,
                                                                tmp_path):
        book = self._book(tmp_path, lambda p: p.__setitem__("schema", 99))
        with pytest.raises(ValueError, match="schema"):
            CB.load_transcript(str(book))

    def test_a_transcript_with_no_replies_is_refused(self, tmp_path):
        book = self._book(tmp_path, lambda p: p.__setitem__("seats", {}))
        with pytest.raises(ValueError, match="no seat replies"):
            CB.load_transcript(str(book))

    def test_a_transcript_with_no_items_is_refused(self, tmp_path):
        book = self._book(tmp_path, lambda p: p.__setitem__("items", []))
        with pytest.raises(ValueError, match="no item set"):
            CB.load_transcript(str(book))

    def test_a_missing_file_exits_two_rather_than_scoring_nothing(self,
                                                                  tmp_path):
        assert CB.main(["--rescore", str(tmp_path / "absent.json")]) == 2

    def test_an_edited_answer_key_cannot_move_rho(self, tmp_path):
        """`is_true` is read to build the Item, but the gate recomputes every
        expression during scoring. A transcript whose truth flags were flipped
        must score the same as one whose were not."""
        import json
        book = tmp_path / "t.json"
        CB.main(["--demo", "--n-items", "12", "--transcript", str(book)])
        payload = json.loads(book.read_text())

        honest_items, honest_seats = CB.load_transcript(str(book))
        honest = CB.run_calibration(honest_seats, honest_items)

        for entry in payload["items"]:
            entry["is_true"] = not entry["is_true"]
        forged = tmp_path / "forged.json"
        forged.write_text(json.dumps(payload))

        lied_items, lied_seats = CB.load_transcript(str(forged))
        lied = CB.run_calibration(lied_seats, lied_items)

        assert lied.rho == pytest.approx(honest.rho)
