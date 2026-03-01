from garden.core.models import Concept, ConceptLink


def find_links(concepts: list[Concept], existing_concepts: list[Concept]) -> list[ConceptLink]:
    links: list[ConceptLink] = []
    all_concepts = existing_concepts + concepts

    # Link concepts from the same source
    by_source: dict[str, list[Concept]] = {}
    for c in all_concepts:
        by_source.setdefault(c.source, []).append(c)

    for source_concepts in by_source.values():
        for i, c1 in enumerate(source_concepts):
            for c2 in source_concepts[i + 1 :]:
                links.append(
                    ConceptLink(
                        source_concept=c1.name,
                        target_concept=c2.name,
                        relation="co_occurs",
                        weight=1.0,
                    )
                )

    # Link new concepts to existing ones that share words
    for new_c in concepts:
        new_words = set(new_c.name.split())
        for existing_c in existing_concepts:
            if new_c.name == existing_c.name:
                continue
            existing_words = set(existing_c.name.split())
            overlap = new_words & existing_words
            if overlap:
                links.append(
                    ConceptLink(
                        source_concept=new_c.name,
                        target_concept=existing_c.name,
                        relation="shared_terms",
                        weight=len(overlap) / max(len(new_words), len(existing_words)),
                    )
                )

    return links
