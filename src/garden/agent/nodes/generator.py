from garden.agent.roles import get_role, get_think_token
from garden.agent.state import AgentState
from garden.core.llm_utils import get_llm
from garden.core.logging import get_logger
from garden.prompts.loader import render

_log = get_logger("agent.generator")


def generate_answer(state: AgentState) -> AgentState:
    question = state.get("rewritten_question") or state["question"]
    documents = state.get("documents", [])
    history = state.get("history", [])

    role = get_role(state.get("role", "general"))
    think_token = get_think_token(role)

    _log.debug(
        "Generating answer with %d documents, %d history entries, role=%s",
        len(documents), len(history), role.name,
    )
    prompt = render(
        "generator.j2",
        question=question,
        documents=documents,
        history=history,
        role_prompt=role.system_prompt,
        think_token=think_token,
    )

    llm = get_llm()
    response = llm.invoke(prompt)

    _log.debug("Generated answer (%d chars)", len(response.content))
    return {**state, "generation": response.content}
