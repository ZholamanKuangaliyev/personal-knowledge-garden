from langchain_ollama import OllamaEmbeddings

from garden.core.config import settings
from garden.core.logging import get_logger

_log = get_logger("embedder")

_embeddings: OllamaEmbeddings | None = None


def get_embeddings() -> OllamaEmbeddings:
    global _embeddings
    if _embeddings is None:
        _log.debug("Initializing embeddings model=%s url=%s", settings.embedding_model, settings.ollama_base_url)
        _embeddings = OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url,
        )
    return _embeddings


def reset_embeddings() -> None:
    """Reset the cached embeddings instance (e.g., after config change)."""
    global _embeddings
    _embeddings = None
