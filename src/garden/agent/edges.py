"""Conditional edge strategies for the RAG agent pipeline.

Strategy Pattern: each conditional edge in the LangGraph pipeline is an
EdgeStrategy subclass. The graph wires these as routing functions; LangGraph
calls them with the current state and expects a node name string back.

Open/Closed Principle: to change routing logic (e.g., add confidence-based
routing, A/B test different strategies), create a new EdgeStrategy subclass
and inject it into build_graph() — existing strategies stay untouched.

Liskov Substitution Principle: any EdgeStrategy subclass can replace another
wherever a routing decision is needed, since they all satisfy the same
decide(state) -> str contract.
"""

from garden.agent.base import EdgeStrategy
from garden.agent.state import AgentState
from garden.core.config import settings


class RouterEdgeStrategy(EdgeStrategy):
    """Routes after the router node: 'generate' for direct answers, 'retrieve' for RAG.

    Decision logic:
        - If the router classified the question as 'direct', skip retrieval
          and go straight to the generator (e.g., greetings, meta-questions).
        - Otherwise, enter the retrieve-grade-generate pipeline.
    """

    def decide(self, state: AgentState) -> str:
        if state.get("route") == "direct":
            return "generate"
        return "retrieve"


class GraderEdgeStrategy(EdgeStrategy):
    """Routes after the grader node: 'generate' if relevant docs found, else 'rewrite'.

    Decision logic:
        - If the grader kept any relevant documents, proceed to generation.
        - If no documents survived grading AND we haven't exceeded max retries,
          rewrite the query for another retrieval attempt.
        - If max retries are exhausted, generate anyway (the generator handles
          missing context gracefully by acknowledging knowledge gaps).

    The max_retries threshold comes from settings so it can be tuned without
    code changes — another application of OCP via configuration.
    """

    def decide(self, state: AgentState) -> str:
        documents = state.get("documents", [])
        retry_count = state.get("retry_count", 0)

        if documents:
            return "generate"
        if retry_count >= settings.max_retries:
            # Signal to generator that we exhausted retries with no docs
            state["knowledge_gap"] = True
            return "generate"
        return "rewrite"


# -- Backward-compatible module-level functions --
# Existing code (graph.py, tests) can still import these as plain callables.
_default_router_edge = RouterEdgeStrategy()
_default_grader_edge = GraderEdgeStrategy()


def route_after_router(state: AgentState) -> str:
    """Module-level wrapper kept for backward compatibility."""
    return _default_router_edge(state)


def route_after_grader(state: AgentState) -> str:
    """Module-level wrapper kept for backward compatibility."""
    return _default_grader_edge(state)
