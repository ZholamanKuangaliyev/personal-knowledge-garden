import click

from garden.cli.chat import chat
from garden.cli.clear import clear
from garden.cli.config import config
from garden.cli.export import export
from garden.cli.forget import forget
from garden.cli.ideate import ideate
from garden.cli.ingest import ingest
from garden.cli.links import links
from garden.cli.migrate_embeddings import migrate_embeddings
from garden.cli.review import review
from garden.cli.search import search
from garden.cli.status import status
from garden.cli.surprise import surprise
from garden.core.logging import setup_logging


@click.group(invoke_without_command=True)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging to stderr.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Personal Knowledge Garden - your second brain CLI."""
    setup_logging(verbose=verbose)
    if ctx.invoked_subcommand is None:
        ctx.invoke(chat)


cli.add_command(ingest)
cli.add_command(chat)
cli.add_command(links)
cli.add_command(review)
cli.add_command(surprise)
cli.add_command(ideate)
cli.add_command(status)
cli.add_command(forget)
cli.add_command(clear)
cli.add_command(config)
cli.add_command(search)
cli.add_command(migrate_embeddings)
cli.add_command(export)
