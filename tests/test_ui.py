"""Tests for UI components — verify they don't crash on various inputs."""

from unittest.mock import patch

import pytest
from rich.panel import Panel
from rich.text import Text

from garden.core.models import GardenStats


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


class TestWelcomeGrid:
    def test_empty_garden_all_grey(self):
        from garden.ui.welcome import build_grid

        stats = GardenStats()
        grid = build_grid(stats)
        assert isinstance(grid, Text)
        plain = grid.plain
        # 8 rows of 8 blocks (each "██") separated by spaces, rows separated by newlines
        lines = plain.split("\n")
        assert len(lines) == 8
        # All cells should be the block character
        for line in lines:
            blocks = line.split(" ")
            assert len(blocks) == 8
            for block in blocks:
                assert block == "\u2588\u2588"

    def test_populated_garden_has_colors(self):
        from garden.ui.welcome import build_grid

        stats = GardenStats(
            total_documents=10,
            total_chunks=20,
            total_concepts=5,
            total_links=3,
            total_cards=8,
            cards_due=2,
        )
        grid = build_grid(stats)
        assert isinstance(grid, Text)
        # Should still have 8 rows
        lines = grid.plain.split("\n")
        assert len(lines) == 8

    def test_deterministic_output(self):
        from garden.ui.welcome import build_grid

        stats = GardenStats(total_documents=5, total_chunks=10)
        grid1 = build_grid(stats)
        grid2 = build_grid(stats)
        assert grid1.plain == grid2.plain


class TestWelcomeInfo:
    def test_all_stats_present(self):
        from garden.ui.welcome import build_info

        stats = GardenStats(
            total_documents=3,
            total_chunks=12,
            total_concepts=5,
            total_links=2,
            total_cards=7,
            cards_due=1,
        )
        info = build_info("gpt-4", "researcher", stats)
        plain = info.plain
        assert "docs:" in plain
        assert "chunks:" in plain
        assert "concepts:" in plain
        assert "links:" in plain
        assert "cards:" in plain
        assert "due:" in plain
        assert "3" in plain
        assert "12" in plain
        assert "gpt-4" in plain
        assert "researcher" in plain

    def test_legend_present(self):
        from garden.ui.welcome import build_info

        stats = GardenStats()
        info = build_info("model", "role", stats)
        plain = info.plain
        assert "Legend" in plain
        for label in ("docs", "chunks", "concepts", "links", "cards", "due"):
            assert label in plain


class TestWelcomePanel:
    def test_narrow_layout_returns_panel(self):
        from garden.ui.welcome import build_welcome_panel

        stats = GardenStats()
        panel = build_welcome_panel("model", "role", stats, width=50)
        assert isinstance(panel, Panel)

    def test_medium_layout_returns_panel(self):
        from garden.ui.welcome import build_welcome_panel

        stats = GardenStats()
        panel = build_welcome_panel("model", "role", stats, width=75)
        assert isinstance(panel, Panel)

    def test_wide_layout_returns_panel(self):
        from garden.ui.welcome import build_welcome_panel

        stats = GardenStats()
        panel = build_welcome_panel("model", "role", stats, width=100)
        assert isinstance(panel, Panel)

    @patch("garden.ui.welcome.console")
    def test_show_welcome_prints(self, mock_console):
        from garden.ui.welcome import show_welcome

        mock_console.width = 80
        stats = GardenStats()
        show_welcome("model", "role", stats)
        assert mock_console.print.call_count >= 1
