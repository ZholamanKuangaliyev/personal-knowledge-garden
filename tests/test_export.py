"""Tests for the export CLI command."""

from datetime import datetime

from click.testing import CliRunner

from garden.core.models import Concept
from garden.store.card_store import add_cards
from garden.store.database import get_connection
from garden.store.graph_store import add_concepts


class TestExportCommand:
    def _register_doc(self, source, tags=None):
        conn = get_connection()
        conn.execute(
            "INSERT INTO documents (source, content_hash, ingested_at, tags) VALUES (?, ?, ?, ?)",
            (source, "abc123", datetime.now().isoformat(), ",".join(tags or [])),
        )
        conn.commit()

    def test_export_empty(self, tmp_path):
        from garden.cli.export import export

        runner = CliRunner()
        out_dir = tmp_path / "out"
        result = runner.invoke(export, ["--output", str(out_dir)])
        assert result.exit_code == 0
        assert "No documents to export" in result.output

    def test_export_single_document(self, tmp_path):
        from garden.cli.export import export

        self._register_doc("notes.md", tags=["study"])
        add_concepts([Concept(name="python", source="notes.md", description="A language")])

        out_dir = tmp_path / "out"
        runner = CliRunner()
        result = runner.invoke(export, ["--output", str(out_dir)])
        assert result.exit_code == 0
        assert "Exported 1 document(s)" in result.output

        exported = (out_dir / "notes.md").read_text(encoding="utf-8")
        assert "source: notes.md" in exported
        assert "tags: [study]" in exported
        assert "## Concepts" in exported
        assert "**python**" in exported

    def test_export_with_frontmatter(self, tmp_path):
        from garden.cli.export import export

        self._register_doc("test.md")

        out_dir = tmp_path / "out"
        runner = CliRunner()
        runner.invoke(export, ["--output", str(out_dir)])

        exported = (out_dir / "test.md").read_text(encoding="utf-8")
        assert exported.startswith("---\n")
        assert "ingested_at:" in exported
