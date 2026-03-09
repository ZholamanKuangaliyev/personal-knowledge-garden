"""Retriever node — fetches relevant documents from the vector store.

Strategy Pattern: RetrieverNode is a concrete AgentNode strategy. It owns the
single responsibility of querying the vector store and shaping results into
the state format expected by downstream nodes.

Open/Closed Principle: to change retrieval behavior (e.g., hybrid search,
re-ranking, multi-index fan-out), subclass RetrieverNode and override execute()
— no existing code is modified.
"""

from garden.agent.base import AgentNode
from garden.agent.state import AgentState
from garden.core.logging import get_logger
from garden.store.vector_store import search

_log = get_logger("agent.retriever")


class RetrieverNode(AgentNode):
    """Queries the ChromaDB vector store for documents matching the question.

    Single Responsibility: this node only retrieves documents. It does not
    judge relevance (that's the grader's job) or generate answers.

    The node respects optional search_filters in state (e.g., filter by source
    document or tag) so retrieval scope can be narrowed by the caller.
    """

    def execute(self, state: AgentState) -> AgentState:
        question = state.get("rewritten_question") or state["question"]
        search_filters = state.get("search_filters")
        _log.debug("Retrieving documents for query=%r filters=%s", question[:80], search_filters)

        results = search(question, where=search_filters)

        _log.debug("Retrieved %d documents", len(results))
        documents = [{"content": r.content, "source": r.source, "score": r.score} for r in results]
        sources = list({r.source for r in results})
        return {**state, "documents": documents, "sources": sources}


# -- Backward-compatible module-level function --
_default_retriever = RetrieverNode()


def retrieve_documents(state: AgentState) -> AgentState:
    """Module-level wrapper kept for backward compatibility with graph.py imports."""
    return _default_retriever(state)
