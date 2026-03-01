"""Tests for UI components — verify they don't crash on various inputs."""

from unittest.mock import patch

import pytest


class TestPanels:
    @patch("garden.ui.panels.console")
    def test_show_answer(self, mock_console):
        from garden.ui.panels import show_answer

        show_answer("This is the answer")
        assert mock_console.print.called

    @patch("garden.ui.panels.console")
    def test_show_answer_with_sources(self, mock_console):
        from garden.ui.panels import show_answer

        show_answer("Answer text", sources=["doc1.md", "doc2.md"])
        assert mock_console.print.call_count >= 2  # panel + sources

    @patch("garden.ui.panels.console")
    def test_show_error(self, mock_console):
        from garden.ui.panels import show_error

        show_error("Something went wrong")
        assert mock_console.print.called


class TestTables:
    @patch("garden.ui.tables.console")
    def test_show_concepts_table(self, mock_console):
        from garden.ui.tables import show_concepts_table

        concepts = [
            {"name": "ai", "source": "doc.md", "connections": 3},
            {"name": "ml", "source": "doc2.md", "connections": 1},
        ]
        show_concepts_table(concepts)
        assert mock_console.print.called

    @patch("garden.ui.tables.console")
    def test_show_concepts_table_empty(self, mock_console):
        from garden.ui.tables import show_concepts_table

        show_concepts_table([])
        assert mock_console.print.called

    @patch("garden.ui.tables.console")
    def test_show_links_table(self, mock_console):
        from garden.ui.tables import show_links_table

        links = [
            {"source": "ai", "target": "ml", "relation": "co_occurs", "weight": 1.0},
        ]
        show_links_table(links)
        assert mock_console.print.called

    @patch("garden.ui.tables.console")
    def test_show_links_table_empty(self, mock_console):
        from garden.ui.tables import show_links_table

        show_links_table([])
        assert mock_console.print.called
