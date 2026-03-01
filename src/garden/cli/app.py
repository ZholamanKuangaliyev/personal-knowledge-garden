import click

from garden.cli.chat import chat
from garden.cli.clear import clear
from garden.cli.config import config
from garden.cli.forget import forget
from garden.cli.ideate import ideate
from garden.cli.ingest import ingest
from garden.cli.links import links
from garden.cli.review import review
from garden.cli.status import status
from garden.cli.surprise import surprise


@click.group()
def cli() -> None:
    """Personal Knowledge Garden - your second brain CLI."""


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
