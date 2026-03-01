from pathlib import Path

import pytest


class TestPromptLoader:
    def test_render_exists(self):
        from garden.prompts.loader import render
        # Just verify the function is importable and callable
        assert callable(render)

    def test_prompts_directory_exists(self):
        from garden.prompts.loader import _PROMPTS_DIR
        assert _PROMPTS_DIR.is_dir()

    def test_templates_exist(self):
        from garden.prompts.loader import _PROMPTS_DIR
        templates = list(_PROMPTS_DIR.glob("*.j2"))
        assert len(templates) > 0, "No .j2 templates found in prompts directory"
