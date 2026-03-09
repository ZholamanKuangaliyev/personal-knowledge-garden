"""LangGraph agent graph definition with dependency injection.

The graph builder accepts optional strategy overrides for every node and edge,
following the Dependency Inversion Principle: high-level graph wiring depends
on abstractions (AgentNode, EdgeStrategy), not on concrete implementations.

Open/Closed Principle: to customize the pipeline (e.g., swap in a
CachedRetriever or a MultiModelGenerator), pass different strategies to
build_graph() — the graph builder itself never changes.

Default behavior: when no overrides are provided, build_graph() uses the
standard concrete strategies so the simple case remains zero-configuration.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from garden.agent.base import AgentNode, EdgeStrategy
from garden.agent.edges import GraderEdgeStrategy, RouterEdgeStrategy
from garden.agent.nodes.generator import GeneratorNode
from garden.agent.nodes.grader import GraderNode
from garden.agent.nodes.retriever import RetrieverNode
from garden.agent.nodes.rewriter import RewriterNode
from garden.agent.nodes.router import RouterNode
from garden.agent.state import AgentState


def build_graph(
    *,
    router: AgentNode | None = None,
    retriever: AgentNode | None = None,
    grader: AgentNode | None = None,
    generator: AgentNode | None = None,
    rewriter: AgentNode | None = None,
    router_edge: EdgeStrategy | None = None,
    grader_edge: EdgeStrategy | None = None,
):
    """Build and compile the RAG agent graph.

    Dependency Injection: every node and edge strategy can be overridden.
    This makes the graph fully testable (inject mocks) and extensible
    (inject custom strategies) without modifying this function (OCP).

    Args:
        router: Strategy for question classification. Default: RouterNode.
        retriever: Strategy for document retrieval. Default: RetrieverNode.
        grader: Strategy for relevance grading. Default: GraderNode.
        generator: Strategy for answer generation. Default: GeneratorNode.
        rewriter: Strategy for query reformulation. Default: RewriterNode.
        router_edge: Routing strategy after the router. Default: RouterEdgeStrategy.
        grader_edge: Routing strategy after the grader. Default: GraderEdgeStrategy.

    Returns:
        A compiled LangGraph agent ready for .invoke() or .stream().
    """
    # Fall back to default concrete strategies when no override is provided.
    # This keeps the simple case zero-config while allowing full customization.
    router = router or RouterNode()
    retriever = retriever or RetrieverNode()
    grader = grader or GraderNode()
    generator = generator or GeneratorNode()
    rewriter = rewriter or RewriterNode()
    router_edge = router_edge or RouterEdgeStrategy()
    grader_edge = grader_edge or GraderEdgeStrategy()

    workflow = StateGraph(AgentState)

    # Register nodes — each is a callable(state) -> state via AgentNode.__call__
    workflow.add_node("router", router)
    workflow.add_node("retrieve", retriever)
    workflow.add_node("grade", grader)
    workflow.add_node("generate", generator)
    workflow.add_node("rewrite", rewriter)

    workflow.set_entry_point("router")

    # Conditional edges use EdgeStrategy.__call__ as the routing function
    workflow.add_conditional_edges(
        "router",
        router_edge,
        {"retrieve": "retrieve", "generate": "generate"},
    )
    workflow.add_edge("retrieve", "grade")
    workflow.add_conditional_edges(
        "grade",
        grader_edge,
        {"generate": "generate", "rewrite": "rewrite"},
    )
    workflow.add_edge("rewrite", "retrieve")
    workflow.add_edge("generate", END)

    return workflow.compile()


# -- Lazy singleton for the default agent --
# Kept for backward compatibility with `get_agent()` callers.
_agent = None


def get_agent():
    """Return the default compiled agent, building it lazily on first call.

    For custom pipelines, call build_graph(...) directly with strategy overrides.
    """
    global _agent
    if _agent is None:
        _agent = build_graph()
    return _agent
