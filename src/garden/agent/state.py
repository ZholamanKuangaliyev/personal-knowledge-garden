from typing import TypedDict


class AgentState(TypedDict, total=False):
    question: str
    rewritten_question: str
    documents: list[dict]
    generation: str
    route: str
    relevance_score: float
    retry_count: int
    sources: list[str]
