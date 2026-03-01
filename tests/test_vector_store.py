"""Tests for vector_store using mocked Chroma."""

from unittest.mock import MagicMock, patch

import pytest

import garden.store.vector_store as vs_mod


@pytest.fixture(autouse=True)
def mock_store():
    """Replace the singleton with a mock for each test."""
    mock = MagicMock()
    original = vs_mod._store
    vs_mod._store = mock
    yield mock
    vs_mod._store = original


class TestAddChunks:
    def test_add_chunks(self, mock_store):
        chunks = [
            {"id": "c1", "content": "text1", "source": "s.md", "tags": ["t1"], "chunk_index": 0},
            {"id": "c2", "content": "text2", "source": "s.md", "tags": [], "chunk_index": 1},
        ]
        vs_mod.add_chunks(chunks)
        mock_store.add_texts.assert_called_once()
        args = mock_store.add_texts.call_args
        assert args.kwargs["texts"] == ["text1", "text2"]
        assert args.kwargs["ids"] == ["c1", "c2"]


class TestSearch:
    def test_search(self, mock_store):
        mock_doc = MagicMock()
        mock_doc.page_content = "result text"
        mock_doc.metadata = {"source": "s.md"}
        mock_store.similarity_search_with_score.return_value = [(mock_doc, 0.9)]

        results = vs_mod.search("query", k=3)
        assert len(results) == 1
        assert results[0]["content"] == "result text"
        assert results[0]["source"] == "s.md"
        assert results[0]["score"] == 0.9


class TestGetChunkCount:
    def test_count(self, mock_store):
        mock_store._collection.count.return_value = 42
        assert vs_mod.get_chunk_count() == 42


class TestGetDocumentSources:
    def test_sources(self, mock_store):
        mock_store._collection.get.return_value = {
            "metadatas": [{"source": "b.md"}, {"source": "a.md"}, {"source": "b.md"}]
        }
        sources = vs_mod.get_document_sources()
        assert sources == ["a.md", "b.md"]


class TestForgetSource:
    def test_forget(self, mock_store):
        mock_store._collection.get.return_value = {"ids": ["c1", "c2"]}
        count = vs_mod.forget_source("s.md")
        assert count == 2
        mock_store._collection.delete.assert_called_once_with(ids=["c1", "c2"])

    def test_forget_empty(self, mock_store):
        mock_store._collection.get.return_value = {"ids": []}
        count = vs_mod.forget_source("missing.md")
        assert count == 0
        mock_store._collection.delete.assert_not_called()


class TestClearAll:
    def test_clear(self, mock_store):
        mock_store._collection.count.return_value = 3
        mock_store._collection.get.return_value = {"ids": ["c1", "c2", "c3"]}
        count = vs_mod.clear_all()
        assert count == 3
        mock_store._collection.delete.assert_called_once()

    def test_clear_empty(self, mock_store):
        mock_store._collection.count.return_value = 0
        count = vs_mod.clear_all()
        assert count == 0
