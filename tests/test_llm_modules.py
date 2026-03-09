"""Tests for LLM-dependent modules using mocked Ollama responses."""

import json
from unittest.mock import MagicMock, patch

import pytest

from garden.core.models import Chunk, Concept, Flashcard, SearchResult


class TestCardGenerator:
    @patch("garden.srs.card_generator.invoke_llm")
    def test_generate_cards(self, mock_invoke):
        from garden.srs.card_generator import generate_cards

        mock_invoke.return_value = json.dumps({
            "cards": [
                {"question": "What is X?", "answer": "X is Y"},
                {"question": "What is A?", "answer": "A is B"},
            ]
        })

        chunks = [Chunk(id="c1", content="Some text about X and A", source="test.md", tags=["t1"], chunk_index=0)]
        cards = generate_cards(chunks)
        assert len(cards) == 2
        assert cards[0].question == "What is X?"
        assert cards[0].source == "test.md"
        assert cards[0].tags == ["t1"]
        assert isinstance(cards[0], Flashcard)

    @patch("garden.srs.card_generator.invoke_llm")
    def test_generate_cards_handles_bad_json(self, mock_invoke):
        from garden.srs.card_generator import generate_cards

        mock_invoke.return_value = "not valid json"

        chunks = [Chunk(id="c1", content="text", source="s.md", tags=[], chunk_index=0)]
        cards = generate_cards(chunks)
        assert cards == []

    @patch("garden.srs.card_generator.invoke_llm")
    def test_generate_cards_empty_chunks(self, mock_invoke):
        from garden.srs.card_generator import generate_cards

        cards = generate_cards([])
        assert cards == []
        mock_invoke.assert_not_called()


class TestConceptExtractor:
    @patch("garden.knowledge.concept_extractor.invoke_llm")
    def test_extract_concepts(self, mock_invoke):
        from garden.knowledge.concept_extractor import extract_concepts

        mock_invoke.return_value = json.dumps({
            "concepts": [
                {"name": "Machine Learning", "description": "A branch of AI"},
                {"name": "Neural Networks", "description": "Computational models"},
            ]
        })

        concepts = extract_concepts(["text about ML"], source="ml.md")
        assert len(concepts) == 2
        assert concepts[0].name == "machine learning"  # lowercased
        assert concepts[0].source == "ml.md"

    @patch("garden.knowledge.concept_extractor.invoke_llm")
    def test_deduplicates_concepts(self, mock_invoke):
        from garden.knowledge.concept_extractor import extract_concepts

        mock_invoke.return_value = json.dumps({
            "concepts": [
                {"name": "Python", "description": "Language"},
                {"name": "python", "description": "Same thing"},
            ]
        })

        concepts = extract_concepts(["text"], source="s.md")
        assert len(concepts) == 1

    @patch("garden.knowledge.concept_extractor.invoke_llm")
    def test_handles_bad_json(self, mock_invoke):
        from garden.knowledge.concept_extractor import extract_concepts

        mock_invoke.return_value = "broken"

        concepts = extract_concepts(["text"], source="s.md")
        assert concepts == []

    @patch("garden.knowledge.concept_extractor.invoke_llm")
    def test_batching(self, mock_invoke):
        from garden.knowledge.concept_extractor import extract_concepts

        mock_invoke.return_value = json.dumps({"concepts": [{"name": "x", "description": ""}]})

        chunks = [f"chunk {i}" for i in range(12)]
        extract_concepts(chunks, source="s.md", batch_size=5)
        # ceil(12/5) = 3 batches
        assert mock_invoke.call_count == 3


class TestInsightEngine:
    @patch("garden.knowledge.insight_engine.invoke_llm")
    @patch("garden.knowledge.insight_engine.search")
    @patch("garden.knowledge.insight_engine.get_graph")
    def test_generate_insights(self, mock_get_graph, mock_search, mock_invoke):
        import networkx as nx
        from garden.knowledge.insight_engine import generate_insights

        # Build a graph with distant nodes
        g = nx.Graph()
        g.add_node("ai", source="a.md")
        g.add_node("biology", source="b.md")
        g.add_node("bridge", source="a.md")
        g.add_edge("ai", "bridge")
        # ai and biology are disconnected (distance=inf)
        mock_get_graph.return_value = g

        mock_search.return_value = [SearchResult(content="context text", source="a.md", score=0.9)]

        mock_invoke.return_value = json.dumps(
            {"insights": [{"title": "Cross-domain insight", "description": "Interesting connection"}]}
        )

        insights = generate_insights(count=1)
        assert isinstance(insights, list)

    @patch("garden.knowledge.insight_engine.get_graph")
    def test_empty_graph_returns_nothing(self, mock_get_graph):
        import networkx as nx
        from garden.knowledge.insight_engine import find_bridge_pairs

        mock_get_graph.return_value = nx.Graph()
        pairs = find_bridge_pairs()
        assert pairs == []


class TestIdeaGenerator:
    @patch("garden.knowledge.idea_generator.invoke_llm")
    @patch("garden.knowledge.idea_generator.get_graph")
    @patch("garden.knowledge.idea_generator.search")
    def test_generate_ideas(self, mock_search, mock_get_graph, mock_invoke):
        import networkx as nx
        from garden.knowledge.idea_generator import generate_ideas

        mock_search.return_value = [SearchResult(content="doc text", source="s.md", score=0.9)]

        g = nx.Graph()
        g.add_node("python")
        g.add_node("automation")
        g.add_edge("python", "automation")
        mock_get_graph.return_value = g

        mock_invoke.return_value = json.dumps({
            "ideas": [{"title": "Auto-testing", "description": "Use python for auto testing", "connections": ["python"]}]
        })

        ideas = generate_ideas("python automation")
        assert len(ideas) == 1
        assert ideas[0]["title"] == "Auto-testing"

    @patch("garden.knowledge.idea_generator.invoke_llm")
    @patch("garden.knowledge.idea_generator.get_graph")
    @patch("garden.knowledge.idea_generator.search")
    def test_handles_bad_json(self, mock_search, mock_get_graph, mock_invoke):
        import networkx as nx
        from garden.knowledge.idea_generator import generate_ideas

        mock_search.return_value = []  # empty SearchResult list, no iteration needed
        mock_get_graph.return_value = nx.Graph()
        mock_invoke.return_value = "not json"

        ideas = generate_ideas("anything")
        assert ideas == []
