from datetime import datetime, timedelta

import pytest

from garden.core.models import Flashcard
from garden.srs.scheduler import sm2_update


def _make_card(**kwargs) -> Flashcard:
    defaults = dict(
        id="test", question="Q?", answer="A", source="s.md",
        easiness=2.5, interval=1, repetitions=0,
        next_review=datetime.now(),
    )
    defaults.update(kwargs)
    return Flashcard(**defaults)


class TestSM2Algorithm:
    def test_first_correct_review(self):
        card = _make_card()
        updated = sm2_update(card, quality=4)
        assert updated.repetitions == 1
        assert updated.interval == 1

    def test_second_correct_review(self):
        card = _make_card(repetitions=1, interval=1)
        updated = sm2_update(card, quality=4)
        assert updated.repetitions == 2
        assert updated.interval == 6

    def test_third_correct_review(self):
        card = _make_card(repetitions=2, interval=6, easiness=2.5)
        updated = sm2_update(card, quality=4)
        assert updated.repetitions == 3
        assert updated.interval == round(6 * 2.5)

    def test_failed_review_resets(self):
        card = _make_card(repetitions=5, interval=30)
        updated = sm2_update(card, quality=2)
        assert updated.repetitions == 0
        assert updated.interval == 1

    def test_perfect_review_increases_easiness(self):
        card = _make_card(easiness=2.5)
        updated = sm2_update(card, quality=5)
        assert updated.easiness > 2.5

    def test_poor_review_decreases_easiness(self):
        card = _make_card(easiness=2.5)
        updated = sm2_update(card, quality=3)
        assert updated.easiness < 2.5

    def test_easiness_floor_at_1_3(self):
        card = _make_card(easiness=1.3)
        updated = sm2_update(card, quality=0)
        assert updated.easiness == 1.3

    def test_quality_clamped_to_range(self):
        card = _make_card()
        updated = sm2_update(card, quality=10)  # should clamp to 5
        assert updated.easiness > 2.5  # quality=5 effect

    def test_quality_clamped_negative(self):
        card = _make_card()
        updated = sm2_update(card, quality=-3)  # should clamp to 0
        assert updated.repetitions == 0  # quality<3 resets

    def test_next_review_set_in_future(self):
        before = datetime.now()
        card = _make_card()
        updated = sm2_update(card, quality=4)
        assert updated.next_review >= before
        assert updated.next_review <= datetime.now() + timedelta(days=updated.interval + 1)

    def test_boundary_quality_3(self):
        card = _make_card()
        updated = sm2_update(card, quality=3)
        assert updated.repetitions == 1  # quality >= 3 counts as pass

    def test_boundary_quality_2(self):
        card = _make_card(repetitions=3, interval=10)
        updated = sm2_update(card, quality=2)
        assert updated.repetitions == 0  # quality < 3 resets
        assert updated.interval == 1
