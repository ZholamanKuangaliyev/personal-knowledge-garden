import click

from garden.ui.console import console


@click.command()
@click.confirmation_option(prompt="This will delete ALL data. Are you sure?")
def clear() -> None:
    """Wipe all data from the garden."""
    from garden.store import card_store, graph_store, vector_store

    from garden.store.database import get_connection

    chunks = vector_store.clear_all()
    concepts = graph_store.clear_all()
    cards = card_store.clear_all()

    conn = get_connection()
    conn.execute("DELETE FROM documents")
    conn.commit()

    console.print(f"[bold green]Garden cleared:[/bold green]")
    console.print(f"  Removed {chunks} chunk(s)")
    console.print(f"  Removed {concepts} concept(s)")
    console.print(f"  Removed {cards} flashcard(s)")
