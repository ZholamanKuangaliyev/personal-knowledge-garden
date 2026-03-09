import uuid

from garden.core.llm_utils import invoke_llm, parse_json_response
from garden.core.logging import get_logger, timed
from garden.core.models import Chunk, Flashcard
from garden.prompts.loader import render

_log = get_logger("card_generator")


@timed("card_generation")
def generate_cards(chunks: list[Chunk]) -> list[Flashcard]:
    all_cards: list[Flashcard] = []
    seen_questions: set[str] = set()

    for chunk in chunks:
        prompt = render(
            "flashcard_generate.j2",
            source=chunk.source,
            content=chunk.content,
        )

        try:
            content = invoke_llm(prompt)
            result = parse_json_response(content)
            for card_data in result.get("cards", []):
                # Deduplicate by normalized question text
                q_norm = card_data["question"].strip().lower()
                if q_norm in seen_questions:
                    _log.debug("Skipping duplicate card question: %s", q_norm[:80])
                    continue
                seen_questions.add(q_norm)

                card = Flashcard(
                    id=str(uuid.uuid4()),
                    question=card_data["question"],
                    answer=card_data["answer"],
                    source=chunk.source,
                    tags=chunk.tags,
                    source_chunk_id=chunk.id,
                )
                all_cards.append(card)
        except (ValueError, KeyError, AttributeError) as exc:
            _log.warning("Failed to generate cards for chunk from '%s': %s", chunk.source, exc)
            continue

    return all_cards
