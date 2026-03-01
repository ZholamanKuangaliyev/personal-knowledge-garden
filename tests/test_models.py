from datetime import datetime

from garden.core.models import (
    Chunk,
    Concept,
    ConceptLink,
    Document,
    Flashcard,
    GardenStats,
)


class TestFlashcard:
    def test_defaults(self):
        card = Flashcard(id="1", question="Q?", answer="A", source="s.md")
        assert card.easiness == 2.5
        assert card.interval == 1
        assert card.repetitions == 0
        assert isinstance(card.created_at, datetime)
        assert isinstance(card.next_review, datetime)
        assert card.tags == []

    def test_custom_tags(self):
        card = Flashcard(id="1", question="Q?", answer="A", source="s.md", tags=["a", "b"])
        assert card.tags == ["a", "b"]


class TestConcept:
    def test_defaults(self):
        c = Concept(name="ai", source="doc.md")
        assert c.description == ""

    def test_with_description(self):
        c = Concept(name="ai", source="doc.md", description="Artificial intelligence")
        assert c.description == "Artificial intelligence"


class TestConceptLink:
    def test_defaults(self):
        link = ConceptLink(source_concept="a", target_concept="b")
        assert link.relation == "related_to"
        assert link.weight == 1.0


class TestDocument:
    def test_defaults(self):
        doc = Document(source="file.md", content="hello")
        assert doc.tags == []
        assert isinstance(doc.ingested_at, datetime)


class TestChunk:
    def test_defaults(self):
        chunk = Chunk(id="c1", source="s.md", content="text")
        assert chunk.tags == []
        assert chunk.chunk_index == 0


class TestGardenStats:
    def test_defaults(self):
        stats = GardenStats()
        assert stats.total_documents == 0
        assert stats.total_chunks == 0
        assert stats.total_concepts == 0
        assert stats.total_links == 0
        assert stats.total_cards == 0
        assert stats.cards_due == 0
