from typing import TypedDict


class AgentState(TypedDict, total=False):
    question: str
    rewritten_question: str
    documents: list[dict]
    graded_out_documents: list[dict]  # docs rejected by the grader, fed to the rewriter
    generation: str
    route: str
    relevance_score: float
    retry_count: int
    sources: list[str]
    history: list[dict]
    search_filters: dict
    role: str
    auto_role: bool
    knowledge_gap: bool  # True when retries exhausted with no relevant docs
