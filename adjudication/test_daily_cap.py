"""The daily ceiling: one shared limit across every tool that spends.

WHAT THIS CLOSES. A per-run ceiling bounds ONE command. Nothing bounded a DAY,
because each entry point built its own ledger with no day state -- each for a
locally defensible reason: a probe should not eat the panel's budget, a
calibration measurement is not an adjudication. Every one of those reasons was
about how to ALLOCATE a budget, and the operator's exposure is the TOTAL. Six
tools each correctly declining to count themselves added up to nothing being
counted, so a run refused at $17 could be restarted immediately, and again,
and no limit anywhere would notice.

The failure mode worth stopping is not one expensive call. It is the same
expensive thing started again because the first looked wrong.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date

import pytest

import cost_ledger as CL

ENTRY_POINTS = ("one_model.py", "stage_zero.py", "full_run.py",
                "accuracy.py", "canary_run.py", "compliance_probe.py")


def _rates():
    return {"seat_1": CL.Rate(4.0, 20.0,
                              verified_on=date.today().isoformat())}


class TestTheCeilingIsOnByDefault:

    def test_a_ledger_built_the_normal_way_has_a_daily_limit(self, monkeypatch):
        """THE WHOLE POINT. Every tool previously defaulted to per_day=None,
        which is no daily limit at all. A ceiling nobody sets is a ceiling
        nobody has."""
        monkeypatch.delenv("ADJUDICATION_DAY_CEILING", raising=False)
        led = CL.operator_ledger(_rates(), per_run=1.0)
        assert led.per_day is not None
        assert led.per_day == CL.DEFAULT_DAY_CEILING

    def test_it_counts_against_a_shared_file(self, monkeypatch):
        """Separate files per tool would be six caps of $25 rather than one."""
        monkeypatch.delenv("ADJUDICATION_DAY_STATE", raising=False)
        led = CL.operator_ledger(_rates(), per_run=1.0)
        assert led.day_state_path == CL.DEFAULT_DAY_STATE

    def test_the_default_admits_one_full_panel_run_and_refuses_two(self):
        """Grounded rather than round: the five-round panel plans at $16.82.
        One fits with room for the cheap instruments; a second does not."""
        assert CL.DEFAULT_DAY_CEILING > 16.82
        assert CL.DEFAULT_DAY_CEILING < 2 * 16.82

    def test_the_ceiling_can_be_raised_deliberately(self, monkeypatch):
        monkeypatch.setenv("ADJUDICATION_DAY_CEILING", "60")
        assert CL.operator_ledger(_rates(), per_run=1.0).per_day == 60.0

    def test_the_state_file_can_be_redirected(self, monkeypatch, tmp_path):
        """How a test run is kept off the operator's real ledger -- a defect
        this project has already had once, at a fabricated $117.53."""
        target = str(tmp_path / "day.json")
        monkeypatch.setenv("ADJUDICATION_DAY_STATE", target)
        assert CL.operator_ledger(_rates(), per_run=1.0).day_state_path == target


class TestEverySpendingToolUsesIt:

    @pytest.mark.parametrize("name", ENTRY_POINTS)
    def test_the_entry_point_builds_the_shared_ledger(self, name):
        """Read from the source, because the failure this prevents is a NEW
        tool quietly constructing CostLedger directly and being invisible to
        the day -- which is exactly how all six got here."""
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, name), encoding="utf-8") as fh:
            src = fh.read()
        assert "operator_ledger" in src, f"{name} does not use the shared ledger"
        assert not re.search(r"CostLedger\(rates=", src), (
            f"{name} builds a CostLedger directly, so it escapes the daily cap")


class TestItActuallyRefuses:

    def test_a_day_already_at_the_ceiling_refuses_the_next_call(self, tmp_path):
        """The behaviour, not the configuration."""
        state = tmp_path / "day.json"
        state.write_text(json.dumps({date.today().isoformat(): 24.90}))
        led = CL.operator_ledger(_rates(), per_run=100.0, per_day=25.0,
                                 day_state_path=str(state))
        with pytest.raises(CL.CeilingReached) as exc:
            led.check_before_call("seat_1", 1000, 20000)
        assert "per-day" in str(exc.value)

    def test_a_day_with_room_is_allowed(self, tmp_path):
        state = tmp_path / "day.json"
        state.write_text(json.dumps({date.today().isoformat(): 1.00}))
        led = CL.operator_ledger(_rates(), per_run=100.0, per_day=25.0,
                                 day_state_path=str(state))
        led.check_before_call("seat_1", 1000, 2000)   # must not raise

    def test_yesterdays_spend_does_not_count_against_today(self, tmp_path):
        """A cap that never resets would refuse everything a day later."""
        state = tmp_path / "day.json"
        state.write_text(json.dumps({"2020-01-01": 999.0}))
        led = CL.operator_ledger(_rates(), per_run=100.0, per_day=25.0,
                                 day_state_path=str(state))
        led.check_before_call("seat_1", 1000, 2000)   # must not raise

    def test_an_unreadable_day_file_refuses_rather_than_assuming_zero(
            self, tmp_path):
        """FAIL CLOSED. Treating an unreadable ledger as $0 spent would make
        corrupting the file the way to remove the limit."""
        state = tmp_path / "day.json"
        state.write_text("{ this is not json")
        led = CL.operator_ledger(_rates(), per_run=100.0, per_day=25.0,
                                 day_state_path=str(state))
        with pytest.raises(CL.CeilingReached):
            led.check_before_call("seat_1", 1000, 2000)


class TestTheOperatorIsToldTheLimit:

    @pytest.mark.parametrize("name", ("one_model.py", "stage_zero.py",
                                      "full_run.py"))
    def test_the_run_prints_the_daily_ceiling_before_spending(self, name):
        """A limit that only appears when it fires is a surprise. These are the
        three an operator starts by hand."""
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, name), encoding="utf-8") as fh:
            src = fh.read()
        assert "daily ceiling" in src, f"{name} never states the daily limit"


# ---------------------------------------------------------------------------
# the price has to be for the model actually called
# ---------------------------------------------------------------------------

class TestTheCeilingIsComputedFromTheRightModelsPrice:
    """Every limit here comes from rates.json; the seats call whatever the
    environment names. Nothing compared the two, so a seat pointed at a
    different model spent against the OLD model's price with the ceiling
    enforced to four decimal places on a number that did not apply. Same
    defect `stale_rates` and `is_priced_for` already refuse in their own
    dimensions, through the one door left open."""

    CFG = {"seat_1": {"_model": "gpt-5.6-sol", "input_per_mtok": 4.0,
                      "output_per_mtok": 20.0}}

    def test_a_matching_model_is_allowed(self):
        CL.check_models_are_priced({"seat_1": ("OpenAI", "gpt-5.6-sol")},
                                   self.CFG)

    def test_a_different_model_is_refused(self):
        with pytest.raises(CL.ModelNotPriced) as exc:
            CL.check_models_are_priced({"seat_1": ("OpenAI", "gpt-6-turbo")},
                                       self.CFG)
        assert "gpt-6-turbo" in str(exc.value)
        assert "gpt-5.6-sol" in str(exc.value), "it must name BOTH ids"

    def test_the_refusal_says_how_to_fix_it(self):
        """A refusal an operator cannot act on is an outage."""
        with pytest.raises(CL.ModelNotPriced) as exc:
            CL.check_models_are_priced({"seat_1": ("OpenAI", "other")}, self.CFG)
        assert "rates.json" in str(exc.value)
        assert "verified_on" in str(exc.value)

    def test_it_is_a_ceiling_error_so_existing_handlers_catch_it(self):
        """Every caller that stops cleanly on cost catches CeilingReached. A
        sibling class would fall to the generic handler and be written out as
        a crash rather than a refusal -- a mistake this project already made
        once with CeilingOverrun."""
        assert issubclass(CL.ModelNotPriced, CL.CeilingReached)

    def test_a_seat_with_no_priced_model_recorded_is_not_refused(self):
        """Absence of a _model note is not a mismatch. Refusing on it would
        break every rates entry that predates the note."""
        CL.check_models_are_priced({"seat_1": ("OpenAI", "anything")},
                                   {"seat_1": {"input_per_mtok": 4.0}})

    def test_the_shipped_rates_match_a_panel_built_from_them(self):
        """The real file, against itself: whatever rates.json prices must be
        what a panel described by those same ids would call."""
        import json as _json
        import os as _os
        here = _os.path.dirname(_os.path.abspath(__file__))
        with open(_os.path.join(here, "rates.json"), encoding="utf-8") as fh:
            cfg = _json.load(fh)
        identity = {s: (str(c.get("_vendor")), str(c.get("_model")))
                    for s, c in cfg.items()
                    if not s.startswith("_") and isinstance(c, dict)}
        CL.check_models_are_priced(identity, cfg)

    def test_a_live_run_checks_it_before_spending(self):
        """Read from the source: the check is worthless if nothing calls it."""
        import inspect

        import night_loop
        src = inspect.getsource(night_loop.live_night)
        assert "check_models_are_priced" in src
        assert src.index("check_models_are_priced(identity") < src.index(
            "live_seats("), "it must refuse BEFORE the panel is built"
