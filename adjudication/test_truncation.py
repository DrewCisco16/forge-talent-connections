"""A reply the output cap cut short is a THIRD case, not a silent seat.

Three facts about a seat look alike on the page and are opposite in meaning.
A seat that FAILED was never reached. A seat that DECLARED NOTHING read the
contract and chose not to write it. A seat CUT OFF AT THE CAP was reached, was
writing, and lost its tail -- and the contract puts every line that matters at
the end. Measured live: claude-opus-5 returned 246 characters at a 4,096-token
cap with stop reason 'max_tokens', was scored as "nothing usable", and the
probe's verdict recommended abandoning the text contract for a structured-
output rewrite. The contract was fine. The cap was small.
"""
from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from datetime import date

import adjudication_orchestrator as AO
import cost_ledger as CL
import night_loop as NL
import seat_adapter as SA


def _profile():
    return SA.ProviderProfile(
        name="v", endpoint="https://a.invalid/v1",
        auth_header="authorization", auth_template="Bearer {key}",
        build_body=lambda m, p, mt, t: {"model": m},
        extract_text=lambda p: p.get("text"))


def _seat(payload):
    led = CL.CostLedger(
        rates={"seat_1": CL.Rate(2.0, 6.0, verified_on=date.today().isoformat(),
                                 output_multiplier=2.0)},
        per_run=1000.0)
    body = json.dumps(payload).encode()
    return SA.HttpSeat(AO.ResolvedSeat("seat_1", "m", "k"), _profile(),
                       lambda *a, **k: (200, body), ledger=led, max_tokens=1000)


class TestTheAdapterRecordsTheCut:

    def test_partial_text_at_the_cap_is_returned_and_flagged(self):
        seat = _seat({"text": "## What I'm standing on\n\nPer-round cost is",
                      "stop_reason": "max_tokens"})
        assert seat("q").startswith("## What I'm standing on")
        assert seat.last_truncated is True
        assert seat.last_stop_reason == "max_tokens"

    def test_a_complete_reply_is_not_flagged(self):
        seat = _seat({"text": "done", "stop_reason": "end_turn"})
        assert seat("q") == "done"
        assert seat.last_truncated is False

    def test_the_openai_shape_is_read_too(self):
        seat = _seat({"text": "partial",
                      "choices": [{"finish_reason": "length"}]})
        seat("q")
        assert seat.last_truncated is True

    def test_the_flag_is_one_reply_deep(self):
        """It must describe the LAST reply only, or one cut reply marks a seat
        truncated for the rest of the run."""
        replies = iter([
            json.dumps({"text": "partial", "stop_reason": "max_tokens"}).encode(),
            json.dumps({"text": "whole", "stop_reason": "end_turn"}).encode(),
        ])
        led = CL.CostLedger(
            rates={"seat_1": CL.Rate(2.0, 6.0, verified_on=date.today().isoformat(),
                                     output_multiplier=2.0)},
            per_run=1000.0)
        seat = SA.HttpSeat(AO.ResolvedSeat("seat_1", "m", "k"), _profile(),
                           lambda *a, **k: (200, next(replies)),
                           ledger=led, max_tokens=1000)
        assert seat("q") == "partial" and seat.last_truncated is True
        assert seat("q") == "whole" and seat.last_truncated is False


class _Cut:
    """A seat whose reply came back short of its contract lines."""
    max_tokens = 4096
    last_stop_reason = "max_tokens"
    last_truncated = True

    def __call__(self, prompt):
        return "## What I'm standing on\n\nPer-round cost is 6 API calls and"


class TestTheNightLoopTellsTheCasesApart:

    OPTION = ("OPTION | run all five rounds\n"
              "PREDICATE | total api calls | = | 30 calls\n"
              "FORMULA | rounds * per_round\n"
              "INPUT | rounds = 5\nINPUT | per_round = 6\n")

    def _panel(self):
        full = {f"seat_{i}": (lambda p: self.OPTION) for i in (1, 2, 4, 5)}
        full["seat_3"] = _Cut()
        return full

    def _run(self, tmp_path):
        return NL.run_night("ask", self._panel(), lambda p: "merged",
                            AO.Orchestrator([AO.ArithmeticGate()]),
                            str(tmp_path), rounds=NL.ROUNDS[:1])

    def test_a_cut_seat_is_recorded_as_cut(self, tmp_path):
        res = self._run(tmp_path)
        assert "seat_3" in res[0].thinkers_truncated
        assert "4096" in res[0].thinkers_truncated["seat_3"]
        assert "seat_3" in res[0].thinkers_ok, "it DID reply; it is not failed"

    def test_a_cut_seat_is_not_reported_silent(self, tmp_path):
        """Its OPTION line is in the part of the reply the cap removed."""
        res = self._run(tmp_path)
        assert "seat_3" not in res[0].silent_seats

    def test_the_verdict_carries_the_cut_as_a_caveat(self, tmp_path):
        v = NL.assess(self._run(tmp_path))
        assert any("CUT OFF BY THE OUTPUT CAP" in c for c in v.caveats)
        assert any("seat_3" in c for c in v.caveats)

    def test_the_cut_is_durable_in_status(self, tmp_path):
        self._run(tmp_path)
        blob = (tmp_path / "status.md").read_text().split("```json")[1].split("```")[0]
        assert json.loads(blob)[0]["thinkers_truncated"] == {
            "seat_3": json.loads(blob)[0]["thinkers_truncated"]["seat_3"]}
        assert "cut off" in json.loads(blob)[0]["thinkers_truncated"]["seat_3"]


class TestTheProbeDoesNotMistakeACapForAContractFailure:

    FULL = ("OPTION | run all five rounds\n"
            "PREDICATE | total api calls | = | 30 calls\n"
            "FORMULA | rounds * per_round\n"
            "INPUT | rounds = 5\nINPUT | per_round = 6\n"
            "CLAIM | arithmetic | 5 * 6 = 30 | thirty calls\n")

    def _report(self, truncated, here):
        import compliance_probe as CP
        replies = {f"seat_{i}": self.FULL for i in (1, 2, 3, 4)}
        replies["seat_5"] = "## What I'm standing on\n\nPer-round cost is"
        buf = io.StringIO()
        with redirect_stdout(buf):
            CP._report(replies, {}, here, truncated)
        # WHITESPACE-NORMALISED, because the verdict is WRAPPED prose. The
        # phrase "Structured output would make it uniform" prints as
        # "Structured\n  output would ...", so an exact substring never
        # matched -- and the NEGATIVE assertion in the cap test passed
        # vacuously for the same reason. A test that cannot fail is not one.
        return " ".join(buf.getvalue().split())

    def test_a_cut_seat_is_listed_as_cut_not_unusable(self, tmp_path):
        out = self._report({"seat_5": "cut off at the 4096-token cap"},
                           str(tmp_path))
        assert "cut off at cap: seat_5" in out
        assert "nothing usable: seat_5" not in out

    def test_the_verdict_names_the_cap_not_the_contract(self, tmp_path):
        """THE FALSE MEASUREMENT THIS PREVENTS. The old verdict on this exact
        input recommended a structured-output rewrite."""
        out = self._report({"seat_5": "cut off at the 4096-token cap"},
                           str(tmp_path))
        assert "cap to raise, not a contract to abandon" in out
        assert "Structured output would make it uniform" not in out

    def test_a_genuinely_silent_seat_still_reads_as_silent(self, tmp_path):
        """The fix must not launder real silence as a cap problem."""
        out = self._report({}, str(tmp_path))
        assert "nothing usable: seat_5" in out
        assert "Structured output would make it uniform" in out
