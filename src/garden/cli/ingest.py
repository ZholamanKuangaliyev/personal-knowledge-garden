import hashlib
from datetime import datetime
from pathlib import Path

import click
from rich.progress import Progress, SpinnerColumn, TextColumn

from garden.core.logging import get_logger
from garden.ui.console import console

_log = get_logger("cli.ingest")


def _compute_hash(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def _check_duplicate(file: Path, content_hash: str) -> str | None:
    """Check if file is a duplicate. Returns a reason string if duplicate, None otherwise."""
    from garden.store.database import get_connection

    conn = get_connection()

    # Check exact content match (same hash, different source name)
    row = conn.execute(
        "SELECT source FROM documents WHERE content_hash = ?", (content_hash,)
    ).fetchone()
    if row:
        return f"identical content already ingested as '{row['source']}'"

    # Check same source name (re-ingest)
    row = conn.execute(
        "SELECT content_hash FROM documents WHERE source = ?", (file.name,)
    ).fetchone()
    if row:
        return f"source '{file.name}' already ingested (use 'garden forget {file.name}' first to re-ingest)"

    return None


def _register_document(source: str, content_hash: str, tags: list[str]) -> None:
    from garden.store.database import get_connection

    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO documents (source, content_hash, ingested_at, tags) VALUES (?, ?, ?, ?)",
        (source, content_hash, datetime.now().isoformat(), ",".join(tags)),
    )
    conn.commit()


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--tag", "-t", multiple=True, help="Tags to apply to the document.")
@click.option("--skip-concepts", is_flag=True, help="Skip concept extraction (faster).")
@click.option("--skip-cards", is_flag=True, help="Skip flashcard generation (faster).")
@click.option("--incremental", is_flag=True, help="Silently skip already-ingested files.")
def ingest(path: Path, tag: tuple[str, ...], skip_concepts: bool, skip_cards: bool, incremental: bool) -> None:
    """Ingest a file or directory into the knowledge garden."""
    from garden.ingestion.chunker import chunk_text
    from garden.ingestion.loader import load_file
    from garden.knowledge.concept_extractor import extract_concepts
    from garden.knowledge.linker import find_links
    from garden.srs.card_generator import generate_cards
    from garden.store.card_store import add_cards
    from garden.store.graph_store import add_concepts, add_links, flush_cache, get_all_concepts
    from garden.store.transaction import garden_transaction
    from garden.store.vector_store import add_chunks

    files = list(path.rglob("*")) if path.is_dir() else [path]
    files = [f for f in files if f.is_file() and f.suffix.lower() in (".txt", ".md", ".pdf")]

    if not files:
        console.print("[yellow]No supported files found.[/yellow]")
        return

    tags = list(tag)
    total_chunks = 0
    total_concepts = 0
    total_cards = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        for file in files:
            try:
                # Duplicate detection
                content_hash = _compute_hash(file)
                dup_reason = _check_duplicate(file, content_hash)
                if dup_reason:
                    if not incremental:
                        console.print(f"  [yellow]~[/yellow] {file.name}: skipped — {dup_reason}")
                    continue

                content = load_file(file)
                chunks = chunk_text(content, source=file.name, tags=tags)

                with garden_transaction():
                    # 1. Embed and store chunks
                    task = progress.add_task(f"Embedding {file.name}...", total=None)
                    add_chunks(chunks)
                    total_chunks += len(chunks)
                    progress.remove_task(task)
                    console.print(f"  [green]+[/green] {file.name} ({len(chunks)} chunks)")

                    # 2. Extract concepts and build graph
                    if not skip_concepts:
                        task = progress.add_task(f"Extracting concepts from {file.name}...", total=None)
                        chunk_texts = [c.content for c in chunks]
                        # Pass existing concept names so the LLM reuses them
                        # instead of creating duplicates under different wording.
                        existing_before = get_all_concepts()
                        existing_names = [c.name for c in existing_before]
                        concepts = extract_concepts(chunk_texts, source=file.name, existing_names=existing_names)
                        if concepts:
                            existing = get_all_concepts()
                            links = find_links(concepts, existing)
                            add_concepts(concepts, batch=True)
                            add_links(links, batch=True)
                            total_concepts += len(concepts)
                            progress.remove_task(task)
                            console.print(f"    [cyan]Concepts:[/cyan] {len(concepts)} extracted, {len(links)} links")
                        else:
                            progress.remove_task(task)

                    # 3. Generate flashcards
                    if not skip_cards:
                        task = progress.add_task(f"Generating flashcards for {file.name}...", total=None)
                        cards = generate_cards(chunks)
                        if cards:
                            add_cards(cards)
                            total_cards += len(cards)
                            progress.remove_task(task)
                            console.print(f"    [cyan]Cards:[/cyan] {len(cards)} generated")
                        else:
                            progress.remove_task(task)

                    # Register document after successful ingestion
                    _register_document(file.name, content_hash, tags)

            except Exception as e:
                _log.error("Failed to ingest '%s': %s", file.name, e, exc_info=True)
                console.print(f"  [red]x[/red] {file.name}: {e}")

    # Flush deferred graph cache invalidation after all files are processed
    flush_cache()
    console.print(f"\n[bold green]Done![/bold green] {len(files)} file(s), {total_chunks} chunks, {total_concepts} concepts, {total_cards} cards")
