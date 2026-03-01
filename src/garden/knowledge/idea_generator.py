import json

from langchain_ollama import ChatOllama

from garden.core.config import settings
from garden.prompts.loader import render
from garden.store.graph_store import get_graph
from garden.store.vector_store import search


def generate_ideas(topic: str) -> list[dict]:
    # Get relevant docs
    documents = search(topic, k=5)

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
    llm = ChatOllama(model=settings.llm_model, base_url=settings.ollama_base_url)
    response = llm.invoke(prompt)

    try:
        result = json.loads(response.content)
        return result.get("ideas", [])
    except (json.JSONDecodeError, AttributeError):
        return []
