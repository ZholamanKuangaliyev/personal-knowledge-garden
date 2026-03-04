import re

from rich.markdown import Markdown
from rich.syntax import Syntax

from garden.core.models import Flashcard
from garden.srs.scheduler import sm2_update
from garden.store.card_store import get_due_cards, update_card
from garden.ui.console import console

_CODE_FENCE_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)


def _render_card_text(text: str) -> None:
    """Render card text with syntax highlighting for code fences."""
    if _CODE_FENCE_RE.search(text):
        # Split text into code and non-code segments
        last_end = 0
        for match in _CODE_FENCE_RE.finditer(text):
            # Render text before code block as markdown
            before = text[last_end:match.start()].strip()
            if before:
                console.print(Markdown(before))
            lang = match.group(1) or "text"
            code = match.group(2).rstrip()
            console.print(Syntax(code, lang, theme="monokai"))
            last_end = match.end()
        # Render remaining text
        after = text[last_end:].strip()
        if after:
            console.print(Markdown(after))
    else:
        console.print(Markdown(text))


def run_review(count: int) -> None:
    cards = get_due_cards(count)

    if not cards:
        console.print("[yellow]No cards due for review![/yellow]")
        return

    console.print(f"\n[bold green]Review Session[/bold green] - {len(cards)} card(s)\n")
    console.print("[dim]Rate your recall: 0=blackout, 1=wrong, 2=hard, 3=ok, 4=good, 5=perfect[/dim]\n")

    for i, card in enumerate(cards, 1):
        console.print(f"[bold]Card {i}/{len(cards)}[/bold] [dim]({card.source})[/dim]")
        console.print(f"\n[cyan]Q:[/cyan]")
        _render_card_text(card.question)

        try:
            console.input("\n[dim]Press Enter to reveal answer...[/dim]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Session ended.[/dim]")
            return

        console.print(f"[green]A:[/green]")
        _render_card_text(card.answer)
        console.print()

        while True:
            try:
                rating_str = console.input("[bold]Rating (0-5):[/bold] ")
                rating = int(rating_str.strip())
                if 0 <= rating <= 5:
                    break
                console.print("[red]Please enter a number 0-5.[/red]")
            except (ValueError, EOFError, KeyboardInterrupt):
                console.print("\n[dim]Session ended.[/dim]")
                return

        updated = sm2_update(card, rating)
        update_card(updated)
        console.print(f"[dim]Next review in {updated.interval} day(s)[/dim]\n")
        console.print("---\n")

    console.print("[bold green]Review complete![/bold green]\n")
