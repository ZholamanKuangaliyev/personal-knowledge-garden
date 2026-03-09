import click

from garden.core.logging import get_logger
from garden.ui.console import console

_log = get_logger("cli.search")


@click.command()
@click.argument("query")
@click.option("--source", "-s", default=None, help="Filter results by source document.")
@click.option("--tag", "-t", default=None, help="Filter results by tag.")
@click.option("--limit", "-n", default=None, type=int, help="Maximum number of results.")
@click.option("--semantic", is_flag=True, help="Also show related concepts from the knowledge graph.")
def search(query: str, source: str | None, tag: str | None, limit: int | None, semantic: bool) -> None:
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
    else:
        console.print(f"[bold green]Found {len(results)} result(s)[/bold green]\n")
        for i, r in enumerate(results, 1):
            console.print(f"[bold]{i}.[/bold] [cyan]{r.source}[/cyan] [dim](score: {r.score:.3f})[/dim]")
            # Show a preview of the content (first 200 chars)
            preview = r.content[:200].replace("\n", " ")
            if len(r.content) > 200:
                preview += "..."
            console.print(f"   {preview}\n")

    if semantic:
        from garden.store.graph_store import get_all_concepts, get_concept_neighbors

        _log.debug("Semantic search: fetching concepts for query=%r", query)
        all_concepts = get_all_concepts()
        query_terms = {w.lower() for w in query.split() if len(w) > 2}
        matches = [c for c in all_concepts if any(t in c.name.lower() for t in query_terms)]

        if matches:
            console.print("[bold]Related Concepts[/bold]\n")
            for concept in matches[:5]:
                neighbors = get_concept_neighbors(concept.name, depth=1)
                neighbor_text = ", ".join(
                    f"{n['target']} [dim]({n['relation']}, w={n['weight']:.1f})[/dim]"
                    for n in neighbors[:5]
                )
                desc = f" — {concept.description}" if concept.description else ""
                console.print(f"  [cyan]{concept.name}[/cyan]{desc}")
                if neighbor_text:
                    console.print(f"    Links: {neighbor_text}")
                console.print()
        else:
            console.print("[dim]No matching concepts found in graph.[/dim]")
