import json
import sqlite3
from contextlib import suppress
from datetime import datetime

from garden.core.config import settings
from garden.core.logging import get_logger

_log = get_logger("database")

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

CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    last_active TEXT NOT NULL,
    role TEXT DEFAULT 'general',
    title TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_flashcards_source ON flashcards(source);
CREATE INDEX IF NOT EXISTS idx_flashcards_next_review ON flashcards(next_review);
CREATE INDEX IF NOT EXISTS idx_concepts_source ON concepts(source);
CREATE INDEX IF NOT EXISTS idx_concept_links_source ON concept_links(source_concept);
CREATE INDEX IF NOT EXISTS idx_concept_links_target ON concept_links(target_concept);
CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_last_active ON chat_sessions(last_active);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
"""

CURRENT_SCHEMA_VERSION = 2


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(str(settings.db_path))
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA foreign_keys=ON")
        _connection.executescript(_SCHEMA)
        _apply_migrations()
        _migrate_json_data()
    return _connection


def _apply_migrations() -> None:
    """Run schema migrations based on version tracking."""
    conn = _connection
    row = conn.execute(
        "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
    ).fetchone()
    current = row[0] if row else 0

    if current < 2:
        _migrate_to_v2(conn)

    if current < CURRENT_SCHEMA_VERSION:
        conn.execute(
            "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
            (CURRENT_SCHEMA_VERSION,),
        )
        conn.commit()
        _log.info("Schema updated to version %d", CURRENT_SCHEMA_VERSION)


def _migrate_to_v2(conn) -> None:
    """Schema v2: add enriched model fields and missing indexes."""
    _log.info("Running migration to schema version 2")

    # New columns on concepts
    for col, typedef in [("category", "TEXT DEFAULT ''"), ("importance", "REAL DEFAULT 0.0")]:
        with suppress(Exception):
            conn.execute(f"ALTER TABLE concepts ADD COLUMN {col} {typedef}")

    # New columns on flashcards
    for col, typedef in [
        ("last_reviewed_at", "TEXT"),
        ("review_count", "INTEGER DEFAULT 0"),
        ("source_chunk_id", "TEXT DEFAULT ''"),
    ]:
        with suppress(Exception):
            conn.execute(f"ALTER TABLE flashcards ADD COLUMN {col} {typedef}")

    # Missing indexes for common queries
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_flashcards_created_at ON flashcards(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_concept_links_weight ON concept_links(weight)",
        "CREATE INDEX IF NOT EXISTS idx_documents_ingested_at ON documents(ingested_at)",
    ]:
        conn.execute(idx_sql)

    conn.commit()


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
    except (json.JSONDecodeError, OSError) as exc:
        _log.error("Failed to read flashcards JSON %s: %s", cards_file, exc)
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
    _log.info("Migrated %d flashcards to SQLite. JSON backed up to %s", len(data), backup)


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
    except (json.JSONDecodeError, OSError) as exc:
        _log.error("Failed to read graph JSON %s: %s", graph_file, exc)
        return
    except Exception as exc:
        _log.error("Failed to parse knowledge graph from %s: %s", graph_file, exc)
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
    _log.info("Migrated %d concepts and %d links to SQLite. JSON backed up to %s", graph.number_of_nodes(), graph.number_of_edges(), backup)
