from datetime import datetime, timedelta

from garden.core.models import Flashcard


def sm2_update(card: Flashcard, quality: int) -> Flashcard:
    """Update card using SM-2 algorithm.

    quality: 0-5 rating (0=complete blackout, 5=perfect recall)
    """
    quality = max(0, min(5, quality))

    if quality >= 3:
        if card.repetitions == 0:
            card.interval = 1
        elif card.repetitions == 1:
            card.interval = 6
        else:
            card.interval = round(card.interval * card.easiness)
        card.repetitions += 1
    else:
        card.repetitions = 0
        card.interval = 1

    card.easiness = max(
        1.3,
        card.easiness + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02),
    )

    card.next_review = datetime.now() + timedelta(days=card.interval)
    return card
