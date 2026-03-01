from datetime import datetime, timedelta

import pytest

from garden.core.models import Flashcard
from garden.store.card_store import (
    add_cards,
    clear_all,
    forget_source,
    get_card_stats,
    get_due_cards,
    update_card,
)


class TestAddCards:
    def test_add_single(self, sample_cards):
        add_cards([sample_cards[0]])
        stats = get_card_stats()
        assert stats["total"] == 1

    def test_add_multiple(self, sample_cards):
        add_cards(sample_cards)
        stats = get_card_stats()
        assert stats["total"] == 3

    def test_add_preserves_fields(self, sample_cards):
        card = sample_cards[0]
        add_cards([card])
        due = get_due_cards(10)
        assert len(due) == 1
        loaded = due[0]
        assert loaded.id == card.id
        assert loaded.question == card.question
        assert loaded.answer == card.answer
        assert loaded.source == card.source
        assert loaded.tags == card.tags
        assert loaded.easiness == card.easiness

    def test_add_duplicate_id_ignored(self, sample_cards):
        add_cards([sample_cards[0]])
        add_cards([sample_cards[0]])  # same id
        stats = get_card_stats()
        assert stats["total"] == 1

    def test_tags_round_trip(self):
        card = Flashcard(
            id="t1", question="Q", answer="A", source="s.md",
            tags=["tag1", "tag2", "tag3"],
            next_review=datetime.now() - timedelta(hours=1),
        )
        add_cards([card])
        loaded = get_due_cards(1)[0]
        assert loaded.tags == ["tag1", "tag2", "tag3"]

    def test_empty_tags_round_trip(self):
        card = Flashcard(
            id="t2", question="Q", answer="A", source="s.md",
            tags=[],
            next_review=datetime.now() - timedelta(hours=1),
        )
        add_cards([card])
        loaded = get_due_cards(1)[0]
        assert loaded.tags == []


class TestGetDueCards:
    def test_returns_only_due(self, sample_cards):
        add_cards(sample_cards)
        due = get_due_cards()
        ids = {c.id for c in due}
        assert "card-1" in ids  # due (past)
        assert "card-3" in ids  # due (past)
        assert "card-2" not in ids  # future

    def test_respects_count_limit(self, sample_cards):
        add_cards(sample_cards)
        due = get_due_cards(count=1)
        assert len(due) == 1

    def test_ordered_by_next_review(self, sample_cards):
        add_cards(sample_cards)
        due = get_due_cards()
        assert len(due) >= 2
        assert due[0].next_review <= due[1].next_review

    def test_no_due_cards(self):
        card = Flashcard(
            id="future", question="Q", answer="A", source="s.md",
            next_review=datetime.now() + timedelta(days=30),
        )
        add_cards([card])
        assert get_due_cards() == []


class TestUpdateCard:
    def test_update_easiness(self, sample_cards):
        add_cards([sample_cards[0]])
        card = sample_cards[0]
        card.easiness = 3.0
        card.repetitions = 5
        update_card(card)
        due = get_due_cards(10)
        assert due[0].easiness == 3.0
        assert due[0].repetitions == 5

    def test_update_next_review(self, sample_cards):
        add_cards([sample_cards[0]])
        card = sample_cards[0]
        future = datetime.now() + timedelta(days=10)
        card.next_review = future
        update_card(card)
        # Now should NOT be due
        assert get_due_cards() == []


class TestForgetSource:
    def test_removes_matching_source(self, sample_cards):
        add_cards(sample_cards)
        removed = forget_source("test.md")
        assert removed == 2
        stats = get_card_stats()
        assert stats["total"] == 1

    def test_keeps_other_sources(self, sample_cards):
        add_cards(sample_cards)
        forget_source("test.md")
        due = get_due_cards(10)
        assert all(c.source == "other.md" for c in due)

    def test_returns_zero_for_unknown(self, sample_cards):
        add_cards(sample_cards)
        removed = forget_source("nonexistent.md")
        assert removed == 0


class TestClearAll:
    def test_removes_all(self, sample_cards):
        add_cards(sample_cards)
        count = clear_all()
        assert count == 3
        assert get_card_stats()["total"] == 0

    def test_clear_empty(self):
        count = clear_all()
        assert count == 0


class TestGetCardStats:
    def test_stats_with_due(self, sample_cards):
        add_cards(sample_cards)
        stats = get_card_stats()
        assert stats["total"] == 3
        assert stats["due"] == 2  # card-1 and card-3 are past due

    def test_stats_empty(self):
        stats = get_card_stats()
        assert stats == {"total": 0, "due": 0}
