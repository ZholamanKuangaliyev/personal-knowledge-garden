from langchain_ollama import ChatOllama

from garden.agent.state import AgentState
from garden.core.config import settings
from garden.prompts.loader import render


def generate_answer(state: AgentState) -> AgentState:
    question = state.get("rewritten_question") or state["question"]
    documents = state.get("documents", [])

    prompt = render("generator.j2", question=question, documents=documents)

    llm = ChatOllama(model=settings.llm_model, base_url=settings.ollama_base_url)
    response = llm.invoke(prompt)

    return {**state, "generation": response.content}
