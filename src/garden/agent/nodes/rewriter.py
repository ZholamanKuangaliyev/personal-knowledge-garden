"""Rewriter node — reformulates questions for better retrieval.

Strategy Pattern: RewriterNode is a concrete AgentNode strategy. When the
grader finds no relevant documents, the rewriter reformulates the question
to improve the next retrieval attempt.

Unlike the original implementation, the rewriter now receives the documents
that were retrieved but rejected by the grader (via state["graded_out_documents"]).
This gives the LLM concrete feedback about what the retriever found, so it
can steer the rewrite away from that content and toward different terminology.

Open/Closed Principle: to change rewriting behavior (e.g., query expansion,
synonym injection, HyDE), subclass RewriterNode and override execute().
"""

from garden.agent.base import AgentNode
from garden.agent.state import AgentState
from garden.core.config import settings
from garden.core.llm_utils import invoke_llm, parse_json_response
from garden.core.logging import get_logger
from garden.prompts.loader import render

_log = get_logger("agent.rewriter")


class RewriterNode(AgentNode):
    """Reformulates the question using the LLM to improve retrieval recall.

    Single Responsibility: this node only rewrites queries. It does not
    retrieve documents or evaluate their relevance.

    The node receives graded_out_documents from the grader so it knows what
    was retrieved but deemed irrelevant. This context helps the LLM write a
    better query that targets different aspects of the topic, rather than
    blindly rephrasing the same question.

    The node increments retry_count so the grader edge strategy knows when
    to stop the rewrite-retrieve loop and fall back to generation without
    supporting documents.
    """

    def execute(self, state: AgentState) -> AgentState:
        question = state.get("rewritten_question") or state["question"]
        retry_count = state.get("retry_count", 0)

        # Pass rejected documents so the rewriter knows what the retriever
        # found and can steer away from that content.
        graded_out = state.get("graded_out_documents", [])
        max_failed = settings.rewriter_failed_docs
        failed_context = [
            {"source": d["source"], "preview": d["content"][:150]}
            for d in graded_out[:max_failed]
        ]

        prompt = render(
            "rewriter.j2",
            question=question,
            failed_documents=failed_context,
        )

        try:
            content = invoke_llm(prompt)
            result = parse_json_response(content)
            rewritten = result.get("rewritten_question", question)
        except (ValueError, AttributeError) as exc:
            _log.warning("Rewriter failed to parse LLM response, keeping original question: %s", exc)
            rewritten = question

        _log.debug("Rewrote query (attempt %d): %r -> %r", retry_count + 1, question[:80], rewritten[:80])
        return {**state, "rewritten_question": rewritten, "retry_count": retry_count + 1}


# -- Backward-compatible module-level function --
_default_rewriter = RewriterNode()


def rewrite_query(state: AgentState) -> AgentState:
    """Module-level wrapper kept for backward compatibility with graph.py imports."""
    return _default_rewriter(state)
