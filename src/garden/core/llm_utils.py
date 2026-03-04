import json
import re

from langchain_ollama import ChatOllama

from garden.core.config import settings
from garden.core.logging import get_logger

_log = get_logger("llm_utils")

_llm: ChatOllama | None = None

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def get_llm() -> ChatOllama:
    global _llm
    if _llm is None:
        _log.debug("Initializing LLM model=%s url=%s", settings.llm_model, settings.ollama_base_url)
        _llm = ChatOllama(model=settings.llm_model, base_url=settings.ollama_base_url)
    return _llm


def reset_llm() -> None:
    global _llm
    _llm = None


def parse_json_response(text: str) -> dict:
    """Parse JSON from LLM response, handling <think> blocks and markdown fences.

    Raises ValueError if no valid JSON can be extracted.
    """
    # Strip think blocks
    cleaned = _THINK_RE.sub("", text).strip()

    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        _log.debug("Direct JSON parse failed, trying fence extraction")

    # Try extracting from markdown fences
    fence_match = _FENCE_RE.search(cleaned)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            _log.debug("Fence JSON parse failed, trying raw brace extraction")

    # Try finding raw JSON object
    brace_start = cleaned.find("{")
    if brace_start != -1:
        # Find matching closing brace
        depth = 0
        for i in range(brace_start, len(cleaned)):
            if cleaned[i] == "{":
                depth += 1
            elif cleaned[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(cleaned[brace_start : i + 1])
                    except json.JSONDecodeError:
                        break

    _log.warning("Could not parse JSON from LLM response: %s", text[:200])
    raise ValueError(f"Could not parse JSON from response: {text[:200]}")
