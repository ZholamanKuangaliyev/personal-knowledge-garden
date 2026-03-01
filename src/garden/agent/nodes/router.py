import json

from langchain_ollama import ChatOllama

from garden.agent.state import AgentState
from garden.core.config import settings
from garden.prompts.loader import render


def route_query(state: AgentState) -> AgentState:
    question = state.get("rewritten_question") or state["question"]
    prompt = render("router.j2", question=question)

    llm = ChatOllama(model=settings.llm_model, base_url=settings.ollama_base_url)
    response = llm.invoke(prompt)

    try:
        result = json.loads(response.content)
        route = result.get("route", "retrieve")
    except (json.JSONDecodeError, AttributeError):
        route = "retrieve"

    return {**state, "route": route}
