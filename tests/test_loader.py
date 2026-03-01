from pathlib import Path

import pytest

from garden.core.exceptions import EmptyDocumentError, UnsupportedFileType
from garden.ingestion.loader import load_file
from garden.ingestion.loaders.text_loader import load_text


class TestLoadFile:
    def test_load_txt(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello world", encoding="utf-8")
        content = load_file(f)
        assert content == "Hello world"

    def test_load_md(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Header\nBody", encoding="utf-8")
        content = load_file(f)
        assert "Header" in content

    def test_unsupported_extension(self, tmp_path):
        f = tmp_path / "test.docx"
        f.write_text("content", encoding="utf-8")
        with pytest.raises(UnsupportedFileType):
            load_file(f)

    def test_case_insensitive_extension(self, tmp_path):
        f = tmp_path / "TEST.TXT"
        f.write_text("content", encoding="utf-8")
        content = load_file(f)
        assert content == "content"


class TestTextLoader:
    def test_loads_content(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello", encoding="utf-8")
        assert load_text(f) == "Hello"

    def test_empty_file_raises(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        with pytest.raises(EmptyDocumentError):
            load_text(f)

    def test_whitespace_only_raises(self, tmp_path):
        f = tmp_path / "blank.txt"
        f.write_text("   \n\n  ", encoding="utf-8")
        with pytest.raises(EmptyDocumentError):
            load_text(f)

    def test_utf8_content(self, tmp_path):
        f = tmp_path / "unicode.txt"
        f.write_text("Hello", encoding="utf-8")
        assert load_text(f) == "Hello"
