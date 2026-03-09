"""Tests for concept linker — stopword filtering and semantic linking."""

from unittest.mock import MagicMock, patch

from garden.core.models import Concept, ConceptLink
from garden.knowledge.linker import _cosine_similarity, _meaningful_words, find_links


class TestMeaningfulWords:
    def test_filters_stop_words(self):
        assert _meaningful_words("the machine in the lab") == {"machine", "lab"}

    def test_filters_single_char_words(self):
        assert _meaningful_words("a b machine") == {"machine"}

    def test_empty_string(self):
        assert _meaningful_words("") == set()

    def test_all_stop_words(self):
        assert _meaningful_words("the in on at to") == set()

    def test_preserves_meaningful(self):
        assert _meaningful_words("neural network model") == {"neural", "network", "model"}


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        assert abs(_cosine_similarity(v, v) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(_cosine_similarity(a, b)) < 1e-6

    def test_zero_vector(self):
        assert _cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

    def test_similar_vectors(self):
        a = [1.0, 0.9, 0.1]
        b = [0.9, 1.0, 0.1]
        assert _cosine_similarity(a, b) > 0.9


class TestFindLinks:
    def test_co_occurrence_links(self):
        concepts = [
            Concept(name="ml", source="doc.md"),
            Concept(name="ai", source="doc.md"),
        ]
        links = find_links(concepts, [])
        co_occurs = [l for l in links if l.relation == "co_occurs"]
        assert len(co_occurs) == 1
        assert co_occurs[0].source_concept == "ml"
        assert co_occurs[0].target_concept == "ai"

    def test_shared_terms_links_with_stopword_filtering(self):
        """Stop words like 'in' should not produce false-positive links."""
        new_concepts = [Concept(name="data in science", source="new.md")]
        existing = [Concept(name="art in history", source="old.md")]
        links = find_links(new_concepts, existing)

        # "in" is a stop word — should NOT create a shared_terms link
        shared = [l for l in links if l.relation == "shared_terms"]
        assert len(shared) == 0

    def test_meaningful_shared_terms(self):
        new_concepts = [Concept(name="neural network architecture", source="new.md")]
        existing = [Concept(name="deep neural network", source="old.md")]
        links = find_links(new_concepts, existing)

        shared = [l for l in links if l.relation == "shared_terms"]
        assert len(shared) == 1
        assert shared[0].weight > 0

    def test_empty_concepts(self):
        links = find_links([], [])
        assert links == []

    def test_same_name_not_linked(self):
        new_concepts = [Concept(name="ml", source="new.md")]
        existing = [Concept(name="ml", source="old.md")]
        links = find_links(new_concepts, existing)

        shared = [l for l in links if l.relation == "shared_terms"]
        assert len(shared) == 0

    @patch("garden.ingestion.embedder.get_embeddings")
    def test_semantic_links_found(self, mock_get_emb):
        """Concepts with high embedding similarity but no word overlap get semantic links."""
        mock_emb = MagicMock()
        # Two very similar vectors, no shared words
        mock_emb.embed_documents.side_effect = [
            [[1.0, 0.0, 0.1]],   # new concept
            [[0.99, 0.01, 0.1]],  # existing concept
        ]
        mock_get_emb.return_value = mock_emb

        new_concepts = [Concept(name="artificial intelligence", source="new.md")]
        existing = [Concept(name="machine learning", source="old.md")]
        links = find_links(new_concepts, existing)

        semantic = [l for l in links if l.relation == "semantic"]
        assert len(semantic) == 1
        assert semantic[0].weight > 0.75

    @patch("garden.ingestion.embedder.get_embeddings")
    def test_semantic_links_not_found_when_dissimilar(self, mock_get_emb):
        """Dissimilar embeddings should not produce semantic links."""
        mock_emb = MagicMock()
        mock_emb.embed_documents.side_effect = [
            [[1.0, 0.0, 0.0]],  # new concept
            [[0.0, 0.0, 1.0]],  # existing concept (orthogonal)
        ]
        mock_get_emb.return_value = mock_emb

        new_concepts = [Concept(name="quantum entanglement", source="new.md")]
        existing = [Concept(name="cooking recipes", source="old.md")]
        links = find_links(new_concepts, existing)

        semantic = [l for l in links if l.relation == "semantic"]
        assert len(semantic) == 0

    @patch("garden.ingestion.embedder.get_embeddings")
    def test_semantic_skips_already_linked(self, mock_get_emb):
        """Concepts already linked via shared_terms should not get a duplicate semantic link."""
        mock_emb = MagicMock()
        mock_emb.embed_documents.side_effect = [
            [[1.0, 0.0]],
            [[0.99, 0.01]],
        ]
        mock_get_emb.return_value = mock_emb

        new_concepts = [Concept(name="neural network", source="new.md")]
        existing = [Concept(name="neural architecture", source="old.md")]
        links = find_links(new_concepts, existing)

        # Should have shared_terms (both have "neural") but not a duplicate semantic
        shared = [l for l in links if l.relation == "shared_terms"]
        semantic = [l for l in links if l.relation == "semantic"]
        assert len(shared) == 1
        assert len(semantic) == 0  # already connected

    @patch("garden.ingestion.embedder.get_embeddings", side_effect=Exception("no embeddings"))
    def test_semantic_graceful_failure(self, mock_get_emb):
        """If embeddings fail, linker still returns word-overlap links."""
        new_concepts = [Concept(name="deep neural network", source="new.md")]
        existing = [Concept(name="convolutional neural architecture", source="old.md")]
        links = find_links(new_concepts, existing)

        # Should still have shared_terms link for "neural"
        shared = [l for l in links if l.relation == "shared_terms"]
        assert len(shared) == 1
        # No semantic links due to error
        semantic = [l for l in links if l.relation == "semantic"]
        assert len(semantic) == 0

    def test_weight_decay_large_source(self):
        """Documents with many concepts should have weaker co-occurrence weights."""
        concepts = [Concept(name=f"concept-{i}", source="big.md") for i in range(10)]
        links = find_links(concepts, [])

        co_occurs = [l for l in links if l.relation == "co_occurs"]
        assert all(l.weight == 2.0 / 10 for l in co_occurs)
