from langgraph.graph import END, StateGraph

from garden.agent.edges import route_after_grader, route_after_router
from garden.agent.nodes.generator import generate_answer
from garden.agent.nodes.grader import grade_documents
from garden.agent.nodes.retriever import retrieve_documents
from garden.agent.nodes.rewriter import rewrite_query
from garden.agent.nodes.router import route_query
from garden.agent.state import AgentState


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("router", route_query)
    workflow.add_node("retrieve", retrieve_documents)
    workflow.add_node("grade", grade_documents)
    workflow.add_node("generate", generate_answer)
    workflow.add_node("rewrite", rewrite_query)

    workflow.set_entry_point("router")

    workflow.add_conditional_edges(
        "router",
        route_after_router,
        {"retrieve": "retrieve", "generate": "generate"},
    )
    workflow.add_edge("retrieve", "grade")
    workflow.add_conditional_edges(
        "grade",
        route_after_grader,
        {"generate": "generate", "rewrite": "rewrite"},
    )
    workflow.add_edge("rewrite", "retrieve")
    workflow.add_edge("generate", END)

    return workflow.compile()


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = build_graph()
    return _agent
