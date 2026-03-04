"""Tests for the search CLI command."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from garden.core.models import SearchResult


class TestSearchCommand:
    @patch("garden.store.vector_store.search")
    def test_search_basic(self, mock_search):
        from garden.cli.search import search

        mock_search.return_value = [
            SearchResult(content="Some text about Python", source="python.md", score=0.95),
        ]
        runner = CliRunner()
        result = runner.invoke(search, ["python"])
        assert result.exit_code == 0
        assert "Found 1 result(s)" in result.output
        assert "python.md" in result.output

    @patch("garden.store.vector_store.search")
    def test_search_no_results(self, mock_search):
        from garden.cli.search import search

        mock_search.return_value = []
        runner = CliRunner()
        result = runner.invoke(search, ["nonexistent"])
        assert result.exit_code == 0
        assert "No results found" in result.output

    @patch("garden.store.vector_store.search")
    def test_search_with_source_filter(self, mock_search):
        from garden.cli.search import search

        mock_search.return_value = []
        runner = CliRunner()
        runner.invoke(search, ["query", "--source", "test.md"])
        mock_search.assert_called_once_with("query", k=None, where={"source": "test.md"})

    @patch("garden.store.vector_store.search")
    def test_search_with_tag_filter(self, mock_search):
        from garden.cli.search import search

        mock_search.return_value = []
        runner = CliRunner()
        runner.invoke(search, ["query", "--tag", "ml"])
        mock_search.assert_called_once_with("query", k=None, where={"tags": {"$contains": "ml"}})

    @patch("garden.store.vector_store.search")
    def test_search_with_limit(self, mock_search):
        from garden.cli.search import search

        mock_search.return_value = []
        runner = CliRunner()
        runner.invoke(search, ["query", "--limit", "3"])
        mock_search.assert_called_once_with("query", k=3, where=None)
