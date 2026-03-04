"""Agent role definitions for the Knowledge Garden chat."""

from __future__ import annotations

from dataclasses import dataclass

from garden.core.llm_utils import get_llm, parse_json_response
from garden.core.logging import get_logger
from garden.prompts.loader import render

_log = get_logger("agent.roles")


@dataclass(frozen=True)
class Role:
    name: str
    think_mode: bool
    description: str
    template: str  # Jinja2 template filename for the system prompt

    @property
    def system_prompt(self) -> str:
        return render(self.template)


ROLES: dict[str, Role] = {
    "general": Role(
        name="general",
        think_mode=False,
        description="Fast, direct answers and simple knowledge retrieval",
        template="role_general.j2",
    ),
    "analyst": Role(
        name="analyst",
        think_mode=True,
        description="Deep analysis, pattern recognition, and data interpretation",
        template="role_analyst.j2",
    ),
    "summarizer": Role(
        name="summarizer",
        think_mode=True,
        description="Condense and restructure knowledge into clear summaries",
        template="role_summarizer.j2",
    ),
    "creative": Role(
        name="creative",
        think_mode=True,
        description="Brainstorm, ideate, and find novel connections",
        template="role_creative.j2",
    ),
    "researcher": Role(
        name="researcher",
        think_mode=True,
        description="Deep investigation, cross-referencing, and fact-checking",
        template="role_researcher.j2",
    ),
}

DEFAULT_ROLE = "general"

VALID_ROLES = set(ROLES.keys())


def get_role(name: str) -> Role:
    return ROLES.get(name, ROLES[DEFAULT_ROLE])


def get_think_token(role: Role) -> str:
    return "/think" if role.think_mode else "/no_think"


def detect_role(question: str, current_role: str) -> str:
    """Use the LLM to auto-detect the best role for a question.

    Only runs when current role is 'general' to avoid unnecessary switches.
    Returns the role name (or 'keep' mapped to current_role).
    """
    if current_role != "general":
        return current_role

    prompt = render(
        "role_router.j2",
        question=question,
        current_role=current_role,
        roles={name: role.description for name, role in ROLES.items()},
    )

    llm = get_llm()
    response = llm.invoke(prompt)

    try:
        result = parse_json_response(response.content)
        detected = result.get("role", "keep")
        if detected == "keep" or detected not in VALID_ROLES:
            return current_role
        _log.debug("Auto-detected role: %s", detected)
        return detected
    except (ValueError, AttributeError) as exc:
        _log.warning("Role detection failed, keeping current role: %s", exc)
        return current_role
