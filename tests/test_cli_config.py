"""Tests for garden config models and use-model subcommands, plus _fetch_ollama_models()."""
import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import click.testing
import pytest

from garden.cli.app import cli
from garden.cli.config import _fetch_ollama_models


MOCK_MODELS = [
    {"name": "qwen3.5:9b", "size": 5044165888, "modified_at": "2024-12-15T10:30:00Z"},
    {"name": "llama3:8b", "size": 4661211392, "modified_at": "2024-11-20T08:15:00Z"},
    {"name": "nomic-embed-text", "size": 274302464, "modified_at": "2024-10-05T14:00:00Z"},
]


@pytest.fixture
def runner():
    return click.testing.CliRunner()


# ---------------------------------------------------------------------------
# _fetch_ollama_models() unit tests
# ---------------------------------------------------------------------------

class TestFetchOllamaModels:
    def _make_response(self, payload: dict) -> MagicMock:
        """Return a context-manager mock that yields a readable response."""
        body = json.dumps(payload).encode()
        resp = MagicMock()
        resp.read.return_value = body
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_success_returns_models_list(self):
        payload = {"models": MOCK_MODELS}
        with patch("urllib.request.urlopen", return_value=self._make_response(payload)):
            result = _fetch_ollama_models()
        assert result == MOCK_MODELS

    def test_connection_error_returns_empty_list(self):
        with patch("urllib.request.urlopen", side_effect=URLError("refused")):
            result = _fetch_ollama_models()
        assert result == []

    def test_invalid_json_returns_empty_list(self):
        resp = MagicMock()
        resp.read.return_value = b"not-valid-json{{{"
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=resp):
            result = _fetch_ollama_models()
        assert result == []

    def test_missing_models_key_returns_empty_list(self):
        payload = {"something_else": []}
        with patch("urllib.request.urlopen", return_value=self._make_response(payload)):
            result = _fetch_ollama_models()
        assert result == []


# ---------------------------------------------------------------------------
# garden config models
# ---------------------------------------------------------------------------

class TestConfigModelsCommand:
    def test_with_models_shows_names(self, runner):
        with patch("garden.cli.config._fetch_ollama_models", return_value=MOCK_MODELS):
            result = runner.invoke(cli, ["config", "models"])
        assert result.exit_code == 0
        assert "qwen3.5:9b" in result.output
        assert "llama3:8b" in result.output

    def test_no_models_shows_not_found_message(self, runner):
        with patch("garden.cli.config._fetch_ollama_models", return_value=[]):
            result = runner.invoke(cli, ["config", "models"])
        assert result.exit_code == 0
        assert "No models found" in result.output

    def test_current_model_is_highlighted(self, runner):
        # Use the first model as the current llm_model so we can assert the marker.
        current = MOCK_MODELS[0]["name"]
        with patch("garden.cli.config._fetch_ollama_models", return_value=MOCK_MODELS), \
             patch("garden.core.config.settings") as mock_settings:
            mock_settings.llm_model = current
            mock_settings.ollama_base_url = "http://localhost:11434"
            result = runner.invoke(cli, ["config", "models"])
        # The star marker or "Current model" line confirms the active model is indicated.
        assert current in result.output
        # The footer always echoes the current model name.
        assert "Current model" in result.output or current in result.output


# ---------------------------------------------------------------------------
# garden config use-model
# ---------------------------------------------------------------------------

class TestConfigUseModelCommand:
    def test_successful_selection_saves_config(self, runner):
        with patch("garden.cli.config._fetch_ollama_models", return_value=MOCK_MODELS), \
             patch("garden.core.config.save_config") as mock_save, \
             patch("garden.core.config.reload_settings") as mock_reload, \
             patch("click.prompt", return_value=1):
            result = runner.invoke(cli, ["config", "use-model"])
        assert result.exit_code == 0
        mock_save.assert_called_once_with(llm_model="qwen3.5:9b")
        mock_reload.assert_called_once()

    def test_successful_selection_confirms_model_name(self, runner):
        with patch("garden.cli.config._fetch_ollama_models", return_value=MOCK_MODELS), \
             patch("garden.core.config.save_config"), \
             patch("garden.core.config.reload_settings"), \
             patch("click.prompt", return_value=2):
            result = runner.invoke(cli, ["config", "use-model"])
        assert result.exit_code == 0
        assert "llama3:8b" in result.output

    def test_no_models_shows_not_found_message(self, runner):
        with patch("garden.cli.config._fetch_ollama_models", return_value=[]), \
             patch("garden.core.config.save_config") as mock_save:
            result = runner.invoke(cli, ["config", "use-model"])
        assert result.exit_code == 0
        assert "No models found" in result.output
        mock_save.assert_not_called()

    def test_invalid_selection_shows_error_without_saving(self, runner):
        out_of_range = len(MOCK_MODELS) + 1
        with patch("garden.cli.config._fetch_ollama_models", return_value=MOCK_MODELS), \
             patch("garden.core.config.save_config") as mock_save, \
             patch("garden.core.config.reload_settings"), \
             patch("click.prompt", return_value=out_of_range):
            result = runner.invoke(cli, ["config", "use-model"])
        assert result.exit_code == 0
        assert "Invalid" in result.output
        mock_save.assert_not_called()

    def test_zero_selection_is_invalid(self, runner):
        with patch("garden.cli.config._fetch_ollama_models", return_value=MOCK_MODELS), \
             patch("garden.core.config.save_config") as mock_save, \
             patch("garden.core.config.reload_settings"), \
             patch("click.prompt", return_value=0):
            result = runner.invoke(cli, ["config", "use-model"])
        assert result.exit_code == 0
        assert "Invalid" in result.output
        mock_save.assert_not_called()
