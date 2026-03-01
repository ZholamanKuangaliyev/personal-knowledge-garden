import networkx as nx

from garden.core.models import Concept, ConceptLink
from garden.store.database import get_connection

_graph_cache: nx.Graph | None = None


def _invalidate_cache() -> None:
    global _graph_cache
    _graph_cache = None


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


def add_concepts(concepts: list[Concept]) -> None:
    conn = get_connection()
    for c in concepts:
        conn.execute(
            "INSERT OR REPLACE INTO concepts (name, source, description) VALUES (?, ?, ?)",
            (c.name, c.source, c.description),
        )
    conn.commit()
    _invalidate_cache()


def add_links(links: list[ConceptLink]) -> None:
    conn = get_connection()
    for link in links:
        existing = conn.execute(
            "SELECT weight FROM concept_links WHERE source_concept = ? AND target_concept = ?",
            (link.source_concept, link.target_concept),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE concept_links SET weight = ? WHERE source_concept = ? AND target_concept = ?",
                (existing["weight"] + link.weight, link.source_concept, link.target_concept),
            )
        else:
            conn.execute(
                "INSERT INTO concept_links (source_concept, target_concept, relation, weight) VALUES (?, ?, ?, ?)",
                (link.source_concept, link.target_concept, link.relation, link.weight),
            )
    conn.commit()
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
    frontier = [(concept, 0)]

    while frontier:
        node, d = frontier.pop(0)
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
