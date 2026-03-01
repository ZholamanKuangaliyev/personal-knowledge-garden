import click
from rich.panel import Panel

from garden.ui.console import console


@click.command()
@click.argument("topic")
def ideate(topic: str) -> None:
    """Generate ideas from your stored knowledge on a topic."""
    from rich.live import Live
    from rich.spinner import Spinner

    from garden.knowledge.idea_generator import generate_ideas

    with Live(Spinner("dots", text="Generating ideas..."), console=console, transient=True):
        ideas = generate_ideas(topic)

    if not ideas:
        console.print("[yellow]Could not generate ideas. Try ingesting more relevant documents.[/yellow]")
        return

    console.print(f"\n[bold green]Ideas for '{topic}'[/bold green]\n")

    for i, idea in enumerate(ideas, 1):
        title = idea.get("title", f"Idea {i}")
        description = idea.get("description", "")
        connections = idea.get("connections", [])
        body = description
        if connections:
            body += f"\n\n[dim]Connected to: {', '.join(connections)}[/dim]"
        console.print(
            Panel(body, title=f"[bold]{i}. {title}[/bold]", border_style="blue", padding=(1, 2))
        )
    console.print()
