import click
from rich.live import Live
from rich.spinner import Spinner

from garden.agent.roles import DEFAULT_ROLE, ROLES, VALID_ROLES, get_role
from garden.core.config import settings
from garden.core.logging import get_logger
from garden.ui.console import console
from garden.ui.panels import show_answer, show_error
from garden.ui.welcome import collect_garden_stats, show_welcome

_log = get_logger("cli.chat")

_MAX_HISTORY = 20  # 10 exchanges (user + assistant)



def _show_roles() -> None:
    console.print("\n[bold]Available Roles:[/bold]")
    for name, role in ROLES.items():
        marker = " [green]*[/green]" if name == DEFAULT_ROLE else ""
        think = "[dim](think)[/dim]" if role.think_mode else "[dim](fast)[/dim]"
        console.print(f"  [bold cyan]{name:<12}[/bold cyan] {think} {role.description}{marker}")
    console.print()


def _handle_command(command: str, current_role: str, auto_detect: bool) -> tuple[str, bool, bool]:
    """Handle slash commands. Returns (role, auto_detect, handled)."""
    cmd = command.strip().lower()

    if cmd == "/roles":
        _show_roles()
        return current_role, auto_detect, True

    if cmd.startswith("/switch"):
        parts = cmd.split(maxsplit=1)
        if len(parts) < 2:
            console.print("[yellow]Usage: /switch <role>[/yellow]")
            console.print(f"[dim]Available: {', '.join(VALID_ROLES)}[/dim]")
            return current_role, auto_detect, True
        new_role = parts[1].strip()
        if new_role not in VALID_ROLES:
            console.print(f"[red]Unknown role: {new_role}[/red]")
            console.print(f"[dim]Available: {', '.join(VALID_ROLES)}[/dim]")
            return current_role, auto_detect, True
        console.print(f"[green]Switched to [bold]{new_role}[/bold] role[/green]")
        return new_role, auto_detect, True

    if cmd == "/auto":
        auto_detect = not auto_detect
        status = "on" if auto_detect else "off"
        console.print(f"[green]Auto role detection: [bold]{status}[/bold][/green]")
        return current_role, auto_detect, True

    return current_role, auto_detect, False


@click.command()
@click.option("--source", "-s", default=None, help="Filter retrieval by source document.")
@click.option("--tag", "-t", default=None, help="Filter retrieval by tag.")
@click.option("--role", "-r", default=DEFAULT_ROLE, type=click.Choice(sorted(VALID_ROLES)), help="Starting role.")
def chat(source: str | None, tag: str | None, role: str) -> None:
    """Interactive chat with your knowledge garden."""
    from garden.agent.graph import get_agent

    stats = collect_garden_stats()
    show_welcome(model=settings.llm_model, role=role, stats=stats)

    if source:
        console.print(f"[dim]Filtering by source: {source}[/dim]")
    if tag:
        console.print(f"[dim]Filtering by tag: {tag}[/dim]")

    agent = get_agent()
    history: list[dict] = []
    current_role = role
    auto_detect = True

    search_filters: dict | None = None
    if source:
        search_filters = {"source": source}
    elif tag:
        search_filters = {"tags": {"$contains": tag}}

    while True:
        try:
            prompt_prefix = f"[dim]\\[{current_role}][/dim] [bold cyan]You:[/bold cyan] "
            question = console.input(prompt_prefix)
        except (EOFError, KeyboardInterrupt):
            _log.debug("Chat session ended by user")
            console.print("\n[dim]Goodbye![/dim]")
            break

        stripped = question.strip()
        if stripped.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        if not stripped:
            continue

        # Handle slash commands
        if stripped.startswith("/"):
            current_role, auto_detect, handled = _handle_command(stripped, current_role, auto_detect)
            if handled:
                continue

        invoke_state: dict = {
            "question": question,
            "retry_count": 0,
            "history": history,
            "role": current_role,
            "auto_role": auto_detect,
        }
        if search_filters:
            invoke_state["search_filters"] = search_filters

        role_obj = get_role(current_role)
        think_label = "Thinking deeply..." if role_obj.think_mode else "Thinking..."

        with Live(Spinner("dots", text=think_label), console=console, transient=True):
            try:
                result = agent.invoke(invoke_state)
                answer = result.get("generation", "No answer generated.")
                sources = result.get("sources", [])

                # Check if role was auto-switched during processing
                result_role = result.get("role", current_role)
                if result_role != current_role and auto_detect:
                    console.print(f"[dim italic]Auto-switched to {result_role} role[/dim italic]")
                    current_role = result_role

                show_answer(answer, sources)

                # Maintain rolling history
                history.append({"role": "user", "content": question})
                history.append({"role": "assistant", "content": answer})
                if len(history) > _MAX_HISTORY:
                    history = history[-_MAX_HISTORY:]
            except Exception as e:
                _log.error("Agent error for question %r: %s", question[:80], e, exc_info=True)
                show_error(f"Error: {e}")
