"""Tests for the seeded-truth rho measurement.

This is the number the panel has never had, and a wrong one is worse than
none: it sets a confidence ceiling a reader acts on. Every failure mode
pinned here is one that would fabricate independence the seats do not have.
"""
from __future__ import annotations

import pytest

import seeded_rho as S


def _m(pattern, n_seats=5):
    m = S.Measurement(seats=[f"seat_{i}" for i in range(1, n_seats + 1)],
                      items=[i.id for i in S.ITEMS])
    for j, s in enumerate(m.seats):
        m.correct[s] = {it.id: pattern(j, k) for k, it in enumerate(S.ITEMS)}
    return m


class TestTheSetHasControls:

    def test_half_the_items_are_clean(self):
        """Every case in the imported eval file contains a defect, so ground
        truth is always 'yes there is an error' -- and a seat answering yes to
        everything scores 100% while detecting nothing."""
        seeded = [i for i in S.ITEMS if i.has_error]
        clean = [i for i in S.ITEMS if not i.has_error]
        assert len(seeded) == len(clean) == 5

    def test_every_seeded_item_has_a_matching_control(self):
        ids = {i.id for i in S.ITEMS}
        for item in S.ITEMS:
            if item.has_error:
                assert f"{item.id}c" in ids, f"{item.id} has no control"

    def test_a_seat_that_always_says_yes_does_not_score_well(self):
        """The whole reason controls exist."""
        always_yes = _m(lambda j, k: S.ITEMS[k].has_error)
        _, _, X = always_yes.matrix()
        per_seat = [sum(r[j] for r in X) for j in range(5)]
        assert all(p == 5 for p in per_seat), "it should get exactly the 5 defects"
        assert all(p < len(X) for p in per_seat), "and fail every control"


class TestScoringIsMechanical:

    @pytest.mark.parametrize("reply,expected", [
        ("ANSWER: yes", True), ("ANSWER: no", False),
        ("working...\nANSWER: YES", True),
        ("ANSWER | no", False),
        ("I think there is an error", None),
        ("", None),
    ])
    def test_only_the_declared_line_counts(self, reply, expected):
        assert S.decide(reply) is expected

    def test_no_answer_is_missing_data_not_a_wrong_answer(self):
        """Scoring silence as an error is the mistake that manufactures a
        correlation nobody observed -- the same reason measure_rho refuses to
        score a seat that raised no claim."""
        m = _m(lambda j, k: True)
        m.correct["seat_1"]["A1"] = None
        common, _, _ = m.matrix()
        assert "A1" not in common, "an item one seat skipped is not common"


class TestTheCorrelationItself:

    def test_identical_seats_measure_as_one(self):
        m = _m(lambda j, k: k not in (0, 1, 2))
        text = "\n".join(S.render(m))
        assert "rho = +1.0000" in text
        assert "1.00 of 5" in text
        assert "FAIL TOGETHER" in text

    def test_seats_wrong_on_different_items_measure_as_independent(self):
        m = _m(lambda j, k: k != j)
        text = "\n".join(S.render(m))
        assert "5.00 of 5" in text
        assert "FAIL DIFFERENTLY" in text

    def test_too_few_common_items_refuses_a_number(self):
        """A correlation over three items is noise wearing four decimal
        places, and it sets a ceiling a reader acts on."""
        m = _m(lambda j, k: True)
        for s in m.seats[:1]:
            for it in list(m.correct[s])[3:]:
                m.correct[s][it] = None
        text = "\n".join(S.render(m))
        assert "NOT MEASURABLE" in text
        assert "rho =" not in text

    def test_one_seat_cannot_have_a_correlation(self):
        text = "\n".join(S.render(_m(lambda j, k: True, n_seats=1)))
        assert "NOT MEASURABLE" in text

    def test_the_report_refuses_to_generalise_the_number(self):
        """SOP 10.1 gives leave-one-domain-out R-squared of -2.09. A rho
        measured on arithmetic says nothing about citation checking."""
        text = "\n".join(S.render(_m(lambda j, k: k != j)))
        assert "does not transfer" in text
        assert "-2.09" in text


class TestTheItemsThemselves:

    def test_every_control_is_arithmetically_correct(self):
        """The controls were COMPUTED, not asserted. If one is wrong, the
        measurement scores a correct seat as mistaken."""
        import re
        checks = {
            "A1c": (65 * 1800 * 3, 351000),
            "A2c": (round((351000 - 246000) / 351000 * 100, 1), 29.9),
            "A3c": (850000 - 85000, 765000),
            "A6c": (10 * 0.40, 4),
        }
        for cid, (computed, claimed) in checks.items():
            assert abs(computed - claimed) < 0.05, cid
            item = next(i for i in S.ITEMS if i.id == cid)
            assert not item.has_error
            digits = re.sub(r"[^0-9]", "", f"{claimed}")
            assert digits[:3] in re.sub(r"[^0-9]", "", item.statement), (
                f"{cid} does not contain the figure it claims")

    def test_every_seeded_item_is_marked_as_containing_an_error(self):
        for item in S.ITEMS:
            if not item.id.endswith("c"):
                assert item.has_error, f"{item.id} should carry a defect"
