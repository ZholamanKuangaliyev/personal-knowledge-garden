import random

import networkx as nx

from garden.core.llm_utils import get_llm, parse_json_response
from garden.core.logging import get_logger
from garden.prompts.loader import render
from garden.store.graph_store import get_graph
from garden.store.vector_store import search

_log = get_logger("insight_engine")


def find_bridge_pairs(max_pairs: int = 5) -> list[dict]:
    graph = get_graph()
    if graph.number_of_nodes() < 2:
        return []

    pairs = []
    nodes = list(graph.nodes(data=True))

    # Find loosely connected or distant node pairs from different sources
    for _ in range(max_pairs * 3):
        if len(nodes) < 2:
            break
        n1, d1 = random.choice(nodes)
        n2, d2 = random.choice(nodes)
        if n1 == n2:
            continue
        if d1.get("source") == d2.get("source"):
            continue

        try:
            distance = nx.shortest_path_length(graph, n1, n2)
        except nx.NetworkXNoPath:
            _log.debug("No path between '%s' and '%s'", n1, n2)
            distance = float("inf")

        if distance >= 2:
            # Get context via vector search
            ctx_a = search(n1, k=1)
            ctx_b = search(n2, k=1)
            pairs.append({
                "concept_a": n1,
                "concept_b": n2,
                "source_a": d1.get("source", ""),
                "source_b": d2.get("source", ""),
                "context_a": ctx_a[0].content if ctx_a else "",
                "context_b": ctx_b[0].content if ctx_b else "",
                "distance": distance,
            })

        if len(pairs) >= max_pairs:
            break

    return pairs


def generate_insights(count: int = 3) -> list[dict]:
    pairs = find_bridge_pairs(max_pairs=count)
    if not pairs:
        return []

    prompt = render("insight.j2", pairs=pairs)
    llm = get_llm()
    response = llm.invoke(prompt)

    try:
        result = parse_json_response(response.content)
        return result.get("insights", [])
    except (ValueError, AttributeError) as exc:
        _log.warning("Failed to generate insights: %s", exc)
        return []
