"""Data-driven welcome screen with 8x8 visualization grid and responsive layout."""

from __future__ import annotations

from datetime import datetime

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from garden.core.models import GardenStats
from garden.ui.console import console

# Grid dimensions
_GRID_ROWS = 8
_GRID_COLS = 8
_TOTAL_CELLS = _GRID_ROWS * _GRID_COLS

# Color categories: (stat_attr, label, style)
_CATEGORIES = [
    ("total_documents", "docs", "green"),
    ("total_chunks", "chunks", "bright_green"),
    ("total_concepts", "concepts", "cyan"),
    ("total_links", "links", "magenta"),
    ("total_cards", "cards", "yellow"),
    ("cards_due", "due", "bright_red"),
]

_EMPTY_STYLE = "grey30"
_BLOCK = "\u2588\u2588"


def collect_garden_stats() -> GardenStats:
    """Query SQLite + vector store and return garden statistics."""
    stats = GardenStats()
    try:
        from garden.store.database import get_connection

        conn = get_connection()
        stats.total_documents = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        stats.total_concepts = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        stats.total_links = conn.execute("SELECT COUNT(*) FROM concept_links").fetchone()[0]
        stats.total_cards = conn.execute("SELECT COUNT(*) FROM flashcards").fetchone()[0]
        stats.cards_due = conn.execute(
            "SELECT COUNT(*) FROM flashcards WHERE next_review <= ?",
            (datetime.now().isoformat(),),
        ).fetchone()[0]
    except Exception:
        pass

    try:
        from garden.store.vector_store import get_chunk_count

        stats.total_chunks = get_chunk_count()
    except Exception:
        pass

    return stats


def build_grid(stats: GardenStats) -> Text:
    """Build an 8x8 colored block grid proportional to garden stats. Pure function."""
    counts = [(getattr(stats, attr), style) for attr, _, style in _CATEGORIES]
    total = sum(c for c, _ in counts)

    # Allocate cells proportionally
    cells: list[str] = []
    if total == 0:
        cells = [_EMPTY_STYLE] * _TOTAL_CELLS
    else:
        remaining = _TOTAL_CELLS
        for i, (count, style) in enumerate(counts):
            if i == len(counts) - 1:
                n = remaining
            else:
                n = round(count / total * _TOTAL_CELLS)
                n = min(n, remaining)
            cells.extend([style] * n)
            remaining -= n

    t = Text()
    for row in range(_GRID_ROWS):
        for col in range(_GRID_COLS):
            idx = row * _GRID_COLS + col
            t.append(_BLOCK, style=cells[idx])
            if col < _GRID_COLS - 1:
                t.append(" ")
        if row < _GRID_ROWS - 1:
            t.append("\n")
    return t


def build_info(model: str, role: str, stats: GardenStats) -> Text:
    """Build the info section with tips, stats, model/role, and legend. Pure function."""
    t = Text()

    # Tips
    t.append("Tips\n", style="bold yellow")
    t.append("  /roles", style="dim")
    t.append("          List available roles\n", style="dim")
    t.append("  /switch <role>", style="dim")
    t.append("  Change active role\n", style="dim")
    t.append("  /auto", style="dim")
    t.append("           Toggle auto-detection\n", style="dim")
    t.append("  quit", style="dim")
    t.append("            Exit the garden\n", style="dim")

    t.append("\n")

    # Garden stats with matching grid colors
    t.append("Garden\n", style="bold yellow")
    stat_items = [
        ("total_documents", "docs"),
        ("total_chunks", "chunks"),
        ("total_concepts", "concepts"),
        ("total_links", "links"),
        ("total_cards", "cards"),
        ("cards_due", "due"),
    ]
    for attr, label in stat_items:
        cat = next(c for c in _CATEGORIES if c[0] == attr)
        style = cat[2]
        value = getattr(stats, attr)
        t.append(f"  {label}: ", style="dim")
        t.append(str(value), style=f"bold {style}")
    t.append("\n")

    t.append("\n")

    # Model and role
    t.append("  model: ", style="dim")
    t.append(model, style="bold")
    t.append("  role: ", style="dim")
    t.append(role, style="bold")
    t.append("\n\n")

    # Legend
    t.append("Legend\n", style="bold yellow")
    for _, label, style in _CATEGORIES:
        t.append(f"  {_BLOCK}", style=style)
        t.append(f" {label}", style="dim")
    t.append("\n")

    return t


def build_welcome_panel(model: str, role: str, stats: GardenStats, width: int = 80) -> Panel:
    """Assemble a responsive welcome panel. Pure function (no I/O)."""
    grid = build_grid(stats)
    info = build_info(model, role, stats)

    if width < 60:
        # Vertical stack
        content = Text()
        content.append_text(grid)
        content.append("\n\n")
        content.append_text(info)
    else:
        # Side-by-side using invisible Table
        pad = (1, 2) if width <= 90 else (1, 3)
        layout = Table(show_header=False, show_edge=False, padding=pad, expand=False)
        layout.add_column(justify="center")
        layout.add_column()
        layout.add_row(grid, info)
        content = layout

    return Panel(
        content,
        title="[bold]Personal Knowledge Garden[/bold]",
        border_style="green",
        padding=(1, 2),
    )


def show_welcome(model: str, role: str, stats: GardenStats) -> None:
    """Entry point: build and print the welcome panel."""
    width = console.width
    panel = build_welcome_panel(model, role, stats, width=width)
    console.print(panel)
    console.print()
