"""Tests for SOP 2.3 (the calibration pass) and 6.2/6.3/6.5/9.3 reporting.

WHAT THESE PIN, AND WHY EACH ONE EXISTS.

The manual says pass five "calibrates confidence and CANNOT RULE ANYTHING
OUT". The live engine gave it the lens "Kill options that require numbers
nobody can derive" and ran `eliminate()` on it like any other round, so the
pass whose job is to say how sure we are was deciding what survives. The other
engine had it right the whole time -- `Pass(eliminative=False)` -- which is
what makes this a drift between two implementations of one spec rather than an
oversight, and drift is exactly what a test file is for.

The reporting tests pin the four quantities SOP 9.1 steps 9-11 tell the
operator to read before committing. They were computable and unreachable from
this engine, which is a worse failure than absent: a packet reported a
survivor while the manual's own stop rule said DO NOT COMMIT, and nothing on
the page said so.

Every test names the failure it prevents. Each was verified to FAIL against
the implementation with its fix removed -- a regression that passes on a
broken build is worse than no test, because it is read as coverage.
"""
from __future__ import annotations

import convergence as CV
import night_loop as NL
from adjudication_orchestrator import ArithmeticGate, Claim, ClaimKind, Orchestrator


def _orch() -> Orchestrator:
    return Orchestrator([ArithmeticGate()])


def _seat(reply: str, log: list | None = None):
    def fn(prompt: str) -> str:
        if log is not None:
            log.append(prompt)
        return reply
    return fn


class _Ruling:
    def __init__(self, status: str, detail: str = "") -> None:
        self.status, self.detail = status, detail


def _round(n, **kw):
    eliminative = kw.get("eliminative", True)
    rulings = kw.get("rulings")
    challenges_by_seat = kw.get("challenges_by_seat")
    rho = kw.get("rho")
    divergence = kw.get("divergence")
    collapse = kw.get("collapse")
    alive = kw.get("alive", ("o1",))
    unexamined = kw.get("unexamined", ())
    observed = kw.get("observed", True)
    failed_seats = kw.get("failed_seats")
    r = NL.RoundResult(n, f"round {n}", eliminative=eliminative)
    r.rulings = rulings or {}
    r.challenges_by_seat = challenges_by_seat or {}
    r.rho = rho
    r.divergence = divergence
    r.collapse_warning = collapse
    r.options_alive = list(alive)
    r.options_unexamined = list(unexamined)
    r.options_observed = observed
    r.thinkers_failed = failed_seats or {}
    return r


# ---------------------------------------------------------------------------
# 1. SOP 2.3 -- the fifth pass calibrates and cannot rule anything out
# ---------------------------------------------------------------------------

class TestTheCalibrationPassCannotEliminate:

    def test_round_five_is_declared_non_eliminative(self):
        """SOP 2.3: "five passes, four of which can eliminate. The fifth
        calibrates confidence and cannot rule anything out." """
        assert [r.eliminates for r in NL.ROUNDS] == [True, True, True, True, False]

    def test_exactly_four_rounds_may_eliminate(self):
        assert sum(1 for r in NL.ROUNDS if r.eliminates) == 4

    def test_the_calibration_lens_does_not_ask_seats_to_kill(self):
        """The lens said "Kill options that require numbers nobody can
        derive". A seat that believes it is eliminating writes to eliminate,
        and what it writes is what gets recomputed."""
        assert "kill" not in NL.ROUNDS[4].lens.lower()

    def test_the_calibration_prompt_says_it_removes_nothing(self):
        p = NL.thinker_prompt(NL.ROUNDS[4], "the ask", "working answer")
        assert "REMOVES NOTHING" in p

    def test_the_calibration_prompt_does_not_claim_to_eliminate(self):
        """It was handed the same "This round only eliminates." line as rounds
        two to four -- the direct contradiction of SOP 2.3."""
        p = NL.thinker_prompt(NL.ROUNDS[4], "the ask", "working answer")
        assert "only eliminates" not in p

    def test_eliminative_rounds_still_say_they_eliminate(self):
        """The fix must not silence rounds two to four, which DO remove."""
        for r in NL.ROUNDS[1:4]:
            assert "only eliminates" in NL.thinker_prompt(r, "ask", "merged")

    def test_the_two_engines_agree_about_which_pass_calibrates(self):
        """The drift this file exists to stop. `Pass.eliminative` in the other
        engine and `Round.eliminates` here are one rule in two places; if they
        ever disagree, one of the two engines is not the specified tool."""
        from adjudication_orchestrator import DEFAULT_PASSES
        assert ([p.eliminative for p in DEFAULT_PASSES]
                == [r.eliminates for r in NL.ROUNDS])

    def test_a_refutation_in_the_calibration_round_does_not_remove(self, tmp_path):
        """The behavioural test, through the real engine.

        THE FIRST VERSION OF THIS TEST WAS VACUOUS AND MUTATION TESTING SAID
        SO. It gave the option arithmetic that did not add up, so round one's
        self-check removed it immediately; by round five there was nothing
        alive to remove and `options_removed == []` held whether the guard
        existed or not. Deleting the guard left it green.

        So the option must SURVIVE round one on its own arithmetic, and the
        refutation must arrive in round five -- which is the only shape that
        exercises the rule. Two seats challenge the same input, corroboration
        outweighs the proposer, the recomputation fails, and the option must
        STILL be standing: fail closed on the conclusion, never on the
        candidate.
        """
        import re

        # 1 * 6 = 6. It holds, so round one keeps it.
        opening = ("OPTION | ship it\n"
                   "PREDICATE | total cost | = | 6 dollars\n"
                   "FORMULA | rounds * per_round\n"
                   "INPUT | rounds = 1\n"
                   "INPUT | per_round = 6\n")

        def challenger(prompt: str) -> str:
            """Reads the commitment id out of its own prompt, as a live seat
            must, and disputes an input. 2 * 6 = 12, not the 6 committed."""
            found = re.findall(r"pred_[0-9a-f]+", prompt)
            if not found:
                return opening
            return f"CHALLENGE | {found[0]} | rounds = 2\n"

        seats = {f"seat_{i}": challenger for i in range(1, 6)}
        calib = NL.Round(5, "Bayesian + MCMC", "calibrate", eliminates=False)
        res = NL.run_night("ask", seats, _seat("merged"), _orch(),
                           str(tmp_path), rounds=(NL.ROUNDS[0], calib))

        assert res[0].options_removed == [], (
            "round one must KEEP it: its own arithmetic holds")
        assert res[1].challenges >= 2, (
            "the setup is broken if the challenges never landed")
        assert any(r.status == "fail" for r in res[1].rulings.values()), (
            "the setup is broken if corroboration did not refute it")
        assert res[1].options_removed == [], (
            "SOP 2.3: the calibration pass cannot rule anything out")
        assert res[1].options_alive, "the option must still be standing"
        assert res[1].calibration_findings, (
            "the refutation must be RECORDED even though it may not act")

    def test_a_calibration_finding_becomes_a_caveat(self):
        """It must not vanish because the pass that found it may not act on
        it. That would be the worst of both: the pass cannot act, so nobody
        hears about it."""
        r1 = _round(1)
        r5 = _round(5, eliminative=False)
        r5.calibration_findings = ["o1: 1 * 6 = 6, not 12"]
        v = NL.assess([r1, r5])
        assert any("CALIBRATION ROUND" in c for c in v.caveats)
        assert any("1 * 6 = 6" in c for c in v.caveats)

    def test_a_calibration_caveat_makes_the_run_untrustworthy(self):
        r5 = _round(5, eliminative=False)
        r5.calibration_findings = ["o1: refuted"]
        assert NL.assess([_round(1), r5]).trustworthy is False


# ---------------------------------------------------------------------------
# 2. SOP 6.3 -- the decay curve over VERIFIED CORRECTIONS
# ---------------------------------------------------------------------------

class TestTheDecayCurve:

    def test_only_gate_failures_count_as_yield(self):
        """Defect 6 in the manual's own log: feeding accepted claims in made a
        pass that confirmed ten true claims and caught nothing report a yield
        of ten, so the residual never decayed."""
        r = _round(1, rulings={"a": _Ruling("pass"), "b": _Ruling("pass"),
                               "c": _Ruling("fail")})
        assert CV.analyse([r]).yields == [1.0]

    def test_a_correction_is_counted_once_in_the_round_it_was_settled(self):
        """Rulings ACCUMULATE across rounds: `RoundResult.rulings` carries
        everything settled so far. Counting FAILs straight out of it reports
        the same refutation in every later round, which turns a decaying
        series into a flat or rising one -- and the residual then never falls
        below tolerance however well the run converged."""
        r1 = _round(1, rulings={"a": _Ruling("fail")})
        r2 = _round(2, rulings={"a": _Ruling("fail"), "b": _Ruling("fail")})
        r3 = _round(3, rulings={"a": _Ruling("fail"), "b": _Ruling("fail")})
        assert CV.analyse([r1, r2, r3]).yields == [1.0, 1.0, 0.0]

    def test_the_calibration_round_is_excluded_from_the_fit(self):
        """It is not a round that found nothing. It is a round that could not
        look, and a zero from it drags the curve toward a false convergence.
        The manual's worked example fits FOUR yields for FIVE passes."""
        rounds = [_round(n, rulings={f"p{n}": _Ruling("fail")})
                  for n in (1, 2, 3, 4)]
        rounds.append(_round(5, eliminative=False,
                             rulings={f"p{n}": _Ruling("fail")
                                      for n in (1, 2, 3, 4)}))
        assert len(CV.analyse(rounds).yields) == 4

    def test_a_single_data_point_is_not_a_curve(self):
        c = CV.analyse([_round(1, rulings={"a": _Ruling("fail")})])
        assert c.fit is None and c.residual is None
        assert any("not decaying" in b for b in c.blockers)

    def test_yields_that_do_not_decay_block_the_stop(self):
        rounds = [_round(1, rulings={"a": _Ruling("fail")}),
                  _round(2, rulings={"a": _Ruling("fail"),
                                     "b": _Ruling("fail"), "c": _Ruling("fail")})]
        c = CV.analyse(rounds)
        assert c.residual is None
        assert c.stop is False


# ---------------------------------------------------------------------------
# 3. SOP 6.3 -- the stop rule is a CONJUNCTION
# ---------------------------------------------------------------------------

class TestTheStopRule:

    def test_an_uncalibrated_singleton_alarm_is_not_armed(self):
        """SOP 8.4: "Set your singleton-fraction alarm. Until you do, that
        check is not armed." An unarmed condition in a conjunction cannot be
        satisfied. Treating it as met lets a run stop on a condition nobody
        ever set, which is the fail-OPEN reading."""
        c = CV.analyse([_round(1)], singleton_alarm=None)
        assert any("NOT ARMED" in b for b in c.blockers)

    def test_a_pending_queue_blocks_however_low_the_residual(self):
        """SOP 6.3: "A low residual is not permission to commit." SOP 10 lists
        an unworked queue as a do-not-build condition."""
        rounds = [_round(1, rulings={f"a{i}": _Ruling("fail") for i in range(9)}),
                  _round(2, rulings={**{f"a{i}": _Ruling("fail") for i in range(9)},
                                     "b": _Ruling("fail")})]
        c = CV.analyse(rounds, escalations_pending=3, singleton_alarm=0.9)
        assert any("judgment queue" in b for b in c.blockers)
        assert c.stop is False

    def test_the_exit_code_is_non_zero_while_any_hole_remains(self):
        """SOP 9.1 step 11 and 9.3: "One surviving candidate with an open
        judgment queue is a shortlist, not an answer, and the exit code says
        so without requiring you to read anything." """
        c = CV.analyse([_round(1, unexamined=("o1",))], singleton_alarm=0.9)
        assert c.holes and c.exit_code == 1

    def test_every_hole_names_what_would_close_it(self):
        """SOP 9.3: "a hole you cannot act on is a disclaimer"."""
        c = CV.analyse([_round(1, alive=("o1", "o2"), unexamined=("o2",),
                               failed_seats={"seat_3": "timeout"},
                               collapse="they agreed exactly")],
                       escalations_pending=2)
        assert c.holes
        for h in c.holes:
            assert h.remedy.strip(), f"hole {h.kind!r} has no remedy"


# ---------------------------------------------------------------------------
# 4. SOP 6.5 -- unanimity is an alarm, silence is not collapse
# ---------------------------------------------------------------------------

def _claim(warrant: str) -> Claim:
    return Claim(id="", text=f"text for {warrant}",
                 kind=ClaimKind.ARITHMETIC, warrant=warrant)


class TestDivergence:

    def test_identical_claim_sets_raise_a_collapse_flag(self):
        seats = {"a": [_claim("2 + 2 = 4")], "b": [_claim("2 + 2 = 4")]}
        j, unanimous, silent, warning = CV.divergence(seats)
        assert j == 1.0 and unanimous and not silent
        assert warning is not None

    def test_every_seat_silent_is_not_a_collapse(self):
        """SOP 6.5: the sets are trivially identical, but that is the
        marginal-yield signal, not a monoculture one. "A warning that fires on
        every empty pass is one operators learn to ignore." """
        _j, _unanimous, silent, warning = CV.divergence({"a": [], "b": []})
        assert silent is True and warning is None

    def test_claims_are_compared_on_content_not_on_wording(self):
        """SOP 6.5 compares on (kind, warrant), so two seats phrasing the same
        finding differently register as AGREEMENT. Comparing on the claim id
        folds in the text and would score them as two separate findings."""
        a = Claim(id="", text="the sum is four",
                  kind=ClaimKind.ARITHMETIC, warrant="2 + 2 = 4")
        b = Claim(id="", text="adding two and two gives four",
                  kind=ClaimKind.ARITHMETIC, warrant="2 + 2 = 4")
        assert a.id != b.id, "different text should give different ids"
        j, unanimous, _, _ = CV.divergence({"a": [a], "b": [b]})
        assert j == 1.0 and unanimous

    def test_disjoint_claim_sets_score_zero(self):
        j, unanimous, _, warning = CV.divergence(
            {"a": [_claim("2 + 2 = 4")], "b": [_claim("3 + 3 = 6")]})
        assert j == 0.0 and not unanimous and warning is None

    def test_one_seat_cannot_be_measured_for_divergence(self):
        j, _, _, _ = CV.divergence({"a": [_claim("2 + 2 = 4")]})
        assert j is None, "one seat has no pair; that is unmeasurable, not zero"


# ---------------------------------------------------------------------------
# 5. SOP 6.2 -- capture-recapture over SEAT detections
# ---------------------------------------------------------------------------

class TestCaptureRecapture:

    def test_a_detection_is_a_seat_challenge_that_was_then_refuted(self):
        r = _round(1, rulings={"p1": _Ruling("fail"), "p2": _Ruling("pass")},
                   challenges_by_seat={"seat_1": ["p1", "p2"],
                                       "seat_2": ["p1"]})
        det = CV.detections_by_seat([r])
        assert det == {"seat_1": {"p1"}, "seat_2": {"p1"}}

    def test_code_found_refutations_are_not_credited_to_any_seat(self):
        """An option refuted by its OWN arithmetic was caught by code, not by
        a seat. Folding those in inflates the observed count with detections
        no seat made, which biases the estimate of what the seats are MISSING
        downward -- the one direction that matters, since the estimator exists
        to count what nobody caught."""
        r = _round(1, rulings={"self": _Ruling("fail")}, challenges_by_seat={})
        assert CV.detections_by_seat([r]) == {}
        assert CV.analyse([r]).capture is None

    def test_the_singleton_fraction_is_reported_with_rho_beside_it(self):
        """SOP 6.2 is a standing order, not a footnote: "Never read this
        estimator without rho beside it. At rho = 1.0 its output carries no
        information at all." """
        r = _round(1, rulings={"p1": _Ruling("fail")},
                   challenges_by_seat={"seat_1": ["p1"]})
        text = "\n".join(CV.render(CV.analyse([r])))
        assert "singleton fraction" in text
        assert "RHO BESIDE IT" in text.upper()


# ---------------------------------------------------------------------------
# 6. the rendered block a reader actually sees
# ---------------------------------------------------------------------------

class TestTheRenderedBlock:

    def test_an_unmeasurable_quantity_says_so_rather_than_showing_zero(self):
        text = "\n".join(CV.render(CV.analyse([_round(1)])))
        assert "NOT MEASURABLE" in text

    def test_it_names_the_two_halves_of_the_commit_rule(self):
        """SOP 9.3: "An answer is resolved only when one candidate survives
        AND no holes remain. Both halves." """
        text = "\n".join(CV.render(CV.analyse([_round(1)])))
        assert "no hole remain" in text.lower()

    def test_the_packet_carries_the_convergence_block(self, tmp_path):
        reply = ("OPTION | an answer\n"
                 "CLAIM | arithmetic | 2 + 2 = 4 | it adds up\n")
        seats = {f"seat_{i}": _seat(reply) for i in range(1, 6)}
        orch = _orch()
        res = NL.run_night("ask", seats, _seat("merged"), orch,
                           str(tmp_path), rounds=NL.ROUNDS[:1])
        path = NL.write_verifier_packet(str(tmp_path), "ask", "merged", orch,
                                        rounds_run=res)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        assert "stop rule" in text.lower()
        assert "SOP 9.3" in text
