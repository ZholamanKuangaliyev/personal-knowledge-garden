from garden.core.llm_utils import get_llm, parse_json_response
from garden.core.logging import get_logger
from garden.core.models import Concept
from garden.prompts.loader import render

_log = get_logger("concept_extractor")


def extract_concepts(chunks: list[str], source: str, batch_size: int = 5) -> list[Concept]:
    llm = get_llm()
    all_concepts: list[Concept] = []
    seen: set[str] = set()

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        prompt = render("concept_extract.j2", source=source, chunks=batch)
        response = llm.invoke(prompt)

        try:
            result = parse_json_response(response.content)
            for c in result.get("concepts", []):
                name = c["name"].lower().strip()
                if name and name not in seen:
                    seen.add(name)
                    all_concepts.append(
                        Concept(name=name, source=source, description=c.get("description", ""))
                    )
        except (ValueError, KeyError, AttributeError) as exc:
            _log.warning("Failed to extract concepts from batch %d of '%s': %s", i // batch_size + 1, source, exc)
            continue

    return all_concepts
