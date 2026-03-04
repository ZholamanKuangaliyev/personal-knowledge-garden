from pathlib import Path

from pypdf import PdfReader

from garden.core.exceptions import EmptyDocumentError
from garden.core.logging import get_logger

_log = get_logger("pdf_loader")


def load_pdf(path: Path) -> str:
    _log.debug("Loading PDF: %s", path)
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    content = "\n\n".join(pages)
    if not content.strip():
        raise EmptyDocumentError(f"PDF has no extractable text: {path}")
    _log.debug("Loaded %d pages from %s", len(pages), path)
    return content
