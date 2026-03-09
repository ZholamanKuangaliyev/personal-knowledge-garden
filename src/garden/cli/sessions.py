import click

from garden.core.logging import get_logger
from garden.ui.console import console

_log = get_logger("cli.sessions")


@click.command()
@click.argument("action", type=click.Choice(["list", "show", "delete"]), default="list")
@click.option("--id", "session_id", default=None, help="Session ID (prefix match supported).")
@click.option("--limit", "-n", default=10, help="Number of sessions to list.")
def sessions(action: str, session_id: str | None, limit: int) -> None:
    """Browse, inspect, and delete past chat sessions."""
    from datetime import datetime

    from garden.store.chat_store import (
        delete_session,
        get_recent_sessions,
        get_session_messages,
    )

    if action == "list":
        recent = get_recent_sessions(limit=limit)
        if not recent:
            console.print("[yellow]No chat sessions found.[/yellow]")
            return

        console.print(f"\n[bold]Chat Sessions[/bold] (showing {len(recent)}):\n")
        for s in recent:
            title = s["title"] or "[dim]untitled[/dim]"
            role = s.get("role", "general")
            last = s["last_active"]
            try:
                last_dt = datetime.fromisoformat(last)
                last_fmt = last_dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                last_fmt = last
            sid = s["id"][:8]
            console.print(
                f"  [bold cyan]{sid}[/bold cyan]  [dim]{last_fmt}[/dim]  "
                f"[magenta]{role:<12}[/magenta]  {title}"
            )
        console.print("\n[dim]Use 'garden sessions show --id <prefix>' to view messages.[/dim]")

    elif action == "show":
        if not session_id:
            console.print("[red]Please provide --id to show a session.[/red]")
            return

        session = _resolve_session(session_id, get_recent_sessions)
        if not session:
            return

        messages = get_session_messages(session["id"], limit=100)
        title = session["title"] or "untitled"
        console.print(f"\n[bold]Session:[/bold] {title}  [dim]({session['id'][:8]})[/dim]\n")

        for msg in messages:
            if msg["role"] == "user":
                console.print(f"  [bold cyan]You:[/bold cyan] {msg['content']}")
            else:
                # Truncate long assistant messages for readability
                content = msg["content"]
                if len(content) > 500:
                    content = content[:500] + "..."
                console.print(f"  [bold green]Assistant:[/bold green] {content}")
            console.print()

        console.print(f"[dim]{len(messages)} message(s)[/dim]")

    elif action == "delete":
        if not session_id:
            console.print("[red]Please provide --id to delete a session.[/red]")
            return

        session = _resolve_session(session_id, get_recent_sessions)
        if not session:
            return

        title = session["title"] or "untitled"
        if not click.confirm(f"Delete session '{title}' ({session['id'][:8]})?"):
            console.print("[dim]Cancelled.[/dim]")
            return

        delete_session(session["id"])
        console.print(f"[green]+[/green] Deleted session '{title}'")


def _resolve_session(prefix: str, get_recent_fn) -> dict | None:
    """Resolve a session ID prefix to a full session dict."""
    recent = get_recent_fn(limit=100)
    matches = [s for s in recent if s["id"].startswith(prefix)]
    if not matches:
        console.print(f"[red]No session found matching '{prefix}'.[/red]")
        return None
    if len(matches) > 1:
        count = len(matches)
        console.print(f"[yellow]Ambiguous prefix '{prefix}', matches {count} sessions. Be more specific.[/yellow]")
        return None
    return matches[0]
