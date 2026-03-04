"""Tests for the agent role system."""

import json
from unittest.mock import MagicMock, patch

import pytest

from garden.agent.roles import (
    DEFAULT_ROLE,
    ROLES,
    VALID_ROLES,
    Role,
    detect_role,
    get_role,
    get_think_token,
)


class TestRoleDefinitions:
    def test_all_five_roles_exist(self):
        expected = {"general", "analyst", "summarizer", "creative", "researcher"}
        assert set(ROLES.keys()) == expected

    def test_valid_roles_matches_keys(self):
        assert VALID_ROLES == set(ROLES.keys())

    def test_default_role_is_general(self):
        assert DEFAULT_ROLE == "general"

    def test_roles_have_required_fields(self):
        for name, role in ROLES.items():
            assert isinstance(role, Role)
            assert role.name == name
            assert isinstance(role.think_mode, bool)
            assert len(role.description) > 0
            assert role.template.endswith(".j2")

    def test_roles_render_system_prompt(self):
        for name, role in ROLES.items():
            prompt = role.system_prompt
            assert len(prompt) > 0, f"{name} system_prompt should not be empty"
            assert isinstance(prompt, str)

    def test_general_is_no_think(self):
        assert ROLES["general"].think_mode is False

    def test_specialist_roles_use_think(self):
        for name in ("analyst", "summarizer", "creative", "researcher"):
            assert ROLES[name].think_mode is True, f"{name} should use think mode"


class TestGetRole:
    def test_get_existing_role(self):
        role = get_role("analyst")
        assert role.name == "analyst"

    def test_get_unknown_role_returns_default(self):
        role = get_role("nonexistent")
        assert role.name == DEFAULT_ROLE


class TestThinkToken:
    def test_think_token_for_think_role(self):
        role = get_role("analyst")
        assert get_think_token(role) == "/think"

    def test_no_think_token_for_general(self):
        role = get_role("general")
        assert get_think_token(role) == "/no_think"


class TestDetectRole:
    @patch("garden.agent.roles.get_llm")
    def test_auto_detect_switches_role(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.invoke.return_value = MagicMock(
            content=json.dumps({"role": "analyst"})
        )

        result = detect_role("Compare and analyze these two theories", "general")
        assert result == "analyst"

    @patch("garden.agent.roles.get_llm")
    def test_detect_keeps_current_when_told(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.invoke.return_value = MagicMock(
            content=json.dumps({"role": "keep"})
        )

        result = detect_role("What is X?", "general")
        assert result == "general"

    def test_detect_skips_when_not_general(self):
        # Should not even call LLM when not in general mode
        result = detect_role("anything", "analyst")
        assert result == "analyst"

    @patch("garden.agent.roles.get_llm")
    def test_detect_handles_bad_json(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.invoke.return_value = MagicMock(content="not json at all")

        result = detect_role("question", "general")
        assert result == "general"

    @patch("garden.agent.roles.get_llm")
    def test_detect_handles_invalid_role(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.invoke.return_value = MagicMock(
            content=json.dumps({"role": "nonexistent_role"})
        )

        result = detect_role("question", "general")
        assert result == "general"


class TestRoleRouterPrompt:
    def test_role_router_template_renders(self):
        from garden.prompts.loader import render

        result = render(
            "role_router.j2",
            question="Analyze the patterns in my notes",
            current_role="general",
            roles={name: role.description for name, role in ROLES.items()},
        )
        assert "Analyze the patterns" in result
        assert "general" in result
        assert "analyst" in result


class TestGeneratorWithRole:
    def test_generator_template_renders_with_role(self):
        from garden.prompts.loader import render

        role = get_role("analyst")
        result = render(
            "generator.j2",
            question="What patterns exist?",
            documents=[{"source": "test.md", "content": "Some content"}],
            history=[],
            role_prompt=role.system_prompt,
            think_token=get_think_token(role),
        )
        assert "/think" in result
        assert "analyt" in result.lower()
        assert "What patterns exist?" in result

    def test_generator_template_no_think_for_general(self):
        from garden.prompts.loader import render

        role = get_role("general")
        result = render(
            "generator.j2",
            question="Hello",
            documents=[],
            history=[],
            role_prompt=role.system_prompt,
            think_token=get_think_token(role),
        )
        assert "/no_think" in result


class TestChatCommands:
    """Test the chat command handling logic."""

    def test_handle_roles_command(self):
        from garden.cli.chat import _handle_command

        role, auto, handled = _handle_command("/roles", "general", True)
        assert handled is True
        assert role == "general"

    def test_handle_switch_command(self):
        from garden.cli.chat import _handle_command

        role, auto, handled = _handle_command("/switch analyst", "general", True)
        assert handled is True
        assert role == "analyst"

    def test_handle_switch_invalid_role(self):
        from garden.cli.chat import _handle_command

        role, auto, handled = _handle_command("/switch fake", "general", True)
        assert handled is True
        assert role == "general"  # unchanged

    def test_handle_switch_no_arg(self):
        from garden.cli.chat import _handle_command

        role, auto, handled = _handle_command("/switch", "general", True)
        assert handled is True
        assert role == "general"

    def test_handle_auto_toggle(self):
        from garden.cli.chat import _handle_command

        role, auto, handled = _handle_command("/auto", "general", True)
        assert handled is True
        assert auto is False

        role, auto, handled = _handle_command("/auto", "general", False)
        assert handled is True
        assert auto is True

    def test_unknown_command_not_handled(self):
        from garden.cli.chat import _handle_command

        role, auto, handled = _handle_command("/unknown", "general", True)
        assert handled is False
