"""Transaction context manager for coordinated multi-store operations."""

from contextlib import contextmanager

from garden.core.logging import get_logger

_log = get_logger("transaction")


@contextmanager
def garden_transaction():
    """Context manager that wraps multi-store operations in a SQLite transaction.

    On success: commits the database transaction.
    On failure: rolls back the database transaction.

    IMPORTANT: ChromaDB operations cannot be rolled back. To minimize
    inconsistency risk, structure code so that ChromaDB writes happen
    AFTER all SQLite operations that might fail. If the ChromaDB write
    succeeds but a later operation fails, the vector data will be
    orphaned — this is recoverable (re-ingest), whereas losing DB
    records is not.

    Recommended ordering inside a garden_transaction() block:
        1. SQLite writes (concepts, links, flashcards, documents)
        2. ChromaDB writes (add_chunks) — last step
    """
    from garden.store.database import get_connection

    conn = get_connection()
    try:
        yield conn
        conn.commit()
        _log.debug("Transaction committed")
    except Exception:
        conn.rollback()
        _log.warning("Transaction rolled back due to error")
        raise
