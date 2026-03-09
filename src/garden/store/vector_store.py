import os

os.environ["ANONYMIZED_TELEMETRY"] = "False"

from langchain_chroma import Chroma

from garden.core.config import settings
from garden.core.logging import get_logger
from garden.core.models import Chunk, SearchResult
from garden.ingestion.embedder import get_embeddings

_log = get_logger("vector_store")

_store: Chroma | None = None


def get_vector_store() -> Chroma:
    global _store
    if _store is None:
        _log.debug("Initializing ChromaDB at %s", settings.chroma_dir)
        settings.ensure_dirs()
        _store = Chroma(
            collection_name="garden",
            persist_directory=str(settings.chroma_dir),
            embedding_function=get_embeddings(),
        )
        # Store embedding model in collection metadata if not set
        meta = _store._collection.metadata or {}
        if not meta.get("embedding_model"):
            _log.info("Setting embedding model metadata to '%s'", settings.embedding_model)
            _store._collection.modify(metadata={"embedding_model": settings.embedding_model})
    return _store


def check_embedding_model_mismatch() -> str | None:
    """Return a warning message if stored embedding model differs from config, else None."""
    store = get_vector_store()
    meta = store._collection.metadata or {}
    stored = meta.get("embedding_model")
    if stored and stored != settings.embedding_model:
        return (
            f"Embedding model mismatch: stored='{stored}', config='{settings.embedding_model}'. "
            f"Run 'garden migrate-embeddings' to re-embed."
        )
    return None


def add_chunks(chunks: list[Chunk]) -> None:
    _log.debug("Adding %d chunks to vector store", len(chunks))
    store = get_vector_store()
    store.add_texts(
        texts=[c.content for c in chunks],
        metadatas=[
            {"source": c.source, "tags": ",".join(c.tags), "chunk_index": c.chunk_index}
            for c in chunks
        ],
        ids=[c.id for c in chunks],
    )


def search(query: str, k: int | None = None, where: dict | None = None) -> list[SearchResult]:
    _log.debug("Searching query=%r k=%s where=%s", query[:80], k or settings.retrieval_k, where)
    store = get_vector_store()
    kwargs: dict = {"query": query, "k": k or settings.retrieval_k}
    if where:
        kwargs["filter"] = where
    results = store.similarity_search_with_score(**kwargs)
    _log.debug("Search returned %d results", len(results))
    return [
        SearchResult(
            content=doc.page_content,
            source=doc.metadata.get("source", "unknown"),
            score=score,
            chunk_index=doc.metadata.get("chunk_index", 0),
            metadata={k: v for k, v in doc.metadata.items() if k not in ("source", "chunk_index")},
        )
        for doc, score in results
    ]


def get_chunk_count() -> int:
    store = get_vector_store()
    return store._collection.count()


def get_document_sources() -> list[str]:
    store = get_vector_store()
    results = store._collection.get(include=["metadatas"])
    sources = {m.get("source", "unknown") for m in (results["metadatas"] or [])}
    return sorted(sources)


def forget_source(source: str) -> int:
    store = get_vector_store()
    results = store._collection.get(where={"source": source}, include=[])
    ids = results["ids"] or []
    if ids:
        store._collection.delete(ids=ids)
        _log.info("Deleted %d chunks for source '%s'", len(ids), source)
    return len(ids)


def clear_all() -> int:
    _log.info("Clearing all chunks from vector store")
    store = get_vector_store()
    count = store._collection.count()
    if count > 0:
        # Get all IDs and delete them
        results = store._collection.get(include=[])
        ids = results["ids"] or []
        if ids:
            store._collection.delete(ids=ids)
    return count
