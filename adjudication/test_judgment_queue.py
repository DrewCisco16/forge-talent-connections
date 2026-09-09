"""Tests for the judgment queue -- SOP 9.1 steps 7-8, 6.3 condition 3, 6.6.

WHY THIS FILE IS STRICT. SOP 10 lists "you will not work the escalation queue"
as a do-not-build condition, and until now there was no way to work it: the
first full five-round run produced 136 claims no gate decided, they were
printed as prose, and nothing read them back. So rho was UNMEASURED in every
round of every run, effective seat count was undefined, and the stop rule
could never be satisfied.

The failure modes worth pinning are the ones that would produce a PLAUSIBLE
number: a human decision quietly overriding a gate, a correlation computed
over too few items, decisions lost on rewrite.
"""
from __future__ import annotations

import json

import pytest

import judgment_queue as Q
from adjudication_orchestrator import ArithmeticGate


def _reply(seat: str) -> str:
    """One claim every seat makes IDENTICALLY -- so the content ids collide,
    which is what gives the matrix a common item -- and one that is that
    seat's alone."""
    lines = [
        # WARRANT_HELD: the arithmetic holds, the sentence it was offered for
        # is open. Every seat writes it identically so the ids collide.
        "CLAIM | arithmetic | 2 + 2 = 4 | two and two make four",
        # PASS: the claim's TEXT is itself the assertion, so the gate rules on
        # the claim rather than on a warrant offered for it.
        "CLAIM | arithmetic | 2 + 2 = 4 | 2 + 2 = 4",
        # FAIL: same shape, and wrong.
        "CLAIM | arithmetic | 2 + 3 = 6 | 2 + 3 = 6",
    ]
    lines += [f"CLAIM | judgment |  | opinion {i} from seat {seat}"
              for i in range(3)]
    return "\n".join(lines) + "\n"


@pytest.fixture()
def run(tmp_path):
    """A minimal run directory of the shape night_loop writes."""
    d = tmp_path / "full-test"
    (d / "round-1").mkdir(parents=True)
    for i in (1, 2, 3):
        (d / "round-1" / f"thinker-seat_{i}.md").write_text(_reply(f"{i}"))
    return str(d)


class TestReplayReproducesTheRunOffline:

    def test_it_costs_nothing_and_reaches_the_same_verdicts(self, run):
        """A queue built from a remembered verdict could disagree with the run
        it claims to describe, and nobody would be able to tell."""
        rep = Q.replay(run, gates=[ArithmeticGate()])
        assert rep.seats == ["seat_1", "seat_2", "seat_3"]
        # three arithmetic claims all three seats make identically, plus
        # three judgment claims each: 3 + 9 = 12 distinct.
        assert len(rep.claims) == 12
        assert len(rep.orch.verdicts) == 12

    def test_it_records_which_seats_asserted_each_claim(self, run):
        """SOP 6.6 needs this: a cell says whether that SEAT took the
        position, not whether the claim held."""
        rep = Q.replay(run, gates=[ArithmeticGate()])
        shared = [cid for cid, s in rep.proposers.items() if len(s) == 3]
        assert len(shared) == 3, (
            "the three identically-worded arithmetic claims should collide "
            "into one item each, asserted by all three seats")
        alone = [cid for cid, s in rep.proposers.items() if len(s) == 1]
        assert len(alone) == 9, "each seat's own judgment claims stay separate"

    def test_a_run_with_no_replies_is_refused(self, tmp_path):
        (tmp_path / "empty").mkdir()
        with pytest.raises(Q.QueueError, match="no thinker replies"):
            Q.replay(str(tmp_path / "empty"))


class TestOnlyUndecidedClaimsAreOffered:

    def test_a_gate_verdict_never_reaches_the_queue(self, run):
        """PASS and FAIL are settled. Offering them invites an override."""
        rep = Q.replay(run, gates=[ArithmeticGate()])
        offered = {c.id for c in Q.open_items(rep)}
        for cid, v in rep.orch.verdicts.items():
            if v.status in (Q.GateStatus.PASS, Q.GateStatus.FAIL):
                assert cid not in offered

    def test_warrant_held_IS_offered(self, run):
        """The gate confirmed the EVIDENCE and said nothing about the
        proposition it was offered for. That is precisely a judgement call and
        precisely what this queue is for."""
        rep = Q.replay(run, gates=[ArithmeticGate()])
        held = [cid for cid, v in rep.orch.verdicts.items()
                if v.status is Q.GateStatus.WARRANT_HELD]
        offered = {c.id for c in Q.open_items(rep)}
        assert held and all(cid in offered for cid in held)


class TestAHumanMayNotOverrideAGate:

    def test_a_decision_on_a_settled_claim_is_refused(self, run, tmp_path):
        """SOP 6.6: overriding a gate moves authority from the mechanical
        bottleneck back to a judgement call, which is the failure this
        architecture exists to prevent."""
        rep = Q.replay(run, gates=[ArithmeticGate()])
        settled = [cid for cid, v in rep.orch.verdicts.items()
                   if v.status in (Q.GateStatus.PASS, Q.GateStatus.FAIL)]
        assert settled, ("the fixture must produce a settled claim or this "
                         "refusal is never exercised")
        path = tmp_path / "q.json"
        path.write_text(json.dumps(
            {"items": [{"id": settled[0], "true": False}]}))
        with pytest.raises(Q.QueueError, match="only a claim NO gate decided"):
            Q.read_decisions(rep, str(path))

    def test_an_unknown_claim_id_is_refused(self, run, tmp_path):
        rep = Q.replay(run, gates=[ArithmeticGate()])
        path = tmp_path / "q.json"
        path.write_text(json.dumps({"items": [{"id": "nope", "true": True}]}))
        with pytest.raises(Q.QueueError, match="no such claim"):
            Q.read_decisions(rep, str(path))

    def test_a_non_boolean_decision_is_refused(self, run, tmp_path):
        rep = Q.replay(run, gates=[ArithmeticGate()])
        cid = Q.open_items(rep)[0].id
        path = tmp_path / "q.json"
        path.write_text(json.dumps({"items": [{"id": cid, "true": "yes"}]}))
        with pytest.raises(Q.QueueError, match="must be true, false or null"):
            Q.read_decisions(rep, str(path))

    def test_null_stays_open_rather_than_being_guessed(self, run, tmp_path):
        """SOP 6.6: defaulting an unknown invents a measurement, and the
        direction of the invention biases rho in a known way."""
        rep = Q.replay(run, gates=[ArithmeticGate()])
        cid = Q.open_items(rep)[0].id
        path = tmp_path / "q.json"
        path.write_text(json.dumps({"items": [{"id": cid, "true": None}]}))
        assert Q.read_decisions(rep, str(path)) == {}


class TestDecisionsAreNotLost:

    def test_rewriting_the_queue_preserves_decisions_already_made(self, run):
        """--open is run again whenever a run is revisited. Losing work
        already done would make the file unsafe to regenerate, and an operator
        who loses 136 judgments once does not do them a second time."""
        rep = Q.replay(run, gates=[ArithmeticGate()])
        path = Q.write_queue(rep)
        with open(path, encoding="utf-8") as fh:
            blob = json.load(fh)
        blob["items"][0]["true"] = True
        kept = blob["items"][0]["id"]
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(blob, fh)
        Q.write_queue(rep)
        with open(path, encoding="utf-8") as fh:
            again = json.load(fh)
        row = next(r for r in again["items"] if r["id"] == kept)
        assert row["true"] is True

    def test_an_unreadable_queue_file_is_refused_not_overwritten(self, run):
        rep = Q.replay(run, gates=[ArithmeticGate()])
        path = Q.write_queue(rep)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{ not json")
        with pytest.raises(Q.QueueError, match="cannot be read"):
            Q.write_queue(rep)


class TestTheFoldedNumbers:

    def _rep(self, run):
        return Q.replay(run, gates=[ArithmeticGate()])

    def test_too_few_items_names_rho_in_words_rather_than_printing_one(
            self, run):
        """SOP 6.6 fails closed here: "A rho that is genuinely undefined is
        named in words." And the floor is the OTHER engine's floor, imported
        rather than re-chosen -- two engines carrying two floors for one
        quantity is the drift that put 'Kill options' in the calibration
        round."""
        from night_loop import MIN_SHARED_ITEMS_FOR_RHO
        rep = self._rep(run)
        # One decision: enough to have an item, far short of the floor.
        folded = Q.fold(rep, {Q.open_items(rep)[0].id: True})
        assert 0 < folded.n_items < MIN_SHARED_ITEMS_FOR_RHO
        assert folded.rho is None
        text = "\n".join(Q.render(folded))
        assert "NOT MEASURABLE" in text
        assert str(MIN_SHARED_ITEMS_FOR_RHO) in text

    def test_working_the_queue_is_what_makes_rho_measurable(self, run):
        """The whole point. rho was UNMEASURED in every round of every run
        because a claim no gate decided has no truth value until a person
        supplies one."""
        rep = self._rep(run)
        assert Q.fold(rep, {}).rho is None
        decisions = {c.id: True for c in Q.open_items(rep)}
        folded = Q.fold(rep, decisions)
        assert folded.rho is not None
        assert folded.n_eff is not None
        assert folded.n_from_human == len(decisions)

    def test_fewer_than_two_seats_cannot_have_a_correlation(self, tmp_path):
        d = tmp_path / "one"
        (d / "round-1").mkdir(parents=True)
        (d / "round-1" / "thinker-seat_1.md").write_text(_reply("1"))
        rep = Q.replay(str(d), gates=[ArithmeticGate()])
        folded = Q.fold(rep, {c.id: True for c in Q.open_items(rep)})
        assert folded.rho is None
        assert any("two seats" in b for b in folded.blockers)

    def test_an_open_item_blocks_the_commit_however_good_the_numbers(
            self, run):
        """SOP 6.3 condition 3. A low rho is not permission to commit."""
        rep = self._rep(run)
        items = Q.open_items(rep)
        folded = Q.fold(rep, {c.id: True for c in items[:-1]})
        assert folded.still_open >= 1
        assert "may not be committed" in "\n".join(Q.render(folded))

    def test_the_report_says_how_it_scores_silence(self, run):
        """The manual and night_loop.measure_rho disagree about this, and the
        number means different things under each. A reader must be told which
        one produced it rather than left to assume."""
        rep = self._rep(run)
        text = "\n".join(Q.render(
            Q.fold(rep, {c.id: True for c in Q.open_items(rep)})))
        assert "scores silence" in text.lower()
        assert "measure_rho" in text

    @staticmethod
    def _panel(tmp_path, name, per_seat):
        d = tmp_path / name
        (d / "round-1").mkdir(parents=True)
        for seat, lines in per_seat.items():
            (d / "round-1" / f"thinker-{seat}.md").write_text(
                "".join(f"CLAIM | judgment |  | {t}\n" for t in lines))
        return Q.replay(str(d), gates=[ArithmeticGate()])

    def test_maximum_independence_reproduces_the_manuals_worked_extreme(
            self, tmp_path):
        """SOP 6.6 pins this by hand: "Three seats, each finding a different
        true defect -> rho -0.500 -> clamped 0 -> 3.00 effective seats,
        maximum independence." The manual adds why it is pinned: "A
        construction that got these backwards would still return a plausible
        number."

        MUTATION TESTING ADDED THIS PAIR. The earlier test asserted only that
        a rho came out, so replacing the matrix cell with the bare truth value
        -- discarding WHICH SEAT asserted what, which is the entire content of
        the measurement -- still produced a number and stayed green.
        """
        rep = self._panel(tmp_path, "independent", {
            f"seat_{i}": [f"defect {i}-{k} found only by seat {i}"
                          for k in range(2)] for i in range(1, 6)})
        f = Q.fold(rep, {c.id: True for c in Q.open_items(rep)})
        assert f.rho is not None and f.rho < 0, (
            "seats finding different true defects must not correlate")
        assert f.n_eff == pytest.approx(5.0), (
            "clamped, five seats are worth five: maximum independence")

    def test_total_collapse_reproduces_the_manuals_other_extreme(
            self, tmp_path):
        """SOP 6.6: "Three seats asserting an identical set, same false claim
        included -> +1.000 -> 1.00 effective seat, total collapse." """
        shared = [f"shared position {k}" for k in range(6)]
        rep = self._panel(tmp_path, "collapsed",
                          {f"seat_{i}": shared for i in range(1, 6)})
        items = Q.open_items(rep)
        decisions = {c.id: True for c in items}
        decisions[items[0].id] = False        # the shared falsehood
        f = Q.fold(rep, decisions)
        assert f.rho == pytest.approx(1.0)
        assert f.n_eff == pytest.approx(1.0), (
            "five seats agreeing exactly are worth one")

    def test_it_flags_a_figure_thinner_than_the_calibration_set(self, run):
        rep = self._rep(run)
        folded = Q.fold(rep, {c.id: True for c in Q.open_items(rep)})
        assert folded.n_items < Q.CALIBRATION_ITEMS
        assert "THIN" in "\n".join(Q.render(folded))
