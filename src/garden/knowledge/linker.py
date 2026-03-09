from garden.core.logging import get_logger
from garden.core.models import Concept, ConceptLink

_log = get_logger("linker")

# Common English stop words that produce false-positive links
_STOP_WORDS = frozenset({
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or",
    "is", "it", "by", "as", "be", "do", "no", "so", "if", "up", "we",
    "with", "from", "that", "this", "not", "but", "are", "was", "were",
    "has", "had", "have", "its", "can", "may", "will",
})


def _meaningful_words(name: str) -> set[str]:
    """Extract meaningful words from a concept name, filtering stop words."""
    return {w.lower() for w in name.split() if w.lower() not in _STOP_WORDS and len(w) > 1}


def find_links(concepts: list[Concept], existing_concepts: list[Concept]) -> list[ConceptLink]:
    links: list[ConceptLink] = []
    all_concepts = existing_concepts + concepts

    # Link concepts from the same source (co-occurrence)
    by_source: dict[str, list[Concept]] = {}
    for c in all_concepts:
        by_source.setdefault(c.source, []).append(c)

    for source_concepts in by_source.values():
        n = len(source_concepts)
        # Weight decay: documents with many concepts produce weaker
        # individual links. This prevents a single large document from
        # dominating the graph with O(n^2) maximum-weight edges.
        co_weight = 2.0 / n if n > 1 else 1.0
        for i, c1 in enumerate(source_concepts):
            for c2 in source_concepts[i + 1 :]:
                links.append(
                    ConceptLink(
                        source_concept=c1.name,
                        target_concept=c2.name,
                        relation="co_occurs",
                        weight=co_weight,
                    )
                )

    # Link new concepts to existing ones via meaningful word overlap
    for new_c in concepts:
        new_words = _meaningful_words(new_c.name)
        if not new_words:
            continue
        for existing_c in existing_concepts:
            if new_c.name == existing_c.name:
                continue
            existing_words = _meaningful_words(existing_c.name)
            if not existing_words:
                continue
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

    # Semantic linking via embedding similarity for new concepts
    # that didn't match via word overlap
    linked_pairs = {
        (lnk.source_concept, lnk.target_concept) for lnk in links if lnk.relation == "shared_terms"
    }
    semantic_links = _find_semantic_links(concepts, existing_concepts, linked_pairs)
    links.extend(semantic_links)

    return links


def _find_semantic_links(
    new_concepts: list[Concept],
    existing_concepts: list[Concept],
    already_linked: set[tuple[str, str]],
    threshold: float = 0.75,
) -> list[ConceptLink]:
    """Find semantic links between concepts using embedding similarity.

    Only links concepts that weren't already connected by word overlap.
    """
    if not new_concepts or not existing_concepts:
        return []

    try:
        from garden.ingestion.embedder import get_embeddings
    except Exception as exc:
        _log.warning("Could not load embeddings for semantic linking: %s", exc)
        return []

    try:
        embedder = get_embeddings()
        new_names = [c.name for c in new_concepts]
        existing_names = [c.name for c in existing_concepts]

        new_vectors = embedder.embed_documents(new_names)
        existing_vectors = embedder.embed_documents(existing_names)
    except Exception as exc:
        _log.warning("Embedding failed during semantic linking: %s", exc)
        return []

    links: list[ConceptLink] = []
    for i, new_c in enumerate(new_concepts):
        for j, existing_c in enumerate(existing_concepts):
            if new_c.name == existing_c.name:
                continue
            pair = (new_c.name, existing_c.name)
            reverse_pair = (existing_c.name, new_c.name)
            if pair in already_linked or reverse_pair in already_linked:
                continue

            similarity = _cosine_similarity(new_vectors[i], existing_vectors[j])
            if similarity >= threshold:
                links.append(
                    ConceptLink(
                        source_concept=new_c.name,
                        target_concept=existing_c.name,
                        relation="semantic",
                        weight=similarity,
                    )
                )

    _log.debug("Found %d semantic links between concepts", len(links))
    return links


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
