import click
from rich.table import Table

from garden.ui.console import console


@click.group(invoke_without_command=True)
@click.pass_context
def config(ctx: click.Context) -> None:
    """View or change garden configuration."""
    if ctx.invoked_subcommand is None:
        _show_config()


def _show_config() -> None:
    from garden.core.config import settings

    table = Table(title="Garden Configuration", show_header=True, padding=(0, 2))
    table.add_column("Setting", style="bold cyan")
    table.add_column("Value", style="white")

    table.add_row("LLM Model", settings.llm_model)
    table.add_row("Embedding Model", settings.embedding_model)
    table.add_row("Ollama URL", settings.ollama_base_url)
    table.add_row("Chunk Size", str(settings.chunk_size))
    table.add_row("Chunk Overlap", str(settings.chunk_overlap))
    table.add_row("Retrieval K", str(settings.retrieval_k))
    table.add_row("Max Retries", str(settings.max_retries))

    console.print()
    console.print(table)
    console.print("\n[dim]Change with: garden config set <key> <value>[/dim]")
    console.print("[dim]Or edit garden.json directly[/dim]\n")


@config.command(name="set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a configuration value."""
    from garden.core.config import reload_settings, save_config, settings

    valid_keys = {
        "llm_model", "embedding_model", "ollama_base_url",
        "chunk_size", "chunk_overlap", "retrieval_k", "max_retries",
    }

    if key not in valid_keys:
        console.print(f"[red]Unknown key '{key}'.[/red]")
        console.print(f"[dim]Valid keys: {', '.join(sorted(valid_keys))}[/dim]")
        return

    # Cast numeric values
    if key in ("chunk_size", "chunk_overlap", "retrieval_k", "max_retries"):
        try:
            save_config(**{key: int(value)})
        except ValueError:
            console.print(f"[red]'{key}' must be an integer.[/red]")
            return
    else:
        save_config(**{key: value})

    reload_settings()
    console.print(f"[green]Set {key} = {value}[/green]")
