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

    def test_an_unreadable_day_file_blocks_rather_than_reading_as_zero(
            self, tmp_path):
        """CORRECTED after outside review. This previously asserted that a
        corrupt state file reads as zero spend, on the reasoning that halting
        every run on a corrupted file is worse.

        That is fail-OPEN, and the reasoning was wrong in the direction that
        costs money: a corrupt file is exactly what a crashed or concurrent
        writer leaves behind, so the failure mode is not "one unlucky halt",
        it is "a whole fresh day's budget granted every time the file breaks".
        "I cannot tell what has been spent today" and "nothing has been spent
        today" are opposite facts, and only one of them authorises calls."""
        state = tmp_path / "day.json"
        state.write_text("{ this is not json")
        led = CL.CostLedger(rates={"seat_1": RATE}, per_day=1.0,
                            day_state_path=str(state))
        with pytest.raises(CL.CeilingReached, match="unreadable"):
            led.day_spent()

    def test_a_nonsense_value_for_today_blocks(self, tmp_path):
        state = tmp_path / "day.json"
        state.write_text(json.dumps({date.today().isoformat(): "lots"}))
        led = CL.CostLedger(rates={"seat_1": RATE}, per_day=1.0,
                            day_state_path=str(state))
        with pytest.raises(CL.CeilingReached, match="not a spend figure"):
            led.day_spent()

    def test_a_negative_value_for_today_blocks(self, tmp_path):
        """A negative would subtract from the day's usage and grant extra."""
        state = tmp_path / "day.json"
        state.write_text(json.dumps({date.today().isoformat(): -50.0}))
        led = CL.CostLedger(rates={"seat_1": RATE}, per_day=1.0,
                            day_state_path=str(state))
        with pytest.raises(CL.CeilingReached):
            led.day_spent()

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


# ---------------------------------------------------------------------------
# Codex H2 / H3 / H4 / H5 / H6 / M4 — the ceiling must bind the real call
# ---------------------------------------------------------------------------

import adjudication_orchestrator as AO  # noqa: E402
import seat_adapter as SA  # noqa: E402

LIVE_RATE = CL.Rate(input_per_mtok=2.0, output_per_mtok=6.0,
                    verified_on=date.today().isoformat())


def _profile():
    return SA.ProviderProfile(
        name="v", endpoint="https://api.example.invalid/v1",
        auth_header="authorization", auth_template="Bearer {key}",
        build_body=lambda m, p, mt, t: {"model": m},
        extract_text=lambda p: p.get("text"),
        usage_input_path=["usage", "prompt_tokens"],
        usage_output_path=["usage", "completion_tokens"])


def _ok(payload=None):
    body = json.dumps(payload or {"text": "ok"}).encode()
    return lambda *a, **k: (200, body)


class TestTheCeilingIsComputedFromTheRealCall:

    def test_a_huge_prompt_cannot_pass_a_flat_three_thousand_token_check(self):
        """Codex H2. The precheck assumed 3,000 input tokens regardless of the
        prompt, so a 400,000-character prompt passed a ceiling it would blow
        straight through and booked its real cost only afterwards -- by which
        point the money was spent."""
        led = CL.CostLedger(rates={"seat_1": LIVE_RATE}, per_run=0.01)
        seat = SA.HttpSeat(AO.ResolvedSeat("seat_1", "m", "k"), _profile(),
                           _ok(), ledger=led)
        with pytest.raises(CL.CeilingReached):
            seat("x" * 400_000)
        assert led.spent == 0.0, "the call ran despite crossing the ceiling"

    def test_the_estimate_over_counts_rather_than_under_counts(self):
        """This number exists to refuse a call. An under-estimate is the one
        direction that spends money the operator forbade."""
        prompt = "word " * 1000            # ~1000 tokens by any real tokeniser
        assert CL.estimate_input_tokens(prompt) > 1000

    def test_the_output_bound_allows_for_reasoning_tokens(self):
        """Measured live: max_tokens 4,096, roughly 15,400 billed as output.
        Treating the cap as the worst case under-counted by about 3.8x."""
        assert CL.HIDDEN_OUTPUT_MULTIPLIER >= 3.8

    def test_a_normal_prompt_still_goes_through(self):
        """A bound so conservative that ordinary runs are refused would be
        raised until it stopped binding, which protects nothing."""
        led = CL.CostLedger(rates={"seat_1": LIVE_RATE}, per_run=5.00)
        seat = SA.HttpSeat(AO.ResolvedSeat("seat_1", "m", "k"), _profile(),
                           _ok(), ledger=led)
        assert seat("a normal sized question about build versus buy") == "ok"


class TestEveryDispatchIsCheckedAndBooked:

    def _seat(self, led, transport, attempts=3, pass_id=None):
        return SA.HttpSeat(AO.ResolvedSeat("seat_1", "m", "k"), _profile(),
                           transport, ledger=led,
                           retry=SA.RetryPolicy(max_attempts=attempts),
                           sleeper=lambda _s: None, pass_id=pass_id)

    def test_each_retry_is_checked_against_the_ceiling(self):
        """Codex H3. The check ran once and the loop then dispatched up to
        max_attempts times. Three requests, one ceiling check, and a vendor
        bills each of them."""
        led = CL.CostLedger(rates={"seat_1": LIVE_RATE})
        calls = {"n": 0}

        def flaky(*a, **k):
            calls["n"] += 1
            raise ConnectionResetError("reset")
        with pytest.raises(SA.SeatError):
            self._seat(led, flaky)("prompt")
        assert calls["n"] == 3
        assert len(led.calls) == 3, "failed dispatches were not booked"

    def test_a_failed_attempt_is_recorded_as_unmeasured(self):
        """It still reached the vendor and may still be billed. Recording
        nothing made the run report 'no billable call was made'."""
        led = CL.CostLedger(rates={"seat_1": LIVE_RATE})
        with pytest.raises(SA.SeatError):
            self._seat(led, lambda *a, **k: (_ for _ in ()).throw(
                ConnectionResetError("x")))("prompt")
        assert led.unmeasured_calls == 3
        assert "LOWER BOUND" in "\n".join(led.render())

    def test_a_timed_out_call_is_not_invisible(self):
        led = CL.CostLedger(rates={"seat_1": LIVE_RATE})
        with pytest.raises(SA.SeatError):
            self._seat(led, lambda *a, **k: (_ for _ in ()).throw(
                TimeoutError("timed out")), attempts=1)("prompt")
        assert len(led.calls) == 1
        assert "no billable call was made" not in "\n".join(led.render())

    def test_a_per_stage_ceiling_binds_a_live_seat_call(self):
        """Codex H6. HttpSeat supplied no pass_id, so every live call recorded
        pass_id=None, stage spend stayed at zero, and a configured per-stage
        limit could never be reached however much was spent."""
        led = CL.CostLedger(rates={"seat_1": LIVE_RATE}, per_stage=0.0001)
        with pytest.raises(CL.CeilingReached, match=r"per-stage \(r1\)"):
            self._seat(led, _ok(), pass_id="r1")("prompt")

    def test_a_successful_call_is_attributed_to_its_stage(self):
        led = CL.CostLedger(rates={"seat_1": LIVE_RATE}, per_run=10.0)
        payload = {"text": "ok", "usage": {"prompt_tokens": 1000,
                                           "completion_tokens": 500}}
        self._seat(led, _ok(payload), pass_id="r2")("prompt")
        assert led.stage_spent("r2") > 0


class TestUsageFiguresMustBeRealCounts:

    P = (["usage", "prompt_tokens"], ["usage", "completion_tokens"])

    def _usage(self, **kw):
        return CL.usage_from_payload({"usage": kw}, *self.P)

    def test_a_boolean_is_not_a_token_count(self):
        """Codex M4. bool subclasses int, so `true` was read as 1 token and
        the call was marked MEASURED."""
        assert self._usage(prompt_tokens=True, completion_tokens=5) == (None, 5)

    def test_a_negative_count_is_refused(self):
        """It produced negative spend, which subtracts from the ceiling."""
        assert self._usage(prompt_tokens=-10, completion_tokens=5) == (None, 5)

    def test_a_fractional_count_is_refused_not_truncated(self):
        assert self._usage(prompt_tokens=12.9, completion_tokens=5) == (None, 5)

    def test_a_whole_float_is_accepted(self):
        """Some vendors emit 1200.0. That is a real count."""
        assert self._usage(prompt_tokens=1200.0, completion_tokens=5) == (1200, 5)

    def test_a_total_that_contradicts_its_parts_is_unmeasured(self):
        """We cannot tell which figure is wrong, so we report none of them --
        an unmeasured call makes the total an explicit lower bound, which is
        honest, where a number reconciled from contradictory inputs is not."""
        assert CL.usage_from_payload(
            {"usage": {"prompt_tokens": 100, "completion_tokens": 50,
                       "total_tokens": 10}}, *self.P) == (None, None)


class TestRatesAndCeilingsMustBeUsable:

    def test_a_malformed_price_loses_its_verification_date(self):
        """Codex H5. A bad price became 0.0 and KEPT its verified_on, so
        stale_rates() reported nothing wrong while the seat it priced could
        never cross a ceiling."""
        rates = CL.rates_from_config({"seat_1": {
            "input_per_mtok": "two dollars", "output_per_mtok": 6.0,
            "verified_on": date.today().isoformat()}})
        assert rates["seat_1"].verified_on is None
        assert "seat_1" in CL.CostLedger(rates=rates).stale_rates()

    def test_a_zero_price_is_reported_stale_however_fresh(self):
        """A zero price means every call is free and the ceiling is
        decorative."""
        rates = {"seat_1": CL.Rate(0.0, 0.0, verified_on=date.today().isoformat())}
        assert "seat_1" in CL.CostLedger(rates=rates).stale_rates()

    def test_a_boolean_price_is_refused(self):
        rates = CL.rates_from_config({"seat_1": {
            "input_per_mtok": True, "output_per_mtok": 6.0,
            "verified_on": date.today().isoformat()}})
        assert rates["seat_1"].verified_on is None

    def test_a_nonfinite_price_is_refused(self):
        assert CL._finite_positive(float("nan")) is None
        assert CL._finite_positive(float("inf")) is None
        assert CL._finite_positive(-1.0) is None
        assert CL._finite_positive(0.0) is None
        assert CL._finite_positive(2.5) == 2.5


class TestConcurrentDayStateWriters:

    def test_two_writers_do_not_clobber_each_other(self, tmp_path):
        """Codex H4. Both shared '<path>.tmp': one os.replace moved the file
        out from under the other, which raised FileNotFoundError, and one
        day's spend was lost -- silently raising the next run's budget."""
        state = str(tmp_path / "day.json")
        a = CL.CostLedger(rates={"seat_1": LIVE_RATE}, day_state_path=state)
        b = CL.CostLedger(rates={"seat_1": LIVE_RATE}, day_state_path=state)
        a.record("seat_1", 1_000_000, 0)
        b.record("seat_1", 1_000_000, 0)
        a.persist_day()
        b.persist_day()
        with open(state) as fh:
            assert json.load(fh)[date.today().isoformat()] == 4.0

    def test_no_temporary_file_is_left_behind(self, tmp_path):
        state = str(tmp_path / "day.json")
        led = CL.CostLedger(rates={"seat_1": LIVE_RATE}, day_state_path=state)
        led.record("seat_1", 1000, 1000)
        led.persist_day()
        assert [f for f in os.listdir(tmp_path) if f.endswith(".tmp")] == []
