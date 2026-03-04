from garden.agent.state import AgentState
from garden.core.logging import get_logger
from garden.store.vector_store import search

_log = get_logger("agent.retriever")


def retrieve_documents(state: AgentState) -> AgentState:
    question = state.get("rewritten_question") or state["question"]
    search_filters = state.get("search_filters")
    _log.debug("Retrieving documents for query=%r filters=%s", question[:80], search_filters)
    results = search(question, where=search_filters)
    _log.debug("Retrieved %d documents", len(results))
    documents = [{"content": r.content, "source": r.source, "score": r.score} for r in results]
    sources = list({r.source for r in results})
    return {**state, "documents": documents, "sources": sources}
