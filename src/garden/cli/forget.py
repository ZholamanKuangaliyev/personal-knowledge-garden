import click

from garden.ui.console import console


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

    chunks = vector_store.forget_source(source)
    concepts = graph_store.forget_source(source)
    cards = card_store.forget_source(source)

    conn = get_connection()
    conn.execute("DELETE FROM documents WHERE source = ?", (source,))
    conn.commit()

    console.print(f"[bold green]Forgot '{source}':[/bold green]")
    console.print(f"  Removed {chunks} chunk(s)")
    console.print(f"  Removed {concepts} concept(s)")
    console.print(f"  Removed {cards} flashcard(s)")
