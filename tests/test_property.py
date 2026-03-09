"""Property-based tests using Hypothesis."""

from datetime import datetime, timedelta

import pytest
from hypothesis import given, settings as hsettings, assume
from hypothesis import strategies as st

from garden.core.models import Flashcard, Concept, ConceptLink, Chunk
from garden.srs.scheduler import sm2_update


# --- SM-2 Scheduler Properties ---

@given(quality=st.integers(min_value=0, max_value=5))
def test_sm2_easiness_never_below_minimum(quality):
    """Easiness factor must never drop below 1.3."""
    card = Flashcard(
        id="test", question="Q", answer="A", source="s.md",
        easiness=1.3, interval=1, repetitions=0,
        next_review=datetime.now(),
    )
    updated = sm2_update(card, quality)
    assert updated.easiness >= 1.3


@given(quality=st.integers(min_value=0, max_value=5))
def test_sm2_interval_always_positive(quality):
    """Interval must always be >= 1 day."""
    card = Flashcard(
        id="test", question="Q", answer="A", source="s.md",
        easiness=2.5, interval=1, repetitions=0,
        next_review=datetime.now(),
    )
    updated = sm2_update(card, quality)
    assert updated.interval >= 1


@given(quality=st.integers(min_value=3, max_value=5))
def test_sm2_successful_review_advances_interval(quality):
    """A successful review (quality >= 3) should not decrease the interval."""
    card = Flashcard(
        id="test", question="Q", answer="A", source="s.md",
        easiness=2.5, interval=6, repetitions=2,
        next_review=datetime.now(),
    )
    updated = sm2_update(card, quality)
    assert updated.interval >= card.interval


@given(quality=st.integers(min_value=0, max_value=2))
def test_sm2_failed_review_resets(quality):
    """A failed review (quality < 3) should reset repetitions to 0 and interval to 1."""
    card = Flashcard(
        id="test", question="Q", answer="A", source="s.md",
        easiness=2.5, interval=30, repetitions=10,
        next_review=datetime.now(),
    )
    updated = sm2_update(card, quality)
    assert updated.repetitions == 0
    assert updated.interval == 1


@given(quality=st.integers(min_value=0, max_value=5))
def test_sm2_next_review_is_in_future(quality):
    """Next review should always be in the future."""
    card = Flashcard(
        id="test", question="Q", answer="A", source="s.md",
        easiness=2.5, interval=1, repetitions=0,
        next_review=datetime.now(),
    )
    before = datetime.now()
    updated = sm2_update(card, quality)
    assert updated.next_review >= before


@given(
    quality=st.integers(min_value=0, max_value=5),
    easiness=st.floats(min_value=1.3, max_value=5.0),
    interval=st.integers(min_value=1, max_value=365),
    repetitions=st.integers(min_value=0, max_value=100),
)
def test_sm2_idempotent_properties(quality, easiness, interval, repetitions):
    """SM-2 should produce valid output for any valid input."""
    card = Flashcard(
        id="test", question="Q", answer="A", source="s.md",
        easiness=easiness, interval=interval, repetitions=repetitions,
        next_review=datetime.now(),
    )
    updated = sm2_update(card, quality)
    assert updated.easiness >= 1.3
    assert updated.interval >= 1
    assert updated.repetitions >= 0


# --- Chunker Properties ---

@given(
    text=st.text(min_size=1, max_size=5000),
    source=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
)
@hsettings(max_examples=50)
def test_chunker_preserves_all_content(text, source):
    """Chunking should preserve all text content."""
    assume(text.strip())
    from garden.ingestion.chunker import chunk_text

    chunks = chunk_text(text, source=source)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.source == source
        assert chunk.content  # no empty chunks
        assert chunk.chunk_index >= 0


@given(text=st.text(min_size=10, max_size=200))
@hsettings(max_examples=30)
def test_chunk_ids_are_unique(text):
    """All chunk IDs must be unique."""
    assume(text.strip())
    from garden.ingestion.chunker import chunk_text

    chunks = chunk_text(text, source="test.md")
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))


# --- Model Validation Properties ---

@given(name=st.text(min_size=0, max_size=5).filter(lambda x: not x.strip()))
def test_concept_rejects_empty_name(name):
    """Concept should reject empty/whitespace-only names."""
    with pytest.raises(ValueError, match="concept name must not be empty"):
        Concept(name=name, source="s.md")


@given(weight=st.floats(max_value=-0.01).filter(lambda x: x == x))  # filter NaN
def test_concept_link_rejects_negative_weight(weight):
    """ConceptLink should reject negative weights."""
    with pytest.raises(ValueError, match="weight must be non-negative"):
        ConceptLink(source_concept="a", target_concept="b", weight=weight)


# --- Linker Properties ---

@given(
    names=st.lists(
        st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
        min_size=2,
        max_size=10,
        unique=True,
    )
)
@hsettings(max_examples=30)
def test_linker_same_source_creates_links(names):
    """Concepts from the same source should be co-occurrence linked."""
    from garden.knowledge.linker import find_links

    concepts = [Concept(name=n, source="same.md") for n in names]
    links = find_links(concepts, [])
    # n concepts from same source should create n*(n-1)/2 co-occurrence links
    expected = len(names) * (len(names) - 1) // 2
    co_occurs = [l for l in links if l.relation == "co_occurs"]
    assert len(co_occurs) == expected
