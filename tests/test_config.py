import json
from pathlib import Path

from garden.core.config import Settings, _find_project_root, _load_config_file, reload_settings, save_config, settings


class TestSettings:
    def test_default_values(self):
        s = Settings()
        assert s.llm_model == "qwen3.5:9b"
        assert s.embedding_model == "nomic-embed-text"
        assert s.chunk_size == 1000
        assert s.chunk_overlap == 200
        assert s.retrieval_k == 3
        assert s.max_retries == 2
        assert s.default_review_count == 10
        assert s.default_surprise_count == 3

    def test_default_paths_are_absolute(self):
        s = Settings()
        assert s.data_dir.is_absolute()
        assert s.chroma_dir.is_absolute()
        assert s.db_path.is_absolute()

    def test_ensure_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setattr("garden.core.config.settings.data_dir", tmp_path / "d")
        monkeypatch.setattr("garden.core.config.settings.chroma_dir", tmp_path / "d" / "c")
        monkeypatch.setattr("garden.core.config.settings.graph_dir", tmp_path / "d" / "g")
        monkeypatch.setattr("garden.core.config.settings.cards_dir", tmp_path / "d" / "cards")
        settings.ensure_dirs()
        assert (tmp_path / "d").is_dir()
        assert (tmp_path / "d" / "c").is_dir()

    def test_custom_settings(self):
        s = Settings(llm_model="llama3:8b", chunk_size=500)
        assert s.llm_model == "llama3:8b"
        assert s.chunk_size == 500


class TestConfigFile:
    def test_load_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr("garden.core.config._CONFIG_FILE", tmp_path / "missing.json")
        assert _load_config_file() == {}

    def test_save_and_load(self, monkeypatch, tmp_path):
        cfg_file = tmp_path / "garden.json"
        monkeypatch.setattr("garden.core.config._CONFIG_FILE", cfg_file)
        save_config(llm_model="test-model")
        data = json.loads(cfg_file.read_text(encoding="utf-8"))
        assert data["llm_model"] == "test-model"

    def test_save_merges(self, monkeypatch, tmp_path):
        cfg_file = tmp_path / "garden.json"
        monkeypatch.setattr("garden.core.config._CONFIG_FILE", cfg_file)
        save_config(llm_model="m1")
        save_config(chunk_size=500)
        data = json.loads(cfg_file.read_text(encoding="utf-8"))
        assert data["llm_model"] == "m1"
        assert data["chunk_size"] == 500


class TestFindProjectRoot:
    def test_finds_root_with_garden_json(self, tmp_path, monkeypatch):
        (tmp_path / "garden.json").write_text("{}")
        monkeypatch.chdir(tmp_path)
        root = _find_project_root()
        assert root == tmp_path

    def test_finds_root_from_subdir(self, tmp_path, monkeypatch):
        (tmp_path / "garden.json").write_text("{}")
        subdir = tmp_path / "src" / "deep"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)
        root = _find_project_root()
        assert root == tmp_path

    def test_returns_none_when_no_garden_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        root = _find_project_root()
        assert root is None


class TestPathResolution:
    def test_paths_resolved_to_absolute(self):
        s = Settings()
        assert s.data_dir.is_absolute()
        assert s.chroma_dir.is_absolute()
        assert s.db_path.is_absolute()
        assert s.graph_dir.is_absolute()
        assert s.cards_dir.is_absolute()

    def test_absolute_paths_unchanged(self, tmp_path):
        s = Settings(data_dir=tmp_path / "mydata")
        assert s.data_dir == (tmp_path / "mydata").resolve()
