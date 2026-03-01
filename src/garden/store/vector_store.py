from langchain_chroma import Chroma

from garden.core.config import settings
from garden.ingestion.embedder import get_embeddings

_store: Chroma | None = None


def get_vector_store() -> Chroma:
    global _store
    if _store is None:
        settings.ensure_dirs()
        _store = Chroma(
            collection_name="garden",
            persist_directory=str(settings.chroma_dir),
            embedding_function=get_embeddings(),
        )
    return _store


def add_chunks(chunks: list[dict]) -> None:
    store = get_vector_store()
    store.add_texts(
        texts=[c["content"] for c in chunks],
        metadatas=[
            {"source": c["source"], "tags": ",".join(c["tags"]), "chunk_index": c["chunk_index"]}
            for c in chunks
        ],
        ids=[c["id"] for c in chunks],
    )


def search(query: str, k: int | None = None) -> list[dict]:
    store = get_vector_store()
    results = store.similarity_search_with_score(query, k=k or settings.retrieval_k)
    return [
        {
            "content": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
            "score": score,
        }
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
    return len(ids)


def clear_all() -> int:
    store = get_vector_store()
    count = store._collection.count()
    if count > 0:
        # Get all IDs and delete them
        results = store._collection.get(include=[])
        ids = results["ids"] or []
        if ids:
            store._collection.delete(ids=ids)
    return count
