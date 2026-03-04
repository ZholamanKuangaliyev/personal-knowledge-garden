from garden.agent.roles import detect_role
from garden.agent.state import AgentState
from garden.core.llm_utils import get_llm, parse_json_response
from garden.core.logging import get_logger
from garden.prompts.loader import render

_log = get_logger("agent.router")


def route_query(state: AgentState) -> AgentState:
    question = state.get("rewritten_question") or state["question"]
    prompt = render("router.j2", question=question)

    llm = get_llm()
    response = llm.invoke(prompt)

    try:
        result = parse_json_response(response.content)
        route = result.get("route", "retrieve")
    except (ValueError, AttributeError) as exc:
        _log.warning("Router failed to parse LLM response, defaulting to 'retrieve': %s", exc)
        route = "retrieve"

    _log.debug("Routed question to '%s'", route)

    # Auto-detect role if currently in general mode
    current_role = state.get("role", "general")
    auto_detect = state.get("auto_role", True)
    if auto_detect and current_role == "general":
        detected_role = detect_role(question, current_role)
        if detected_role != current_role:
            _log.debug("Auto-switched role from '%s' to '%s'", current_role, detected_role)
            return {**state, "route": route, "role": detected_role}

    return {**state, "route": route}
