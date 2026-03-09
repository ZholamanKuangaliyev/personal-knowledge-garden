from garden.core.llm_utils import invoke_llm, parse_json_response
from garden.core.logging import get_logger, timed
from garden.prompts.loader import render
from garden.store.graph_store import get_graph
from garden.store.vector_store import search

_log = get_logger("idea_generator")


@timed("idea_generation")
def generate_ideas(topic: str) -> list[dict]:
    # Get relevant docs — convert to dicts for template rendering
    raw_results = search(topic, k=5)
    documents = [{"content": r.content, "source": r.source, "score": r.score} for r in raw_results]

    # Get related concepts from graph
    graph = get_graph()
    concepts = []
    topic_words = set(topic.lower().split())
    for node in graph.nodes():
        node_words = set(node.split())
        if topic_words & node_words:
            concepts.append(node)
            for neighbor in graph.neighbors(node):
                concepts.append(neighbor)
    concepts = list(set(concepts))[:10]

    prompt = render("ideate.j2", topic=topic, documents=documents, concepts=concepts)

    try:
        content = invoke_llm(prompt)
        result = parse_json_response(content)
        return result.get("ideas", [])
    except (ValueError, AttributeError) as exc:
        _log.warning("Failed to generate ideas for topic '%s': %s", topic, exc)
        return []
