from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import click.testing
import pytest

from garden.cli.app import cli
from garden.core.models import Flashcard


@pytest.fixture
def runner():
    return click.testing.CliRunner()


class TestStatusCommand:
    def test_status_empty(self, runner):
        with patch("garden.store.vector_store.get_document_sources", return_value=[]), \
             patch("garden.store.vector_store.get_chunk_count", return_value=0):
            result = runner.invoke(cli, ["status"])
            assert result.exit_code == 0
            assert "Garden Status" in result.output

    def test_status_with_data(self, runner):
        with patch("garden.store.vector_store.get_document_sources", return_value=["doc.md"]), \
             patch("garden.store.vector_store.get_chunk_count", return_value=5):
            result = runner.invoke(cli, ["status"])
            assert result.exit_code == 0
            assert "doc.md" in result.output


class TestClearCommand:
    def test_clear_with_confirmation(self, runner):
        with patch("garden.store.card_store.clear_all", return_value=3), \
             patch("garden.store.graph_store.clear_all", return_value=5), \
             patch("garden.store.vector_store.clear_all", return_value=10):
            result = runner.invoke(cli, ["clear", "--yes"])
            assert result.exit_code == 0
            assert "Garden cleared" in result.output

    def test_clear_aborted_without_confirmation(self, runner):
        result = runner.invoke(cli, ["clear"], input="n\n")
        assert result.exit_code != 0 or "Aborted" in result.output


class TestForgetCommand:
    def test_forget_existing(self, runner):
        with patch("garden.store.vector_store.get_document_sources", return_value=["doc.md"]), \
             patch("garden.store.vector_store.forget_source", return_value=5), \
             patch("garden.store.graph_store.forget_source", return_value=2), \
             patch("garden.store.card_store.forget_source", return_value=3):
            result = runner.invoke(cli, ["forget", "doc.md"])
            assert result.exit_code == 0
            assert "Forgot" in result.output

    def test_forget_unknown_source(self, runner):
        with patch("garden.store.vector_store.get_document_sources", return_value=[]):
            result = runner.invoke(cli, ["forget", "missing.md"])
            assert result.exit_code == 0
            assert "not found" in result.output


class TestReviewCommand:
    def test_review_no_cards(self, runner):
        with patch("garden.srs.reviewer.get_due_cards", return_value=[]):
            result = runner.invoke(cli, ["review"])
            assert result.exit_code == 0
            assert "No cards due" in result.output


class TestIngestCommand:
    def test_ingest_no_supported_files(self, runner, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("a,b,c", encoding="utf-8")
        result = runner.invoke(cli, ["ingest", str(tmp_path)])
        assert result.exit_code == 0
        assert "No supported files" in result.output

    def test_ingest_duplicate_detected(self, runner, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("Hello world", encoding="utf-8")

        with patch("garden.ingestion.loader.load_file", return_value="Hello world"), \
             patch("garden.ingestion.chunker.chunk_text", return_value=[]), \
             patch("garden.store.vector_store.add_chunks"), \
             patch("garden.knowledge.concept_extractor.extract_concepts", return_value=[]), \
             patch("garden.srs.card_generator.generate_cards", return_value=[]):

            # First ingest — registers the document
            result1 = runner.invoke(cli, ["ingest", str(f)])
            assert result1.exit_code == 0

            # Second ingest — should detect duplicate by hash
            result2 = runner.invoke(cli, ["ingest", str(f)])
            assert "skipped" in result2.output


class TestConfigCommand:
    def test_config_show(self, runner):
        result = runner.invoke(cli, ["config"])
        assert result.exit_code == 0
        assert "llm_model" in result.output or "Configuration" in result.output
