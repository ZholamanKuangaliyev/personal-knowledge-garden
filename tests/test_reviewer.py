"""Tests for the SRS reviewer interactive session."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, call, patch

import pytest

from garden.core.models import Flashcard


def _make_due_card(card_id="c1", question="What is X?", answer="X is Y"):
    return Flashcard(
        id=card_id, question=question, answer=answer,
        source="s.md", next_review=datetime.now() - timedelta(hours=1),
    )


class TestRunReview:
    @patch("garden.srs.reviewer.update_card")
    @patch("garden.srs.reviewer.get_due_cards")
    @patch("garden.srs.reviewer.console")
    def test_no_cards_due(self, mock_console, mock_get_due, mock_update):
        from garden.srs.reviewer import run_review

        mock_get_due.return_value = []
        run_review(10)
        mock_console.print.assert_called()
        # Should say "No cards due"
        assert any("No cards due" in str(c) for c in mock_console.print.call_args_list)

    @patch("garden.srs.reviewer.update_card")
    @patch("garden.srs.reviewer.get_due_cards")
    @patch("garden.srs.reviewer.console")
    def test_review_single_card(self, mock_console, mock_get_due, mock_update):
        from garden.srs.reviewer import run_review

        card = _make_due_card()
        mock_get_due.return_value = [card]
        # Simulate: Enter to reveal, then "4" for rating
        mock_console.input.side_effect = ["", "4"]

        run_review(10)
        mock_update.assert_called_once()
        updated_card = mock_update.call_args[0][0]
        assert updated_card.repetitions == 1  # quality=4 increments

    @patch("garden.srs.reviewer.update_card")
    @patch("garden.srs.reviewer.get_due_cards")
    @patch("garden.srs.reviewer.console")
    def test_review_interrupted_on_reveal(self, mock_console, mock_get_due, mock_update):
        from garden.srs.reviewer import run_review

        mock_get_due.return_value = [_make_due_card()]
        mock_console.input.side_effect = EOFError()

        run_review(10)
        mock_update.assert_not_called()

    @patch("garden.srs.reviewer.update_card")
    @patch("garden.srs.reviewer.get_due_cards")
    @patch("garden.srs.reviewer.console")
    def test_review_interrupted_on_rating(self, mock_console, mock_get_due, mock_update):
        from garden.srs.reviewer import run_review

        mock_get_due.return_value = [_make_due_card()]
        mock_console.input.side_effect = ["", KeyboardInterrupt()]

        run_review(10)
        mock_update.assert_not_called()


class TestRenderCardText:
    @patch("garden.srs.reviewer.console")
    def test_plain_text_rendered_as_markdown(self, mock_console):
        from garden.srs.reviewer import _render_card_text

        _render_card_text("Simple answer text")
        mock_console.print.assert_called_once()

    @patch("garden.srs.reviewer.console")
    def test_code_fence_rendered_with_syntax(self, mock_console):
        from garden.srs.reviewer import _render_card_text

        text = "Here is code:\n```python\nprint('hello')\n```"
        _render_card_text(text)
        # Should call print multiple times (text before + syntax block)
        assert mock_console.print.call_count >= 2
