import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from garden.core.models import Concept, ConceptLink, Flashcard


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Give every test its own SQLite database and reset the module-level connection."""
    import garden.store.database as db_mod
    from garden.core.config import Settings

    db_file = tmp_path / "test.db"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    graph_dir = tmp_path / "graph"
    graph_dir.mkdir()

    monkeypatch.setattr("garden.core.config.settings.db_path", db_file)
    monkeypatch.setattr("garden.core.config.settings.data_dir", data_dir)
    monkeypatch.setattr("garden.core.config.settings.cards_dir", cards_dir)
    monkeypatch.setattr("garden.core.config.settings.graph_dir", graph_dir)

    # Reset the global connection so each test gets a fresh DB
    db_mod._connection = None

    # Also reset graph cache
    import garden.store.graph_store as gs_mod
    gs_mod._graph_cache = None

    yield tmp_path

    # Cleanup: close connection if open
    if db_mod._connection is not None:
        db_mod._connection.close()
        db_mod._connection = None


@pytest.fixture
def sample_cards():
    now = datetime.now()
    return [
        Flashcard(
            id="card-1",
            question="What is Python?",
            answer="A programming language",
            source="test.md",
            tags=["programming"],
            created_at=now,
            next_review=now - timedelta(hours=1),
        ),
        Flashcard(
            id="card-2",
            question="What is Rust?",
            answer="A systems programming language",
            source="test.md",
            tags=["programming"],
            created_at=now,
            next_review=now + timedelta(days=5),
        ),
        Flashcard(
            id="card-3",
            question="What is SQL?",
            answer="Structured Query Language",
            source="other.md",
            tags=["database"],
            created_at=now,
            next_review=now - timedelta(days=1),
        ),
    ]


@pytest.fixture
def sample_concepts():
    return [
        Concept(name="machine learning", source="ml.md", description="A branch of AI"),
        Concept(name="neural networks", source="ml.md", description="Computational models"),
        Concept(name="data science", source="ds.md", description="Interdisciplinary field"),
    ]


@pytest.fixture
def sample_links():
    return [
        ConceptLink(source_concept="machine learning", target_concept="neural networks", relation="co_occurs", weight=1.0),
        ConceptLink(source_concept="machine learning", target_concept="data science", relation="shared_terms", weight=0.5),
    ]
