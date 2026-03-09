"""Persistent chat history stored in SQLite."""

import uuid
from datetime import datetime

from garden.store.database import get_connection


def create_session(role: str = "general") -> str:
    """Create a new chat session and return its ID."""
    conn = get_connection()
    session_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO chat_sessions (id, started_at, last_active, role, title) VALUES (?, ?, ?, ?, ?)",
        (session_id, now, now, role, ""),
    )
    conn.commit()
    return session_id


def add_message(session_id: str, role: str, content: str) -> None:
    """Add a message to a chat session."""
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO chat_messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, role, content, now),
    )
    conn.execute(
        "UPDATE chat_sessions SET last_active = ? WHERE id = ?",
        (now, session_id),
    )
    conn.commit()


def get_session_messages(session_id: str, limit: int = 50) -> list[dict]:
    """Get messages from a session, most recent last."""
    conn = get_connection()
    # Use a subquery to get the most recent N messages, then order chronologically
    rows = conn.execute(
        "SELECT role, content, timestamp FROM ("
        "  SELECT role, content, timestamp, id FROM chat_messages"
        "  WHERE session_id = ? ORDER BY id DESC LIMIT ?"
        ") ORDER BY id ASC",
        (session_id, limit),
    ).fetchall()
    return [{"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]} for r in rows]


def get_recent_sessions(limit: int = 10) -> list[dict]:
    """Get recent chat sessions."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, started_at, last_active, role, title FROM chat_sessions ORDER BY last_active DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "started_at": r["started_at"],
            "last_active": r["last_active"],
            "role": r["role"],
            "title": r["title"],
        }
        for r in rows
    ]


def update_session_title(session_id: str, title: str) -> None:
    """Update the title of a chat session."""
    conn = get_connection()
    conn.execute("UPDATE chat_sessions SET title = ? WHERE id = ?", (title, session_id))
    conn.commit()


def delete_session(session_id: str) -> None:
    """Delete a chat session and all its messages."""
    conn = get_connection()
    conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
    conn.commit()
