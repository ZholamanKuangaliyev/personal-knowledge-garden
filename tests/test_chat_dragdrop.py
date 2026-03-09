from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from garden.cli.chat import _detect_file_path, _ingest_dropped_file


class TestDetectFilePath:
    def test_valid_txt_file(self, tmp_path):
        f = tmp_path / "notes.txt"
        f.write_text("hello", encoding="utf-8")
        result = _detect_file_path(str(f))
        assert result == f

    def test_valid_md_file(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("# hello", encoding="utf-8")
        result = _detect_file_path(str(f))
        assert result == f

    def test_quoted_path_double_quotes(self, tmp_path):
        f = tmp_path / "notes.txt"
        f.write_text("hello", encoding="utf-8")
        result = _detect_file_path(f'"{f}"')
        assert result == f

    def test_quoted_path_single_quotes(self, tmp_path):
        f = tmp_path / "notes.txt"
        f.write_text("hello", encoding="utf-8")
        result = _detect_file_path(f"'{f}'")
        assert result == f

    def test_unsupported_extension(self, tmp_path):
        f = tmp_path / "script.py"
        f.write_text("print('hi')", encoding="utf-8")
        result = _detect_file_path(str(f))
        assert result is None

    def test_nonexistent_file(self):
        result = _detect_file_path("/nonexistent/file.txt")
        assert result is None

    def test_normal_text_not_a_path(self):
        result = _detect_file_path("What is machine learning?")
        assert result is None

    def test_empty_string(self):
        result = _detect_file_path("")
        assert result is None


class TestIngestDroppedFile:
    def test_successful_ingestion(self):
        mock_result = {"chunks": 5, "concepts": 3, "cards": 2, "links": 4}
        with patch("garden.cli.ingest.ingest_single_file", return_value=mock_result) as mock_ingest, \
             patch("garden.store.graph_store.flush_cache") as mock_flush, \
             patch("garden.cli.chat.Live"), \
             patch("garden.cli.chat.console"):
            _ingest_dropped_file(Path("test.txt"))
            mock_ingest.assert_called_once()
            mock_flush.assert_called_once()

    def test_duplicate_file_value_error(self):
        with patch("garden.cli.ingest.ingest_single_file", side_effect=ValueError("already ingested")), \
             patch("garden.store.graph_store.flush_cache") as mock_flush, \
             patch("garden.cli.chat.Live"), \
             patch("garden.cli.chat.console"):
            _ingest_dropped_file(Path("test.txt"))
            mock_flush.assert_not_called()

    def test_ingestion_failure_runtime_error(self):
        with patch("garden.cli.ingest.ingest_single_file", side_effect=RuntimeError("disk full")), \
             patch("garden.store.graph_store.flush_cache") as mock_flush, \
             patch("garden.cli.chat.Live"), \
             patch("garden.cli.chat.console"):
            _ingest_dropped_file(Path("test.txt"))
            mock_flush.assert_not_called()
