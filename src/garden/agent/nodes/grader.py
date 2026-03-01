import json

from langchain_ollama import ChatOllama

from garden.agent.state import AgentState
from garden.core.config import settings
from garden.prompts.loader import render


def grade_documents(state: AgentState) -> AgentState:
    question = state.get("rewritten_question") or state["question"]
    documents = state.get("documents", [])

    if not documents:
        return {**state, "documents": [], "relevance_score": 0.0}

    prompt = render("grader.j2", question=question, documents=documents)

    llm = ChatOllama(model=settings.llm_model, base_url=settings.ollama_base_url)
    response = llm.invoke(prompt)

    try:
        result = json.loads(response.content)
        relevant_indices = result.get("relevant_indices", [])
        relevant_docs = [documents[i] for i in relevant_indices if i < len(documents)]
    except (json.JSONDecodeError, AttributeError, IndexError):
        relevant_docs = documents

    score = len(relevant_docs) / len(documents) if documents else 0.0
    sources = list({d["source"] for d in relevant_docs})

    return {**state, "documents": relevant_docs, "relevance_score": score, "sources": sources}
