"""Router node — classifies incoming questions for the RAG pipeline.

Strategy Pattern: RouterNode is a concrete AgentNode strategy. Its job is to
decide whether a question needs retrieval or can be answered directly, and
optionally auto-detect the best agent role.

Open/Closed Principle: to change routing behavior (e.g., add a "web_search"
route), subclass RouterNode and override execute() — the existing implementation
stays untouched.
"""

from garden.agent.base import AgentNode
from garden.agent.roles import VALID_ROLES
from garden.agent.state import AgentState
from garden.core.llm_utils import invoke_llm, parse_json_response
from garden.core.logging import get_logger
from garden.prompts.loader import render

_log = get_logger("agent.router")


class RouterNode(AgentNode):
    """Classifies questions as 'retrieve' (needs RAG) or 'direct' (answer from LLM).

    Single Responsibility: this node only decides the routing path and optionally
    detects the agent role. It never retrieves, grades, or generates.

    When auto_role is enabled and the current role is 'general', the router
    combines route classification with role detection in a single LLM call
    to avoid an extra round-trip.
    """

    def execute(self, state: AgentState) -> AgentState:
        question = state.get("rewritten_question") or state["question"]
        current_role = state.get("role", "general")
        auto_detect = state.get("auto_role", False)

        # Combine route + role detection into one LLM call when auto-detect is on
        # and no specific role has been set yet. This saves a round-trip compared
        # to routing first and detecting role separately.
        if auto_detect and current_role == "general":
            prompt = render("router.j2", question=question, detect_role=True, roles=sorted(VALID_ROLES))
        else:
            prompt = render("router.j2", question=question, detect_role=False, roles=[])

        try:
            content = invoke_llm(prompt)
            result = parse_json_response(content)
            route = result.get("route", "retrieve")
        except (ValueError, AttributeError) as exc:
            _log.warning("Router failed to parse LLM response, defaulting to 'retrieve': %s", exc)
            route = "retrieve"
            result = {}

        _log.debug("Routed question to '%s'", route)

        # If the LLM also returned a role suggestion, apply it
        if auto_detect and current_role == "general":
            detected = result.get("role", "general")
            if detected in VALID_ROLES and detected != current_role:
                _log.debug("Auto-switched role from '%s' to '%s'", current_role, detected)
                return {**state, "route": route, "role": detected}

        return {**state, "route": route}


# -- Backward-compatible module-level function --
# Existing code (graph.py, tests) can still import `route_query` as a callable.
# Under the hood it delegates to the default RouterNode instance.
_default_router = RouterNode()


def route_query(state: AgentState) -> AgentState:
    """Module-level wrapper kept for backward compatibility with graph.py imports."""
    return _default_router(state)
