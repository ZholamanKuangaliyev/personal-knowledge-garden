from garden.agent.state import AgentState
from garden.store.vector_store import search


def retrieve_documents(state: AgentState) -> AgentState:
    question = state.get("rewritten_question") or state["question"]
    documents = search(question)
    sources = list({d["source"] for d in documents})
    return {**state, "documents": documents, "sources": sources}
