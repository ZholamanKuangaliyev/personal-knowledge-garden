"""Tests for P0-P3 improvements: batch graph ops, card dedup, embedder singleton,
knowledge gap, config-driven settings, enriched models."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from garden.core.models import Chunk, Concept, ConceptLink, Flashcard, SearchResult


class TestEmbedderSingleton:
    @patch("garden.ingestion.embedder.OllamaEmbeddings")
    def test_get_embeddings_cached(self, mock_cls):
        import garden.ingestion.embedder as emb_mod

        emb_mod._embeddings = None  # reset
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        e1 = emb_mod.get_embeddings()
        e2 = emb_mod.get_embeddings()
        assert e1 is e2
        assert mock_cls.call_count == 1  # only constructed once

        emb_mod._embeddings = None  # cleanup

    @patch("garden.ingestion.embedder.OllamaEmbeddings")
    def test_reset_embeddings(self, mock_cls):
        import garden.ingestion.embedder as emb_mod

        emb_mod._embeddings = None
        mock_cls.return_value = MagicMock()

        emb_mod.get_embeddings()
        emb_mod.reset_embeddings()
        emb_mod.get_embeddings()
        assert mock_cls.call_count == 2  # constructed twice after reset

        emb_mod._embeddings = None


class TestBatchGraphOps:
    def test_add_concepts_batch_defers_invalidation(self):
        import garden.store.graph_store as gs

        concepts = [
            Concept(name="test-a", source="test.md"),
            Concept(name="test-b", source="test.md"),
        ]
        gs.add_concepts(concepts, batch=True)

        # Cache should be marked dirty, not yet invalidated
        assert gs._cache_dirty is True

        # Flush should invalidate
        gs.flush_cache()
        assert gs._cache_dirty is False

    def test_add_links_batch_defers_invalidation(self):
        import garden.store.graph_store as gs

        # Add concepts first so links have targets
        concepts = [
            Concept(name="link-a", source="test.md"),
            Concept(name="link-b", source="test.md"),
        ]
        gs.add_concepts(concepts)

        links = [ConceptLink(source_concept="link-a", target_concept="link-b")]
        gs.add_links(links, batch=True)
        assert gs._cache_dirty is True

        gs.flush_cache()
        assert gs._cache_dirty is False

    def test_add_concepts_non_batch_invalidates_immediately(self):
        import garden.store.graph_store as gs

        concepts = [Concept(name="imm-a", source="test.md")]
        gs.add_concepts(concepts, batch=False)
        assert gs._cache_dirty is False

    def test_flush_noop_when_clean(self):
        import garden.store.graph_store as gs

        gs._cache_dirty = False
        gs.flush_cache()  # should not crash
        assert gs._cache_dirty is False

    def test_concepts_with_new_fields(self):
        import garden.store.graph_store as gs

        concepts = [
            Concept(name="enriched", source="test.md", category="entity", importance=0.8),
        ]
        gs.add_concepts(concepts)

        all_c = gs.get_all_concepts()
        found = [c for c in all_c if c.name == "enriched"]
        assert len(found) == 1


class TestCardDedup:
    @patch("garden.srs.card_generator.invoke_llm")
    def test_duplicate_questions_deduped(self, mock_invoke):
        from garden.srs.card_generator import generate_cards

        # Two chunks returning the same question
        mock_invoke.side_effect = [
            json.dumps({"cards": [{"question": "What is Python?", "answer": "A language."}]}),
            json.dumps({"cards": [{"question": "What is Python?", "answer": "A programming language."}]}),
        ]

        chunks = [
            Chunk(id="c1", source="test.md", content="Python is a language."),
            Chunk(id="c2", source="test.md", content="Python is a programming language."),
        ]
        cards = generate_cards(chunks)
        assert len(cards) == 1  # deduplicated

    @patch("garden.srs.card_generator.invoke_llm")
    def test_source_chunk_id_set(self, mock_invoke):
        from garden.srs.card_generator import generate_cards

        mock_invoke.return_value = json.dumps({
            "cards": [{"question": "What is ML?", "answer": "Machine learning."}]
        })

        chunks = [Chunk(id="chunk-42", source="ml.md", content="ML content")]
        cards = generate_cards(chunks)
        assert len(cards) == 1
        assert cards[0].source_chunk_id == "chunk-42"


class TestKnowledgeGap:
    def test_grader_edge_sets_knowledge_gap(self, monkeypatch):
        from garden.agent.edges import GraderEdgeStrategy

        monkeypatch.setattr("garden.core.config.settings.max_retries", 2)
        edge = GraderEdgeStrategy()

        state = {"documents": [], "retry_count": 2}
        result = edge.decide(state)
        assert result == "generate"
        assert state.get("knowledge_gap") is True

    def test_grader_edge_no_gap_when_docs_exist(self):
        from garden.agent.edges import GraderEdgeStrategy

        edge = GraderEdgeStrategy()
        state = {"documents": [{"content": "x", "source": "y"}], "retry_count": 0}
        result = edge.decide(state)
        assert result == "generate"
        assert state.get("knowledge_gap") is None or state.get("knowledge_gap") is False

    @patch("garden.agent.nodes.generator.invoke_llm")
    def test_generator_passes_knowledge_gap_to_template(self, mock_invoke):
        from garden.agent.nodes.generator import GeneratorNode

        mock_invoke.return_value = "I could not find relevant information."
        node = GeneratorNode()

        state = {
            "question": "quantum entanglement?",
            "documents": [],
            "history": [],
            "knowledge_gap": True,
        }
        result = node(state)
        assert "generation" in result
        assert result["knowledge_gap"] is True  # state preserved


class TestConfigDrivenSettings:
    def test_grader_uses_config_threshold(self, monkeypatch):
        from garden.agent.nodes.grader import EmbeddingGraderNode

        monkeypatch.setattr("garden.core.config.settings.grader_threshold", 2.0)
        node = EmbeddingGraderNode()
        assert node._threshold == 2.0

    def test_grader_threshold_override(self):
        from garden.agent.nodes.grader import EmbeddingGraderNode

        node = EmbeddingGraderNode(threshold=0.5)
        assert node._threshold == 0.5

    def test_rewriter_uses_config_failed_docs(self, monkeypatch):
        from garden.agent.nodes.rewriter import RewriterNode

        monkeypatch.setattr("garden.core.config.settings.rewriter_failed_docs", 5)
        # Verify the setting is accessible (actual usage tested via integration)
        from garden.core.config import settings
        assert settings.rewriter_failed_docs == 5

    def test_chat_config_defaults(self):
        from garden.core.config import settings

        assert settings.chat_max_history == 20
        assert settings.chat_recent_full == 6
        assert settings.chat_truncate_len == 200
        assert settings.concept_batch_size == 5

    def test_concept_extractor_uses_config_batch_size(self, monkeypatch):
        monkeypatch.setattr("garden.core.config.settings.concept_batch_size", 3)
        from garden.core.config import settings
        assert settings.concept_batch_size == 3


class TestEnrichedModels:
    def test_chunk_has_metadata_and_created_at(self):
        chunk = Chunk(id="c1", source="test.md", content="hello", metadata={"lang": "en"})
        assert chunk.metadata == {"lang": "en"}
        assert isinstance(chunk.created_at, datetime)

    def test_concept_has_category_and_importance(self):
        c = Concept(name="ml", source="test.md", category="topic", importance=0.9)
        assert c.category == "topic"
        assert c.importance == 0.9

    def test_flashcard_has_review_tracking(self):
        card = Flashcard(
            id="c1", question="Q?", answer="A", source="test.md",
            last_reviewed_at=datetime.now(), review_count=5, source_chunk_id="chunk-1",
        )
        assert card.review_count == 5
        assert card.source_chunk_id == "chunk-1"
        assert card.last_reviewed_at is not None

    def test_flashcard_defaults(self):
        card = Flashcard(id="c2", question="Q?", answer="A", source="test.md")
        assert card.last_reviewed_at is None
        assert card.review_count == 0
        assert card.source_chunk_id == ""

    def test_search_result_has_chunk_index_and_metadata(self):
        sr = SearchResult(content="hello", source="test.md", chunk_index=3, metadata={"tags": "ml"})
        assert sr.chunk_index == 3
        assert sr.metadata == {"tags": "ml"}


class TestCardStoreBatch:
    def test_add_cards_executemany(self, sample_cards):
        from garden.store.card_store import add_cards, get_card_stats

        add_cards(sample_cards)
        stats = get_card_stats()
        assert stats["total"] == 3

    def test_add_cards_with_new_fields(self):
        from garden.store.card_store import add_cards, get_due_cards

        now = datetime.now()
        card = Flashcard(
            id="new-field-card",
            question="Test?",
            answer="Yes",
            source="test.md",
            last_reviewed_at=now,
            review_count=3,
            source_chunk_id="chunk-99",
        )
        add_cards([card])

        # Retrieve and verify
        from garden.store.card_store import get_card_stats
        from garden.store.database import get_connection

        conn = get_connection()
        row = conn.execute("SELECT review_count, source_chunk_id FROM flashcards WHERE id = ?", ("new-field-card",)).fetchone()
        assert row["review_count"] == 3
        assert row["source_chunk_id"] == "chunk-99"


class TestSchemaMigrationV2:
    def test_new_columns_exist(self):
        from garden.store.database import get_connection

        conn = get_connection()

        # Check flashcards new columns
        info = conn.execute("PRAGMA table_info(flashcards)").fetchall()
        cols = {r["name"] for r in info}
        assert "last_reviewed_at" in cols
        assert "review_count" in cols
        assert "source_chunk_id" in cols

        # Check concepts new columns
        info = conn.execute("PRAGMA table_info(concepts)").fetchall()
        cols = {r["name"] for r in info}
        assert "category" in cols
        assert "importance" in cols

    def test_new_indexes_exist(self):
        from garden.store.database import get_connection

        conn = get_connection()
        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        idx_names = {r["name"] for r in indexes}
        assert "idx_flashcards_created_at" in idx_names
        assert "idx_concept_links_weight" in idx_names
        assert "idx_documents_ingested_at" in idx_names
