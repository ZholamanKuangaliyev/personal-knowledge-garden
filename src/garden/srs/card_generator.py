import uuid

from garden.core.llm_utils import get_llm, parse_json_response
from garden.core.logging import get_logger
from garden.core.models import Chunk, Flashcard
from garden.prompts.loader import render

_log = get_logger("card_generator")


def generate_cards(chunks: list[Chunk]) -> list[Flashcard]:
    llm = get_llm()
    all_cards: list[Flashcard] = []

    for chunk in chunks:
        prompt = render(
            "flashcard_generate.j2",
            source=chunk.source,
            content=chunk.content,
        )
        response = llm.invoke(prompt)

        try:
            result = parse_json_response(response.content)
            for card_data in result.get("cards", []):
                card = Flashcard(
                    id=str(uuid.uuid4()),
                    question=card_data["question"],
                    answer=card_data["answer"],
                    source=chunk.source,
                    tags=chunk.tags,
                )
                all_cards.append(card)
        except (ValueError, KeyError, AttributeError) as exc:
            _log.warning("Failed to generate cards for chunk from '%s': %s", chunk.source, exc)
            continue

    return all_cards
