import urllib.request
import json

import click
from rich.table import Table

from garden.core.logging import get_logger
from garden.ui.console import console

_log = get_logger("garden.cli.config")


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


def _fetch_ollama_models() -> list[dict]:
    from garden.core.config import settings

    url = f"{settings.ollama_base_url}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("models", [])
    except Exception as exc:
        _log.warning("Failed to fetch Ollama models: %s", exc)
        return []


@config.command(name="models")
def config_models() -> None:
    """List installed Ollama models."""
    from garden.core.config import settings

    models = _fetch_ollama_models()
    if not models:
        console.print("[yellow]No models found. Is Ollama running?[/yellow]")
        return

    table = Table(show_header=True, padding=(0, 2))
    table.add_column("#", style="dim")
    table.add_column("Model", style="white")
    table.add_column("Size", style="white")
    table.add_column("Modified", style="white")

    for i, model in enumerate(models, start=1):
        name = model.get("name", "")
        size_bytes = model.get("size", 0)
        modified_at = model.get("modified_at", "")
        date_str = modified_at.split("T")[0] if "T" in modified_at else modified_at

        if size_bytes >= 1024 ** 3:
            size_str = f"{size_bytes / 1024 ** 3:.1f} GB"
        else:
            size_str = f"{size_bytes / 1024 ** 2:.1f} MB"

        if name == settings.llm_model:
            table.add_row(str(i), f"[bold green]{name} ⭐[/bold green]", size_str, date_str)
        else:
            table.add_row(str(i), name, size_str, date_str)

    console.print(table)
    console.print(f"[dim]Current model: {settings.llm_model}[/dim]")
    console.print("[dim]Switch with: garden config use-model[/dim]")


@config.command(name="use-model")
def config_use_model() -> None:
    """Interactively select an Ollama model."""
    from garden.core.config import reload_settings, save_config

    models = _fetch_ollama_models()
    if not models:
        console.print("[yellow]No models found. Is Ollama running?[/yellow]")
        return

    for i, model in enumerate(models, start=1):
        console.print(f"  {i}. {model.get('name', '')}")

    choice = click.prompt("Select model number", type=int)
    if choice < 1 or choice > len(models):
        console.print(f"[red]Invalid selection. Choose 1–{len(models)}.[/red]")
        return

    name = models[choice - 1].get("name", "")
    save_config(llm_model=name)
    reload_settings()
    console.print(f"[green]Switched to model: {name}[/green]")
