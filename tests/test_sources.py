"""Tests for get_source_details() and the 'garden sources' CLI command."""

from unittest.mock import MagicMock

import pytest
import garden.store.vector_store as vs_mod
from click.testing import CliRunner

from garden.cli.sources import sources
from garden.store.vector_store import get_source_details


@pytest.fixture(autouse=True)
def mock_store():
    """Replace the vector store singleton with a mock for each test."""
    mock = MagicMock()
    original = vs_mod._store
    vs_mod._store = mock
    yield mock
    vs_mod._store = original


class TestGetSourceDetails:
    def test_empty_store(self, mock_store):
        mock_store._collection.get.return_value = {"metadatas": []}
        result = get_source_details()
        assert result == []

    def test_single_source(self, mock_store):
        mock_store._collection.get.return_value = {
            "metadatas": [
                {"source": "notes.md", "tags": "ml,python"},
                {"source": "notes.md", "tags": "ml"},
            ]
        }
        result = get_source_details()
        assert len(result) == 1
        assert result[0]["source"] == "notes.md"
        assert result[0]["chunks"] == 2
        assert result[0]["tags"] == ["ml", "python"]

    def test_multiple_sources_sorted(self, mock_store):
        mock_store._collection.get.return_value = {
            "metadatas": [
                {"source": "zebra.md", "tags": ""},
                {"source": "alpha.md", "tags": "ai"},
                {"source": "alpha.md", "tags": "ml"},
            ]
        }
        result = get_source_details()
        assert len(result) == 2
        assert result[0]["source"] == "alpha.md"
        assert result[0]["chunks"] == 2
        assert result[0]["tags"] == ["ai", "ml"]
        assert result[1]["source"] == "zebra.md"
        assert result[1]["chunks"] == 1
        assert result[1]["tags"] == []

    def test_no_tags(self, mock_store):
        mock_store._collection.get.return_value = {
            "metadatas": [{"source": "bare.txt", "tags": ""}]
        }
        result = get_source_details()
        assert result[0]["tags"] == []

    def test_none_metadatas(self, mock_store):
        mock_store._collection.get.return_value = {"metadatas": None}
        result = get_source_details()
        assert result == []

    def test_missing_source_defaults_to_unknown(self, mock_store):
        mock_store._collection.get.return_value = {
            "metadatas": [{"tags": "foo"}]
        }
        result = get_source_details()
        assert result[0]["source"] == "unknown"

    def test_tags_deduped_and_sorted(self, mock_store):
        mock_store._collection.get.return_value = {
            "metadatas": [
                {"source": "doc.md", "tags": "z-tag,a-tag"},
                {"source": "doc.md", "tags": "a-tag"},
            ]
        }
        result = get_source_details()
        assert result[0]["tags"] == ["a-tag", "z-tag"]

    def test_missing_tags_key(self, mock_store):
        """Chunks with no 'tags' key at all should be handled gracefully."""
        mock_store._collection.get.return_value = {
            "metadatas": [{"source": "bare.txt"}]
        }
        result = get_source_details()
        assert result[0]["tags"] == []


class TestSourcesCLI:
    def test_empty_garden(self, mock_store):
        mock_store._collection.get.return_value = {"metadatas": []}
        runner = CliRunner()
        result = runner.invoke(sources)
        assert result.exit_code == 0
        assert "No documents ingested" in result.output

    def test_with_sources(self, mock_store):
        mock_store._collection.get.return_value = {
            "metadatas": [
                {"source": "notes.md", "tags": "ml"},
                {"source": "notes.md", "tags": "python"},
                {"source": "paper.pdf", "tags": ""},
            ]
        }
        runner = CliRunner()
        result = runner.invoke(sources)
        assert result.exit_code == 0
        assert "notes.md" in result.output
        assert "paper.pdf" in result.output
        assert "2 source(s)" in result.output
        assert "3 chunk(s)" in result.output

    def test_single_source_output(self, mock_store):
        mock_store._collection.get.return_value = {
            "metadatas": [
                {"source": "guide.md", "tags": "tutorial,python"},
            ]
        }
        runner = CliRunner()
        result = runner.invoke(sources)
        assert result.exit_code == 0
        assert "guide.md" in result.output
        assert "1 source(s)" in result.output
        assert "1 chunk(s)" in result.output

    def test_tags_appear_in_output(self, mock_store):
        mock_store._collection.get.return_value = {
            "metadatas": [
                {"source": "tagged.md", "tags": "ml,ai"},
            ]
        }
        runner = CliRunner()
        result = runner.invoke(sources)
        assert result.exit_code == 0
        assert "ml" in result.output
        assert "ai" in result.output

    def test_hint_message_shown(self, mock_store):
        mock_store._collection.get.return_value = {
            "metadatas": [{"source": "doc.md", "tags": ""}]
        }
        runner = CliRunner()
        result = runner.invoke(sources)
        assert result.exit_code == 0
        assert "garden chat" in result.output
