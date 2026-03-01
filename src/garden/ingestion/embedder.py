from langchain_ollama import OllamaEmbeddings

from garden.core.config import settings


def get_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )
