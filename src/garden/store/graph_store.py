from collections import deque

import networkx as nx

from garden.core.models import Concept, ConceptLink
from garden.store.database import get_connection

_graph_cache: nx.Graph | None = None
_cache_dirty: bool = False


def _invalidate_cache() -> None:
    global _graph_cache
    _graph_cache = None


def mark_cache_dirty() -> None:
    """Mark the graph cache as dirty for deferred invalidation.

    Use this during batch operations (e.g., ingestion) to avoid
    rebuilding the graph after every individual write. Call
    flush_cache() when the batch is done.
    """
    global _cache_dirty
    _cache_dirty = True


def flush_cache() -> None:
    """Invalidate the graph cache if it was marked dirty."""
    global _cache_dirty
    if _cache_dirty:
        _invalidate_cache()
        _cache_dirty = False


def get_graph() -> nx.Graph:
    global _graph_cache
    if _graph_cache is not None:
        return _graph_cache

    conn = get_connection()
    graph = nx.Graph()

    for row in conn.execute("SELECT name, source, description FROM concepts").fetchall():
        graph.add_node(row["name"], source=row["source"], description=row["description"])

    for row in conn.execute("SELECT source_concept, target_concept, relation, weight FROM concept_links").fetchall():
        graph.add_edge(
            row["source_concept"],
            row["target_concept"],
            relation=row["relation"],
            weight=row["weight"],
        )

    _graph_cache = graph
    return graph


def add_concepts(concepts: list[Concept], *, batch: bool = False) -> None:
    conn = get_connection()
    conn.executemany(
        "INSERT OR REPLACE INTO concepts (name, source, description, category, importance) VALUES (?, ?, ?, ?, ?)",
        [(c.name, c.source, c.description, c.category, c.importance) for c in concepts],
    )
    conn.commit()
    if batch:
        mark_cache_dirty()
    else:
        _invalidate_cache()


def add_links(links: list[ConceptLink], *, batch: bool = False) -> None:
    conn = get_connection()
    # Single atomic upsert per link — accumulates weight on conflict.
    # Replaces the old SELECT + INSERT/UPDATE two-query pattern, cutting
    # database round-trips in half and eliminating race conditions.
    for link in links:
        conn.execute(
            "INSERT INTO concept_links (source_concept, target_concept, relation, weight) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(source_concept, target_concept) DO UPDATE SET weight = weight + excluded.weight",
            (link.source_concept, link.target_concept, link.relation, link.weight),
        )
    conn.commit()
    if batch:
        mark_cache_dirty()
    else:
        _invalidate_cache()


def get_all_concepts() -> list[Concept]:
    conn = get_connection()
    rows = conn.execute("SELECT name, source, description FROM concepts").fetchall()
    return [Concept(name=r["name"], source=r["source"], description=r["description"]) for r in rows]


def get_concept_neighbors(concept: str, depth: int = 1) -> list[dict]:
    graph = get_graph()
    if concept not in graph:
        return []

    visited = set()
    result = []
    frontier = deque([(concept, 0)])

    while frontier:
        node, d = frontier.popleft()
        if node in visited or d > depth:
            continue
        visited.add(node)

        for neighbor in graph.neighbors(node):
            if neighbor not in visited:
                edge_data = graph[node][neighbor]
                result.append({
                    "source": node,
                    "target": neighbor,
                    "relation": edge_data.get("relation", "related_to"),
                    "weight": edge_data.get("weight", 1.0),
                    "depth": d + 1,
                })
                frontier.append((neighbor, d + 1))

    return result


def forget_source(source: str) -> int:
    conn = get_connection()

    # Get concepts to remove
    rows = conn.execute("SELECT name FROM concepts WHERE source = ?", (source,)).fetchall()
    names = [r["name"] for r in rows]
    if not names:
        return 0

    # Remove links involving these concepts
    placeholders = ",".join("?" * len(names))
    conn.execute(
        f"DELETE FROM concept_links WHERE source_concept IN ({placeholders}) OR target_concept IN ({placeholders})",
        names + names,
    )

    # Remove concepts
    conn.execute(f"DELETE FROM concepts WHERE source = ?", (source,))
    conn.commit()
    _invalidate_cache()
    return len(names)


def clear_all() -> int:
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
    conn.execute("DELETE FROM concept_links")
    conn.execute("DELETE FROM concepts")
    conn.commit()
    _invalidate_cache()
    return count


def get_graph_stats() -> dict:
    conn = get_connection()
    nodes = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
    edges = conn.execute("SELECT COUNT(*) FROM concept_links").fetchone()[0]
    return {"nodes": nodes, "edges": edges}
