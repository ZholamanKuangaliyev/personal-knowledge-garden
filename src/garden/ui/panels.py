from rich.markdown import Markdown
from rich.panel import Panel

from garden.ui.console import console


def show_answer(answer: str, sources: list[str] | None = None) -> None:
    md = Markdown(answer)
    console.print(Panel(md, title="Answer", border_style="green", padding=(1, 2)))
    if sources:
        source_text = ", ".join(sources)
        console.print(f"  [dim]Sources: {source_text}[/dim]\n")


def show_error(message: str) -> None:
    console.print(Panel(message, title="Error", border_style="red", padding=(1, 2)))
