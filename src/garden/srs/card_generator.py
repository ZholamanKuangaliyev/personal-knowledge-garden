import json
import uuid

from langchain_ollama import ChatOllama

from garden.core.config import settings
from garden.core.models import Flashcard
from garden.prompts.loader import render


def generate_cards(chunks: list[dict]) -> list[Flashcard]:
    llm = ChatOllama(model=settings.llm_model, base_url=settings.ollama_base_url)
    all_cards: list[Flashcard] = []

    for chunk in chunks:
        prompt = render(
            "flashcard_generate.j2",
            source=chunk["source"],
            content=chunk["content"],
        )
        response = llm.invoke(prompt)

        try:
            result = json.loads(response.content)
            for card_data in result.get("cards", []):
                card = Flashcard(
                    id=str(uuid.uuid4()),
                    question=card_data["question"],
                    answer=card_data["answer"],
                    source=chunk["source"],
                    tags=chunk.get("tags", []),
                )
                all_cards.append(card)
        except (json.JSONDecodeError, KeyError, AttributeError):
            continue

    return all_cards
