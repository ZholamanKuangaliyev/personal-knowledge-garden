"""Grader node — evaluates retrieved documents for relevance.

Strategy Pattern: two concrete grading strategies share the AgentNode interface.

    EmbeddingGraderNode (default) — uses ChromaDB similarity scores that are
        already computed during retrieval. Zero LLM calls, microsecond latency.
        This is the right default because the embedding model saw the full text
        while the LLM grader only sees a 300-char truncation.

    LLMGraderNode — asks the LLM to judge relevance per-document. Higher
        precision for ambiguous cases, but adds 1-3 seconds of latency.

Open/Closed Principle: new grading strategies (e.g., hybrid, learned ranker)
are added by subclassing AgentNode — existing strategies stay untouched.

Both strategies store rejected documents in state["graded_out_documents"]
so the rewriter can see what was retrieved but deemed irrelevant, enabling
better query reformulation.
"""

from garden.agent.base import AgentNode
from garden.agent.state import AgentState
from garden.core.config import settings
from garden.core.llm_utils import invoke_llm, parse_json_response
from garden.core.logging import get_logger
from garden.prompts.loader import render

_log = get_logger("agent.grader")


def _build_result(state, relevant_docs, all_docs):
    """Shared helper to build grader output state with rejected docs.

    Computes relevance_score, extracts sources, and separates rejected
    documents into graded_out_documents for the rewriter to consume.
    """
    score = len(relevant_docs) / len(all_docs) if all_docs else 0.0
    sources = list({d["source"] for d in relevant_docs})
    relevant_set = set(id(d) for d in relevant_docs)
    graded_out = [d for d in all_docs if id(d) not in relevant_set]
    return {
        **state,
        "documents": relevant_docs,
        "graded_out_documents": graded_out,
        "relevance_score": score,
        "sources": sources,
    }


class EmbeddingGraderNode(AgentNode):
    """Filters documents by embedding similarity score — no LLM call needed.

    ChromaDB already computes cosine/L2 distance during retrieval. The score
    is carried in each document dict as doc["score"]. Using a threshold on
    this score eliminates an entire LLM round-trip (~1-3s per query).

    Why this is more reliable than LLM grading for a 9B model:
        - The embedding model saw the full document text during indexing.
        - The LLM grader only saw a 300-char truncation.
        - Embedding similarity is deterministic; LLM grading is not.

    The threshold is configurable via constructor injection (DIP). Lower
    values are stricter (ChromaDB L2 distance: lower = more similar).
    """

    def __init__(self, threshold: float | None = None) -> None:
        # Default threshold from config; works well for nomic-embed-text L2 distances.
        # Typical relevant docs score 0.5-1.2; irrelevant docs score 1.5+.
        self._threshold = threshold if threshold is not None else settings.grader_threshold

    def execute(self, state: AgentState) -> AgentState:
        documents = state.get("documents", [])

        if not documents:
            _log.debug("No documents to grade")
            return {**state, "documents": [], "graded_out_documents": [], "relevance_score": 0.0}

        # Fast-path: skip grading entirely when configured.
        if settings.skip_grading:
            _log.debug("Grading skipped (skip_grading=True), passing all %d docs", len(documents))
            sources = list({d["source"] for d in documents})
            return {**state, "documents": documents, "graded_out_documents": [], "relevance_score": 1.0, "sources": sources}

        # Filter by embedding similarity score. ChromaDB returns L2 distance
        # where lower = more similar. Documents below threshold are relevant.
        relevant_docs = [d for d in documents if d.get("score", 0) <= self._threshold]

        # Always keep at least the best-scoring document so the generator
        # has some context even if all scores are above threshold.
        if not relevant_docs and documents:
            best = min(documents, key=lambda d: d.get("score", float("inf")))
            relevant_docs = [best]

        _log.debug(
            "Embedding grader kept %d/%d documents (threshold=%.2f)",
            len(relevant_docs), len(documents), self._threshold,
        )
        return _build_result(state, relevant_docs, documents)


class LLMGraderNode(AgentNode):
    """Filters retrieved documents by LLM-judged relevance.

    Sends truncated document content to the LLM and asks it to return
    indices of relevant documents. Higher precision than embedding scores
    for ambiguous queries, but adds 1-3 seconds of latency per call.

    Design note: documents are truncated before sending to the grader to
    reduce token usage, but the *full* documents are forwarded to the
    generator so no context is lost in the final answer.
    """

    def execute(self, state: AgentState) -> AgentState:
        question = state.get("rewritten_question") or state["question"]
        documents = state.get("documents", [])

        if not documents:
            _log.debug("No documents to grade")
            return {**state, "documents": [], "graded_out_documents": [], "relevance_score": 0.0}

        if settings.skip_grading:
            _log.debug("Grading skipped (skip_grading=True), passing all %d docs", len(documents))
            sources = list({d["source"] for d in documents})
            return {**state, "documents": documents, "graded_out_documents": [], "relevance_score": 1.0, "sources": sources}

        # Truncate document content for the grading prompt — the grader only
        # needs a preview to judge relevance, not the full text.
        max_len = settings.grader_content_len
        truncated_docs = [
            {**d, "content": d["content"][:max_len]}
            for d in documents
        ]

        prompt = render("grader.j2", question=question, documents=truncated_docs)

        try:
            content = invoke_llm(prompt)
            result = parse_json_response(content)
            relevant_indices = result.get("relevant_indices", [])
            # Return full (non-truncated) documents so the generator has
            # complete context for answer synthesis.
            relevant_docs = [documents[i] for i in relevant_indices if i < len(documents)]
        except (ValueError, AttributeError, IndexError) as exc:
            _log.warning("Grader failed to parse LLM response, keeping all %d docs: %s", len(documents), exc)
            relevant_docs = documents

        _log.debug("LLM graded %d/%d documents as relevant", len(relevant_docs), len(documents))
        return _build_result(state, relevant_docs, documents)


# -- Backward-compatible aliases --
# GraderNode now points to the embedding-based strategy (the optimized default).
# Code that imported GraderNode still works but gets the faster implementation.
GraderNode = EmbeddingGraderNode

_default_grader = EmbeddingGraderNode()


def grade_documents(state: AgentState) -> AgentState:
    """Module-level wrapper kept for backward compatibility with graph.py imports."""
    return _default_grader(state)
