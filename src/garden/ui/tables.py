from rich.table import Table

from garden.ui.console import console


def show_concepts_table(concepts: list[dict]) -> None:
    table = Table(title="Concepts", padding=(0, 2))
    table.add_column("Concept", style="bold cyan")
    table.add_column("Source", style="dim")
    table.add_column("Connections", style="green")

    for c in concepts:
        table.add_row(c["name"], c.get("source", ""), str(c.get("connections", 0)))

    console.print(table)


def show_links_table(links: list[dict]) -> None:
    table = Table(title="Concept Links", padding=(0, 2))
    table.add_column("From", style="bold cyan")
    table.add_column("Relation", style="yellow")
    table.add_column("To", style="bold cyan")
    table.add_column("Weight", style="dim")

    for link in links:
        table.add_row(
            link["source"],
            link.get("relation", "related_to"),
            link["target"],
            f"{link.get('weight', 1.0):.1f}",
        )

    console.print(table)
