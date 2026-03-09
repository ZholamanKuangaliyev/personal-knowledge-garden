"""Tests for persistent chat history."""

from garden.store.chat_store import (
    add_message,
    create_session,
    delete_session,
    get_recent_sessions,
    get_session_messages,
    update_session_title,
)


class TestChatStore:
    def test_create_session(self):
        session_id = create_session(role="analyst")
        assert session_id
        sessions = get_recent_sessions(limit=1)
        assert len(sessions) == 1
        assert sessions[0]["id"] == session_id
        assert sessions[0]["role"] == "analyst"

    def test_add_and_retrieve_messages(self):
        session_id = create_session()
        add_message(session_id, "user", "Hello")
        add_message(session_id, "assistant", "Hi there!")

        messages = get_session_messages(session_id)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Hi there!"

    def test_message_order_preserved(self):
        session_id = create_session()
        for i in range(5):
            add_message(session_id, "user", f"msg-{i}")

        messages = get_session_messages(session_id)
        assert [m["content"] for m in messages] == [f"msg-{i}" for i in range(5)]

    def test_message_limit(self):
        session_id = create_session()
        for i in range(10):
            add_message(session_id, "user", f"msg-{i}")

        messages = get_session_messages(session_id, limit=3)
        assert len(messages) == 3
        # Should be the 3 most recent
        assert messages[-1]["content"] == "msg-9"

    def test_update_session_title(self):
        session_id = create_session()
        update_session_title(session_id, "My Test Session")

        sessions = get_recent_sessions(limit=1)
        assert sessions[0]["title"] == "My Test Session"

    def test_delete_session(self):
        session_id = create_session()
        add_message(session_id, "user", "test")

        delete_session(session_id)

        sessions = get_recent_sessions()
        assert all(s["id"] != session_id for s in sessions)
        messages = get_session_messages(session_id)
        assert messages == []

    def test_recent_sessions_ordered_by_activity(self):
        import time
        s1 = create_session()
        time.sleep(0.05)
        s2 = create_session()
        time.sleep(0.05)
        # Update s1 to make it most recent
        add_message(s1, "user", "newer message")

        sessions = get_recent_sessions(limit=2)
        assert sessions[0]["id"] == s1  # s1 was updated more recently

    def test_multiple_sessions_independent(self):
        s1 = create_session()
        s2 = create_session()
        add_message(s1, "user", "session1")
        add_message(s2, "user", "session2")

        m1 = get_session_messages(s1)
        m2 = get_session_messages(s2)
        assert len(m1) == 1
        assert len(m2) == 1
        assert m1[0]["content"] == "session1"
        assert m2[0]["content"] == "session2"
