from pathlib import Path

import click

from garden.core.logging import get_logger
from garden.ui.console import console

_log = get_logger("cli.export")


@click.command()
@click.option("--output", "-o", default="export", type=click.Path(path_type=Path), help="Output directory.")
def export(output: Path) -> None:
    """Export knowledge garden as markdown files."""
    from garden.store.card_store import get_due_cards
    from garden.store.database import get_connection
    from garden.store.graph_store import get_all_concepts

    conn = get_connection()
    rows = conn.execute("SELECT source, ingested_at, tags FROM documents").fetchall()

    if not rows:
        console.print("[yellow]No documents to export.[/yellow]")
        return

    output.mkdir(parents=True, exist_ok=True)

    concepts = get_all_concepts()
    concepts_by_source = {}
    for c in concepts:
        concepts_by_source.setdefault(c.source, []).append(c)

    # Get all flashcards (not just due)
    all_cards_rows = conn.execute("SELECT * FROM flashcards").fetchall()
    cards_by_source: dict[str, list] = {}
    for row in all_cards_rows:
        src = row["source"]
        cards_by_source.setdefault(src, []).append(row)

    exported = 0
    for row in rows:
        source = row["source"]
        ingested_at = row["ingested_at"]
        tags = row["tags"].split(",") if row["tags"] else []

        lines = []
        # YAML frontmatter
        lines.append("---")
        lines.append(f"source: {source}")
        if tags:
            lines.append(f"tags: [{', '.join(tags)}]")
        lines.append(f"ingested_at: {ingested_at}")
        lines.append("---")
        lines.append("")

        lines.append(f"# {source}")
        lines.append("")

        # Concepts section
        source_concepts = concepts_by_source.get(source, [])
        if source_concepts:
            lines.append("## Concepts")
            lines.append("")
            for c in source_concepts:
                desc = f" - {c.description}" if c.description else ""
                lines.append(f"- **{c.name}**{desc}")
            lines.append("")

        # Flashcards section
        source_cards = cards_by_source.get(source, [])
        if source_cards:
            lines.append("## Flashcards")
            lines.append("")
            for card in source_cards:
                lines.append(f"**Q:** {card['question']}")
                lines.append(f"**A:** {card['answer']}")
                lines.append("")

        # Write file
        out_name = Path(source).stem + ".md"
        out_path = output / out_name
        out_path.write_text("\n".join(lines), encoding="utf-8")
        _log.debug("Exported '%s' to %s", source, out_path)
        exported += 1

    console.print(f"[bold green]Exported {exported} document(s) to {output}/[/bold green]")
