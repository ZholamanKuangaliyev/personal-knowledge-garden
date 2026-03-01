import json

from langchain_ollama import ChatOllama

from garden.agent.state import AgentState
from garden.core.config import settings
from garden.prompts.loader import render


def rewrite_query(state: AgentState) -> AgentState:
    question = state.get("rewritten_question") or state["question"]
    retry_count = state.get("retry_count", 0)

    prompt = render("rewriter.j2", question=question)

    llm = ChatOllama(model=settings.llm_model, base_url=settings.ollama_base_url)
    response = llm.invoke(prompt)

    try:
        result = json.loads(response.content)
        rewritten = result.get("rewritten_question", question)
    except (json.JSONDecodeError, AttributeError):
        rewritten = question

    return {**state, "rewritten_question": rewritten, "retry_count": retry_count + 1}
