import json
import sqlite3
from datetime import datetime

import pytest

from garden.store.database import get_connection


class TestDatabaseInit:
    def test_creates_tables(self):
        conn = get_connection()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = sorted(r["name"] for r in tables)
        assert "concept_links" in table_names
        assert "concepts" in table_names
        assert "documents" in table_names
        assert "flashcards" in table_names

    def test_flashcards_schema(self):
        conn = get_connection()
        info = conn.execute("PRAGMA table_info(flashcards)").fetchall()
        columns = {r["name"] for r in info}
        assert columns == {
            "id", "question", "answer", "source", "tags",
            "created_at", "easiness", "interval", "repetitions", "next_review",
        }

    def test_concepts_schema(self):
        conn = get_connection()
        info = conn.execute("PRAGMA table_info(concepts)").fetchall()
        columns = {r["name"] for r in info}
        assert columns == {"name", "source", "description"}

    def test_concept_links_schema(self):
        conn = get_connection()
        info = conn.execute("PRAGMA table_info(concept_links)").fetchall()
        columns = {r["name"] for r in info}
        assert columns == {"source_concept", "target_concept", "relation", "weight"}

    def test_documents_schema(self):
        conn = get_connection()
        info = conn.execute("PRAGMA table_info(documents)").fetchall()
        columns = {r["name"] for r in info}
        assert columns == {"source", "content_hash", "ingested_at", "tags"}

    def test_connection_reuse(self):
        conn1 = get_connection()
        conn2 = get_connection()
        assert conn1 is conn2

    def test_wal_mode(self):
        conn = get_connection()
        mode = conn.execute("PRAGMA journal_mode").fetchone()
        assert mode[0] == "wal"


class TestMigration:
    def test_migrate_flashcards_from_json(self, isolated_db):
        cards_dir = isolated_db / "cards"
        cards_data = [
            {
                "id": "migrated-1",
                "question": "Q?",
                "answer": "A",
                "source": "old.md",
                "tags": ["t1"],
                "created_at": "2024-01-01T00:00:00",
                "easiness": 2.5,
                "interval": 1,
                "repetitions": 0,
                "next_review": "2024-01-01T00:00:00",
            }
        ]
        (cards_dir / "flashcards.json").write_text(
            json.dumps(cards_data), encoding="utf-8"
        )

        conn = get_connection()
        row = conn.execute("SELECT COUNT(*) FROM flashcards").fetchone()
        assert row[0] == 1

        # JSON file should be renamed to .bak
        assert not (cards_dir / "flashcards.json").exists()
        assert (cards_dir / "flashcards.json.bak").exists()

    def test_migrate_graph_from_json(self, isolated_db):
        import networkx as nx

        graph_dir = isolated_db / "graph"
        g = nx.Graph()
        g.add_node("concept_a", source="doc.md", description="desc")
        g.add_node("concept_b", source="doc.md", description="desc2")
        g.add_edge("concept_a", "concept_b", relation="co_occurs", weight=1.0)

        data = nx.node_link_data(g)
        (graph_dir / "knowledge_graph.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

        conn = get_connection()
        concepts = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        links = conn.execute("SELECT COUNT(*) FROM concept_links").fetchone()[0]
        assert concepts == 2
        assert links == 1

        assert not (graph_dir / "knowledge_graph.json").exists()
        assert (graph_dir / "knowledge_graph.json.bak").exists()

    def test_no_migration_when_no_json(self):
        conn = get_connection()
        assert conn.execute("SELECT COUNT(*) FROM flashcards").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0] == 0

    def test_no_double_migration(self, isolated_db):
        """If DB already has data, don't re-import JSON."""
        import garden.store.database as db_mod

        cards_dir = isolated_db / "cards"
        cards_data = [
            {
                "id": "x",
                "question": "Q",
                "answer": "A",
                "source": "s.md",
                "tags": [],
                "created_at": "2024-01-01T00:00:00",
                "easiness": 2.5,
                "interval": 1,
                "repetitions": 0,
                "next_review": "2024-01-01T00:00:00",
            }
        ]

        # First migration
        (cards_dir / "flashcards.json").write_text(
            json.dumps(cards_data), encoding="utf-8"
        )
        conn = get_connection()
        assert conn.execute("SELECT COUNT(*) FROM flashcards").fetchone()[0] == 1

        # Put JSON back (simulate leftover)
        bak = cards_dir / "flashcards.json.bak"
        bak.rename(cards_dir / "flashcards.json")

        # Reset and reconnect — should skip migration since table has data
        db_mod._connection.close()
        db_mod._connection = None
        conn = get_connection()
        assert conn.execute("SELECT COUNT(*) FROM flashcards").fetchone()[0] == 1
