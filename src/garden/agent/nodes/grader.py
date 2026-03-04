from garden.agent.state import AgentState
from garden.core.llm_utils import get_llm, parse_json_response
from garden.core.logging import get_logger
from garden.prompts.loader import render

_log = get_logger("agent.grader")


def grade_documents(state: AgentState) -> AgentState:
    question = state.get("rewritten_question") or state["question"]
    documents = state.get("documents", [])

    if not documents:
        _log.debug("No documents to grade")
        return {**state, "documents": [], "relevance_score": 0.0}

    prompt = render("grader.j2", question=question, documents=documents)

    llm = get_llm()
    response = llm.invoke(prompt)

    try:
        result = parse_json_response(response.content)
        relevant_indices = result.get("relevant_indices", [])
        relevant_docs = [documents[i] for i in relevant_indices if i < len(documents)]
    except (ValueError, AttributeError, IndexError) as exc:
        _log.warning("Grader failed to parse LLM response, keeping all %d docs: %s", len(documents), exc)
        relevant_docs = documents

    score = len(relevant_docs) / len(documents) if documents else 0.0
    _log.debug("Graded %d/%d documents as relevant (score=%.2f)", len(relevant_docs), len(documents), score)
    sources = list({d["source"] for d in relevant_docs})

    return {**state, "documents": relevant_docs, "relevance_score": score, "sources": sources}
