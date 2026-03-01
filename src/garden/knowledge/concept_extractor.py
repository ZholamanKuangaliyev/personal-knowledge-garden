import json

from langchain_ollama import ChatOllama

from garden.core.config import settings
from garden.core.models import Concept
from garden.prompts.loader import render


def extract_concepts(chunks: list[str], source: str, batch_size: int = 5) -> list[Concept]:
    llm = ChatOllama(model=settings.llm_model, base_url=settings.ollama_base_url)
    all_concepts: list[Concept] = []
    seen: set[str] = set()

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        prompt = render("concept_extract.j2", source=source, chunks=batch)
        response = llm.invoke(prompt)

        try:
            result = json.loads(response.content)
            for c in result.get("concepts", []):
                name = c["name"].lower().strip()
                if name and name not in seen:
                    seen.add(name)
                    all_concepts.append(
                        Concept(name=name, source=source, description=c.get("description", ""))
                    )
        except (json.JSONDecodeError, KeyError, AttributeError):
            continue

    return all_concepts
