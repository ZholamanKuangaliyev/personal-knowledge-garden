from datetime import datetime

from garden.core.models import Flashcard
from garden.store.database import get_connection


def _row_to_card(row) -> Flashcard:
    keys = row.keys()
    last_reviewed = row["last_reviewed_at"] if "last_reviewed_at" in keys else None
    return Flashcard(
        id=row["id"],
        question=row["question"],
        answer=row["answer"],
        source=row["source"],
        tags=row["tags"].split(",") if row["tags"] else [],
        created_at=datetime.fromisoformat(row["created_at"]),
        easiness=row["easiness"],
        interval=row["interval"],
        repetitions=row["repetitions"],
        next_review=datetime.fromisoformat(row["next_review"]),
        last_reviewed_at=datetime.fromisoformat(last_reviewed) if last_reviewed else None,
        review_count=row["review_count"] if "review_count" in keys else 0,
        source_chunk_id=row["source_chunk_id"] if "source_chunk_id" in keys else "",
    )


def add_cards(cards: list[Flashcard]) -> None:
    conn = get_connection()
    conn.executemany(
        "INSERT OR IGNORE INTO flashcards"
        " (id, question, answer, source, tags, created_at, easiness,"
        " interval, repetitions, next_review, last_reviewed_at,"
        " review_count, source_chunk_id)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                card.id,
                card.question,
                card.answer,
                card.source,
                ",".join(card.tags),
                card.created_at.isoformat(),
                card.easiness,
                card.interval,
                card.repetitions,
                card.next_review.isoformat(),
                card.last_reviewed_at.isoformat() if card.last_reviewed_at else None,
                card.review_count,
                card.source_chunk_id,
            )
            for card in cards
        ],
    )
    conn.commit()


def get_due_cards(count: int | None = None) -> list[Flashcard]:
    conn = get_connection()
    now = datetime.now().isoformat()
    query = "SELECT * FROM flashcards WHERE next_review <= ? ORDER BY next_review"
    params: list = [now]
    if count:
        query += " LIMIT ?"
        params.append(count)
    rows = conn.execute(query, params).fetchall()
    return [_row_to_card(r) for r in rows]


def update_card(card: Flashcard) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE flashcards SET question=?, answer=?, source=?, tags=?,"
        " created_at=?, easiness=?, interval=?, repetitions=?,"
        " next_review=?, last_reviewed_at=?, review_count=?,"
        " source_chunk_id=? WHERE id=?",
        (
            card.question,
            card.answer,
            card.source,
            ",".join(card.tags),
            card.created_at.isoformat(),
            card.easiness,
            card.interval,
            card.repetitions,
            card.next_review.isoformat(),
            card.last_reviewed_at.isoformat() if card.last_reviewed_at else None,
            card.review_count,
            card.source_chunk_id,
            card.id,
        ),
    )
    conn.commit()


def forget_source(source: str) -> int:
    conn = get_connection()
    cursor = conn.execute("DELETE FROM flashcards WHERE source = ?", (source,))
    conn.commit()
    return cursor.rowcount


def clear_all() -> int:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) FROM flashcards").fetchone()
    count = row[0]
    conn.execute("DELETE FROM flashcards")
    conn.commit()
    return count


def get_card_stats() -> dict:
    conn = get_connection()
    now = datetime.now().isoformat()
    total = conn.execute("SELECT COUNT(*) FROM flashcards").fetchone()[0]
    due = conn.execute("SELECT COUNT(*) FROM flashcards WHERE next_review <= ?", (now,)).fetchone()[0]
    return {"total": total, "due": due}
