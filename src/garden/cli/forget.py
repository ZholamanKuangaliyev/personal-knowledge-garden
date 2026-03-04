import click

from garden.core.logging import get_logger
from garden.ui.console import console

_log = get_logger("cli.forget")


@click.command()
@click.argument("source")
def forget(source: str) -> None:
    """Remove a document and all its data from the garden."""
    from garden.store import card_store, graph_store, vector_store

    sources = vector_store.get_document_sources()
    if source not in sources:
        console.print(f"[yellow]Document '{source}' not found.[/yellow]")
        console.print(f"[dim]Known documents: {', '.join(sources) or 'none'}[/dim]")
        return

    from garden.store.database import get_connection

    errors: list[str] = []
    chunks = 0
    concepts = 0
    cards = 0

    _log.info("Forgetting source '%s'", source)
    try:
        chunks = vector_store.forget_source(source)
    except Exception as e:
        _log.error("Failed to forget source '%s' from vector store: %s", source, e, exc_info=True)
        errors.append(f"vector store: {e}")

    # Group SQLite operations under a single transaction
    conn = get_connection()
    try:
        concepts = graph_store.forget_source(source)
        cards = card_store.forget_source(source)
        conn.execute("DELETE FROM documents WHERE source = ?", (source,))
        conn.commit()
    except Exception as e:
        _log.error("Failed to forget source '%s' from database: %s", source, e, exc_info=True)
        errors.append(f"database: {e}")

    if errors:
        console.print(f"[bold yellow]Partial failure forgetting '{source}':[/bold yellow]")
        for err in errors:
            console.print(f"  [red]{err}[/red]")
    else:
        console.print(f"[bold green]Forgot '{source}':[/bold green]")

    console.print(f"  Removed {chunks} chunk(s)")
    console.print(f"  Removed {concepts} concept(s)")
    console.print(f"  Removed {cards} flashcard(s)")
