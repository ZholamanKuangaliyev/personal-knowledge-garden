import click

from garden.core.config import settings


@click.command()
@click.option("--count", "-n", default=None, type=int, help="Number of cards to review.")
def review(count: int | None) -> None:
    """Run a spaced repetition review session."""
    from garden.srs.reviewer import run_review

    run_review(count or settings.default_review_count)
