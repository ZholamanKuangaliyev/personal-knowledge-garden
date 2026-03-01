import pytest

from garden.ingestion.chunker import chunk_text


class TestChunkText:
    def test_short_text_single_chunk(self):
        chunks = chunk_text("Hello world", source="test.md")
        assert len(chunks) == 1
        assert chunks[0]["content"] == "Hello world"
        assert chunks[0]["source"] == "test.md"
        assert chunks[0]["chunk_index"] == 0

    def test_id_format(self):
        chunks = chunk_text("Short", source="doc.md")
        assert chunks[0]["id"] == "doc.md::chunk_0"

    def test_tags_propagated(self):
        chunks = chunk_text("Hello", source="s.md", tags=["t1", "t2"])
        assert chunks[0]["tags"] == ["t1", "t2"]

    def test_default_empty_tags(self):
        chunks = chunk_text("Hello", source="s.md")
        assert chunks[0]["tags"] == []

    def test_long_text_produces_multiple_chunks(self):
        # Create text longer than default chunk_size (1000)
        text = "word " * 500  # ~2500 chars
        chunks = chunk_text(text, source="big.md")
        assert len(chunks) >= 2
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i
            assert chunk["id"] == f"big.md::chunk_{i}"

    def test_chunk_structure(self):
        chunks = chunk_text("Test content", source="s.md", tags=["x"])
        chunk = chunks[0]
        assert set(chunk.keys()) == {"id", "content", "source", "tags", "chunk_index"}
