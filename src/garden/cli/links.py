import click

from garden.ui.console import console
from garden.ui.tables import show_concepts_table, show_links_table


@click.command()
@click.option("--concept", "-c", default=None, help="Explore connections for a specific concept.")
@click.option("--depth", "-d", default=1, help="Depth of graph traversal.")
def links(concept: str | None, depth: int) -> None:
    """Explore concept graph connections."""
    from garden.store.graph_store import get_all_concepts, get_concept_neighbors, get_graph

    graph = get_graph()

    if graph.number_of_nodes() == 0:
        console.print("[yellow]No concepts found. Ingest some documents first.[/yellow]")
        return

    if concept:
        neighbors = get_concept_neighbors(concept.lower(), depth=depth)
        if not neighbors:
            console.print(f"[yellow]No connections found for '{concept}'.[/yellow]")
            return
        console.print(f"\n[bold]Connections for '[cyan]{concept}[/cyan]' (depth={depth}):[/bold]\n")
        show_links_table(neighbors)
    else:
        concepts = get_all_concepts()
        concept_data = []
        for c in concepts:
            connections = len(list(graph.neighbors(c.name)))
            concept_data.append({"name": c.name, "source": c.source, "connections": connections})
        concept_data.sort(key=lambda x: x["connections"], reverse=True)
        console.print()
        show_concepts_table(concept_data)
    console.print()
