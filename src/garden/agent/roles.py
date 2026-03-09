"""Agent role definitions for the Knowledge Garden chat."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from garden.core.llm_utils import invoke_llm, parse_json_response
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


class _RoleRegistry:
    """Extensible registry for agent roles."""

    def __init__(self) -> None:
        self._roles: dict[str, Role] = {}
        self._default: str = "general"

    def register(self, role: Role) -> Role:
        self._roles[role.name] = role
        return role

    def get(self, name: str) -> Role:
        return self._roles.get(name, self._roles[self._default])

    @property
    def valid_roles(self) -> set[str]:
        return set(self._roles.keys())

    @property
    def all_roles(self) -> dict[str, Role]:
        return dict(self._roles)

    def set_default(self, name: str) -> None:
        if name in self._roles:
            self._default = name

    @property
    def default_name(self) -> str:
        return self._default


role_registry = _RoleRegistry()

# Register built-in roles
role_registry.register(Role(
    name="general",
    think_mode=False,
    description="Fast, direct answers and simple knowledge retrieval",
    template="role_general.j2",
))
role_registry.register(Role(
    name="analyst",
    think_mode=True,
    description="Deep analysis, pattern recognition, and data interpretation",
    template="role_analyst.j2",
))
role_registry.register(Role(
    name="summarizer",
    think_mode=True,
    description="Condense and restructure knowledge into clear summaries",
    template="role_summarizer.j2",
))
role_registry.register(Role(
    name="creative",
    think_mode=True,
    description="Brainstorm, ideate, and find novel connections",
    template="role_creative.j2",
))
role_registry.register(Role(
    name="researcher",
    think_mode=True,
    description="Deep investigation, cross-referencing, and fact-checking",
    template="role_researcher.j2",
))

# Backwards-compatible aliases
ROLES = role_registry.all_roles
DEFAULT_ROLE = role_registry.default_name
VALID_ROLES = role_registry.valid_roles


def get_role(name: str) -> Role:
    return role_registry.get(name)


def get_think_token(role: Role) -> str:
    return "/think" if role.think_mode else "/no_think"


@lru_cache(maxsize=128)
def _cached_detect(question_key: str, current_role: str) -> str:
    """Cached role detection based on first 100 chars of question."""
    prompt = render(
        "role_router.j2",
        question=question_key,
        current_role=current_role,
        roles={name: role.description for name, role in role_registry.all_roles.items()},
    )

    content = invoke_llm(prompt)

    try:
        result = parse_json_response(content)
        detected = result.get("role", "keep")
        if detected == "keep" or detected not in role_registry.valid_roles:
            return current_role
        return detected
    except (ValueError, AttributeError):
        return current_role


def detect_role(question: str, current_role: str) -> str:
    """Use the LLM to auto-detect the best role for a question.

    Only runs when current role is 'general' to avoid unnecessary switches.
    Returns the role name (or 'keep' mapped to current_role).
    """
    if current_role != "general":
        return current_role

    # Cache key: truncate to first 100 chars for similar questions
    question_key = question[:100].strip().lower()
    try:
        detected = _cached_detect(question_key, current_role)
        if detected != current_role:
            _log.debug("Auto-detected role: %s", detected)
        return detected
    except Exception as exc:
        _log.warning("Role detection failed, keeping current role: %s", exc)
        return current_role
