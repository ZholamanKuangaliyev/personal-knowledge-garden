from pathlib import Path
from typing import Callable, Protocol

from garden.core.exceptions import UnsupportedFileType
from garden.core.logging import get_logger

_log = get_logger("loader")

LoaderFunc = Callable[[Path], str]


class _LoaderRegistry:
    """Extensible registry for file type loaders."""

    def __init__(self) -> None:
        self._loaders: dict[str, LoaderFunc] = {}

    def register(self, *extensions: str) -> Callable[[LoaderFunc], LoaderFunc]:
        """Decorator to register a loader for one or more file extensions."""

        def decorator(func: LoaderFunc) -> LoaderFunc:
            for ext in extensions:
                key = ext if ext.startswith(".") else f".{ext}"
                self._loaders[key.lower()] = func
                _log.debug("Registered loader for '%s': %s", key, func.__name__)
            return func

        return decorator

    def get(self, extension: str) -> LoaderFunc | None:
        return self._loaders.get(extension.lower())

    @property
    def supported_extensions(self) -> set[str]:
        return set(self._loaders.keys())


registry = _LoaderRegistry()


# Register built-in loaders
@registry.register(".txt", ".md")
def _load_text(path: Path) -> str:
    from garden.ingestion.loaders.text_loader import load_text
    return load_text(path)


@registry.register(".pdf")
def _load_pdf(path: Path) -> str:
    from garden.ingestion.loaders.pdf_loader import load_pdf
    return load_pdf(path)


def load_file(path: Path) -> str:
    suffix = path.suffix.lower()
    loader = registry.get(suffix)
    if loader is None:
        _log.warning("Unsupported file type: %s (file: %s)", suffix, path)
        raise UnsupportedFileType(
            f"Unsupported file type: {suffix}. Supported: {', '.join(sorted(registry.supported_extensions))}"
        )
    _log.debug("Loading file %s with %s loader", path, suffix)
    return loader(path)
