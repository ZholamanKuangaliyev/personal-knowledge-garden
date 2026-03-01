import hashlib
from datetime import datetime

import pytest

from garden.store.database import get_connection


class TestDuplicateDetection:
    def _register(self, source, content_hash, tags=None):
        conn = get_connection()
        conn.execute(
            "INSERT INTO documents (source, content_hash, ingested_at, tags) VALUES (?, ?, ?, ?)",
            (source, content_hash, datetime.now().isoformat(), ",".join(tags or [])),
        )
        conn.commit()

    def test_check_duplicate_by_hash(self):
        from garden.cli.ingest import _check_duplicate

        self._register("original.md", "abc123")

        # A different filename but same content hash
        fake_file = type("FakePath", (), {"name": "copy.md"})()
        reason = _check_duplicate(fake_file, "abc123")
        assert reason is not None
        assert "original.md" in reason

    def test_check_duplicate_by_source_name(self):
        from garden.cli.ingest import _check_duplicate

        self._register("notes.md", "hash1")

        fake_file = type("FakePath", (), {"name": "notes.md"})()
        reason = _check_duplicate(fake_file, "different_hash")
        assert reason is not None
        assert "already ingested" in reason

    def test_no_duplicate_for_new_file(self):
        from garden.cli.ingest import _check_duplicate

        fake_file = type("FakePath", (), {"name": "brand_new.md"})()
        reason = _check_duplicate(fake_file, "unique_hash")
        assert reason is None

    def test_compute_hash(self, tmp_path):
        from garden.cli.ingest import _compute_hash

        f = tmp_path / "test.txt"
        f.write_bytes(b"hello world")
        h = _compute_hash(f)
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert h == expected

    def test_register_document(self):
        from garden.cli.ingest import _register_document

        _register_document("file.md", "hash123", ["tag1", "tag2"])
        conn = get_connection()
        row = conn.execute("SELECT * FROM documents WHERE source = 'file.md'").fetchone()
        assert row is not None
        assert row["content_hash"] == "hash123"
        assert row["tags"] == "tag1,tag2"

    def test_register_replaces_on_same_source(self):
        from garden.cli.ingest import _register_document

        _register_document("file.md", "hash1", [])
        _register_document("file.md", "hash2", [])
        conn = get_connection()
        rows = conn.execute("SELECT * FROM documents WHERE source = 'file.md'").fetchall()
        assert len(rows) == 1
        assert rows[0]["content_hash"] == "hash2"


class TestDocumentCleanup:
    def test_clear_removes_documents(self):
        conn = get_connection()
        conn.execute(
            "INSERT INTO documents (source, content_hash, ingested_at) VALUES (?, ?, ?)",
            ("x.md", "hash", datetime.now().isoformat()),
        )
        conn.commit()

        conn.execute("DELETE FROM documents")
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0

    def test_forget_removes_single_document(self):
        conn = get_connection()
        conn.execute(
            "INSERT INTO documents (source, content_hash, ingested_at) VALUES (?, ?, ?)",
            ("a.md", "h1", datetime.now().isoformat()),
        )
        conn.execute(
            "INSERT INTO documents (source, content_hash, ingested_at) VALUES (?, ?, ?)",
            ("b.md", "h2", datetime.now().isoformat()),
        )
        conn.commit()

        conn.execute("DELETE FROM documents WHERE source = ?", ("a.md",))
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
        remaining = conn.execute("SELECT source FROM documents").fetchone()
        assert remaining["source"] == "b.md"
