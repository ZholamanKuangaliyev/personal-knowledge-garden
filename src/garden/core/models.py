from datetime import datetime

from pydantic import BaseModel, Field


class Document(BaseModel):
    source: str
    content: str
    tags: list[str] = Field(default_factory=list)
    ingested_at: datetime = Field(default_factory=datetime.now)


class Chunk(BaseModel):
    id: str
    source: str
    content: str
    tags: list[str] = Field(default_factory=list)
    chunk_index: int = 0


class Concept(BaseModel):
    name: str
    source: str
    description: str = ""


class ConceptLink(BaseModel):
    source_concept: str
    target_concept: str
    relation: str = "related_to"
    weight: float = 1.0


class Flashcard(BaseModel):
    id: str
    question: str
    answer: str
    source: str
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    # SM-2 fields
    easiness: float = 2.5
    interval: int = 1
    repetitions: int = 0
    next_review: datetime = Field(default_factory=datetime.now)


class SearchResult(BaseModel):
    content: str
    source: str
    score: float = 0.0


class GardenStats(BaseModel):
    total_documents: int = 0
    total_chunks: int = 0
    total_concepts: int = 0
    total_links: int = 0
    total_cards: int = 0
    cards_due: int = 0
