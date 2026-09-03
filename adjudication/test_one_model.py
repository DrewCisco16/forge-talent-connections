"""Tests for one model plus gates -- the mode Stage 0 measured us into.

THE LOAD-BEARING PROPERTY. Dropping from five seats to one must keep
self-refutation and must lose corroboration, and it must SAY it lost it. A
one-seat run that quietly reported panel diagnostics would be describing the
absence of a panel as agreement, which is the same class of error as every
other defect this project has found.
"""
from __future__ import annotations

import adjudication_orchestrator as AO
import one_model as OM


def _gates():
    return [AO.ArithmeticGate()]


SOUND = ("OPTION | rent capacity for six months\n"
         "PREDICATE | fixed cost | = | 10000 dollars\n"
         "FORMULA | monthly_cost * months\n"
         "INPUT | monthly_cost = 1666.67\n"
         "INPUT | months = 6\n")

BROKEN = ("OPTION | run all five rounds\n"
          "PREDICATE | total api calls | = | 30 calls\n"
          "FORMULA | rounds * per_round\n"
          "INPUT | rounds = 5\n"
          "INPUT | per_round = 7\n")


class TestSelfRefutationSurvivesTheDropToOneSeat:

    def test_one_seat_still_removes_an_answer_on_its_own_arithmetic(self):
        """THE REASON THIS FILE EXISTS. 5 * 7 = 35, not the 30 committed. No
        other seat is involved and none is needed: it is the model's own
        formula against the model's own figure, and it is the only removal
        mechanism that ever worked correctly in this project."""
        r = OM.check("q", lambda p: BROKEN, gates=_gates())
        assert r.options_removed, "one seat must still catch its own bad sum"
        assert r.options_standing == []
        assert "35" in r.options_removed[0][1]

    def test_a_sound_answer_stands(self):
        """1666.67 * 6 is 10000.02, which rounds to the 10000 written. The
        precision fix has to hold here too, or the instrument removes correct
        answers over fractions of a cent."""
        r = OM.check("q", lambda p: SOUND, gates=_gates())
        assert r.options_removed == []
        assert len(r.options_standing) == 1

    def test_an_answer_with_no_commitment_is_untested_not_verified(self):
        """UNTESTED IN THE STRONG SENSE: nothing about it could be computed,
        so nothing was. That blocks resolution."""
        r = OM.check("q", lambda p: "OPTION | just do it\n", gates=_gates())
        assert r.options_standing, "it should still stand"
        assert r.options_untested, "and it must be reported as never tested"
        assert r.resolved is False

    def test_a_fully_ruled_answer_is_not_flagged_untested(self):
        """The other half. `unexamined` requires evidence from OUTSIDE the
        option, which one seat can never supply -- so reusing it here made
        every answer permanently untested and the exit code carried no
        information. The standing limit is stated unconditionally in section 4
        instead."""
        r = OM.check("q", lambda p: SOUND, gates=_gates())
        assert r.options_untested == []

    def test_the_report_always_says_nothing_was_externally_tested(self):
        text = "\n".join(OM.render(OM.check("q", lambda p: SOUND, gates=_gates())))
        assert "TESTED BY ANYTHING OUTSIDE ITSELF" in text


class TestItNeverClaimsWhatOneSeatCannotSupport:

    def test_the_report_says_there_is_no_panel(self):
        text = "\n".join(OM.render(OM.check("q", lambda p: SOUND, gates=_gates())))
        assert "ONE MODEL" in text
        assert "UNDEFINED at one seat" in text

    def test_it_reports_no_correlation_divergence_or_effective_seats(self):
        """At n=1 these are undefined, not zero. A one-seat run printing
        'divergence = 0.00' would read as agreement where there is no panel."""
        text = "\n".join(OM.render(OM.check("q", lambda p: SOUND, gates=_gates())))
        import re
        # A NUMBER beside one of those names, not the name itself -- section 4
        # names them precisely to say they are undefined here, and the first
        # version of this test tripped on that disclaimer.
        for pattern in (r"rho\s*=\s*[-\d]", r"divergence\s*=\s*[-\d]",
                        r"effective seats?\s*[:=]\s*[\d]",
                        r"worth\s+[\d.]+\s+independent"):
            assert not re.search(pattern, text, re.IGNORECASE), (
                f"a one-seat run must not report {pattern!r}")

    def test_the_answer_section_does_not_invite_a_challenge(self):
        """FOUND BY READING THE OUTPUT, which is how the round-five contract
        defect was found too. render_record prints the panel's CHALLENGE
        instructions -- how to dispute an input, and that agreement between
        seats is what carries weight. With one seat that mechanism cannot
        operate, and section 4 of this same report says so. A deliverable
        contradicting itself between section 3 and section 4 is worse than
        either half alone."""
        text = "\n".join(OM.render(OM.check("q", lambda p: SOUND, gates=_gates())))
        assert "CHALLENGE | <commitment id>" not in text
        assert "two seats put" not in text
        assert "Options still standing" in text, "the answer must still print"

    def test_the_panel_still_gets_its_challenge_instructions(self):
        """The suppression must be opt-in. Removing it from the panel would
        take away the only line a seat can write to dispute an input."""
        import option_set as OS
        opts = OS.parse_proposals({"seat_1": SOUND})
        assert "CHALLENGE | <commitment id>" in OS.render_working(opts)
        assert "CHALLENGE | <commitment id>" not in OS.render_working(
            opts, invite_challenges=False)

    def test_it_says_corroboration_is_unavailable(self):
        text = "\n".join(OM.render(OM.check("q", lambda p: SOUND, gates=_gates())))
        assert "NO CORROBORATION" in text

    def test_it_says_a_verified_claim_is_not_a_true_answer(self):
        text = "\n".join(OM.render(OM.check("q", lambda p: SOUND, gates=_gates())))
        assert "NOT A TRUE ANSWER" in text.upper()


class TestTheGatesStillRule:

    def test_a_false_arithmetic_claim_is_refuted(self):
        reply = SOUND + "CLAIM | arithmetic | 3 + 1 = 5 | the total is 5 units\n"
        r = OM.check("q", lambda p: reply, gates=_gates())
        assert r.failed, "the gate must refute 3 + 1 = 5"
        assert "recomputed 4" in r.failed[0][1]

    def test_a_true_arithmetic_claim_is_recorded_with_its_evidence(self):
        reply = SOUND + "CLAIM | arithmetic | 3 + 1 = 4 | the total is 4 units\n"
        r = OM.check("q", lambda p: reply, gates=_gates())
        settled = r.passed + r.warrant_held
        assert settled, "a holding warrant must be recorded"
        assert settled[0][1], "and it must carry the gate's evidence"

    def test_a_judgment_claim_is_routed_to_the_operator(self):
        reply = SOUND + "CLAIM | judgment |  | this turns on how the contract reads\n"
        r = OM.check("q", lambda p: reply, gates=_gates())
        assert r.open_items, "a judgment claim has no gate and must reach a person"
        assert r.resolved is False

    def test_blocked_is_reported_as_not_evidence_against(self):
        reply = SOUND + "CLAIM | arithmetic | sqrt(81) = 9 | nine\n"
        r = OM.check("q", lambda p: reply, gates=_gates())
        text = "\n".join(OM.render(r))
        if r.blocked:
            assert "NOT evidence against" in text


class TestTheReadOrderAndTheExitCode:

    def test_gate_results_come_before_the_answer(self):
        """SOP 9.1 step 4. Dell'Acqua et al. found wrong answers from AI users
        were graded MORE coherent, so prose first is how a polished error gets
        committed."""
        text = "\n".join(OM.render(OM.check("q", lambda p: SOUND, gates=_gates())))
        assert text.index("WHAT THE GATES FOUND") < text.index("3. THE ANSWER")

    def test_a_clean_single_answer_resolves_and_exits_zero(self):
        r = OM.check("q", lambda p: SOUND, gates=_gates())
        assert r.resolved is True and r.exit_code == 0

    def test_a_refuted_claim_blocks_resolution_even_with_one_answer(self):
        """A claim proven false alongside a standing answer is exactly what an
        operator must not miss."""
        reply = SOUND + "CLAIM | arithmetic | 2 + 2 = 5 | four is five\n"
        r = OM.check("q", lambda p: reply, gates=_gates())
        assert r.failed and r.resolved is False and r.exit_code == 1

    def test_two_answers_standing_does_not_resolve(self):
        r = OM.check("q", lambda p: SOUND + BROKEN.replace("per_round = 7",
                                                            "per_round = 6"),
                     gates=_gates())
        assert len(r.options_standing) == 2
        assert r.resolved is False

    def test_nothing_checkable_says_so_rather_than_reading_as_clean(self):
        r = OM.check("q", lambda p: "I think you should just proceed.",
                     gates=_gates())
        text = "\n".join(OM.render(r))
        assert "NOTHING WAS MECHANICALLY CHECKED" in text
        assert r.exit_code == 1

    def test_an_unparseable_reply_does_not_crash(self):
        r = OM.check("q", lambda p: "OPTION |\nPREDICATE | | | \n", gates=_gates())
        assert r.exit_code == 1
