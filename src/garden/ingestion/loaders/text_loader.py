from pathlib import Path

from garden.core.exceptions import EmptyDocumentError


def load_text(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        raise EmptyDocumentError(f"File is empty: {path}")
    return content
