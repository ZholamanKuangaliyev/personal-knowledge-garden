import click

from garden.core.logging import get_logger
from garden.ui.console import console

_log = get_logger("cli.search")


@click.command()
@click.argument("query")
@click.option("--source", "-s", default=None, help="Filter results by source document.")
@click.option("--tag", "-t", default=None, help="Filter results by tag.")
@click.option("--limit", "-n", default=None, type=int, help="Maximum number of results.")
def search(query: str, source: str | None, tag: str | None, limit: int | None) -> None:
    """Search your knowledge garden."""
    from garden.store.vector_store import search as vs_search

    where: dict | None = None
    if source:
        where = {"source": source}
    elif tag:
        where = {"tags": {"$contains": tag}}

    _log.debug("Search query=%r source=%s tag=%s limit=%s", query, source, tag, limit)
    results = vs_search(query, k=limit, where=where)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    console.print(f"[bold green]Found {len(results)} result(s)[/bold green]\n")
    for i, r in enumerate(results, 1):
        console.print(f"[bold]{i}.[/bold] [cyan]{r.source}[/cyan] [dim](score: {r.score:.3f})[/dim]")
        # Show a preview of the content (first 200 chars)
        preview = r.content[:200].replace("\n", " ")
        if len(r.content) > 200:
            preview += "..."
        console.print(f"   {preview}\n")
