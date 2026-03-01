import json
import sqlite3
from datetime import datetime
from pathlib import Path

from garden.core.config import settings

_connection: sqlite3.Connection | None = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS flashcards (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    source TEXT NOT NULL,
    tags TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    easiness REAL DEFAULT 2.5,
    interval INTEGER DEFAULT 1,
    repetitions INTEGER DEFAULT 0,
    next_review TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS concepts (
    name TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS concept_links (
    source_concept TEXT NOT NULL,
    target_concept TEXT NOT NULL,
    relation TEXT DEFAULT 'related_to',
    weight REAL DEFAULT 1.0,
    PRIMARY KEY (source_concept, target_concept)
);

CREATE TABLE IF NOT EXISTS documents (
    source TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    tags TEXT DEFAULT ''
);
"""


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(str(settings.db_path))
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA foreign_keys=ON")
        _connection.executescript(_SCHEMA)
        _migrate_json_data()
    return _connection


def _migrate_json_data() -> None:
    _migrate_flashcards()
    _migrate_graph()


def _migrate_flashcards() -> None:
    cards_file = settings.cards_dir / "flashcards.json"
    if not cards_file.exists():
        return

    conn = _connection
    row = conn.execute("SELECT COUNT(*) FROM flashcards").fetchone()
    if row[0] > 0:
        return

    try:
        data = json.loads(cards_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    if not data:
        return

    for card in data:
        tags = ",".join(card.get("tags", []))
        conn.execute(
            "INSERT OR IGNORE INTO flashcards (id, question, answer, source, tags, created_at, easiness, interval, repetitions, next_review) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                card["id"],
                card["question"],
                card["answer"],
                card["source"],
                tags,
                str(card.get("created_at", datetime.now().isoformat())),
                card.get("easiness", 2.5),
                card.get("interval", 1),
                card.get("repetitions", 0),
                str(card.get("next_review", datetime.now().isoformat())),
            ),
        )
    conn.commit()

    backup = cards_file.with_suffix(".json.bak")
    cards_file.rename(backup)
    print(f"Migrated {len(data)} flashcards to SQLite. JSON backed up to {backup}")


def _migrate_graph() -> None:
    import networkx as nx

    graph_file = settings.graph_dir / "knowledge_graph.json"
    if not graph_file.exists():
        return

    conn = _connection
    row = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()
    if row[0] > 0:
        return

    try:
        data = json.loads(graph_file.read_text(encoding="utf-8"))
        graph = nx.node_link_graph(data)
    except (json.JSONDecodeError, OSError, Exception):
        return

    if graph.number_of_nodes() == 0:
        return

    for node, attrs in graph.nodes(data=True):
        conn.execute(
            "INSERT OR IGNORE INTO concepts (name, source, description) VALUES (?, ?, ?)",
            (node, attrs.get("source", ""), attrs.get("description", "")),
        )

    for u, v, attrs in graph.edges(data=True):
        conn.execute(
            "INSERT OR IGNORE INTO concept_links (source_concept, target_concept, relation, weight) VALUES (?, ?, ?, ?)",
            (u, v, attrs.get("relation", "related_to"), attrs.get("weight", 1.0)),
        )

    conn.commit()

    backup = graph_file.with_suffix(".json.bak")
    graph_file.rename(backup)
    print(f"Migrated {graph.number_of_nodes()} concepts and {graph.number_of_edges()} links to SQLite. JSON backed up to {backup}")
