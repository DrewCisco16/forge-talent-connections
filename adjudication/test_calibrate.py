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
        for it in CB.build_items(40, seed=3):
            if it.is_true:
                continue
            lhs, _, rhs = it.expression.rpartition("=")
            assert 0 < abs(_arith(lhs) - int(rhs)) <= 9

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
        assert "KEEP FIVE" not in line and "CUT SEATS" not in line

    def test_a_nan_rho_yields_no_recommendation(self):
        """THE BUG THIS CLASS EXISTS FOR. NaN fails every comparison, so the
        threshold ladder fell through to its last branch and a run that
        measured NOTHING printed 'CUT SEATS ... the seats mostly fail
        together'. Wrong, expensive, and in the confident direction."""
        line = CB.verdict_line(float("nan"), 5)
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
        assert "CUT SEATS" in CB.verdict_line(
            res.rho, len(res.scored_seats), res.mean_accuracy)

    def test_failing_nearly_everything_refuses_a_verdict(self):
        items = CB.build_items(24, seed=11)
        ids = {i.item_id for i in items[:20]}
        _, seats = self._panel(ids)
        res = CB.run_calibration(seats, items)
        line = CB.verdict_line(res.rho, len(res.scored_seats), res.mean_accuracy)
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
                   for i in CB.build_items(1000, seed=seed)]
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
        cov = res.report["coverage"]
        assert cov.n_items == len(true_items), (
            "wordings did not collide: the extractor is not wired in")
        assert not res.unmatched_claims
        assert res.seat_accuracy["seat_a"] == res.seat_accuracy["seat_b"] == 1.0
