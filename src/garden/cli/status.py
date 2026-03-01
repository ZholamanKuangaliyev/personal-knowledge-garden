import click
from rich.table import Table

from garden.ui.console import console


@click.command()
def status() -> None:
    """Show garden statistics."""
    from garden.store.vector_store import get_chunk_count, get_document_sources

    sources = get_document_sources()
    chunk_count = get_chunk_count()

    # Concept and card counts
    concept_count = 0
    link_count = 0
    try:
        from garden.store.graph_store import get_graph_stats
        stats = get_graph_stats()
        concept_count = stats["nodes"]
        link_count = stats["edges"]
    except Exception:
        pass

    card_count = 0
    cards_due = 0
    try:
        from garden.store.card_store import get_card_stats
        stats = get_card_stats()
        card_count = stats["total"]
        cards_due = stats["due"]
    except Exception:
        pass

    table = Table(title="Garden Status", show_header=False, padding=(0, 2))
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Documents", str(len(sources)))
    table.add_row("Chunks", str(chunk_count))
    table.add_row("Concepts", str(concept_count))
    table.add_row("Concept Links", str(link_count))
    table.add_row("Flashcards", str(card_count))
    table.add_row("Cards Due", str(cards_due))

    console.print()
    console.print(table)

    if sources:
        console.print("\n[bold]Documents:[/bold]")
        for s in sources:
            console.print(f"  - {s}")
    console.print()
