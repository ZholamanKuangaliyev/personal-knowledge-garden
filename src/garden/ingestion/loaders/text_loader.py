from pathlib import Path

from garden.core.exceptions import EmptyDocumentError
from garden.core.logging import get_logger

_log = get_logger("text_loader")


def load_text(path: Path) -> str:
    _log.debug("Loading text file: %s", path)
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        raise EmptyDocumentError(f"File is empty: {path}")
    return content
