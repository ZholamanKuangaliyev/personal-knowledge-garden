from garden.agent.state import AgentState
from garden.core.llm_utils import get_llm, parse_json_response
from garden.core.logging import get_logger
from garden.prompts.loader import render

_log = get_logger("agent.rewriter")


def rewrite_query(state: AgentState) -> AgentState:
    question = state.get("rewritten_question") or state["question"]
    retry_count = state.get("retry_count", 0)

    prompt = render("rewriter.j2", question=question)

    llm = get_llm()
    response = llm.invoke(prompt)

    try:
        result = parse_json_response(response.content)
        rewritten = result.get("rewritten_question", question)
    except (ValueError, AttributeError) as exc:
        _log.warning("Rewriter failed to parse LLM response, keeping original question: %s", exc)
        rewritten = question

    _log.debug("Rewrote query (attempt %d): %r -> %r", retry_count + 1, question[:80], rewritten[:80])
    return {**state, "rewritten_question": rewritten, "retry_count": retry_count + 1}
