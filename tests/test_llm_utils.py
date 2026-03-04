"""Tests for centralized LLM utilities."""

import pytest

from garden.core.llm_utils import parse_json_response, reset_llm


class TestParseJsonResponse:
    def test_plain_json(self):
        result = parse_json_response('{"route": "retrieve"}')
        assert result == {"route": "retrieve"}

    def test_think_block_before_json(self):
        text = '<think>Let me reason about this...</think>{"route": "direct"}'
        result = parse_json_response(text)
        assert result == {"route": "direct"}

    def test_multiline_think_block(self):
        text = '<think>\nStep 1: analyze\nStep 2: decide\n</think>\n{"route": "retrieve"}'
        result = parse_json_response(text)
        assert result == {"route": "retrieve"}

    def test_markdown_fenced_json(self):
        text = '```json\n{"concepts": [{"name": "AI"}]}\n```'
        result = parse_json_response(text)
        assert result == {"concepts": [{"name": "AI"}]}

    def test_markdown_fence_without_lang(self):
        text = '```\n{"key": "value"}\n```'
        result = parse_json_response(text)
        assert result == {"key": "value"}

    def test_think_block_plus_fence(self):
        text = '<think>thinking...</think>\n```json\n{"ideas": []}\n```'
        result = parse_json_response(text)
        assert result == {"ideas": []}

    def test_json_with_surrounding_text(self):
        text = 'Here is the result: {"cards": []} and some trailing text.'
        result = parse_json_response(text)
        assert result == {"cards": []}

    def test_nested_json(self):
        text = '{"outer": {"inner": [1, 2, 3]}}'
        result = parse_json_response(text)
        assert result == {"outer": {"inner": [1, 2, 3]}}

    def test_raises_on_no_json(self):
        with pytest.raises(ValueError, match="Could not parse JSON"):
            parse_json_response("This has no JSON at all")

    def test_raises_on_empty(self):
        with pytest.raises(ValueError):
            parse_json_response("")

    def test_raises_on_only_think_block(self):
        with pytest.raises(ValueError):
            parse_json_response("<think>just thinking, no json</think>")

    def test_real_qwen3_response(self):
        """Simulate a realistic qwen3 response with think block."""
        text = (
            "<think>\nThe user asked about routing. I should analyze the question "
            "and determine if retrieval is needed.\nLet me check: the question is "
            "about stored documents, so retrieve.\n</think>\n"
            '{"route": "retrieve"}'
        )
        result = parse_json_response(text)
        assert result["route"] == "retrieve"


class TestResetLlm:
    def test_reset_clears_singleton(self):
        import garden.core.llm_utils as mod
        mod._llm = "fake"
        reset_llm()
        assert mod._llm is None
