import click
from rich.live import Live
from rich.spinner import Spinner

from garden.ui.console import console
from garden.ui.panels import show_answer, show_error


@click.command()
def chat() -> None:
    """Interactive RAG chat with your knowledge garden."""
    from garden.agent.graph import get_agent

    console.print("[bold green]Knowledge Garden Chat[/bold green]")
    console.print("[dim]Type 'quit' or 'exit' to leave. Ask anything about your stored knowledge.[/dim]\n")

    agent = get_agent()

    while True:
        try:
            question = console.input("[bold cyan]You:[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if question.strip().lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        if not question.strip():
            continue

        with Live(Spinner("dots", text="Thinking..."), console=console, transient=True):
            try:
                result = agent.invoke({"question": question, "retry_count": 0})
                answer = result.get("generation", "No answer generated.")
                sources = result.get("sources", [])
                show_answer(answer, sources)
            except Exception as e:
                show_error(f"Error: {e}")
