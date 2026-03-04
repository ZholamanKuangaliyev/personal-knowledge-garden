import click

from garden.core.logging import get_logger
from garden.ui.console import console

_log = get_logger("cli.migrate_embeddings")


@click.command("migrate-embeddings")
def migrate_embeddings() -> None:
    """Re-embed all chunks with the current embedding model."""
    from garden.core.config import settings
    from garden.ingestion.embedder import get_embeddings
    from garden.store.vector_store import get_vector_store

    store = get_vector_store()
    collection = store._collection

    # Check if migration is needed
    meta = collection.metadata or {}
    stored_model = meta.get("embedding_model")
    current_model = settings.embedding_model

    _log.info("Checking embedding migration: stored=%s current=%s", stored_model, current_model)
    if stored_model and stored_model == current_model:
        console.print(f"[green]Embeddings already use '{current_model}'. No migration needed.[/green]")
        return

    if stored_model:
        console.print(f"[yellow]Migrating from '{stored_model}' to '{current_model}'...[/yellow]")
    else:
        console.print(f"[yellow]Re-embedding all chunks with '{current_model}'...[/yellow]")

    # Get all documents and metadata
    all_data = collection.get(include=["documents", "metadatas"])
    ids = all_data["ids"] or []
    documents = all_data["documents"] or []
    metadatas = all_data["metadatas"] or []

    if not ids:
        console.print("[yellow]No chunks to migrate.[/yellow]")
        return

    total = len(ids)
    console.print(f"[dim]Found {total} chunks to re-embed.[/dim]")

    # Delete all existing
    collection.delete(ids=ids)

    # Re-add in batches with new embeddings
    embedder = get_embeddings()
    batch_size = 50
    for i in range(0, total, batch_size):
        batch_ids = ids[i : i + batch_size]
        batch_docs = documents[i : i + batch_size]
        batch_meta = metadatas[i : i + batch_size]
        batch_embeddings = embedder.embed_documents(batch_docs)

        collection.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_meta,
            embeddings=batch_embeddings,
        )
        _log.debug("Re-embedded batch %d/%d", min(i + batch_size, total), total)
        console.print(f"  [dim]Processed {min(i + batch_size, total)}/{total} chunks[/dim]")

    # Update collection metadata
    collection.modify(metadata={"embedding_model": current_model})

    console.print(f"[bold green]Migration complete![/bold green] {total} chunks re-embedded with '{current_model}'.")
