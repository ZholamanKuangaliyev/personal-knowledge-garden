"""Generator node — synthesizes final answers from retrieved context.

Strategy Pattern (two layers):
    1. GeneratorNode is a concrete AgentNode strategy for the pipeline step.
    2. The LLMInvoker injected via constructor is a strategy for *how* the LLM
       is called (sync, streaming, cached, etc.).

This double-strategy design replaces the old mutable global `_stream_callback`
with proper dependency injection. The generator doesn't know or care whether
tokens are streamed to a Rich Live display or returned in one batch — that's
the invoker's concern (SRP).

Open/Closed Principle:
    - To change answer generation logic (e.g., chain-of-thought, multi-step),
      subclass GeneratorNode and override execute().
    - To change LLM call behavior (e.g., add caching, switch to async),
      create a new LLMInvoker subclass — the generator stays untouched.
"""

from garden.agent.base import AgentNode, LLMInvoker
from garden.agent.roles import get_role, get_think_token
from garden.agent.state import AgentState
from garden.core.llm_utils import invoke_llm
from garden.core.logging import get_logger
from garden.prompts.loader import render

_log = get_logger("agent.generator")


class StandardInvoker(LLMInvoker):
    """Default LLM invocation strategy — synchronous call via invoke_llm.

    This is the standard path used for non-streaming chat and all non-interactive
    contexts (tests, batch processing). It delegates to the centralized invoke_llm
    which includes tenacity retry and @timed instrumentation.
    """

    def invoke(self, prompt: str) -> str:
        return invoke_llm(prompt)


class StreamingInvoker(LLMInvoker):
    """Streaming LLM invocation strategy — delegates to a caller-provided callback.

    The callback receives the full prompt and is responsible for streaming tokens
    to the user (e.g., via Rich Live). It must return the complete response text
    once streaming is done.

    Why a callback and not direct stream_llm usage:
        The streaming UI logic (Rich Live, refresh rate, Markdown rendering) is
        a CLI concern, not a generator concern. The callback lets the CLI own
        its display logic while the generator stays UI-agnostic (SRP).
    """

    def __init__(self, callback) -> None:
        # callback signature: (prompt: str) -> str
        self._callback = callback

    def invoke(self, prompt: str) -> str:
        return self._callback(prompt)


class GeneratorNode(AgentNode):
    """Synthesizes a final answer using retrieved documents and conversation history.

    Single Responsibility: this node builds the generation prompt and interprets
    the response. *How* the LLM is called is delegated to the injected LLMInvoker
    strategy (Dependency Inversion Principle).

    Constructor injection of LLMInvoker replaces the old module-level
    set_stream_callback/clear_stream_callback pattern, eliminating mutable
    global state and making the node thread-safe and easier to test.
    """

    def __init__(self, invoker: LLMInvoker | None = None) -> None:
        # Default to synchronous invocation if no strategy is provided.
        # This keeps the simple case simple — callers that don't need streaming
        # can create GeneratorNode() with zero configuration.
        self._invoker = invoker or StandardInvoker()

    @property
    def invoker(self) -> LLMInvoker:
        """The current LLM invocation strategy. Exposed for introspection/testing."""
        return self._invoker

    @invoker.setter
    def invoker(self, value: LLMInvoker) -> None:
        """Swap the invocation strategy at runtime.

        This setter exists so the chat command can switch between standard and
        streaming invokers per-message without rebuilding the entire graph.
        Prefer constructor injection when possible; use this for dynamic cases.
        """
        self._invoker = value

    def execute(self, state: AgentState) -> AgentState:
        question = state.get("rewritten_question") or state["question"]
        documents = state.get("documents", [])
        history = state.get("history", [])
        knowledge_gap = state.get("knowledge_gap", False)

        role = get_role(state.get("role", "general"))
        think_token = get_think_token(role)

        _log.debug(
            "Generating answer with %d documents, %d history entries, role=%s, knowledge_gap=%s",
            len(documents), len(history), role.name, knowledge_gap,
        )
        prompt = render(
            "generator.j2",
            question=question,
            documents=documents,
            history=history,
            role_prompt=role.system_prompt,
            think_token=think_token,
            knowledge_gap=knowledge_gap,
        )

        # Delegate to the injected LLM invocation strategy.
        # The generator doesn't know if this streams tokens or runs synchronously.
        content = self._invoker.invoke(prompt)

        _log.debug("Generated answer (%d chars)", len(content))
        return {**state, "generation": content}


# -- Backward-compatible module-level API --
# The default instance uses StandardInvoker (synchronous).
# chat.py swaps the invoker to StreamingInvoker when --stream is active.
_default_generator = GeneratorNode()


def generate_answer(state: AgentState) -> AgentState:
    """Module-level wrapper kept for backward compatibility with graph.py imports."""
    return _default_generator(state)


def set_stream_callback(callback) -> None:
    """Switch the default generator to streaming mode.

    Backward-compatible shim — new code should prefer constructing a
    GeneratorNode(invoker=StreamingInvoker(callback)) directly.
    """
    _default_generator.invoker = StreamingInvoker(callback)


def clear_stream_callback() -> None:
    """Reset the default generator back to synchronous mode.

    Backward-compatible shim — new code should prefer constructing a
    GeneratorNode(invoker=StandardInvoker()) directly.
    """
    _default_generator.invoker = StandardInvoker()
