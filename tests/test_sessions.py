"""Tests for the sessions CLI command."""

from click.testing import CliRunner

from garden.cli.app import cli
from garden.store.chat_store import add_message, create_session, update_session_title


class TestSessionsList:
    def test_list_empty(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["sessions", "list"])
        assert result.exit_code == 0
        assert "No chat sessions" in result.output

    def test_list_shows_sessions(self):
        s1 = create_session(role="general")
        update_session_title(s1, "My first session")
        add_message(s1, "user", "hello")

        runner = CliRunner()
        result = runner.invoke(cli, ["sessions", "list"])
        assert result.exit_code == 0
        assert "My first session" in result.output
        assert s1[:8] in result.output

    def test_list_shows_multiple(self):
        for i in range(3):
            sid = create_session()
            update_session_title(sid, f"session-{i}")

        runner = CliRunner()
        result = runner.invoke(cli, ["sessions", "list"])
        assert result.exit_code == 0
        assert "session-0" in result.output
        assert "session-2" in result.output

    def test_list_limit(self):
        for i in range(5):
            sid = create_session()
            update_session_title(sid, f"session-{i}")

        runner = CliRunner()
        result = runner.invoke(cli, ["sessions", "list", "-n", "2"])
        assert result.exit_code == 0
        assert "showing 2" in result.output


class TestSessionsShow:
    def test_show_requires_id(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["sessions", "show"])
        assert result.exit_code == 0
        assert "provide --id" in result.output

    def test_show_displays_messages(self):
        sid = create_session()
        update_session_title(sid, "Test Chat")
        add_message(sid, "user", "What is Python?")
        add_message(sid, "assistant", "A programming language.")

        runner = CliRunner()
        result = runner.invoke(cli, ["sessions", "show", "--id", sid[:8]])
        assert result.exit_code == 0
        assert "What is Python?" in result.output
        assert "A programming language." in result.output
        assert "2 message(s)" in result.output

    def test_show_unknown_id(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["sessions", "show", "--id", "nonexistent"])
        assert result.exit_code == 0
        assert "No session found" in result.output


class TestSessionsDelete:
    def test_delete_requires_id(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["sessions", "delete"])
        assert result.exit_code == 0
        assert "provide --id" in result.output

    def test_delete_with_confirm(self):
        sid = create_session()
        update_session_title(sid, "To Delete")

        runner = CliRunner()
        result = runner.invoke(cli, ["sessions", "delete", "--id", sid[:8]], input="y\n")
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_cancelled(self):
        sid = create_session()
        update_session_title(sid, "Keep Me")

        runner = CliRunner()
        result = runner.invoke(cli, ["sessions", "delete", "--id", sid[:8]], input="n\n")
        assert result.exit_code == 0
        assert "Cancelled" in result.output

    def test_default_action_is_list(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["sessions"])
        assert result.exit_code == 0
        # Default action is list, should not crash
        assert "No chat sessions" in result.output or "Chat Sessions" in result.output
