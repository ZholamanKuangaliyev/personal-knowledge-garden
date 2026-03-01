from datetime import datetime

from garden.core.models import Flashcard
from garden.store.database import get_connection


def _row_to_card(row) -> Flashcard:
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
    )


def add_cards(cards: list[Flashcard]) -> None:
    conn = get_connection()
    for card in cards:
        conn.execute(
            "INSERT OR IGNORE INTO flashcards (id, question, answer, source, tags, created_at, easiness, interval, repetitions, next_review) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
            ),
        )
    conn.commit()


def get_due_cards(count: int | None = None) -> list[Flashcard]:
    conn = get_connection()
    now = datetime.now().isoformat()
    query = "SELECT * FROM flashcards WHERE next_review <= ? ORDER BY next_review"
    if count:
        query += f" LIMIT {count}"
    rows = conn.execute(query, (now,)).fetchall()
    return [_row_to_card(r) for r in rows]


def update_card(card: Flashcard) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE flashcards SET question=?, answer=?, source=?, tags=?, created_at=?, easiness=?, interval=?, repetitions=?, next_review=? WHERE id=?",
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
