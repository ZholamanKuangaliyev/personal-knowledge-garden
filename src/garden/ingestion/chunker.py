from langchain_text_splitters import RecursiveCharacterTextSplitter

from garden.core.config import settings


def chunk_text(text: str, source: str, tags: list[str] | None = None) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_text(text)
    return [
        {
            "id": f"{source}::chunk_{i}",
            "content": chunk,
            "source": source,
            "tags": tags or [],
            "chunk_index": i,
        }
        for i, chunk in enumerate(chunks)
    ]
