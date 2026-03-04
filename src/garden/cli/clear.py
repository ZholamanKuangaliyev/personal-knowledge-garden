import click

from garden.core.logging import get_logger
from garden.ui.console import console

_log = get_logger("cli.clear")


@click.command()
@click.confirmation_option(prompt="This will delete ALL data. Are you sure?")
def clear() -> None:
    """Wipe all data from the garden."""
    from garden.store import card_store, graph_store, vector_store

    from garden.store.database import get_connection

    _log.info("Clearing all garden data")
    errors: list[str] = []
    chunks = 0
    concepts = 0
    cards = 0

    try:
        chunks = vector_store.clear_all()
    except Exception as e:
        _log.error("Failed to clear vector store: %s", e, exc_info=True)
        errors.append(f"vector store: {e}")

    # Group SQLite operations under a single transaction
    conn = get_connection()
    try:
        concepts = graph_store.clear_all()
        cards = card_store.clear_all()
        conn.execute("DELETE FROM documents")
        conn.commit()
    except Exception as e:
        _log.error("Failed to clear database: %s", e, exc_info=True)
        errors.append(f"database: {e}")

    if errors:
        console.print(f"[bold yellow]Partial failure during clear:[/bold yellow]")
        for err in errors:
            console.print(f"  [red]{err}[/red]")
    else:
        console.print(f"[bold green]Garden cleared:[/bold green]")

    console.print(f"  Removed {chunks} chunk(s)")
    console.print(f"  Removed {concepts} concept(s)")
    console.print(f"  Removed {cards} flashcard(s)")
