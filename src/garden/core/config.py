import json
import logging
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings

_log = logging.getLogger("garden.config")

_CONFIG_FILE = Path("garden.json")


def _find_project_root() -> Path | None:
    """Walk up from cwd looking for garden.json to find the project root."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "garden.json").exists():
            return parent
    return None


def _load_config_file() -> dict:
    if _CONFIG_FILE.exists():
        try:
            return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            _log.warning("Failed to load config file %s: %s", _CONFIG_FILE, exc)
    return {}


class Settings(BaseSettings):
    model_config = {"env_prefix": "PKG_"}

    # LLM
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen3.5:9b"
    embedding_model: str = "nomic-embed-text"

    # Paths
    data_dir: Path = Path("data")
    chroma_dir: Path = Path("data/chroma")
    db_path: Path = Path("data/garden.db")
    graph_dir: Path = Path("data/graph")
    cards_dir: Path = Path("data/cards")

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Retrieval
    retrieval_k: int = 5
    max_retries: int = 2

    # SRS
    default_review_count: int = 10

    # Insight
    default_surprise_count: int = 3

    @model_validator(mode="after")
    def _resolve_paths(self) -> "Settings":
        root = _find_project_root() or Path.cwd()
        for field_name in ("data_dir", "chroma_dir", "db_path", "graph_dir", "cards_dir"):
            path = getattr(self, field_name)
            if not path.is_absolute():
                object.__setattr__(self, field_name, (root / path).resolve())
        return self

    def ensure_dirs(self) -> None:
        for d in [self.data_dir, self.chroma_dir, self.graph_dir, self.cards_dir]:
            d.mkdir(parents=True, exist_ok=True)


def _build_settings() -> Settings:
    file_overrides = _load_config_file()
    return Settings(**file_overrides)


settings = _build_settings()


def save_config(**kwargs: object) -> None:
    existing = _load_config_file()
    existing.update(kwargs)
    _CONFIG_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def reload_settings() -> None:
    global settings
    settings = _build_settings()
