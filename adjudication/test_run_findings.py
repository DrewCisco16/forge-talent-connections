"""Three defects the first full five-round run exposed, and nothing else could.

WHY THESE ARE TOGETHER. Every one came out of a single paid run of thirty
calls, and each is a case where the machinery reported something other than
what it had established:

  1. A sound option was ELIMINATED over two cents, because the predicate
     evaluator compares exact Fractions and 1666.67 * 6 is 10000.02, not
     10000. It was the only removal in the entire run, so the elimination
     engine's whole measured output for five rounds was one false positive.

  2. Two of twenty-one commitments came back BLOCKED on "unsupported
     expression" for floor() and min(). A blocked commitment can never be
     verified OR refuted, so the options carrying them survived marked
     untested -- a tenth of everything the panel committed to, lost because
     the evaluator could not do floor.

  3. Eighteen commitments PASSED, and all eighteen were an option checking its
     own multiplication: "gives 30, committed equals 30". Twelve options
     survived with those PASSes listed under rulings, which reads as twelve
     answers that were checked and held. Nothing outside any of them had
     tested anything.

The third is the one that matters. The first two are bugs; the third is the
engine measuring the wrong thing and reporting it as scrutiny.
"""
from __future__ import annotations

import ast
import dataclasses
from fractions import Fraction
from typing import ClassVar

import pytest

import adjudication_orchestrator as AO
import option_set as OS
import predicate as P


def _pred(written, value, relation="=", formula="", inputs=(), **kw):
    return P.Predicate(option_id="o1", subject="cost", relation=relation,
                       value=Fraction(value), unit="dollars",
                       written=written, formula=formula,
                       inputs=tuple(inputs), **kw)


# ---------------------------------------------------------------------------
# 1. the two cents that removed a sound answer
# ---------------------------------------------------------------------------

class TestAFigureIsHeldToThePrecisionItWasWrittenIn:

    def test_the_live_false_positive_no_longer_removes_the_option(self):
        """The exact case, from runs/full-20260829-103548:

            monthly_cost * months with (monthly_cost=1666.67, months=6)
            gives 10000.02 dollars, but it committed ... equals 10000 dollars
        """
        pred = _pred("10000", 10000, formula="monthly_cost * months",
                     inputs=(("monthly_cost", Fraction("1666.67")),
                             ("months", Fraction(6))))
        assert P.adjudicate([pred], [])[pred.id].status == "pass"

    def test_a_real_discrepancy_still_fails(self):
        """The fix must not buy the false positive with a false negative. A
        whole unit out at the precision written is still a refutation."""
        pred = _pred("10000", 10000, formula="monthly_cost * months",
                     inputs=(("monthly_cost", Fraction(2000)),
                             ("months", Fraction(6))))
        assert P.adjudicate([pred], [])[pred.id].status == "fail"

    def test_a_seat_that_writes_cents_is_held_to_cents(self):
        """The precision is the SEAT'S. Someone who writes 10000.00 has
        asserted cents and 10000.02 is not that figure."""
        pred = _pred("10000.00", 10000, formula="monthly_cost * months",
                     inputs=(("monthly_cost", Fraction("1666.67")),
                             ("months", Fraction(6))))
        assert P.adjudicate([pred], [])[pred.id].status == "fail"

    @pytest.mark.parametrize("written,value,got,expected", [
        ("30", 30, "30.4", True),
        ("30", 30, "30.6", False),      # rounds to 31
        ("30", 30, "31", False),
        ("0.5", "0.5", "0.5", True),
        ("2.50", "2.5", "2.504", True),
        ("2.50", "2.5", "2.51", False),
    ])
    def test_rounding_is_half_up_at_the_written_place(self, written, value,
                                                      got, expected):
        pred = _pred(written, Fraction(value))
        assert P._holds(pred, Fraction(got)) is expected

    @pytest.mark.parametrize("relation,got,expected", [
        ("<", "30.0", False), ("<", "29.6", True),
        ("<=", "30.0", True), ("<=", "30.4", False),
        (">", "30.0", False), (">", "30.4", True),
        (">=", "30.0", True), (">=", "29.6", False),
    ])
    def test_no_order_relation_is_softened_by_rounding(self, relation, got,
                                                       expected):
        """MUTATION TESTING ADDED THIS. The first version only exercised >=,
        so `"<": same or got < pred.value` -- rounding a value INTO satisfying
        a strict bound -- survived every test in the file. A boundary the seat
        chose is exact on both sides; only equality is read at the written
        precision."""
        pred = _pred("30", 30, relation=relation)
        assert P._holds(pred, Fraction(got)) is expected

    def test_an_order_relation_is_never_rounded_into_holding(self):
        """"at least 12" is a boundary the SEAT chose. Rounding a computed
        11.6 up to 12 would satisfy a bound the arithmetic misses, which is
        the false negative this whole file exists to avoid."""
        pred = _pred("12", 12, relation=">=")
        assert P._holds(pred, Fraction("11.6")) is False
        assert P._holds(pred, Fraction(12)) is True

    def test_a_predicate_with_no_written_form_falls_back_to_exact(self):
        """Nothing constructed in code loses its old behaviour."""
        pred = _pred("", 10000)
        assert P._holds(pred, Fraction("10000.02")) is False


# ---------------------------------------------------------------------------
# 2. floor() and min() are arithmetic
# ---------------------------------------------------------------------------

class TestTheEvaluatorDoesOrdinaryArithmeticFunctions:

    @pytest.mark.parametrize("expr,expected", [
        ("floor(7/2)", 3), ("ceil(7/2)", 4), ("abs(-4)", 4),
        ("min(5, 3, 9)", 3), ("max(5, 3, 9)", 9),
        ("round(2.5)", 3), ("round(1.2345, 2)", Fraction("1.23")),
        ("min(5, floor(9/2))", 4), ("floor(30/7) * 2", 8),
    ])
    def test_it_computes_them_exactly(self, expr, expected):
        assert AO._safe_eval(ast.parse(expr, mode="eval"), expr) == expected

    def test_round_is_half_up_not_bankers(self):
        """Python's round() is half-to-even: round(0.5) is 0 and round(2.5) is
        2. A seat writing round(x) means the schoolroom rule, and a commitment
        refuted on a convention the seat did not intend is a refutation of
        this code's reading rather than of the seat's arithmetic."""
        for expr, expected in (("round(0.5)", 1), ("round(2.5)", 3),
                               ("round(-0.5)", -1)):
            assert AO._safe_eval(ast.parse(expr, mode="eval"), expr) == expected

    @pytest.mark.parametrize("expr", [
        "sqrt(4)", "__import__('os')", "open('x')", "eval('1')",
        "floor(1, 2)", "min()", "abs()", "os.system('x')",
        "floor(x=1)", "min(*[1,2])",
    ])
    def test_nothing_outside_the_allowlist_is_reachable(self, expr):
        """The evaluator still never calls eval(), and the function name must
        be a bare identifier in the map -- no attributes, no keywords, no
        starargs -- so there is no route from an expression to any other
        callable."""
        with pytest.raises(ValueError, match="unsupported expression"):
            AO._safe_eval(ast.parse(expr, mode="eval"), expr)

    def test_a_keyword_argument_is_refused_rather_than_silently_dropped(self):
        """MUTATION TESTING ADDED THIS, and it is the one guard that is not
        redundant. Without the keyword check, `round(2.4, ndigits=2)` still
        evaluates -- node.args holds only 2.4, so the ndigits the seat asked
        for is DISCARDED and the call returns round(2.4) = 2. A commitment
        ruled on a formula quietly different from the one written is worse
        than one refused."""
        with pytest.raises(ValueError, match="unsupported expression"):
            AO._safe_eval(ast.parse("round(2.4, ndigits=2)", mode="eval"), "x")

    def test_a_commitment_using_floor_is_now_ruled_rather_than_blocked(self):
        """The live case: floor(cap / per_round) came back BLOCKED, so the
        option carrying it could never be verified or refuted."""
        pred = _pred("4", 4, formula="floor(cap / per_round)",
                     inputs=(("cap", Fraction(30)), ("per_round", Fraction(7))))
        assert P.adjudicate([pred], [])[pred.id].status == "pass"


# ---------------------------------------------------------------------------
# 3. a PASS on your own multiplication is not scrutiny
# ---------------------------------------------------------------------------

class TestSelfConsistencyIsNotScrutiny:

    @staticmethod
    def _opt(pred):
        opt = OS.Option(id="o1", text="an option")
        opt.predicates = [pred]
        return opt

    SELF: ClassVar[dict] = {"formula": "rounds * per_round",
            "inputs": (("rounds", Fraction(5)), ("per_round", Fraction(6)))}

    def test_an_option_only_checked_against_itself_is_reported_untested(self):
        """The live shape, eighteen times over: 5 * 6 = 30, committed 30."""
        opt = self._opt(_pred("30", 30, **self.SELF))
        rulings = P.adjudicate(opt.predicates, [])
        assert rulings[opt.predicates[0].id].status == "pass"
        assert OS.unexamined([opt], rulings) == [opt]

    def test_surviving_a_dispute_counts_as_tested(self):
        """Without this the warning fires on every survivor forever, and a
        warning that always fires is one an operator learns to ignore."""
        opt = self._opt(_pred("30", 30, **self.SELF))
        pid = opt.predicates[0].id
        rulings = P.adjudicate(opt.predicates,
                               [(pid, {"per_round": Fraction(9)})])
        assert rulings[pid].disputes, "the setup is broken; no dispute recorded"
        assert OS.unexamined([opt], rulings) == []

    def test_a_second_seats_route_to_the_same_figure_counts_as_tested(self):
        opt = self._opt(_pred("30", 30, **self.SELF))
        opt.predicates = [dataclasses.replace(
            opt.predicates[0],
            alternates=(("a * b", (("a", Fraction(3)), ("b", Fraction(10)))),))]
        assert OS.unexamined([opt], P.adjudicate(opt.predicates, [])) == []

    def test_the_pass_is_still_reported_as_a_pass(self):
        """This changes what SURVIVING means, not what the arithmetic found.
        A reader still gets the ruling; it just stops implying scrutiny."""
        opt = self._opt(_pred("30", 30, **self.SELF))
        rulings = P.adjudicate(opt.predicates, [])
        assert rulings[opt.predicates[0].id].status == "pass"
        assert opt.alive is True

    def test_the_run_verdict_carries_the_warning(self):
        """It has to reach the deliverable, not just the data structure."""
        import night_loop as NL
        r = NL.RoundResult(1, "r", eliminative=True)
        r.options_observed = True
        r.options_alive = ["o1"]
        r.options_unexamined = ["o1"]
        r.options_created = 1
        r.options_removed = ["o2"]
        v = NL.assess([r])
        assert any("NEVER TESTED" in c for c in v.caveats)
        assert v.trustworthy is False


# ---------------------------------------------------------------------------
# 4. two seats who agree in different rounds still agree
# ---------------------------------------------------------------------------

class TestChallengesAccumulateAcrossRounds:
    """FOUND BY REPLAYING THE FIVE-ROUND RUN THROUGH THE FIXED CODE.

    Rulings accumulate across rounds and challenges did not, so each round
    ruled on its own challenges alone. Corroboration needs TWO seats to give
    the same value for the same input; checked one round at a time, two seats
    who did exactly that in different rounds never met.

    They are blind to each other across rounds -- what carries forward is the
    surviving option list and its commitments, never anyone's challenge -- so
    agreement in different rounds is the same independent agreement the rule
    is built on.

    Replaying the live run's own eight challenges: ruled round by round they
    remove nothing, ruled together they remove one option.
    """

    OPENING = ("OPTION | run all five rounds\n"
               "PREDICATE | total api calls | = | 30 calls\n"
               "FORMULA | rounds * per_round\n"
               "INPUT | rounds = 5\n"
               "INPUT | per_round = 6\n")

    @staticmethod
    def _panel(same_round):
        """Two seats give the same value for the same input. When same_round
        is False they do it in DIFFERENT rounds, which is the case that used
        to be thrown away."""
        import re
        calls: dict[int, int] = {}

        def make(i):
            def seat(prompt):
                pids = re.findall(r"pred_[0-9a-f]+", prompt)
                if not pids:
                    return TestChallengesAccumulateAcrossRounds.OPENING
                calls[i] = calls.get(i, 0) + 1
                n = calls[i]
                mine = (n == 1) if same_round else (n == i)
                if i in (1, 2) and mine:
                    return f"CHALLENGE | {pids[0]} | per_round = 9\n"
                return "CLAIM | judgment |  | nothing to add\n"
            return seat
        return {f"seat_{i}": make(i) for i in range(1, 6)}

    @staticmethod
    def _run(panel, out):
        import night_loop as NL
        from adjudication_orchestrator import ArithmeticGate, Orchestrator
        return NL.run_night("ask", panel, lambda p: "merged",
                            Orchestrator([ArithmeticGate()]), str(out),
                            rounds=NL.ROUNDS[:3])

    def test_two_seats_agreeing_in_different_rounds_remove_the_option(
            self, tmp_path):
        """seat_1 disputes in round two, seat_2 in round three. 5 * 9 = 45,
        not the 30 committed. Before this, each round ruled on its own
        challenges alone and the two never met."""
        res = self._run(self._panel(same_round=False), tmp_path)
        removed = [o for r in res for o in r.options_removed]
        assert removed, "a cross-round corroborated dispute removed nothing"
        detail = " ".join(rul.detail for r in res
                          for rul in r.rulings.values() if rul.status == "fail")
        assert "agreed by 2 seats" in detail

    def test_the_same_agreement_inside_one_round_still_works(self, tmp_path):
        """The change must not cost the case that already worked."""
        res = self._run(self._panel(same_round=True), tmp_path / "b")
        assert [o for r in res for o in r.options_removed]

    def test_one_seat_disputing_twice_is_still_one_seat(self, tmp_path):
        """THE RISK THIS FIX CREATES, closed. Accumulating challenges must not
        let a SINGLE seat corroborate itself by repeating the same dispute in
        two rounds -- that would hand any seat the power to delete any answer
        by saying the same thing twice, which is the exact defect the
        corroboration rule exists to prevent."""
        import re
        calls = {"n": 0}

        def repeater(prompt):
            pids = re.findall(r"pred_[0-9a-f]+", prompt)
            if not pids:
                return self.OPENING
            calls["n"] += 1
            return f"CHALLENGE | {pids[0]} | per_round = 9\n"

        panel = {"seat_1": repeater}
        panel.update({f"seat_{i}": (lambda p: self.OPENING if "pred_" not in p
                                    else "CLAIM | judgment |  | none\n")
                      for i in range(2, 6)})
        res = self._run(panel, tmp_path / "c")
        assert [o for r in res for o in r.options_removed] == [], (
            "one seat repeating itself across rounds corroborated itself")
