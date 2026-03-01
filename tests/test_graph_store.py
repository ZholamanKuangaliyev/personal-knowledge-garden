import pytest

from garden.core.models import Concept, ConceptLink
from garden.store.graph_store import (
    add_concepts,
    add_links,
    clear_all,
    forget_source,
    get_all_concepts,
    get_concept_neighbors,
    get_graph,
    get_graph_stats,
)


class TestAddConcepts:
    def test_add_single(self, sample_concepts):
        add_concepts([sample_concepts[0]])
        stats = get_graph_stats()
        assert stats["nodes"] == 1

    def test_add_multiple(self, sample_concepts):
        add_concepts(sample_concepts)
        stats = get_graph_stats()
        assert stats["nodes"] == 3

    def test_upsert_replaces(self, sample_concepts):
        add_concepts([sample_concepts[0]])
        updated = Concept(name="machine learning", source="new.md", description="Updated")
        add_concepts([updated])
        concepts = get_all_concepts()
        ml = [c for c in concepts if c.name == "machine learning"][0]
        assert ml.source == "new.md"
        assert ml.description == "Updated"
        assert get_graph_stats()["nodes"] == 1


class TestAddLinks:
    def test_add_links(self, sample_concepts, sample_links):
        add_concepts(sample_concepts)
        add_links(sample_links)
        stats = get_graph_stats()
        assert stats["edges"] == 2

    def test_accumulate_weight(self, sample_concepts):
        add_concepts(sample_concepts)
        link = ConceptLink(source_concept="machine learning", target_concept="neural networks", weight=1.0)
        add_links([link])
        add_links([link])  # same link again, weight should accumulate
        stats = get_graph_stats()
        assert stats["edges"] == 1

        # Verify weight accumulated
        from garden.store.database import get_connection
        conn = get_connection()
        row = conn.execute(
            "SELECT weight FROM concept_links WHERE source_concept = ? AND target_concept = ?",
            ("machine learning", "neural networks"),
        ).fetchone()
        assert row["weight"] == 2.0


class TestGetAllConcepts:
    def test_returns_all(self, sample_concepts):
        add_concepts(sample_concepts)
        concepts = get_all_concepts()
        names = {c.name for c in concepts}
        assert names == {"machine learning", "neural networks", "data science"}

    def test_empty(self):
        assert get_all_concepts() == []


class TestGetGraph:
    def test_returns_networkx_graph(self, sample_concepts, sample_links):
        add_concepts(sample_concepts)
        add_links(sample_links)
        graph = get_graph()
        assert graph.number_of_nodes() == 3
        assert graph.number_of_edges() == 2

    def test_graph_has_node_attributes(self, sample_concepts):
        add_concepts(sample_concepts)
        graph = get_graph()
        data = graph.nodes["machine learning"]
        assert data["source"] == "ml.md"
        assert data["description"] == "A branch of AI"

    def test_graph_has_edge_attributes(self, sample_concepts, sample_links):
        add_concepts(sample_concepts)
        add_links(sample_links)
        graph = get_graph()
        edge = graph["machine learning"]["neural networks"]
        assert edge["relation"] == "co_occurs"
        assert edge["weight"] == 1.0

    def test_graph_cache_invalidates_on_add(self, sample_concepts):
        graph1 = get_graph()
        assert graph1.number_of_nodes() == 0
        add_concepts(sample_concepts)
        graph2 = get_graph()
        assert graph2.number_of_nodes() == 3


class TestGetConceptNeighbors:
    def test_direct_neighbors(self, sample_concepts, sample_links):
        add_concepts(sample_concepts)
        add_links(sample_links)
        neighbors = get_concept_neighbors("machine learning", depth=1)
        targets = {n["target"] for n in neighbors}
        assert "neural networks" in targets
        assert "data science" in targets

    def test_depth_2(self):
        concepts = [
            Concept(name="a", source="s.md"),
            Concept(name="b", source="s.md"),
            Concept(name="c", source="s.md"),
        ]
        links = [
            ConceptLink(source_concept="a", target_concept="b"),
            ConceptLink(source_concept="b", target_concept="c"),
        ]
        add_concepts(concepts)
        add_links(links)
        neighbors = get_concept_neighbors("a", depth=2)
        targets = {n["target"] for n in neighbors}
        assert "b" in targets
        assert "c" in targets

    def test_unknown_concept(self):
        assert get_concept_neighbors("nonexistent") == []

    def test_result_structure(self, sample_concepts, sample_links):
        add_concepts(sample_concepts)
        add_links(sample_links)
        neighbors = get_concept_neighbors("machine learning", depth=1)
        for n in neighbors:
            assert "source" in n
            assert "target" in n
            assert "relation" in n
            assert "weight" in n
            assert "depth" in n


class TestForgetSource:
    def test_removes_concepts_and_links(self, sample_concepts, sample_links):
        add_concepts(sample_concepts)
        add_links(sample_links)
        removed = forget_source("ml.md")
        assert removed == 2  # machine learning + neural networks
        stats = get_graph_stats()
        assert stats["nodes"] == 1  # only data science remains
        assert stats["edges"] == 0  # all links involved ml.md concepts

    def test_returns_zero_for_unknown(self):
        assert forget_source("nonexistent.md") == 0


class TestClearAll:
    def test_clears_everything(self, sample_concepts, sample_links):
        add_concepts(sample_concepts)
        add_links(sample_links)
        count = clear_all()
        assert count == 3
        assert get_graph_stats() == {"nodes": 0, "edges": 0}

    def test_clear_empty(self):
        assert clear_all() == 0


class TestGetGraphStats:
    def test_with_data(self, sample_concepts, sample_links):
        add_concepts(sample_concepts)
        add_links(sample_links)
        stats = get_graph_stats()
        assert stats["nodes"] == 3
        assert stats["edges"] == 2

    def test_empty(self):
        stats = get_graph_stats()
        assert stats == {"nodes": 0, "edges": 0}
