"""Tests for transaction safety."""

import pytest

from garden.store.transaction import garden_transaction
from garden.store.database import get_connection


class TestTransaction:
    def test_commit_on_success(self):
        with garden_transaction() as conn:
            conn.execute(
                "INSERT INTO concepts (name, source, description) VALUES (?, ?, ?)",
                ("test_concept", "test.md", "desc"),
            )

        # Should be committed
        conn = get_connection()
        row = conn.execute("SELECT name FROM concepts WHERE name = ?", ("test_concept",)).fetchone()
        assert row is not None

    def test_rollback_on_error(self):
        with pytest.raises(ValueError):
            with garden_transaction() as conn:
                conn.execute(
                    "INSERT INTO concepts (name, source, description) VALUES (?, ?, ?)",
                    ("rollback_concept", "test.md", "desc"),
                )
                raise ValueError("Simulated failure")

        # Should be rolled back
        conn = get_connection()
        row = conn.execute("SELECT name FROM concepts WHERE name = ?", ("rollback_concept",)).fetchone()
        assert row is None

    def test_nested_operations(self):
        with garden_transaction() as conn:
            conn.execute(
                "INSERT INTO concepts (name, source, description) VALUES (?, ?, ?)",
                ("concept_a", "test.md", "A"),
            )
            conn.execute(
                "INSERT INTO concepts (name, source, description) VALUES (?, ?, ?)",
                ("concept_b", "test.md", "B"),
            )
            conn.execute(
                "INSERT INTO concept_links (source_concept, target_concept, relation, weight) VALUES (?, ?, ?, ?)",
                ("concept_a", "concept_b", "related_to", 1.0),
            )

        conn = get_connection()
        count = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        assert count == 2
        links = conn.execute("SELECT COUNT(*) FROM concept_links").fetchone()[0]
        assert links == 1
