from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class Document(BaseModel):
    source: str
    content: str
    tags: list[str] = Field(default_factory=list)
    ingested_at: datetime = Field(default_factory=datetime.now)

    @field_validator("source")
    @classmethod
    def source_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source must not be empty")
        return v.strip()

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content must not be empty")
        return v


class Chunk(BaseModel):
    id: str
    source: str
    content: str
    tags: list[str] = Field(default_factory=list)
    chunk_index: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)

    @field_validator("chunk_index")
    @classmethod
    def chunk_index_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("chunk_index must be non-negative")
        return v


class Concept(BaseModel):
    name: str
    source: str
    description: str = ""
    category: str = ""
    importance: float = 0.0

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("concept name must not be empty")
        return v.strip()


class ConceptLink(BaseModel):
    source_concept: str
    target_concept: str
    relation: str = "related_to"
    weight: float = 1.0

    @field_validator("weight")
    @classmethod
    def weight_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("weight must be non-negative")
        return v


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
    last_reviewed_at: datetime | None = None
    review_count: int = 0
    source_chunk_id: str = ""

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be empty")
        return v

    @field_validator("answer")
    @classmethod
    def answer_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("answer must not be empty")
        return v

    @field_validator("easiness")
    @classmethod
    def easiness_minimum(cls, v: float) -> float:
        if v < 1.3:
            raise ValueError("easiness must be >= 1.3")
        return v

    @field_validator("interval")
    @classmethod
    def interval_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("interval must be >= 1")
        return v


class SearchResult(BaseModel):
    content: str
    source: str
    score: float = 0.0
    chunk_index: int = 0
    metadata: dict = Field(default_factory=dict)


class GardenStats(BaseModel):
    total_documents: int = 0
    total_chunks: int = 0
    total_concepts: int = 0
    total_links: int = 0
    total_cards: int = 0
    cards_due: int = 0
