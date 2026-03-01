from garden.agent.state import AgentState
from garden.core.config import settings


def route_after_router(state: AgentState) -> str:
    if state.get("route") == "direct":
        return "generate"
    return "retrieve"


def route_after_grader(state: AgentState) -> str:
    documents = state.get("documents", [])
    retry_count = state.get("retry_count", 0)

    if documents:
        return "generate"
    if retry_count >= settings.max_retries:
        return "generate"
    return "rewrite"
