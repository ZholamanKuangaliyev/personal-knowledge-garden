"""Tests for the --semantic flag on the garden search CLI command."""

from unittest.mock import patch

from click.testing import CliRunner

from garden.cli.app import cli
from garden.core.models import Concept, ConceptLink, SearchResult
from garden.store.graph_store import add_concepts, add_links


class TestSemanticSearch:
    """Tests for the --semantic flag on `garden search`."""

    def _make_result(self, content="test content", source="test.md", score=0.5):
        return SearchResult(content=content, source=source, score=score)

    @patch("garden.store.vector_store.search")
    def test_search_without_semantic(self, mock_vs):
        """Basic search works and does not show concept section."""
        mock_vs.return_value = [self._make_result()]
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test query"])

        assert result.exit_code == 0
        assert "Related Concepts" not in result.output

    @patch("garden.store.vector_store.search")
    def test_search_with_semantic_finds_concepts(self, mock_vs):
        """--semantic flag shows matching concepts from the graph."""
        mock_vs.return_value = [self._make_result()]
        add_concepts([
            Concept(name="machine learning", source="ml.md", description="A branch of AI"),
        ])

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "machine", "--semantic"])

        assert result.exit_code == 0
        assert "Related Concepts" in result.output
        assert "machine learning" in result.output

    @patch("garden.store.vector_store.search")
    def test_search_semantic_no_matches(self, mock_vs):
        """--semantic with no matching concepts shows appropriate message."""
        mock_vs.return_value = [self._make_result()]

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "xyznonexistent", "--semantic"])

        assert result.exit_code == 0
        assert "No matching concepts" in result.output

    @patch("garden.store.vector_store.search")
    def test_search_semantic_shows_neighbors(self, mock_vs):
        """Concepts with links show neighbor info."""
        mock_vs.return_value = [self._make_result()]
        add_concepts([
            Concept(name="neural networks", source="ml.md", description="Computational models"),
            Concept(name="deep learning", source="ml.md", description="Subset of ML"),
        ])
        add_links([
            ConceptLink(
                source_concept="neural networks",
                target_concept="deep learning",
                relation="co_occurs",
                weight=1.0,
            ),
        ])

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "neural", "--semantic"])

        assert result.exit_code == 0
        assert "deep learning" in result.output
        assert "co_occurs" in result.output

    @patch("garden.store.vector_store.search")
    def test_search_semantic_empty_results(self, mock_vs):
        """No vector results but --semantic still runs without crashing."""
        mock_vs.return_value = []
        add_concepts([
            Concept(name="machine learning", source="ml.md", description="A branch of AI"),
        ])

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "machine", "--semantic"])

        assert result.exit_code == 0
        assert "No results found" in result.output
