import pytest

from garden.core.models import Concept, ConceptLink
from garden.knowledge.linker import find_links


class TestFindLinks:
    def test_co_occurrence_same_source(self):
        concepts = [
            Concept(name="python", source="doc.md"),
            Concept(name="django", source="doc.md"),
        ]
        links = find_links(concepts, existing_concepts=[])
        co_occurs = [l for l in links if l.relation == "co_occurs"]
        assert len(co_occurs) == 1
        names = {co_occurs[0].source_concept, co_occurs[0].target_concept}
        assert names == {"python", "django"}

    def test_no_co_occurrence_different_source(self):
        concepts = [
            Concept(name="python", source="a.md"),
            Concept(name="django", source="b.md"),
        ]
        links = find_links(concepts, existing_concepts=[])
        co_occurs = [l for l in links if l.relation == "co_occurs"]
        assert len(co_occurs) == 0

    def test_shared_terms_with_existing(self):
        new = [Concept(name="machine learning", source="new.md")]
        existing = [Concept(name="deep learning", source="old.md")]
        links = find_links(new, existing)
        shared = [l for l in links if l.relation == "shared_terms"]
        assert len(shared) == 1
        assert shared[0].source_concept == "machine learning"
        assert shared[0].target_concept == "deep learning"

    def test_no_shared_terms_when_no_overlap(self):
        new = [Concept(name="python", source="a.md")]
        existing = [Concept(name="mathematics", source="b.md")]
        links = find_links(new, existing)
        shared = [l for l in links if l.relation == "shared_terms"]
        assert len(shared) == 0

    def test_no_self_link_for_shared_terms(self):
        new = [Concept(name="python", source="a.md")]
        existing = [Concept(name="python", source="b.md")]
        links = find_links(new, existing)
        shared = [l for l in links if l.relation == "shared_terms"]
        assert len(shared) == 0

    def test_weight_calculation(self):
        new = [Concept(name="natural language processing", source="new.md")]
        existing = [Concept(name="natural language understanding", source="old.md")]
        links = find_links(new, existing)
        shared = [l for l in links if l.relation == "shared_terms"]
        assert len(shared) == 1
        # overlap = {"natural", "language"} = 2, max_len = 3
        assert abs(shared[0].weight - 2 / 3) < 0.01

    def test_empty_inputs(self):
        assert find_links([], []) == []

    def test_three_concepts_same_source(self):
        concepts = [
            Concept(name="a", source="s.md"),
            Concept(name="b", source="s.md"),
            Concept(name="c", source="s.md"),
        ]
        links = find_links(concepts, [])
        co_occurs = [l for l in links if l.relation == "co_occurs"]
        # C(3,2) = 3 pairs: (a,b), (a,c), (b,c)
        assert len(co_occurs) == 3

    def test_combined_co_occurrence_and_shared_terms(self):
        new = [
            Concept(name="deep learning", source="new.md"),
            Concept(name="reinforcement learning", source="new.md"),
        ]
        existing = [Concept(name="machine learning", source="old.md")]
        links = find_links(new, existing)
        co_occurs = [l for l in links if l.relation == "co_occurs"]
        shared = [l for l in links if l.relation == "shared_terms"]
        assert len(co_occurs) >= 1  # deep+reinforcement from same source
        assert len(shared) == 2  # both share "learning" with "machine learning"
