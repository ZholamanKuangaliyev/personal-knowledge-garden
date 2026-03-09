import json
import re

from langchain_ollama import ChatOllama
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from garden.core.config import settings
from garden.core.exceptions import OllamaConnectionError
from garden.core.logging import get_logger, timed

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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10, jitter=2),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
    reraise=True,
)
@timed("llm.invoke")
def invoke_llm(prompt: str) -> str:
    """Invoke the LLM with retry logic and timing. Returns the response content string."""
    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        return response.content
    except (ConnectionError, TimeoutError, OSError) as exc:
        _log.warning("LLM connection failed (will retry): %s", exc)
        raise
    except Exception as exc:
        _log.error("LLM invocation failed: %s", exc)
        raise OllamaConnectionError(f"LLM invocation failed: {exc}") from exc


def stream_llm(prompt: str):
    """Stream LLM response token-by-token. Yields content strings."""
    try:
        llm = get_llm()
        for chunk in llm.stream(prompt):
            if chunk.content:
                yield chunk.content
    except Exception as exc:
        _log.error("LLM streaming failed: %s", exc)
        raise OllamaConnectionError(f"LLM streaming failed: {exc}") from exc


async def ainvoke_llm(prompt: str) -> str:
    """Async version of invoke_llm for concurrent operations."""
    try:
        llm = get_llm()
        response = await llm.ainvoke(prompt)
        return response.content
    except (ConnectionError, TimeoutError, OSError) as exc:
        _log.warning("Async LLM connection failed: %s", exc)
        raise
    except Exception as exc:
        _log.error("Async LLM invocation failed: %s", exc)
        raise OllamaConnectionError(f"Async LLM invocation failed: {exc}") from exc


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
