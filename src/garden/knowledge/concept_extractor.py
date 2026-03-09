from garden.core.config import settings
from garden.core.llm_utils import invoke_llm, parse_json_response
from garden.core.logging import get_logger, timed
from garden.core.models import Concept
from garden.prompts.loader import render

_log = get_logger("concept_extractor")


@timed("concept_extraction")
def extract_concepts(
    chunks: list[str],
    source: str,
    batch_size: int | None = None,
    existing_names: list[str] | None = None,
) -> list[Concept]:
    """Extract concepts from text chunks using the LLM.

    Args:
        chunks: Text content strings to extract concepts from.
        source: Source document name.
        batch_size: Number of chunks per LLM call.
        existing_names: Concept names already in the garden. Passed to the
            prompt so the LLM reuses existing names instead of creating
            duplicates under different wording (e.g., "ML" vs "machine learning").
    """
    all_concepts: list[Concept] = []
    seen: set[str] = set()
    batch_size = batch_size or settings.concept_batch_size

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        prompt = render(
            "concept_extract.j2",
            source=source,
            chunks=batch,
            existing_concepts=existing_names or [],
        )

        try:
            content = invoke_llm(prompt)
            result = parse_json_response(content)
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
