from langchain_ollama import OllamaEmbeddings

from garden.core.config import settings
from garden.core.logging import get_logger

_log = get_logger("embedder")


def get_embeddings() -> OllamaEmbeddings:
    _log.debug("Initializing embeddings model=%s url=%s", settings.embedding_model, settings.ollama_base_url)
    return OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )
