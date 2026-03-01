from pathlib import Path

from garden.core.exceptions import UnsupportedFileType
from garden.ingestion.loaders.pdf_loader import load_pdf
from garden.ingestion.loaders.text_loader import load_text

_LOADERS: dict[str, object] = {
    ".txt": load_text,
    ".md": load_text,
    ".pdf": load_pdf,
}


def load_file(path: Path) -> str:
    suffix = path.suffix.lower()
    loader = _LOADERS.get(suffix)
    if loader is None:
        raise UnsupportedFileType(
            f"Unsupported file type: {suffix}. Supported: {', '.join(_LOADERS)}"
        )
    return loader(path)
