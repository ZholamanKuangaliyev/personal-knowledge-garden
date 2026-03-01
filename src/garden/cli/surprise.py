import click
from rich.panel import Panel

from garden.core.config import settings
from garden.ui.console import console


@click.command()
@click.option("--count", "-n", default=None, type=int, help="Number of insights to generate.")
def surprise(count: int | None) -> None:
    """Surface unexpected cross-domain insights."""
    from rich.live import Live
    from rich.spinner import Spinner

    from garden.knowledge.insight_engine import generate_insights

    n = count or settings.default_surprise_count

    with Live(Spinner("dots", text="Discovering insights..."), console=console, transient=True):
        insights = generate_insights(n)

    if not insights:
        console.print("[yellow]Not enough diverse knowledge yet. Ingest more documents![/yellow]")
        return

    console.print(f"\n[bold green]Surprise Insights[/bold green] ({len(insights)} found)\n")

    for i, insight in enumerate(insights, 1):
        title = f"{insight.get('concept_a', '?')} <-> {insight.get('concept_b', '?')}"
        console.print(
            Panel(
                insight.get("insight", ""),
                title=f"[bold]{i}. {title}[/bold]",
                border_style="magenta",
                padding=(1, 2),
            )
        )
    console.print()
