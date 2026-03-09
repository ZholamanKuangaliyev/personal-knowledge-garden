import heapq

import networkx as nx

from garden.core.llm_utils import invoke_llm, parse_json_response
from garden.core.logging import get_logger, timed
from garden.prompts.loader import render
from garden.store.graph_store import get_graph
from garden.store.vector_store import search

_log = get_logger("insight_engine")


def find_bridge_pairs(max_pairs: int = 5) -> list[dict]:
    """Find distant concept pairs from different sources for insight generation.

    Uses a deterministic strategy: iterates over all cross-source node pairs,
    computes graph distance, and returns the most distant (most surprising)
    pairs ranked by distance. Falls back gracefully for disconnected components.
    """
    graph = get_graph()
    if graph.number_of_nodes() < 2:
        return []

    nodes = list(graph.nodes(data=True))

    # Group nodes by source for efficient cross-source pairing
    by_source: dict[str, list[tuple[str, dict]]] = {}
    for name, data in nodes:
        src = data.get("source", "")
        by_source.setdefault(src, []).append((name, data))

    sources = list(by_source.keys())
    if len(sources) < 2:
        return []

    # Use a min-heap to find top-k most distant cross-source pairs
    # Score = graph distance (higher = more surprising)
    candidates: list[tuple[float, str, str, dict, dict]] = []

    for i, src_a in enumerate(sources):
        for src_b in sources[i + 1 :]:
            for n1, d1 in by_source[src_a]:
                for n2, d2 in by_source[src_b]:
                    try:
                        distance = nx.shortest_path_length(graph, n1, n2)
                    except nx.NetworkXNoPath:
                        distance = float("inf")

                    if distance < 2:
                        continue

                    # Use negative distance for min-heap (we want max distance)
                    score = -distance if distance != float("inf") else -1e6
                    if len(candidates) < max_pairs:
                        heapq.heappush(candidates, (score, n1, n2, d1, d2))
                    elif score < candidates[0][0]:
                        heapq.heapreplace(candidates, (score, n1, n2, d1, d2))

    # Build result pairs with context from vector search
    pairs = []
    for score, n1, n2, d1, d2 in sorted(candidates):
        ctx_a = search(n1, k=1)
        ctx_b = search(n2, k=1)
        distance = -score if score > -1e6 else float("inf")
        pairs.append({
            "concept_a": n1,
            "concept_b": n2,
            "source_a": d1.get("source", ""),
            "source_b": d2.get("source", ""),
            "context_a": ctx_a[0].content if ctx_a else "",
            "context_b": ctx_b[0].content if ctx_b else "",
            "distance": distance,
        })

    _log.debug("Found %d bridge pairs for insight generation", len(pairs))
    return pairs


@timed("insight_generation")
def generate_insights(count: int = 3) -> list[dict]:
    pairs = find_bridge_pairs(max_pairs=count)
    if not pairs:
        return []

    prompt = render("insight.j2", pairs=pairs)

    try:
        content = invoke_llm(prompt)
        result = parse_json_response(content)
        return result.get("insights", [])
    except (ValueError, AttributeError) as exc:
        _log.warning("Failed to generate insights: %s", exc)
        return []
