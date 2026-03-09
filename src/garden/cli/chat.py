from contextlib import contextmanager
from pathlib import Path

import click
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner


@contextmanager
def _nullcontext():
    yield

from garden.agent.roles import DEFAULT_ROLE, ROLES, VALID_ROLES, get_role
from garden.core.config import settings
from garden.core.logging import get_logger
from garden.ui.console import console
from garden.ui.panels import show_answer, show_error
from garden.ui.welcome import collect_garden_stats, show_welcome

_log = get_logger("cli.chat")

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


def _detect_file_path(text: str) -> Path | None:
    """Detect if input text is a file path (e.g., from drag-and-drop)."""
    cleaned = text.strip().strip("'\"")  # Strip quotes added by terminal
    # On Windows, drag-drop may add quotes or use backslashes
    if not cleaned:
        return None
    try:
        p = Path(cleaned)
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            return p
    except (OSError, ValueError):
        pass
    return None


def _ingest_dropped_file(file: Path) -> None:
    """Ingest a file dropped into the chat."""
    from garden.cli.ingest import ingest_single_file
    from garden.store.graph_store import flush_cache

    console.print(f"\n[bold cyan]📄 File detected:[/bold cyan] {file.name}")
    console.print("[dim]Starting ingestion...[/dim]")

    with Live(Spinner("dots", text="Ingesting..."), console=console, transient=True) as live:
        def _update_status(msg: str) -> None:
            live.update(Spinner("dots", text=msg))

        try:
            result = ingest_single_file(file, on_progress=_update_status)
            flush_cache()
        except ValueError as e:
            console.print(f"[yellow]Skipped:[/yellow] {e}")
            return
        except Exception as e:
            _log.error("Drop-ingest failed for '%s': %s", file.name, e, exc_info=True)
            console.print(f"[red]Ingestion failed:[/red] {e}")
            return

    # Success summary
    console.print(f"[bold green]✓ Ingested {file.name}[/bold green]")
    parts = []
    if result["chunks"]:
        parts.append(f"{result['chunks']} chunks")
    if result["concepts"]:
        parts.append(f"{result['concepts']} concepts")
    if result["cards"]:
        parts.append(f"{result['cards']} cards")
    if parts:
        console.print(f"  [dim]{', '.join(parts)}[/dim]")
    console.print()


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
@click.option("--continue-session", "continue_session", is_flag=True, help="Continue the last chat session.")
@click.option("--stream/--no-stream", default=False, help="Stream responses token-by-token.")
def chat(source: str | None, tag: str | None, role: str, continue_session: bool, stream: bool) -> None:
    """Interactive chat with your knowledge garden."""
    from garden.agent.graph import get_agent
    from garden.agent.nodes.generator import clear_stream_callback, set_stream_callback
    from garden.core.llm_utils import stream_llm
    from garden.store.chat_store import (
        add_message,
        create_session,
        get_recent_sessions,
        get_session_messages,
        update_session_title,
    )

    stats = collect_garden_stats()
    show_welcome(model=settings.llm_model, role=role, stats=stats)

    if source:
        console.print(f"[dim]Filtering by source: {source}[/dim]")
    if tag:
        console.print(f"[dim]Filtering by tag: {tag}[/dim]")

    agent = get_agent()
    history: list[dict] = []
    current_role = role
    auto_detect = False

    # Session management
    session_id = None
    if continue_session:
        recent = get_recent_sessions(limit=1)
        if recent:
            session_id = recent[0]["id"]
            current_role = recent[0].get("role", role)
            # Load previous messages into history
            prev_messages = get_session_messages(session_id, limit=settings.chat_max_history)
            history = [{"role": m["role"], "content": m["content"]} for m in prev_messages]
            console.print(f"[dim]Resuming session with {len(history)} messages[/dim]")

    if session_id is None:
        session_id = create_session(role=current_role)

    search_filters: dict | None = None
    if source:
        search_filters = {"source": source}
    elif tag:
        search_filters = {"tags": {"$contains": tag}}

    first_question = True

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

        # Detect file drag-and-drop
        dropped_file = _detect_file_path(stripped)
        if dropped_file:
            _ingest_dropped_file(dropped_file)
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

        # Set up streaming callback if enabled
        if stream:
            def _do_stream(prompt: str) -> str:
                chunks: list[str] = []
                with Live(Markdown(""), console=console, refresh_per_second=8) as live:
                    for token in stream_llm(prompt):
                        chunks.append(token)
                        live.update(Markdown("".join(chunks)))
                return "".join(chunks)
            set_stream_callback(_do_stream)

        with Live(Spinner("dots", text=think_label), console=console, transient=True) if not stream else _nullcontext():
            try:
                result = agent.invoke(invoke_state)
                answer = result.get("generation", "No answer generated.")
                sources = result.get("sources", [])

                if stream:
                    clear_stream_callback()

                # Check if role was auto-switched during processing
                result_role = result.get("role", current_role)
                if result_role != current_role and auto_detect:
                    console.print(f"[dim italic]Auto-switched to {result_role} role[/dim italic]")
                    current_role = result_role

                if not stream:
                    show_answer(answer, sources)
                else:
                    # Answer was already streamed, just show sources
                    if sources:
                        source_text = ", ".join(sources)
                        console.print(f"\n  [dim]Sources: {source_text}[/dim]\n")

                # Persist messages
                add_message(session_id, "user", question)
                add_message(session_id, "assistant", answer)

                # Auto-title session from first question
                if first_question:
                    title = question[:80].strip()
                    update_session_title(session_id, title)
                    first_question = False

                # Maintain rolling history with truncation to limit
                # context window usage. Recent messages stay full; older
                # assistant messages are truncated to settings.chat_truncate_len chars.
                history.append({"role": "user", "content": question})
                history.append({"role": "assistant", "content": answer})
                if len(history) > settings.chat_max_history:
                    history = history[-settings.chat_max_history:]
                # Truncate older assistant messages to save context space
                for j in range(len(history) - settings.chat_recent_full):
                    if history[j]["role"] == "assistant" and len(history[j]["content"]) > settings.chat_truncate_len:
                        truncated = history[j]["content"][:settings.chat_truncate_len] + "..."
                        history[j] = {**history[j], "content": truncated}
            except Exception as e:
                if stream:
                    clear_stream_callback()
                _log.error("Agent error for question %r: %s", question[:80], e, exc_info=True)
                # Provide specific error messages based on exception type
                from garden.core.exceptions import OllamaConnectionError
                if isinstance(e, OllamaConnectionError):
                    show_error("Could not connect to Ollama. Is it running? Check 'ollama serve'.")
                elif isinstance(e, (ConnectionError, TimeoutError, OSError)):
                    show_error(f"Connection error: {e}. Check your Ollama server.")
                else:
                    show_error(f"Error: {e}")
