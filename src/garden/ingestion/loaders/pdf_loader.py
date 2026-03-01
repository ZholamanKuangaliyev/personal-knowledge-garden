from pathlib import Path

from pypdf import PdfReader

from garden.core.exceptions import EmptyDocumentError


def load_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    content = "\n\n".join(pages)
    if not content.strip():
        raise EmptyDocumentError(f"PDF has no extractable text: {path}")
    return content
