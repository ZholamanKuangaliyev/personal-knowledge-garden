from garden.core.models import Flashcard
from garden.srs.scheduler import sm2_update
from garden.store.card_store import get_due_cards, update_card
from garden.ui.console import console


def run_review(count: int) -> None:
    cards = get_due_cards(count)

    if not cards:
        console.print("[yellow]No cards due for review![/yellow]")
        return

    console.print(f"\n[bold green]Review Session[/bold green] - {len(cards)} card(s)\n")
    console.print("[dim]Rate your recall: 0=blackout, 1=wrong, 2=hard, 3=ok, 4=good, 5=perfect[/dim]\n")

    for i, card in enumerate(cards, 1):
        console.print(f"[bold]Card {i}/{len(cards)}[/bold] [dim]({card.source})[/dim]")
        console.print(f"\n[cyan]Q:[/cyan] {card.question}")

        try:
            console.input("\n[dim]Press Enter to reveal answer...[/dim]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Session ended.[/dim]")
            return

        console.print(f"[green]A:[/green] {card.answer}\n")

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
