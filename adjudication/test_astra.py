"""
test_astra.py -- failure modes found by the Night Agent's outside reviewer,
tested against Adjudication Five.

The reviewer's eighteen findings were about the Night Agent's own design.
Six of the failure modes transfer, and each was CONFIRMED here by probe before
it was fixed. The finding id is kept on each test so the two records match.
"""
from __future__ import annotations

import json
import typing

import pytest

import calibrate as CB
import convergence as CV
from adjudication_orchestrator import (
    Claim,
    ClaimKind,
    Pass,
    SeatResponse,
    classify_source,
    measure_divergence,
)
from night_loop import RoundResult
from predicate import Ruling


def _claim(i, kind="arithmetic"):
    return Claim(id=f"c{i}", text=f"t{i}", kind=kind, warrant=f"{i} + {i} = {2 * i}",
                 source_pass="p1", source_seat="s")


class TestAstra09_ARefutedClaimAgainstASurvivorIsAHole:
    """assess() printed the caveat and set trustworthy False; analyse(), which
    owns the EXIT CODE, never saw it. With yields decaying and the alarm armed
    a run carrying a refuted claim about its one survivor exited 0. A script
    keyed on the exit code would have committed."""

    def _rounds(self, refuted_in=3):
        rs = []
        for n in range(1, 6):
            r = RoundResult(n, f"r{n}", eliminative=(n < 5))
            r.options_observed = True
            r.options_created = 3 if n == 1 else 0
            r.options_removed = ["opt_b", "opt_c"] if n == 1 else []
            r.options_alive = ["opt_a"]
            r.options_unexamined = []
            r.thinkers_ok = [f"seat_{i}" for i in range(1, 6)]
            r.passed, r.escalated, r.blocked, r.rho = 4, 0, 0, 0.1
            r.failed = 1 if n == refuted_in else 0
            fails = [9, 3, 1, 0, 0][n - 1]
            r.rulings = {f"pred_{n}_{k}": Ruling(f"pred_{n}_{k}", "fail", "x")
                         for k in range(fails)}
            rs.append(r)
        return rs

    def test_the_exit_code_stays_non_zero(self):
        c = CV.analyse(self._rounds(), escalations_pending=0,
                       singleton_alarm=0.9, tolerance=0.5)
        assert c.exit_code == 1
        assert any(h.kind == "refuted claim stands against a survivor" for h in c.holes)

    def test_the_hole_names_the_round_and_a_remedy(self):
        c = CV.analyse(self._rounds(refuted_in=4), escalations_pending=0,
                       singleton_alarm=0.9, tolerance=0.5)
        h = next(h for h in c.holes if h.kind.startswith("refuted claim"))
        assert "round(s) 4" in h.detail
        assert h.remedy.strip()

    def test_the_same_run_without_the_refutation_exits_zero(self):
        """The control: the hole is the refutation, not the shape of the run."""
        c = CV.analyse(self._rounds(refuted_in=99), escalations_pending=0,
                       singleton_alarm=0.9, tolerance=0.5)
        assert c.exit_code == 0
        assert not any(h.kind.startswith("refuted claim") for h in c.holes)

    def test_a_refutation_that_removed_an_option_is_not_a_hole(self):
        """A FAILED claim that killed its option is the mechanism working."""
        rs = self._rounds(refuted_in=1)   # round 1 also removed two options
        c = CV.analyse(rs, escalations_pending=0, singleton_alarm=0.9, tolerance=0.5)
        assert not any(h.kind.startswith("refuted claim") for h in c.holes)


class TestAstra02_PaddingDoesNotBuyIndependence:
    """Ten shared claims plus twenty irrelevant additions took mean Jaccard
    from 1.0 to 0.556 and switched the collapse warning off, without one seat
    challenging anything. Both divergence measures had the hole."""

    shared: typing.ClassVar[list] = [_claim(i) for i in range(1, 11)]

    def test_convergence_flags_nested_sets(self):
        j, unanimous, _silent, warn = CV.divergence({
            "a": self.shared, "b": list(self.shared),
            "c": list(self.shared) + [_claim(100 + i) for i in range(20)]})
        assert j < 0.6 and not unanimous
        assert warn is None                      # collapse still means unanimity
        nest = CV.nesting_warning({
            "a": self.shared, "b": list(self.shared),
            "c": list(self.shared) + [_claim(100 + i) for i in range(20)]})
        assert nest and "NEST" in nest

    def test_a_silent_seat_is_not_a_nested_set(self):
        """The empty set is inside every set. One seat that said nothing next
        to one that spoke is silence (SOP 6.5), not padding -- the first
        version of this fix flagged it, and an existing test caught that."""
        assert CV.nesting_warning({"a": [], "b": self.shared}) is None
        assert not CV.nested([frozenset(), frozenset({1})])

    def test_convergence_still_reports_identical_sets_as_unanimity(self):
        _, unanimous, _, warn = CV.divergence({"a": self.shared, "b": list(self.shared)})
        assert unanimous and "IDENTICAL" in warn

    def test_genuinely_different_sets_are_not_flagged(self):
        """The negative control. Disagreement must still read as disagreement."""
        _, _, _, warn = CV.divergence({"a": self.shared,
                                       "b": [_claim(50 + i) for i in range(10)]})
        assert warn is None

    def test_partial_overlap_is_not_nesting(self):
        a = self.shared
        b = list(self.shared[:5]) + [_claim(200 + i) for i in range(5)]
        assert CV.nested([frozenset((c.kind, c.warrant) for c in a),
                          frozenset((c.kind, c.warrant) for c in b)]) is False

    def test_the_orchestrators_measure_flags_it_too(self):
        p = Pass("p1", "probe", "instr", True)
        kinds = ClaimKind("arithmetic")
        def resp(seat, claims):
            return SeatResponse(seat_id=seat, pass_id="p1",
                                claims=[Claim(id=c.id, text=c.text, kind=kinds, warrant=c.warrant,
                                              source_pass="p1", source_seat=seat) for c in claims],
                                raw="", error=None)
        d = measure_divergence(p, [resp("a", self.shared), resp("b", self.shared),
                                   resp("c", self.shared + [_claim(300 + i) for i in range(20)])])
        assert not d.unanimous
        assert d.collapse_warning is None
        assert d.nesting_warning and "NEST" in d.nesting_warning


class TestAstra15_ADoiIsADoiHoweverItIsWritten:
    """Every form a model actually writes a DOI in was INADMISSIBLE, because
    the pattern anchored on the bare '10.' prefix. Real dissertation citations
    were being refused for their punctuation."""

    @pytest.mark.parametrize("form", [
        "10.1038/s41586-020-2649-2",
        "doi:10.1038/s41586-020-2649-2",
        "DOI: 10.1038/s41586-020-2649-2",
        "https://doi.org/10.1038/s41586-020-2649-2",
        "http://dx.doi.org/10.1038/s41586-020-2649-2",
    ])
    def test_every_form_is_peer_reviewed(self, form):
        assert classify_source(form).value == "peer_reviewed"

    def test_a_data_repository_doi_is_still_data(self):
        assert classify_source("https://doi.org/10.5281/zenodo.1234567").value == "empirical_data"

    def test_a_prefix_alone_does_not_launder_a_blog(self):
        """The negative control. Stripping the prefix must not make anything
        after it admissible by itself."""
        assert classify_source("doi: https://medium.com/@x/y").value == "inadmissible"
        assert classify_source("https://doi.org/").value == "inadmissible"


def _transcript(tmp_path, n=12, seed=4):
    items = CB.build_items(n, seed=seed)
    captured: dict[str, dict[str, str]] = {}
    seats = CB.recording_seats(CB._demo_seats(items), captured)
    CB.run_calibration(seats, items)
    path = tmp_path / "t.json"
    CB.write_transcript(str(path), items=items, seed=seed, replies=captured)
    return str(path), sorted(seats)


class TestAstra12_AReScoreIsNotASecondObservation:
    """The same replies scored twice are one measurement. A re-score report
    that could not be told from a fresh paid run would be counted twice."""

    def test_the_render_says_so_at_the_top(self, tmp_path, capsys):
        path, _ = _transcript(tmp_path)
        CB.main(["--rescore", path])
        out = capsys.readouterr().out
        head = out.splitlines()[:6]
        assert any("RE-SCORE of" in ln for ln in head)
        assert any("NOT a new observation" in ln for ln in head)

    def test_the_json_carries_provenance(self, tmp_path, capsys):
        path, _ = _transcript(tmp_path)
        jp = tmp_path / "out.json"
        CB.main(["--rescore", path, "--json", str(jp)])
        capsys.readouterr()
        payload = json.loads(jp.read_text())
        assert payload["rescored_from"] == path
        assert payload["new_observation"] is False

    def test_a_demo_run_is_a_new_observation(self, tmp_path, capsys):
        jp = tmp_path / "demo.json"
        CB.main(["--demo", "--n-items", "12", "--json", str(jp)])
        out = capsys.readouterr().out
        assert "RE-SCORE" not in out
        payload = json.loads(jp.read_text())
        assert payload["rescored_from"] is None and payload["new_observation"] is True


class TestAstra10_CuttingSeatsIsMeasuredOnTheSameReplies:
    """SOP 6.7: cut seats, never passes. What the cut seats added is the
    difference between two rows scored from one transcript, free."""

    def test_the_subset_and_the_full_panel_are_printed_side_by_side(self, tmp_path, capsys):
        path, seats = _transcript(tmp_path)
        keep = ",".join(seats[:3])
        rc = CB.main(["--rescore", path, "--seats", keep])
        out = capsys.readouterr().out
        assert rc in (0, 1)
        assert "SEAT CUT" in out
        assert "full panel" in out and "retained" in out
        assert f"seats={len(seats)}" in out and "seats=3" in out
        assert f"cut: {', '.join(seats[3:])}" in out

    def test_json_records_which_seats_were_retained(self, tmp_path, capsys):
        path, seats = _transcript(tmp_path)
        jp = tmp_path / "sub.json"
        CB.main(["--rescore", path, "--seats", ",".join(seats[:2]), "--json", str(jp)])
        capsys.readouterr()
        assert json.loads(jp.read_text())["seats_retained"] == seats[:2]

    def test_an_unknown_seat_refuses_without_scoring(self, tmp_path, capsys):
        path, _ = _transcript(tmp_path)
        assert CB.main(["--rescore", path, "--seats", "seat_9"]) == 2
        assert "not in the transcript" in capsys.readouterr().err

    def test_a_subset_of_a_live_panel_is_refused(self, capsys):
        """Cutting seats from a LIVE run would spend money to measure fewer
        seats than were paid for. Record the full run; re-score for free."""
        assert CB.main(["--demo", "--seats", "seat_1"]) == 2
        assert "only applies to --rescore" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# ASTRA-16: no per-round budget reserve
# ---------------------------------------------------------------------------

_OPTION_REPLY = ("OPTION | an answer worth considering\n"
                 "\nCLAIM | arithmetic | 2 + 2 = 4 | it adds up")
"""A round one that declares no option stops the run on purpose, so the
stub seats must declare one for a second round to exist at all."""


def _spend_until_short(led, label, need, limit=1_000):
    """Book measured calls until less than `need` is left under `label`.

    BOUNDED. An unbounded loop here hung for ever on a room() that ignored
    spend -- the mutant was caught by a timeout rather than a failure."""
    for _ in range(limit):
        if led.room()[label] <= need:
            return
        led.record("seat_1", 200_000, 50_000)
    raise AssertionError(f"room()[{label!r}] never fell below {need}: "
                         f"spend is not being counted")


class TestAstra16:
    """The plan checked the run once and the ledger checked one call at a
    time. Nothing asked, at the top of a round, whether the whole round
    still fit. CONFIRMED by probe: a ledger with room for five calls and not
    six dispatched the thinkers and refused the merge."""

    @staticmethod
    def _rates():
        import os

        import cost_ledger as CL
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "rates.json"), encoding="utf-8") as fh:
            return CL.rates_from_config(json.load(fh))

    @staticmethod
    def _caps():
        return {f"seat_{i}": 4096 for i in range(1, 6)}

    def test_the_hook_runs_before_any_seat_in_the_round(self, tmp_path):
        import night_loop as NL
        from adjudication_orchestrator import ArithmeticGate, Orchestrator
        order: list[str] = []

        def seat(_p):
            order.append("seat")
            return _OPTION_REPLY
        panel = {f"seat_{i}": seat for i in range(1, 6)}
        seen: list[int] = []

        def before(n):
            seen.append(n)
            order.append(f"before-{n}")
        NL.run_night("ask", panel, lambda p: "merged",
                     Orchestrator([ArithmeticGate()]), str(tmp_path),
                     rounds=NL.ROUNDS[:2], before_round=before)
        assert seen == [1, 2]
        # Round 1's hook precedes every seat call of round 1; round 2's hook
        # precedes every seat call of round 2.
        assert order.index("before-1") < order.index("seat")
        second_round_first_seat = [i for i, o in enumerate(order)
                                   if o == "seat"][5]
        assert order.index("before-2") < second_round_first_seat

    def test_a_refused_round_dispatches_nothing_and_keeps_the_earlier_rounds(
            self, tmp_path):
        import night_loop as NL
        from adjudication_orchestrator import ArithmeticGate, Orchestrator
        calls: list[int] = []

        def seat(_p):
            calls.append(1)
            return _OPTION_REPLY
        panel = {f"seat_{i}": seat for i in range(1, 6)}

        def before(n):
            if n == 2:
                raise NL.RunTooExpensive("round 2 is estimated at $9.00 and "
                                         "only $1.00 remains")
        with pytest.raises(NL.RunTooExpensive):
            NL.run_night("ask", panel, lambda p: "merged",
                         Orchestrator([ArithmeticGate()]), str(tmp_path),
                         rounds=NL.ROUNDS[:3], before_round=before)
        assert len(calls) == 5            # round 1's thinkers, nothing more
        assert (tmp_path / "round-1" / "thinker-seat_1.md").exists()
        assert not (tmp_path / "round-2" / "thinker-seat_1.md").exists()
        note = (tmp_path / "round-2" / "NOT-STARTED.md").read_text()
        assert "$9.00" in note and "No seat was called" in note
        status = (tmp_path / "status.md").read_text()
        assert '"round": 1' in status and '"round": 2' not in status

    def test_the_reserve_refuses_when_the_run_ceiling_is_short(self):
        import cost_ledger as CL
        import night_loop as NL
        led = CL.CostLedger(rates=self._rates(), per_run=10.0)
        caps = self._caps()
        one_round = CL.plan_run(led, caps, rounds=1).estimate
        check = NL.round_reserve(led, caps)
        check(1)                                   # nothing spent: fits
        # Spend until less than one round is left, by booking measured calls.
        _spend_until_short(led, "per-run", one_round)
        with pytest.raises(NL.RoundUnfunded) as exc:
            check(4)
        msg = str(exc.value)
        assert "round 4" in msg and "per-run" in msg
        assert f"${one_round:.2f}" in msg
        # A CeilingReached, so the watcher and the console file it as PARTIAL
        # with the rounds already run kept -- not as "refused, nothing spent".
        assert isinstance(exc.value, CL.CeilingReached)
        assert exc.value.round == 4

    def test_the_reserve_refuses_on_the_day_ceiling_too(self, tmp_path):
        """The day ceiling is shared with other watchers, so it can be drawn
        down by a process this run never sees."""
        import cost_ledger as CL
        import night_loop as NL
        led = CL.CostLedger(rates=self._rates(), per_run=50.0, per_day=10.0)
        caps = self._caps()
        one_round = CL.plan_run(led, caps, rounds=1).estimate
        check = NL.round_reserve(led, caps)
        check(1)
        _spend_until_short(led, "per-day", one_round)
        assert led.room()["per-run"] > one_round   # the run ceiling is fine
        with pytest.raises(NL.RoundUnfunded) as exc:
            check(3)
        assert "per-day" in str(exc.value)

    def test_room_matches_what_the_pre_call_check_would_allow(self):
        """room() is only useful if it agrees with check_before_call."""
        import cost_ledger as CL
        led = CL.CostLedger(rates=self._rates(), per_run=1.0)
        led.record("seat_1", 100_000, 10_000)
        left = led.room()["per-run"]
        assert 0 < left < 1.0
        assert left == pytest.approx(1.0 - led.committed)


# ---------------------------------------------------------------------------
# ASTRA-04: the audit chain was written and never verified by any run path
# ---------------------------------------------------------------------------

class TestAstra04:

    @staticmethod
    def _seats():
        line = "CLAIM | arithmetic | 2 + 2 = 4 | the total is 4\n"
        return {"s1": lambda _p: line, "s2": lambda _p: line}

    def test_every_run_verifies_its_own_chain_and_says_so(self):
        from run_adjudication import render_report, run_adjudication
        answer = run_adjudication("artifact", [], self._seats())
        assert answer.audit_verified is True
        assert "verified" in answer.audit_check
        assert "not an external attestation" in answer.audit_check
        report = render_report(answer)
        assert "audit chain     : verified" in report

    def test_a_durable_log_is_verified_against_its_sidecar(self, tmp_path):
        from run_adjudication import run_adjudication
        path = str(tmp_path / "audit.jsonl")
        answer = run_adjudication("artifact", [], self._seats(),
                                  audit_path=path)
        assert answer.audit_verified is True
        assert "sidecar" in answer.audit_check

    def test_a_chain_that_does_not_verify_is_a_hole_and_blocks_commit(
            self, monkeypatch):
        import audit_log as AL
        import run_adjudication as RA

        def broken(self, *a, **k):
            return AL.ChainVerdict(valid=False, entries_checked=3, head=None,
                                   failures=["entry 2: hash mismatch"])
        monkeypatch.setattr(AL.AuditLog, "verify", broken)
        answer = RA.run_adjudication("artifact", [], self._seats())
        assert answer.audit_verified is False
        assert answer.holes and answer.holes[0].kind == "audit chain"
        assert "hash mismatch" in answer.holes[0].detail
        assert answer.resolved is False
        assert "FAILED" in RA.render_report(answer)


# ---------------------------------------------------------------------------
# The Night Agent's final protocol, second report. Numbered by its points.
# ---------------------------------------------------------------------------

class TestProtocolPoint6_TheRecordCarriesItsChecksums:
    """Point 6: save the raw body, character count and byte hash of every
    capture, and check them offline. CONFIRMED absent: no hash anywhere in
    the round record, so an edited round file was indistinguishable from
    the original."""

    @staticmethod
    def _run(tmp_path, rounds=2):
        import night_loop as NL
        from adjudication_orchestrator import ArithmeticGate, Orchestrator
        panel = {f"seat_{i}": (lambda _p: _OPTION_REPLY) for i in range(1, 6)}
        NL.run_night("ask", panel, lambda p: "merged text",
                     Orchestrator([ArithmeticGate()]), str(tmp_path),
                     rounds=NL.ROUNDS[:rounds])
        return json.loads((tmp_path / "status.md").read_text()
                          .split("```json")[1].split("```")[0])

    def test_every_reply_and_prompt_is_hashed_into_status(self, tmp_path):
        import hashlib
        rounds = self._run(tmp_path)
        for rec in rounds:
            assert sorted(rec["reply_sha256"]) == [f"seat_{i}" for i in range(1, 6)]
            assert sorted(rec["prompt_sha256"]) == sorted(rec["reply_sha256"])
            for seat, h in rec["reply_sha256"].items():
                on_disk = (tmp_path / f"round-{rec['round']}" /
                           f"thinker-{seat}.md").read_text()
                assert hashlib.sha256(on_disk.encode()).hexdigest() == h
                assert rec["reply_chars"][seat] == len(on_disk)
            assert rec["merged_sha256"]
            assert rec["ask_sha256"]

    def test_the_offline_verifier_passes_an_untouched_run(self, tmp_path):
        import night_loop as NL
        self._run(tmp_path)
        assert NL.verify_run(str(tmp_path)) == []

    def test_an_edited_reply_file_is_reported(self, tmp_path):
        import night_loop as NL
        self._run(tmp_path)
        f = tmp_path / "round-2" / "thinker-seat_3.md"
        f.write_text(f.read_text() + "\nOPTION | added afterwards\n")
        problems = NL.verify_run(str(tmp_path))
        assert any("round-2/thinker-seat_3.md" in p and "sha256" in p
                   for p in problems)
        assert any("chars" in p for p in problems)

    def test_an_edited_merge_and_ask_are_reported(self, tmp_path):
        import night_loop as NL
        self._run(tmp_path)
        (tmp_path / "round-1" / "merged-1.md").write_text("something else")
        (tmp_path / "ask.md").write_text("a different question\n")
        problems = NL.verify_run(str(tmp_path))
        assert any("merged-1.md" in p for p in problems)
        assert any("ask.md" in p for p in problems)

    def test_no_status_is_a_failure_not_a_pass(self, tmp_path):
        import night_loop as NL
        problems = NL.verify_run(str(tmp_path))
        assert problems and "status.md" in problems[0]


class TestProtocolPoint2_WhatAnsweredIsRecorded:
    """Point 2: a model echo cannot attest identity, but it is the only
    identity signal a reply carries, and the run kept none of it. CONFIRMED:
    the adapter read the vendor's reply for text and usage and never for the
    model it named."""

    def test_reported_model_is_read_by_structure_only(self):
        import seat_adapter as SA
        assert SA.reported_model(b'{"model": "vendor-x-2026-03"}') == "vendor-x-2026-03"
        assert SA.reported_model(b'{"modelVersion": "g-3"}') == "g-3"
        assert SA.reported_model(b'{"model": ""}') is None
        assert SA.reported_model(b'[1, 2]') is None
        assert SA.reported_model(b'not json') is None

    @pytest.mark.parametrize("configured, reported, mismatch", [
        ("gpt-5", "gpt-5-2026-03-01", False),      # dated snapshot of the alias
        ("claude-x-4-1", "claude-x-4-1", False),
        ("GPT-5", "gpt-5-mini", False),            # prefix, case-folded
        ("gpt-5", "gpt-4o", True),
        ("grok-4", "grok-3-mini", True),
        ("", "anything", False),                   # nothing configured: no claim
    ])
    def test_mismatch_rule(self, configured, reported, mismatch):
        import night_loop as NL
        why = NL.model_identity_mismatch(configured, reported)
        assert (why is not None) is mismatch
        if mismatch:
            assert reported in why and configured in why

    def test_the_live_adapter_captures_the_echo(self, tmp_path):
        import json as _json

        import run_adjudication as RA
        import seat_adapter as SA
        from test_suite import _GOOD_PROFILE, _transport
        path = tmp_path / "p.json"
        path.write_text(_json.dumps({f"seat_{i}": _GOOD_PROFILE
                                     for i in range(1, 6)}))
        env = {f"ADJ_SEAT_{i}_API_KEY": f"k{i}" for i in range(1, 6)}
        env.update({f"ADJ_SEAT_{i}_MODEL": "m" for i in range(1, 6)})
        body = {"choices": [{"message": {
                    "content": "CLAIM | arithmetic | 2+2 = 4 | ok"}}],
                "model": "m-2026-served"}
        fns = RA.live_seats(str(path), env=env, transport=_transport(body=body),
                            ledger=SA.UNMETERED)
        seat = fns["seat_1"]
        assert getattr(seat, "last_reported_model", None) is None
        seat("prompt")
        assert seat.last_reported_model == "m-2026-served"

    def test_a_mismatch_is_recorded_and_is_a_hole(self, tmp_path):
        import convergence as CV
        import night_loop as NL
        from adjudication_orchestrator import ArithmeticGate, Orchestrator

        class Seat:
            def __init__(self, configured, reported):
                self.model = configured
                self.last_reported_model = reported

            def __call__(self, _p):
                return _OPTION_REPLY
        panel = {f"seat_{i}": Seat("wanted-9", "wanted-9-2026")
                 for i in range(1, 5)}
        panel["seat_5"] = Seat("wanted-9", "other-2")
        results = NL.run_night("ask", panel, lambda p: "merged",
                               Orchestrator([ArithmeticGate()]),
                               str(tmp_path), rounds=NL.ROUNDS[:1])
        r = results[0]
        assert r.models_reported["seat_1"] == "wanted-9-2026"
        assert list(r.model_mismatch) == ["seat_5"]
        assert "other-2" in r.model_mismatch["seat_5"]
        status = (tmp_path / "status.md").read_text()
        assert "other-2" in status
        holes = CV.analyse(results).holes
        assert any(h.kind == "panel identity" and "seat_5" in h.detail
                   for h in holes)

    def test_a_matching_echo_is_not_a_hole(self, tmp_path):
        import convergence as CV
        import night_loop as NL
        from adjudication_orchestrator import ArithmeticGate, Orchestrator

        class Seat:
            model = "wanted-9"
            last_reported_model = "wanted-9-2026"

            def __call__(self, _p):
                return _OPTION_REPLY
        panel = {f"seat_{i}": Seat() for i in range(1, 6)}
        results = NL.run_night("ask", panel, lambda p: "merged",
                               Orchestrator([ArithmeticGate()]),
                               str(tmp_path), rounds=NL.ROUNDS[:1])
        assert results[0].model_mismatch == {}
        assert not any(h.kind == "panel identity"
                       for h in CV.analyse(results).holes)


class TestProtocolPoint1_ThePlanIsOnDisk:
    """Point 1: freeze the limits and record them. CONFIRMED: the plan was
    spoken once to on_event and kept nowhere."""

    def test_live_night_writes_plan_md_once_the_run_goes_ahead(
            self, tmp_path, monkeypatch):
        import json as _json
        import os

        import cost_ledger as CL
        import night_loop as NL
        import run_adjudication as RA
        p = tmp_path / "profiles.json"
        p.write_text(_json.dumps({
            f"seat_{i}": {"vendor": v, "model": f"m{i}", "max_tokens": 4096}
            for i, v in enumerate(
                ("openai", "google", "mistral", "xai", "anthropic"), start=1)}))
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "rates.json"), encoding="utf-8") as fh:
            rates = CL.rates_from_config(_json.load(fh))
        led = CL.CostLedger(rates=rates, per_run=50.0)

        class Seat:
            max_tokens = 4096

            def __call__(self, _p):
                return _OPTION_REPLY
        monkeypatch.setattr(RA, "live_seats",
                            lambda *a, **k: {f"seat_{i}": Seat()
                                             for i in range(1, 6)})
        monkeypatch.setattr(RA, "load_env_file", lambda *a, **k: None)
        monkeypatch.setattr(CL, "check_models_are_priced",
                            lambda *a, **k: None)
        out = tmp_path / "run"
        NL.live_night("ask", str(p), str(out), ledger=led)
        plan = (out / "plan.md").read_text()
        assert "calls: 30" in plan
        assert "per-run ceiling: $50.00" in plan
        assert "seat_5" in plan and "estimate: $" in plan


class TestProtocolPoint10_IncompleteIsPartialNotRefused:
    """Point 10: incomplete evidence collection yields PARTIAL. A round
    refused mid-run must reach the callers as the same kind of stop a
    per-call ceiling is, or the watcher files it as "nothing was spent"."""

    def test_a_round_refusal_propagates_as_a_ceiling(self, tmp_path):
        import cost_ledger as CL
        import night_loop as NL
        from adjudication_orchestrator import ArithmeticGate, Orchestrator
        panel = {f"seat_{i}": (lambda _p: _OPTION_REPLY) for i in range(1, 6)}

        def before(n):
            if n == 2:
                raise NL.RoundUnfunded(2, "per-run", 4.5, 5.0, 1.2)
        with pytest.raises(CL.CeilingReached) as exc:
            NL.run_night("ask", panel, lambda p: "merged",
                         Orchestrator([ArithmeticGate()]), str(tmp_path),
                         rounds=NL.ROUNDS[:3], before_round=before)
        assert "round 2" in str(exc.value) and "$0.50" in str(exc.value)
        assert (tmp_path / "round-2" / "NOT-STARTED.md").exists()

    def test_the_watcher_files_it_as_partial_with_the_rounds_kept(
            self, tmp_path, monkeypatch):
        import os

        import night_loop as NL
        import watcher as W
        make = next(getattr(W.Folders, n) for n in ("at", "under", "create", "make", "build")
                    if callable(getattr(W.Folders, n, None)))
        folders = make(str(tmp_path / "w"))
        os.makedirs(folders.inbox, exist_ok=True)
        ask = os.path.join(folders.inbox, "q.md")
        with open(ask, "w", encoding="utf-8") as fh:
            fh.write("what is 2 + 2?\n")

        def fake_live_night(ask_text, profiles_path, out, **kw):
            os.makedirs(out, exist_ok=True)
            with open(os.path.join(out, "status.md"), "w") as fh:
                fh.write("round 1 done")
            raise NL.RoundUnfunded(2, "per-run", 4.5, 5.0, 1.2)
        monkeypatch.setattr(NL, "live_night", fake_live_night)
        monkeypatch.setattr(W, "read_ask", lambda p: "what is 2 + 2?")
        monkeypatch.setattr(W, "_rejects_claimed_file", lambda *a: None)
        out = W.process(ask, folders, 5.0, str(tmp_path / "profiles.json"))
        assert os.path.exists(os.path.join(out, "PARTIAL.md"))
        assert not os.path.exists(os.path.join(out, "REFUSED.md"))
        assert os.path.exists(os.path.join(folders.done, "q.md"))


class TestProtocolPoint8_TheScorerIsPartOfTheMeasurement:
    """Point 8: freeze runner hashes with the suite. CONFIRMED: a transcript
    recorded the replies and the quiz and nothing about the code that
    scored them."""

    def test_a_transcript_records_the_scorer_and_a_rescore_checks_it(
            self, tmp_path):
        from pathlib import Path
        path = Path(_transcript(tmp_path)[0])
        raw = json.loads(path.read_text())
        assert raw["scorer_sha256"] == CB.scorer_identity()
        assert CB.scorer_note(str(path)) is None
        raw["scorer_sha256"] = "0" * 64
        path.write_text(json.dumps(raw))
        assert "SCORER CHANGED" in CB.scorer_note(str(path))
        del raw["scorer_sha256"]
        path.write_text(json.dumps(raw))
        assert "SCORER UNKNOWN" in CB.scorer_note(str(path))

    def test_the_rescore_banner_carries_the_note(self, tmp_path, capsys):
        from pathlib import Path
        path = Path(_transcript(tmp_path)[0])
        raw = json.loads(path.read_text())
        raw["scorer_sha256"] = "0" * 64
        path.write_text(json.dumps(raw))
        CB.main(["--rescore", str(path)])
        out = capsys.readouterr().out
        assert "RE-SCORE of" in out and "SCORER CHANGED" in out
