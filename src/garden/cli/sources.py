import click
from rich.table import Table

from garden.core.logging import get_logger
from garden.ui.console import console

_log = get_logger("cli.sources")


@click.command()
def sources() -> None:
    """List all ingested document sources."""
    from garden.store.vector_store import get_source_details

    details = get_source_details()

    if not details:
        console.print("[dim]No documents ingested yet. Run 'garden ingest <file>' to add documents.[/dim]")
        return

    table = Table(title="Ingested Sources", padding=(0, 2))
    table.add_column("Source", style="bold cyan")
    table.add_column("Chunks", style="white", justify="right")
    table.add_column("Tags", style="dim")

    total_chunks = 0
    for d in details:
        tags = ", ".join(d["tags"]) if d["tags"] else ""
        table.add_row(d["source"], str(d["chunks"]), tags)
        total_chunks += d["chunks"]

    console.print()
    console.print(table)
    console.print(f"\n[dim]{len(details)} source(s), {total_chunks} chunk(s) total[/dim]")
    console.print("[dim]Use 'garden chat --source <name>' to chat about a specific document.[/dim]")
    console.print()
