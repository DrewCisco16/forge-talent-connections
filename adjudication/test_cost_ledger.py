"""
test_cost_ledger.py — tests for the module that stops the operator overspending.

WHY THIS FILE EXISTS. cost_ledger.py sat at 57% coverage and was absent from
the CI coverage list entirely, so the module whose entire job is to refuse an
expensive call was the least verified part of the toolchain. check_before_call
is the only thing standing between a misconfigured run and an unbounded bill,
and it ran on a real panel while largely untested.

The recurring theme is that this module must fail CLOSED. Every branch below
that refuses something is a branch that, inverted, spends the operator's money
silently -- and a ceiling that does not hold is worse than no ceiling, because
the operator stops watching.
"""
from __future__ import annotations

import json
import os
from datetime import date, timedelta

import pytest

import cost_ledger as CL

RATE = CL.Rate(input_per_mtok=1.0, output_per_mtok=10.0)


def _led(**kw):
    return CL.CostLedger(rates={"seat_1": RATE}, **kw)


# ---------------------------------------------------------------------------
# refusing a call BEFORE it is made
# ---------------------------------------------------------------------------

class TestTheCeilingIsCheckedBeforeSpending:

    def test_a_call_that_would_cross_the_run_ceiling_is_refused(self):
        led = _led(per_run=0.01)
        with pytest.raises(CL.CeilingReached) as err:
            led.check_before_call("seat_1", 1_000_000, 1_000_000)
        assert "per-run" in str(err.value)

    def test_a_call_that_fits_is_allowed(self):
        _led(per_run=100.0).check_before_call("seat_1", 1000, 1000)

    def test_no_ceiling_means_no_refusal(self):
        _led().check_before_call("seat_1", 10_000_000, 10_000_000)

    def test_an_unpriced_seat_is_refused_not_treated_as_free(self):
        """An unpriced seat under a ceiling is an unbounded seat. Treating a
        missing rate as zero would let the one seat nobody configured spend
        without limit while every dashboard still read green."""
        with pytest.raises(CL.CeilingReached, match="no rate configured"):
            _led(per_run=1.0).check_before_call("seat_UNKNOWN", 10, 10)

    def test_an_unpriced_seat_is_refused_even_with_no_ceiling_set(self):
        """Fail closed does not depend on a ceiling being configured: the
        inability to price a call is itself the finding."""
        with pytest.raises(CL.CeilingReached, match="no rate configured"):
            _led().check_before_call("seat_UNKNOWN", 10, 10)

    def test_the_estimate_uses_the_worst_case_not_the_average(self):
        """Estimating with anything smaller than the configured cap lets the
        last call of a run cross the limit it was checked against -- which is
        how a $3.00 ceiling produced a $3.14 bill."""
        led = _led(per_run=0.02)
        led.check_before_call("seat_1", 1000, 1000)
        with pytest.raises(CL.CeilingReached):
            led.check_before_call("seat_1", 1000, 10_000)

    def test_spend_already_booked_counts_toward_the_ceiling(self):
        led = _led(per_run=0.05)
        led.record("seat_1", 1_000_000, 1_000_000)   # $11.00
        with pytest.raises(CL.CeilingReached):
            led.check_before_call("seat_1", 10, 10)

    def test_the_refusal_names_the_numbers(self):
        """'Ceiling reached' without the figures leaves the operator unable to
        tell a correct stop from a bug in the estimator."""
        led = _led(per_run=0.5)
        with pytest.raises(CL.CeilingReached) as err:
            led.check_before_call("seat_1", 1_000_000, 1_000_000)
        msg = str(err.value)
        assert "0.50" in msg and "Call not made" in msg


class TestPerStageAndPerDayCeilings:

    def test_a_stage_ceiling_binds_within_one_pass(self):
        led = _led(per_stage=0.02)
        led.record("seat_1", 1000, 1000, pass_id="p1")
        with pytest.raises(CL.CeilingReached, match=r"per-stage \(p1\)"):
            led.check_before_call("seat_1", 1_000_000, 1_000_000, pass_id="p1")

    def test_a_stage_ceiling_does_not_leak_between_passes(self):
        """Spend booked to p1 must not refuse a call in p2, or a long run
        would stop on a limit that was never reached."""
        led = _led(per_stage=0.05)
        led.record("seat_1", 1_000_000, 1_000_000, pass_id="p1")
        led.check_before_call("seat_1", 1000, 1000, pass_id="p2")

    def test_a_stage_ceiling_is_skipped_when_no_pass_is_named(self):
        led = _led(per_stage=0.0001)
        led.check_before_call("seat_1", 1000, 1000, pass_id=None)

    def test_a_day_ceiling_counts_yesterdays_file_plus_todays_run(self, tmp_path):
        state = tmp_path / "day.json"
        state.write_text(json.dumps({date.today().isoformat(): 9.99}))
        led = CL.CostLedger(rates={"seat_1": RATE}, per_day=10.0,
                            day_state_path=str(state))
        with pytest.raises(CL.CeilingReached, match="per-day"):
            led.check_before_call("seat_1", 1_000_000, 1_000_000)

    def test_only_todays_entry_is_read(self, tmp_path):
        state = tmp_path / "day.json"
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        state.write_text(json.dumps({yesterday: 999.0}))
        led = CL.CostLedger(rates={"seat_1": RATE}, per_day=1.0,
                            day_state_path=str(state))
        assert led.day_spent() == 0.0
        led.check_before_call("seat_1", 1000, 1000)

    def test_an_unreadable_day_file_is_not_treated_as_spend(self, tmp_path):
        """Unreadable state is not evidence of spending. Treating it as a huge
        number would halt every run on a corrupted file."""
        state = tmp_path / "day.json"
        state.write_text("{ this is not json")
        led = CL.CostLedger(rates={"seat_1": RATE}, per_day=1.0,
                            day_state_path=str(state))
        assert led.day_spent() == 0.0

    def test_a_missing_day_file_is_zero_not_an_error(self, tmp_path):
        led = CL.CostLedger(rates={"seat_1": RATE},
                            day_state_path=str(tmp_path / "nope.json"))
        assert led.day_spent() == 0.0


class TestPersistingTheDay:

    def test_todays_spend_is_added_to_what_was_already_there(self, tmp_path):
        state = tmp_path / "day.json"
        state.write_text(json.dumps({date.today().isoformat(): 1.0}))
        led = CL.CostLedger(rates={"seat_1": RATE}, day_state_path=str(state))
        led.record("seat_1", 1_000_000, 0)          # $1.00
        led.persist_day()
        assert json.loads(state.read_text())[date.today().isoformat()] == 2.0

    def test_the_write_is_atomic(self, tmp_path):
        """A crash mid-write must not leave a truncated file, because the next
        run reads it as zero and the day ceiling silently resets."""
        state = tmp_path / "day.json"
        led = CL.CostLedger(rates={"seat_1": RATE}, day_state_path=str(state))
        led.record("seat_1", 1000, 1000)
        led.persist_day()
        assert not os.path.exists(str(state) + ".tmp")

    def test_a_corrupt_existing_file_is_replaced_not_propagated(self, tmp_path):
        state = tmp_path / "day.json"
        state.write_text("garbage")
        led = CL.CostLedger(rates={"seat_1": RATE}, day_state_path=str(state))
        led.record("seat_1", 1_000_000, 0)
        led.persist_day()
        assert json.loads(state.read_text())[date.today().isoformat()] == 1.0

    def test_no_path_means_no_write(self):
        _led().persist_day()   # must not raise


# ---------------------------------------------------------------------------
# what a run actually cost
# ---------------------------------------------------------------------------

class TestRecordingAndReporting:

    def test_an_unmeasured_call_is_counted_not_priced(self):
        """A vendor that returns no usage block leaves the total a floor.
        Pricing it at an assumed number would report a bill nobody can check."""
        led = _led()
        led.record("seat_1", None, None)
        assert led.spent == 0.0
        assert led.unmeasured_calls == 1

    def test_the_total_is_labelled_a_lower_bound_when_anything_is_unmeasured(self):
        led = _led()
        led.record("seat_1", 1000, 1000)
        led.record("seat_1", None, None)
        text = "\n".join(led.render())
        assert "LOWER BOUND" in text
        assert "floor, not the bill" in text

    def test_a_fully_measured_run_is_not_labelled_a_bound(self):
        led = _led()
        led.record("seat_1", 1000, 1000)
        assert "LOWER BOUND" not in "\n".join(led.render())

    def test_no_calls_says_so_rather_than_reporting_zero_dollars(self):
        """'$0.0000' reads as a completed free run; 'no billable call' reads as
        what it is."""
        assert "no billable call was made" in "\n".join(_led().render())

    def test_stale_rates_are_named_in_the_report(self):
        """A ceiling computed from unchecked prices does not bound anything."""
        old = (date.today() - timedelta(days=400)).isoformat()
        led = CL.CostLedger(rates={"seat_1": CL.Rate(1.0, 1.0, verified_on=old)})
        led.record("seat_1", 10, 10)
        text = "\n".join(led.render())
        assert "STALE" in text and "seat_1" in text

    def test_a_rate_with_no_verification_date_is_stale(self):
        """Unverified and expired are the same fact: nobody has confirmed the
        number the ceiling is computed from."""
        led = CL.CostLedger(rates={"seat_1": CL.Rate(1.0, 1.0)})
        assert "seat_1" in led.stale_rates()

    def test_stage_spend_is_attributed_to_its_pass(self):
        led = _led()
        led.record("seat_1", 1_000_000, 0, pass_id="p1")
        assert led.stage_spent("p1") == 1.0
        assert led.stage_spent("p2") == 0.0


class TestRatesFromConfig:

    def test_an_unreadable_price_becomes_stale_rather_than_a_wrong_number(self):
        """0.0 makes the rate obviously unusable. A guessed number would price
        a ceiling silently wrong, which is the failure that has no symptom."""
        assert CL._as_float("not a number") == 0.0
        assert CL._as_float(None) == 0.0
        assert CL._as_float(2.5) == 2.5

    def test_underscore_keys_are_comments_not_seats(self):
        """rates.json carries _vendor, _model and _source beside the prices."""
        out = CL.rates_from_config({
            "_note": {"input_per_mtok": 1},
            "seat_1": {"input_per_mtok": 1.0, "output_per_mtok": 2.0,
                       "verified_on": "2026-08-25"}})
        assert "_note" not in out
        assert out["seat_1"].output_per_mtok == 2.0

    def test_a_misnamed_price_field_yields_a_stale_rate_not_a_free_seat(self):
        """A config written to the wrong key names prices the seat at zero,
        and a seat priced at zero can never cross a ceiling. It must surface
        as unverified rather than as a cheap seat."""
        out = CL.rates_from_config({"seat_1": {"input": 5.0, "output": 25.0}})
        assert out["seat_1"].input_per_mtok == 0.0
        led = CL.CostLedger(rates=out)
        assert "seat_1" in led.stale_rates()

    def test_the_real_rates_file_parses_and_is_verified(self):
        """The prices a live run is actually bounded by."""
        with open("rates.json", encoding="utf-8") as fh:
            rates = CL.rates_from_config(json.load(fh))
        assert len(rates) == 5
        led = CL.CostLedger(rates=rates)
        assert led.stale_rates() == [], (
            "a ceiling computed from unverified prices does not bound anything")
        for seat, r in rates.items():
            assert r.input_per_mtok > 0 and r.output_per_mtok > 0, seat
