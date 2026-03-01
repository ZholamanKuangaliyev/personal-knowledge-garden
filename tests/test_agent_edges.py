import pytest

from garden.agent.edges import route_after_grader, route_after_router
from garden.agent.state import AgentState


class TestRouteAfterRouter:
    def test_direct_route(self):
        state: AgentState = {"route": "direct"}
        assert route_after_router(state) == "generate"

    def test_retrieve_route(self):
        state: AgentState = {"route": "retrieve"}
        assert route_after_router(state) == "retrieve"

    def test_missing_route_defaults_to_retrieve(self):
        state: AgentState = {}
        assert route_after_router(state) == "retrieve"

    def test_unknown_route_goes_to_retrieve(self):
        state: AgentState = {"route": "something_else"}
        assert route_after_router(state) == "retrieve"


class TestRouteAfterGrader:
    def test_has_documents_generates(self):
        state: AgentState = {"documents": [{"content": "doc"}], "retry_count": 0}
        assert route_after_grader(state) == "generate"

    def test_no_documents_rewrites(self):
        state: AgentState = {"documents": [], "retry_count": 0}
        assert route_after_grader(state) == "rewrite"

    def test_no_documents_but_max_retries_generates(self, monkeypatch):
        monkeypatch.setattr("garden.core.config.settings.max_retries", 2)
        state: AgentState = {"documents": [], "retry_count": 2}
        assert route_after_grader(state) == "generate"

    def test_missing_documents_key_rewrites(self):
        state: AgentState = {"retry_count": 0}
        assert route_after_grader(state) == "rewrite"

    def test_missing_retry_count_defaults_zero(self):
        state: AgentState = {"documents": []}
        # retry_count defaults to 0, which is < max_retries
        assert route_after_grader(state) == "rewrite"
