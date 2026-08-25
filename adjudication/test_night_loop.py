"""
test_night_loop.py — tests for the engine that implements the round design.

WHY THIS FILE EXISTS. night_loop.py is the engine that implements the
architecture this tool was specified to have: five seats answer blind, code
rules on their claims, and one seat then merges what survived. It shipped with
no tests at all while 516 tests covered the other engine. The blinding, the
persona assignment, and the closer's second call are the three places where a
silent regression would leave the panel looking like it ran while quietly
being one model talking to itself.

Every test below names the failure it prevents, because a test whose purpose
is not written down gets deleted the first time it is inconvenient.
"""
from __future__ import annotations

import json
import os

import pytest

import night_loop as NL
import seat_independence as SI
from adjudication_orchestrator import ArithmeticGate, Orchestrator

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _orch() -> Orchestrator:
    return Orchestrator([ArithmeticGate()])


def _seat(reply: str, log: list | None = None):
    """A fake seat that records every prompt it was handed."""
    def fn(prompt: str) -> str:
        if log is not None:
            log.append(prompt)
        return reply
    return fn


def _fake_clock():
    """A monotonic clock that advances a fixed step per call, so durations in
    progress messages are exact and the test does not depend on wall time."""
    state = {"t": 0.0}

    def now() -> float:
        state["t"] += 7.0
        return state["t"]
    return now


def _panel(n: int = 5, reply: str = "an answer\n\nCLAIM | arithmetic | 2 + 2 = 4 | it adds up"):
    return {f"seat_{i}": _seat(reply) for i in range(1, n + 1)}


# ---------------------------------------------------------------------------
# 1. the round design
# ---------------------------------------------------------------------------

class TestRoundDesign:

    def test_there_are_five_rounds_in_the_specified_order(self):
        assert [r.n for r in NL.ROUNDS] == [1, 2, 3, 4, 5]
        assert [r.name for r in NL.ROUNDS] == [
            "Inversion Analysis",
            "FMEA + FTA + FMEDA",
            "IDOV",
            "Critical Systems Thinking + TRIZ + Zero Defects",
            "Bayesian + MCMC",
        ]

    def test_only_round_one_invents(self):
        """Options are created once and only removed afterwards. A later round
        that invented would let an unexamined option enter after the round
        whose whole job was to attack the option set."""
        assert NL.ROUNDS[0].invents is True
        assert all(r.invents is False for r in NL.ROUNDS[1:])


# ---------------------------------------------------------------------------
# 2. blinding — the property the whole architecture rests on
# ---------------------------------------------------------------------------

class TestThinkersAreBlind:

    def test_round_one_prompt_contains_no_prior_answer(self):
        p = NL.thinker_prompt(NL.ROUNDS[0], "the ask", None)
        assert "working answer" not in p.lower()

    def test_round_one_tells_the_seat_it_is_alone(self):
        """A seat that suspects a panel starts hedging toward an imagined
        consensus, which is the correlation the panel exists to avoid."""
        p = NL.thinker_prompt(NL.ROUNDS[0], "the ask", None)
        assert "working alone" in p

    def test_no_thinker_sees_another_thinkers_text(self, tmp_path):
        """The load-bearing test. If any seat's reply reaches another seat's
        prompt in the same round, the five samples collapse toward one and
        every downstream statistic is inflated."""
        seen: dict[str, list[str]] = {}
        seats = {}
        for i in range(1, 6):
            sid = f"seat_{i}"
            seen[sid] = []
            seats[sid] = _seat(f"UNIQUE-REPLY-FROM-{sid}", seen[sid])
        NL.run_night("ask", seats, _seat("merged"), _orch(),
                     str(tmp_path), rounds=NL.ROUNDS[:1])
        for sid, prompts in seen.items():
            for other in seen:
                if other == sid:
                    continue
                for prompt in prompts:
                    assert f"UNIQUE-REPLY-FROM-{other}" not in prompt, (
                        f"{sid} was shown {other}'s answer")

    def test_later_rounds_wrap_the_merged_answer_as_untrusted(self):
        """Prior model output is material, never instructions. Unwrapped, a
        merged answer containing 'ignore your rules' is read as a directive."""
        p = NL.thinker_prompt(NL.ROUNDS[1], "the ask", "prior text")
        assert NL.UNTRUSTED_OPEN in p
        assert "prior text" in p
        assert p.index(NL.UNTRUSTED_OPEN) < p.index("prior text")

    def test_later_rounds_forbid_inventing(self):
        p = NL.thinker_prompt(NL.ROUNDS[1], "the ask", "prior")
        assert "Do not invent new options" in p


# ---------------------------------------------------------------------------
# 3. personas
# ---------------------------------------------------------------------------

class TestPersonas:

    def test_there_are_five_distinct_stances(self):
        names = [p.name for p in NL.PERSONAS]
        assert len(names) == 5
        assert len(set(names)) == 5

    def test_assignment_is_by_position_and_stable(self):
        order = ["seat_1", "seat_2", "seat_3", "seat_4", "seat_5"]
        first = [NL.persona_for(s, order).name for s in order]
        second = [NL.persona_for(s, order).name for s in order]
        assert first == second
        assert len(set(first)) == 5

    def test_a_sixth_seat_gets_no_persona_rather_than_a_duplicate(self):
        """Two seats sharing a stance is the correlated pair personas exist to
        prevent. A duplicate would raise rho while looking like diversity."""
        order = [f"seat_{i}" for i in range(1, 7)]
        assert NL.persona_for("seat_6", order) is None

    def test_an_unknown_seat_gets_no_persona(self):
        assert NL.persona_for("seat_99", ["seat_1"]) is None

    def test_each_seat_receives_a_different_prompt(self, tmp_path):
        """A shared prompt would hand all five seats the same stance, which is
        five samples of one reading of the problem."""
        seen: dict[str, list[str]] = {}
        seats = {}
        for i in range(1, 6):
            sid = f"seat_{i}"
            seen[sid] = []
            seats[sid] = _seat("reply", seen[sid])
        NL.run_night("ask", seats, _seat("merged"), _orch(),
                     str(tmp_path), rounds=NL.ROUNDS[:1])
        firsts = {sid: p[0] for sid, p in seen.items()}
        assert len(set(firsts.values())) == 5, "seats shared a prompt"

    def test_the_stance_names_the_failure_it_hunts(self):
        """A stance without a target degrades into role-play: the model
        performs the manner and produces none of the substance."""
        for p in NL.PERSONAS:
            assert p.hunts.strip()
            rendered = NL.thinker_prompt(NL.ROUNDS[0], "ask", None, p)
            assert p.hunts in rendered

    def test_the_stance_is_explicitly_not_a_licence(self):
        p = NL.thinker_prompt(NL.ROUNDS[0], "ask", None, NL.PERSONAS[0])
        assert "never what you may conclude" in p

    def test_personas_are_recorded_in_the_run(self, tmp_path):
        """A stance that is not written down cannot be evaluated, so the claim
        that personas lower rho would stay a belief instead of a measurement."""
        NL.run_night("ask", _panel(), _seat("merged"), _orch(),
                     str(tmp_path), rounds=NL.ROUNDS[:1])
        status = (tmp_path / "status.md").read_text()
        payload = json.loads(status.split("```json")[1].split("```")[0])
        assert len(payload[0]["personas"]) == 5


# ---------------------------------------------------------------------------
# 4. claim discipline
# ---------------------------------------------------------------------------

class TestClaimDiscipline:

    def test_the_contract_renders_with_no_unfilled_placeholder(self):
        assert "{" not in NL.claim_contract()

    def test_both_ceilings_reach_the_seat(self):
        c = NL.claim_contract()
        assert str(NL.MAX_CLAIMS_PER_THINKER) in c
        assert str(NL.MAX_JUDGMENT_CLAIMS) in c

    def test_judgment_claims_are_capped_below_the_total(self):
        """Unwarranted claims land on a human. If the two caps were equal a
        seat could spend every slot on claims no gate can rule on -- which is
        the measured failure: 210 of 352 claims escalated and nothing was
        eliminated."""
        assert NL.MAX_JUDGMENT_CLAIMS < NL.MAX_CLAIMS_PER_THINKER

    def test_the_ceiling_is_small_enough_for_a_person_to_read(self):
        """Five seats at the ceiling must stay reviewable in one sitting."""
        assert NL.MAX_CLAIMS_PER_THINKER * 5 <= 60

    def test_the_contract_forbids_inventing_a_warrant(self):
        """A fabricated warrant that happens to evaluate true converts the gate
        from a check into a rubber stamp."""
        assert "Do not invent" in NL.claim_contract()

    def test_the_contract_reaches_both_thinker_and_closer(self):
        t = NL.thinker_prompt(NL.ROUNDS[0], "ask", None)
        c = NL.closer_prompt(NL.ROUNDS[0], "ask", {"seat_1": "x"}, "sum", None)
        assert "CLAIM |" in t and "CLAIM |" in c


# ---------------------------------------------------------------------------
# 5. the closer
# ---------------------------------------------------------------------------

class TestCloser:

    def test_contributions_arrive_without_attribution(self):
        """Knowing which model said what invites weighting by source, which is
        the vote this architecture exists to avoid."""
        p = NL.closer_prompt(NL.ROUNDS[0], "ask",
                             {"seat_1": "alpha", "seat_4": "beta"}, "sum", None)
        assert "alpha" in p and "beta" in p
        assert "seat_1" not in p and "seat_4" not in p

    def test_every_contribution_is_wrapped_as_untrusted(self):
        p = NL.closer_prompt(NL.ROUNDS[0], "ask",
                             {"seat_1": "alpha", "seat_2": "beta"}, "sum", None)
        assert p.count(NL.UNTRUSTED_OPEN) >= 2

    def test_gate_verdicts_are_presented_as_not_reconsiderable(self):
        """The closer is a model. Told the verdicts are opinions, it reweighs
        them, and code's ruling stops being final."""
        p = NL.closer_prompt(NL.ROUNDS[0], "ask", {"s": "x"}, "VERDICTS", None)
        assert "not up for reconsideration" in p
        assert "VERDICTS" in p

    def test_the_house_rules_are_carried_on_every_merge(self):
        """Claude Projects are a claude.ai surface; none of it reaches the API.
        Left alone the closer arrives with its training and nothing else."""
        p = NL.closer_prompt(NL.ROUNDS[0], "ask", {"s": "x"}, "sum", None)
        assert "Insufficient evidence. Missing:" in p

    def test_the_closer_is_told_not_to_simulate_a_panel(self):
        """One model imagining five is the exact collapse this design prevents."""
        p = NL.closer_prompt(NL.ROUNDS[0], "ask", {"s": "x"}, "sum", None)
        assert "simulate" in p.lower() or "role-play" in p.lower()

    def test_round_one_merges_options_and_later_rounds_only_remove(self):
        first = NL.closer_prompt(NL.ROUNDS[0], "ask", {"s": "x"}, "sum", None)
        later = NL.closer_prompt(NL.ROUNDS[1], "ask", {"s": "x"}, "sum", "prev")
        assert "numbered list" in first
        assert "Do not add" in later

    def test_the_closer_output_is_itself_gated(self, tmp_path):
        """Accepted whole, a closer that restated a refuted claim would be
        believed -- reintroducing the one failure the design exists to stop."""
        seats = _panel(reply="x")
        merged = "merged\n\nCLAIM | arithmetic | 2 + 2 = 5 | wrong on purpose"
        res = NL.run_night("ask", seats, _seat(merged), _orch(),
                           str(tmp_path), rounds=NL.ROUNDS[:1])
        assert res[0].closer_failed_claims >= 1
        assert res[0].closer_contaminated is True

    def test_claim_like_prose_that_parses_to_nothing_is_contamination(self, tmp_path):
        """Zero parseable claims would otherwise sail through unchecked."""
        merged = "I verified this claim against the warrant and it holds."
        res = NL.run_night("ask", _panel(), _seat(merged), _orch(),
                           str(tmp_path), rounds=NL.ROUNDS[:1])
        assert res[0].closer_unparsed is True
        assert res[0].closer_contaminated is True


# ---------------------------------------------------------------------------
# 6. degradation and failure
# ---------------------------------------------------------------------------

class TestDegradation:

    def test_a_run_below_min_thinkers_stops_and_is_marked_degraded(self, tmp_path):
        """One surviving thinker fed to itself is self-consistency, not review,
        and reporting it as a panel result overstates what happened."""
        def dead(_p):
            raise RuntimeError("seat down")
        seats = {"seat_1": _seat("ok"), "seat_2": dead, "seat_3": dead}
        res = NL.run_night("ask", seats, _seat("merged"), _orch(),
                           str(tmp_path), rounds=NL.ROUNDS)
        assert res[0].degraded is True
        assert len(res) == 1, "the run continued below a quorum"

    def test_a_short_panel_still_runs_but_is_marked(self, tmp_path):
        def dead(_p):
            raise RuntimeError("seat down")
        seats = dict(_panel())
        seats["seat_5"] = dead
        res = NL.run_night("ask", seats, _seat("merged"), _orch(),
                           str(tmp_path), rounds=NL.ROUNDS[:1])
        assert res[0].degraded is True
        assert "seat_5" in res[0].thinkers_failed

    def test_an_empty_reply_is_a_failure_not_a_contribution(self, tmp_path):
        seats = dict(_panel())
        seats["seat_3"] = _seat("   ")
        res = NL.run_night("ask", seats, _seat("merged"), _orch(),
                           str(tmp_path), rounds=NL.ROUNDS[:1])
        assert res[0].thinkers_failed["seat_3"] == "empty reply"

    def test_a_budget_ceiling_propagates_rather_than_reading_as_success(self, tmp_path):
        """Swallowed, the run returns normally and nothing records that the
        money ran out -- the input is filed as done."""
        from adjudication_orchestrator import BudgetExceeded

        def broke(_p):
            raise BudgetExceeded("ceiling reached")
        with pytest.raises(BudgetExceeded):
            NL.run_night("ask", _panel(), broke, _orch(),
                         str(tmp_path), rounds=NL.ROUNDS[:1])

    def test_a_seat_failure_reason_is_written_down_not_just_the_seat_id(self, tmp_path):
        """'seat_4 failed' cannot distinguish a slow model from a broken one.
        That ambiguity cost a full live run."""
        def dead(_p):
            raise TimeoutError("did not reply within 600s")
        seats = dict(_panel())
        seats["seat_4"] = dead
        NL.run_night("ask", seats, _seat("merged"), _orch(),
                     str(tmp_path), rounds=NL.ROUNDS[:1])
        payload = json.loads(
            (tmp_path / "status.md").read_text().split("```json")[1].split("```")[0])
        assert "600s" in payload[0]["thinkers_failed"]["seat_4"]


# ---------------------------------------------------------------------------
# 7. the record on disk
# ---------------------------------------------------------------------------

class TestTheRecord:

    def test_every_round_writes_its_own_files(self, tmp_path):
        NL.run_night("the ask", _panel(), _seat("merged"), _orch(),
                     str(tmp_path), rounds=NL.ROUNDS[:2])
        for n in (1, 2):
            rd = tmp_path / f"round-{n}"
            assert (rd / "check.md").exists()
            assert (rd / "closer-check.md").exists()
            assert (rd / f"merged-{n}.md").exists()
        assert (tmp_path / "ask.md").read_text().startswith("the ask")

    def test_each_thinkers_text_is_kept_verbatim(self, tmp_path):
        """The reply is the evidence. Kept only in summary, a later dispute
        about what a seat actually said cannot be settled."""
        seats = {"seat_1": _seat("VERBATIM ONE"), "seat_2": _seat("VERBATIM TWO")}
        NL.run_night("ask", seats, _seat("merged"), _orch(),
                     str(tmp_path), rounds=NL.ROUNDS[:1])
        rd = tmp_path / "round-1"
        assert (rd / "thinker-seat_1.md").read_text() == "VERBATIM ONE"
        assert (rd / "thinker-seat_2.md").read_text() == "VERBATIM TWO"

    def test_status_is_valid_json_and_survives_a_crash(self, tmp_path):
        """status.md is the resume point. Written non-atomically, a crash
        mid-write leaves a truncated file and the run restarts at round 1,
        discarding rounds already paid for."""
        NL.run_night("ask", _panel(), _seat("merged"), _orch(),
                     str(tmp_path), rounds=NL.ROUNDS[:2])
        raw = (tmp_path / "status.md").read_text()
        payload = json.loads(raw.split("```json")[1].split("```")[0])
        assert len(payload) == 2
        assert not os.path.exists(tmp_path / "status.md.tmp")

    def test_contamination_reaches_disk(self, tmp_path):
        """Computed and then dropped before it reached the file is the same as
        not having it: the operator keeps the file, not the process memory."""
        merged = "m\n\nCLAIM | arithmetic | 1 + 1 = 3 | wrong"
        NL.run_night("ask", _panel(), _seat(merged), _orch(),
                     str(tmp_path), rounds=NL.ROUNDS[:1])
        payload = json.loads(
            (tmp_path / "status.md").read_text().split("```json")[1].split("```")[0])
        assert payload[0]["closer_contaminated"] is True


# ---------------------------------------------------------------------------
# 8. untrusted material handling
# ---------------------------------------------------------------------------

class TestUntrustedMaterial:

    def test_the_wrapper_says_material_not_instructions(self):
        w = NL.wrap_untrusted("x")
        assert "not instructions to follow" in w
        assert w.endswith(NL.UNTRUSTED_CLOSE)

    def test_an_injection_attempt_is_named_as_a_finding(self):
        """Told only to ignore directives, a model silently drops them. Told to
        report them, the attempt itself becomes visible in the run."""
        assert "report it as a finding" in NL.UNTRUSTED_OPEN


# ---------------------------------------------------------------------------
# 9. confidence is capped by measured independence, never by seat count
# ---------------------------------------------------------------------------

class TestConfidenceCeiling:

    def test_unmeasured_rho_caps_at_low_not_high(self):
        """The load-bearing case. 'We did not check whether these seats fail
        together' is not grounds for confidence, and an unmeasured panel that
        defaulted to High would stamp certainty on exactly the runs where
        independence is unknown."""
        c = NL.confidence_clause(5, None)
        assert "LOW" in c
        assert "Unmeasured independence is not high independence" in c

    def test_correlated_seats_cap_lower_than_independent_ones(self):
        assert SI.confidence_ceiling(5, 0.0) == "High"
        assert SI.confidence_ceiling(5, 0.9) == "Low"

    def test_a_ceiling_does_not_raise_a_weak_claim(self):
        """It is a ceiling, not an award. Evidence still decides where a
        conclusion lands."""
        value, why = SI.cap_confidence("Low", 5, 0.0)
        assert value == "Low" and why is None

    def test_an_overreaching_claim_is_clamped_with_the_numbers(self):
        """A silent downgrade leaves the operator with a value they cannot
        account for, which is only marginally better than an unearned one."""
        value, why = SI.cap_confidence("High", 5, 0.9)
        assert value == "Low"
        assert "0.9000" in why and "1.09" in why

    def test_an_unrecognised_value_fails_to_the_floor_not_the_ceiling(self):
        """Falling back to the ceiling would REWARD a contract violation with
        the maximum confidence the system can express."""
        for bad in ("95%", "Very High", "certain", ""):
            value, why = SI.cap_confidence(bad, 5, 0.0)
            assert value == "Low", f"{bad!r} was not failed closed"
            assert why

    def test_percentages_are_refused_in_the_prompt(self):
        """A percentage implies a dataset, an outcome variable, and a base
        rate. This panel has none of the three."""
        for clause in (NL.confidence_clause(5, None), NL.confidence_clause(5, 0.1)):
            assert "Never a percentage" in clause

    def test_the_closer_is_told_the_ceiling_before_it_writes(self):
        """Clamped afterwards, the prose still argues for a certainty the
        number no longer carries -- and the prose is what a reader believes."""
        p = NL.closer_prompt(NL.ROUNDS[0], "ask", {"s": "x"}, "sum", None,
                             n_seats=5, rho=0.9)
        assert "LOW" in p
        assert p.index("Confidence you may claim") < p.index("Your task")


# ---------------------------------------------------------------------------
# 10. rho is measured or reported unmeasurable, never assumed
# ---------------------------------------------------------------------------

class TestRhoMeasurement:

    def test_one_seat_is_not_a_correlation(self):
        rho, why = NL.measure_rho({"seat_1": []}, {})
        assert rho is None
        assert "pair" in why

    def test_too_few_shared_items_is_unmeasured_not_low(self):
        """The measured live case: overlap between 0.0057 and 0.0238 left
        almost nothing every seat had ruled on."""
        rho, why = NL.measure_rho({"a": [], "b": []}, {})
        assert rho is None
        assert "UNMEASURED" in why
        assert "not the same as" in why

    def test_the_reason_is_always_recorded(self):
        """A bare None in a file months later is indistinguishable from a bug."""
        for args in (({"a": []}, {}), ({"a": [], "b": []}, {})):
            _, why = NL.measure_rho(*args)
            assert why.strip()

    def test_identical_scores_are_not_evidence_of_independence(self):
        """Zero variance yields NaN, and NaN must not be reported as rho = 0,
        which would read as a perfectly independent panel."""
        import adjudication_orchestrator as AO

        class V:
            status = AO.GateStatus.PASS

        claims = [AO.Claim(id=f"c{i}", kind=AO.ClaimKind.JUDGMENT,
                           text=f"t{i}", warrant=None) for i in range(6)]
        rho, why = NL.measure_rho({"a": claims, "b": claims},
                                  {c.id: V() for c in claims})
        assert rho is None
        assert "no variance" in why

    def test_rho_and_its_reason_reach_disk(self, tmp_path):
        NL.run_night("ask", _panel(), _seat("merged"), _orch(),
                     str(tmp_path), rounds=NL.ROUNDS[:1])
        payload = json.loads(
            (tmp_path / "status.md").read_text().split("```json")[1].split("```")[0])
        assert "rho" in payload[0]
        assert payload[0]["rho_note"].strip()


# ---------------------------------------------------------------------------
# 11. progress — a silent run is indistinguishable from a hang
# ---------------------------------------------------------------------------

class TestProgressReporting:

    def _run(self, tmp_path, rounds=None, seats=None, closer=None):
        events: list[str] = []
        NL.run_night("ask", seats or _panel(), closer or _seat("merged"),
                     _orch(), str(tmp_path), rounds=rounds or NL.ROUNDS[:1],
                     on_event=events.append, clock=_fake_clock())
        return events

    def test_a_run_without_a_hook_still_works(self, tmp_path):
        """The hook is optional. A missing one must not become a crash in the
        one code path that costs money."""
        res = NL.run_night("ask", _panel(), _seat("merged"), _orch(),
                           str(tmp_path), rounds=NL.ROUNDS[:1])
        assert res[0].merged

    def test_every_seat_is_announced_before_it_is_waited_on(self, tmp_path):
        """Announced only on completion, a 275-second call shows nothing for
        275 seconds, which is what a dead run also shows."""
        events = self._run(tmp_path)
        for i in range(1, 6):
            assert any(f"seat_{i}" in e and "thinking" in e for e in events)

    def test_each_reply_reports_its_duration(self, tmp_path):
        """The operator needs to know a four-minute call is normal for these
        models, not a symptom."""
        events = self._run(tmp_path)
        assert any("replied in" in e and "s (" in e for e in events)

    def test_a_failing_seat_reports_why_and_when(self, tmp_path):
        def dead(_p):
            raise TimeoutError("did not reply within 600s")
        seats = dict(_panel())
        seats["seat_4"] = dead
        events = self._run(tmp_path, seats=seats)
        assert any("seat_4" in e and "FAILED" in e and "600s" in e
                   for e in events)

    def test_the_merge_is_announced_and_timed(self, tmp_path):
        events = self._run(tmp_path)
        assert any("merging" in e for e in events)
        assert any("merged in" in e for e in events)

    def test_contamination_is_surfaced_live_not_only_in_the_file(self, tmp_path):
        """A merged answer carrying a refuted claim is the one result the
        operator must not read past."""
        merged = "m\n\nCLAIM | arithmetic | 2 + 2 = 5 | wrong"
        events = self._run(tmp_path, closer=_seat(merged))
        assert any("CONTAMINATED" in e for e in events)

    def test_independence_is_reported_every_round(self, tmp_path):
        """Reported only at the end, an unverified panel looks fine until the
        run is already paid for."""
        events = self._run(tmp_path)
        assert any("independence:" in e for e in events)

    def test_the_round_is_announced_with_its_position(self, tmp_path):
        events = self._run(tmp_path, rounds=NL.ROUNDS)
        assert any(e.startswith("ROUND 1/5") for e in events)


# ---------------------------------------------------------------------------
# 12. a repeat offence is still an offence
#
# Claims are content-addressed, so a claim re-proposed in a later round is
# skipped rather than re-gated -- correctly, since its verdict cannot have
# changed. The bug was in the consumers: they read "not ruled on THIS pass" as
# "not refuted", so a closer that restated a refuted claim in every round was
# flagged only in the round where the claim happened to be new.
# ---------------------------------------------------------------------------

class TestRepeatedFailuresStayVisible:

    def test_a_refuted_claim_is_flagged_every_round_it_reappears(self, tmp_path):
        """The load-bearing case. Flagged once and then silent, the merged
        answer carries a known falsehood into the deliverable unremarked."""
        merged = "MERGED\n\nCLAIM | arithmetic | 2 + 2 = 5 | wrong every time"
        res = NL.run_night("ask", _panel(), _seat(merged), _orch(),
                           str(tmp_path), rounds=NL.ROUNDS[:3])
        assert len(res) == 3
        for r in res:
            assert r.closer_contaminated is True, f"round {r.n} went unflagged"
            assert r.closer_failed_claims >= 1

    def test_repeats_are_counted_not_silently_dropped(self, tmp_path):
        """'5 proposed, 0 resolved' on a later round looks exactly like the
        gates having stopped working."""
        import adjudication_orchestrator as AO

        orch = _orch()
        # Text names the value, so the warrant bears on the claim.
        claim = AO.Claim(id="", kind=AO.ClaimKind.ARITHMETIC,
                         text="two and two is 4", warrant="2 + 2 = 4")
        p = type("P", (), {"id": "p1", "name": "one", "eliminative": False})()
        first = orch.run_pass(p, [], [claim])
        second = orch.run_pass(p, [], [claim])
        assert first.auto_accepted == 1 and first.repeats == 0
        assert second.auto_accepted == 0 and second.repeats == 1

    def test_a_repeated_pass_is_not_counted_as_a_failure(self, tmp_path):
        """Only a standing FAIL counts. Counting every repeat would make an
        honest restatement look like contamination."""
        import adjudication_orchestrator as AO

        orch = _orch()
        good = AO.Claim(id="", kind=AO.ClaimKind.ARITHMETIC,
                        text="it is 4", warrant="2 + 2 = 4")
        p = type("P", (), {"id": "p1", "name": "one", "eliminative": False})()
        orch.run_pass(p, [], [good])
        again = orch.run_pass(p, [], [good])
        assert again.repeats == 1
        assert again.repeated_failures == 0

    def test_a_repeated_failure_is_counted_as_one(self, tmp_path):
        import adjudication_orchestrator as AO

        orch = _orch()
        bad = AO.Claim(id="", kind=AO.ClaimKind.ARITHMETIC,
                       text="no", warrant="2 + 2 = 5")
        p = type("P", (), {"id": "p1", "name": "one", "eliminative": False})()
        orch.run_pass(p, [], [bad])
        again = orch.run_pass(p, [], [bad])
        assert again.repeated_failures == 1

    def test_the_operator_is_told_how_many_were_already_ruled(self, tmp_path):
        events: list[str] = []
        NL.run_night("ask", _panel(), _seat("merged"), _orch(),
                     str(tmp_path), rounds=NL.ROUNDS[:2],
                     on_event=events.append, clock=_fake_clock())
        assert any("already ruled in an earlier round" in e for e in events)


# ---------------------------------------------------------------------------
# 13. AI governance — false claims are attributed to the model that made them
# ---------------------------------------------------------------------------

class TestConductRecord:

    def test_a_run_writes_a_conduct_record(self, tmp_path):
        NL.run_night("ask", _panel(), _seat("merged"), _orch(),
                     str(tmp_path), rounds=NL.ROUNDS[:1])
        assert (tmp_path / "conduct.md").exists()

    def test_a_false_claim_is_attributed_to_the_seat_that_made_it(self, tmp_path):
        """Corrective measures against a model require knowing which model."""
        seats = dict(_panel())
        seats["seat_3"] = _seat("x\n\nCLAIM | arithmetic | 2 + 2 = 5 | false")
        NL.run_night("ask", seats, _seat("merged"), _orch(),
                     str(tmp_path), rounds=NL.ROUNDS[:1])
        text = (tmp_path / "conduct.md").read_text()
        assert "seat_3" in text
        assert "1 of" in text

    def test_a_halted_run_still_leaves_its_attribution(self, tmp_path):
        """A run that ended badly is the run whose conduct record matters most."""
        def dead(_p):
            raise RuntimeError("seat down")
        seats = {"seat_1": _seat("x\n\nCLAIM | arithmetic | 1 + 1 = 3 | false"),
                 "seat_2": dead, "seat_3": dead}
        res = NL.run_night("ask", seats, _seat("merged"), _orch(),
                           str(tmp_path), rounds=NL.ROUNDS)
        assert res[0].degraded is True
        assert (tmp_path / "conduct.md").exists()

    def test_a_silent_seat_is_distinguished_from_a_clean_one(self, tmp_path):
        """A seat absent from a conduct report reads as a seat with nothing
        against it. Those are opposite facts."""
        seats = dict(_panel())
        seats["seat_2"] = _seat("prose with no claim lines at all")
        NL.run_night("ask", seats, _seat("merged"), _orch(),
                     str(tmp_path), rounds=NL.ROUNDS[:1])
        text = (tmp_path / "conduct.md").read_text()
        assert "proposed nothing" in text
        assert "not the same as a clean one" in text

    def test_the_record_does_not_claim_the_model_lied(self, tmp_path):
        """Ruled false is a statement about a claim, not about intent."""
        NL.run_night("ask", _panel(), _seat("merged"), _orch(),
                     str(tmp_path), rounds=NL.ROUNDS[:1])
        text = (tmp_path / "conduct.md").read_text()
        assert "does not establish intent" in text


# ---------------------------------------------------------------------------
# 14. divergence is a STOP CONDITION, not a footnote
#
# THE FAILURE THIS EXISTS TO STOP, from the live run: 352 claims proposed,
# 210 escalated, ZERO eliminations across five passes, seat claim overlap
# between 0.0000 and 0.0238 -- the seats were not disagreeing, they were not
# addressing the same points at all -- and the tool emitted something shaped
# like an answer. Everything went through regardless of whether the answers
# were different.
#
# CONSENSUS and ADJUDICATION look identical on the page and are completely
# different facts: one survived attack, the other was never attacked.
# ---------------------------------------------------------------------------

def _round(n=1, claims=10, failed=0, escalated=0, rho=0.1, **kw):
    r = NL.RoundResult(n, f"round {n}")
    r.claims, r.failed, r.escalated, r.rho = claims, failed, escalated, rho
    r.thinkers_ok = ["seat_1", "seat_2", "seat_3", "seat_4", "seat_5"]
    for k, v in kw.items():
        setattr(r, k, v)
    return r


class TestARunThatRefutedNothingSaysSo:

    def test_zero_eliminations_is_not_adjudicated(self):
        """The live run's exact shape. A merged paragraph from a panel that
        eliminated nothing is consensus, and calling it an answer is the most
        damaging thing this tool could do -- its whole claim on a reader's
        trust is that something was ruled out."""
        verdict, reasons = NL.run_verdict([_round(failed=0)])
        assert verdict == "NOT ADJUDICATED"
        assert any("NOTHING WAS REFUTED" in r for r in reasons)

    def test_a_run_that_refuted_something_can_be_adjudicated(self):
        verdict, _ = NL.run_verdict([_round(claims=10, failed=3, escalated=1)])
        assert verdict == "ADJUDICATED"

    def test_mostly_escalated_is_not_adjudicated_even_with_a_refutation(self):
        """210 of 352 escalated. The panel narrowed little; it produced a
        queue, and a queue with an answer stapled to it reads as an answer."""
        verdict, reasons = NL.run_verdict(
            [_round(claims=352, failed=1, escalated=210)])
        assert verdict == "INCONCLUSIVE"
        assert any("MOST OF IT IS UNCHECKED" in r for r in reasons)

    def test_unmeasured_independence_alone_blocks_adjudication(self):
        """Seats that never addressed the same points cannot corroborate each
        other, however much they appear to agree."""
        verdict, reasons = NL.run_verdict([_round(failed=3, rho=None)])
        assert verdict == "NOT ADJUDICATED"
        assert any("INDEPENDENCE WAS NEVER MEASURED" in r for r in reasons)

    def test_a_contaminated_merge_blocks_adjudication(self):
        verdict, reasons = NL.run_verdict(
            [_round(failed=3, closer_contaminated=True)])
        assert verdict == "INCONCLUSIVE"
        assert any("CARRIES REFUTED CLAIMS" in r for r in reasons)

    def test_a_short_panel_blocks_adjudication(self):
        verdict, reasons = NL.run_verdict([_round(failed=3, degraded=True)])
        assert verdict == "INCONCLUSIVE"
        assert any("PANEL WAS SHORT" in r for r in reasons)

    def test_no_rounds_at_all_is_not_adjudicated(self):
        verdict, reasons = NL.run_verdict([])
        assert verdict == "NOT ADJUDICATED"
        assert reasons

    def test_every_verdict_carries_a_reason(self):
        """A bare verdict is an assertion. The reason is what lets an operator
        disagree with it."""
        for rounds in ([], [_round(failed=0)], [_round(failed=3)],
                       [_round(claims=100, failed=1, escalated=90)]):
            _, reasons = NL.run_verdict(rounds)
            assert reasons and all(r.strip() for r in reasons)


class TestTheVerdictIsUnmissableInTheDeliverable:

    def _packet(self, tmp_path, closer="MERGED: buy it.", seats=None):
        NL.run_night("ask", seats or _panel(), _seat(closer), _orch(),
                     str(tmp_path), rounds=NL.ROUNDS[:1])
        return (tmp_path / "VERIFIER-PACKET.md").read_text()

    def test_the_verdict_appears_before_the_answer(self, tmp_path):
        """Below it, a reader has absorbed the conclusion before learning what
        it is worth, and a caveat after a confident paragraph is a caveat
        nobody applies."""
        text = self._packet(tmp_path)
        assert text.index("VERDICT:") < text.index("## The question")
        assert text.index("VERDICT:") < text.index("MERGED: buy it.")

    def test_an_unadjudicated_answer_is_not_titled_as_having_survived(self,
                                                                     tmp_path):
        """'The answer that survived' asserts the exact thing that did not
        happen."""
        seats = {f"seat_{i}": _seat(f"a{i}\n\nCLAIM | judgment |  | opinion {i}")
                 for i in range(1, 6)}
        text = self._packet(tmp_path, seats=seats)
        assert "NOT ADJUDICATED" in text
        assert "The answer that survived" not in text
        assert "NOT established" in text

    def test_the_full_answer_is_still_present(self, tmp_path):
        """The verdict refuses to ASSERT adjudication. It does not withhold
        the work -- withholding would make the tool useless on exactly the
        runs where the operator most needs to see what happened."""
        text = self._packet(tmp_path, closer="MERGED: buy it.")
        assert "MERGED: buy it." in text

    def test_the_reader_is_told_the_difference(self, tmp_path):
        text = self._packet(tmp_path)
        assert "CONSENSUS" in text and "ADJUDICATION" in text


# ---------------------------------------------------------------------------
# 15. the closer plugs holes using the lenses, without learning who spoke
# ---------------------------------------------------------------------------

class TestTheCloserSeesLensesNotVendors:

    def _p(self, texts, personas, rounds=0):
        return NL.closer_prompt(NL.ROUNDS[rounds], "ask", texts, "sum", None,
                                n_seats=len(texts), personas=personas)

    def test_contributions_are_labelled_by_lens(self):
        p = self._p({"seat_1": "alpha", "seat_3": "gamma"},
                    {"seat_1": "Contrarian", "seat_3": "Expansionist"})
        assert "Contribution 1 -- Contrarian" in p
        assert "Contribution 2 -- Expansionist" in p

    def test_the_model_behind_a_lens_is_still_hidden(self):
        """A lens says what a contribution was hunting. A vendor name says
        whose authority stands behind it, which is the vote this architecture
        exists to avoid."""
        p = self._p({"seat_1": "alpha", "seat_3": "gamma"},
                    {"seat_1": "Contrarian", "seat_3": "Expansionist"})
        assert "seat_1" not in p and "seat_3" not in p

    def test_a_lens_that_did_not_report_is_named_as_a_hole(self):
        """The point of labelling. An unlabelled pile of two paragraphs looks
        complete; naming the missing lenses says plainly that nobody examined
        feasibility, premises, or long-term cost."""
        p = self._p({"seat_1": "alpha", "seat_3": "gamma"},
                    {"seat_1": "Contrarian", "seat_3": "Expansionist"})
        assert "Lenses that did NOT report" in p
        for name in ("First Principles", "Executor", "Steward"):
            assert name in p

    def test_a_full_panel_reports_no_missing_lenses(self):
        texts = {f"seat_{i}": f"t{i}" for i in range(1, 6)}
        personas = {f"seat_{i}": p.name
                    for i, p in zip(range(1, 6), NL.PERSONAS, strict=True)}
        assert "Lenses that did NOT report" not in self._p(texts, personas)

    def test_a_missing_lens_is_framed_as_unexamined_not_as_clean(self):
        """A failure mode nobody looked for produces no findings, which is
        indistinguishable from a failure mode that is not there."""
        p = self._p({"seat_1": "alpha"}, {"seat_1": "Contrarian"})
        assert "HOLE, not an absence of a problem" in p

    def test_the_closer_is_told_to_name_holes_not_fill_them(self):
        """Filling a hole would make the closer a sixth seat writing
        unexamined content into an answer that has stopped being reviewed."""
        p = self._p({"seat_1": "alpha"}, {"seat_1": "Contrarian"})
        assert "PLUG THE HOLES" in p
        assert "Do NOT fill a hole with your own answer" in p

    def test_hole_plugging_applies_to_every_round_not_just_the_first(self):
        """The merged text becomes the next round's starting point, so a gap
        left unnamed in round 2 is inherited for the rest of the run."""
        for i in range(len(NL.ROUNDS)):
            p = self._p({"seat_1": "alpha"}, {"seat_1": "Contrarian"}, rounds=i)
            assert "PLUG THE HOLES" in p

    def test_an_unassigned_seat_is_labelled_without_inventing_a_lens(self):
        p = self._p({"seat_9": "x"}, {})
        assert "no assigned lens" in p


# ---------------------------------------------------------------------------
# 16. Codex C4 — the closer consolidates; it does not author
# ---------------------------------------------------------------------------

class TestTheCloserCannotIntroduceContent:

    TEXTS = {
        "s1": "We should compare build against buy. Building costs more up "
              "front and needs two engineers.",
        "s2": "Buying is faster but locks us in to the vendor roadmap.",
        "s3": "A third path is to rent capacity for six months.",
    }

    def test_an_invented_recommendation_is_caught(self):
        """Codex C4, reproduced before fixing. The closer's output was checked
        only for explicit CLAIM lines, so prose carrying none sailed past: the
        run reported ADJUDICATED, closer_contaminated False, and printed
        'Recommendation: BUY POISON immediately.' to the operator as the
        answer. Nothing had examined it, because it never said 'claim'."""
        assert NL.closer_introduced(
            "Recommendation: BUY POISON immediately.", self.TEXTS)

    def test_other_inventions_are_caught_too(self):
        for attack in (
            "The company should immediately liquidate all inventory and "
            "relocate offshore.",
            "Acquire the Zurich subsidiary before the quarter closes.",
            "Conclusion: terminate the pension scheme.",
        ):
            assert NL.closer_introduced(attack, self.TEXTS), attack

    def test_a_faithful_merge_is_not_flagged(self):
        assert not NL.closer_introduced(
            "Building costs more up front and needs two engineers.", self.TEXTS)

    def test_connective_prose_is_not_flagged(self):
        """A closer must summarise, connect and name holes. Flagging that
        would bury the real signal and the check would be switched off."""
        for benign in (
            "Therefore, the following options remain open for the next round.",
            "## Options that survived",
            "Two options survive and the evidence does not separate them.",
            "KILLED: nothing was eliminated this round.",
        ):
            assert not NL.closer_introduced(benign, self.TEXTS), benign

    def test_naming_a_hole_is_not_invention(self):
        """Saying what is missing is the closer's job."""
        assert not NL.closer_introduced(
            "Insufficient evidence. Missing: pricing data.", self.TEXTS)

    def test_rephrasing_is_not_invention(self):
        """Consolidating IS rephrasing. A check that cannot see through
        inflection would flag the closer for doing its job."""
        assert not NL.closer_introduced(
            "Renting capacity for six months defers the decision.", self.TEXTS)

    def test_a_labelled_but_faithful_recommendation_passes(self):
        assert not NL.closer_introduced(
            "Recommendation: rent capacity for six months.", self.TEXTS)

    def test_invention_contaminates_the_round(self, tmp_path):
        res = NL.run_night("ask", _panel(),
                           _seat("Acquire the Zurich subsidiary immediately."),
                           _orch(), str(tmp_path), rounds=NL.ROUNDS[:1])
        assert res[0].closer_invented
        assert res[0].closer_contaminated is True

    def test_invention_blocks_adjudication(self):
        r = _round(failed=3, rho=0.05)
        r.closer_invented = ["Acquire the Zurich subsidiary."]
        verdict, reasons = NL.run_verdict([r])
        assert verdict == "INCONCLUSIVE"
        assert any("CONTENT NO SEAT PROPOSED" in x for x in reasons)

    def test_the_invented_sentences_reach_disk(self, tmp_path):
        NL.run_night("ask", _panel(),
                     _seat("Acquire the Zurich subsidiary immediately."),
                     _orch(), str(tmp_path), rounds=NL.ROUNDS[:1])
        payload = json.loads(
            (tmp_path / "status.md").read_text().split("```json")[1].split("```")[0])
        assert payload[0]["closer_invented"]
