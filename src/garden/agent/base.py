"""Abstract base classes for the RAG agent pipeline.

Implements the Strategy Pattern to make agent nodes extensible without modification
(Open/Closed Principle). Each node in the pipeline is a strategy that can be swapped,
subclassed, or composed independently.

Why Strategy + ABC here:
    - LangGraph requires each node to be a callable(state) -> state. By defining an
      abstract `execute()` method and routing `__call__` through it, we satisfy
      LangGraph's interface while keeping the extension point clean.
    - New node behaviors (e.g., a CachedRetriever, a MultiModelGenerator) are added
      by creating new subclasses — existing node code never needs to change (OCP).
    - Each base class enforces a Single Responsibility: AgentNode handles pipeline
      step execution, LLMInvoker handles LLM call mechanics, EdgeStrategy handles
      routing decisions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from garden.agent.state import AgentState


class AgentNode(ABC):
    """Strategy interface for agent pipeline nodes.

    Every node in the RAG pipeline (router, retriever, grader, rewriter, generator)
    implements this interface. LangGraph calls nodes as regular functions, so
    __call__ delegates to the abstract execute() method.

    Open/Closed Principle: to add a new node behavior, create a subclass and
    override execute() — no existing node code is modified.

    Single Responsibility: each subclass owns exactly one pipeline step.
    """

    def __call__(self, state: AgentState) -> AgentState:
        """LangGraph-compatible entry point — delegates to the Strategy's execute()."""
        return self.execute(state)

    @abstractmethod
    def execute(self, state: AgentState) -> AgentState:
        """Execute this pipeline step. Subclasses define the concrete behavior."""
        ...


class LLMInvoker(ABC):
    """Strategy interface for LLM invocation.

    Decouples *how* we call the LLM from *what* we do with the result.
    This replaces the old mutable global `_stream_callback` in generator.py
    with proper dependency injection.

    Why a separate strategy (SRP):
        - The generator node's job is to build a prompt and interpret the response.
        - Whether the LLM call streams tokens to a Rich Live display or runs
          synchronously is an orthogonal concern — it belongs in the invoker.

    Open/Closed Principle: to add a new invocation mode (e.g., batched, async,
    cached), create a new LLMInvoker subclass — the generator remains untouched.
    """

    @abstractmethod
    def invoke(self, prompt: str) -> str:
        """Send a prompt to the LLM and return the full response text."""
        ...


class EdgeStrategy(ABC):
    """Strategy interface for conditional edge routing decisions.

    Each conditional edge in the LangGraph pipeline (after-router, after-grader)
    is an EdgeStrategy. This makes routing logic testable and swappable without
    modifying the graph definition (OCP).

    Why a separate strategy:
        - Routing decisions may depend on configuration, thresholds, or even
          learned policies. Encapsulating them behind an interface lets us swap
          the decision logic independently of the graph wiring.
    """

    def __call__(self, state: AgentState) -> str:
        """LangGraph-compatible entry point — delegates to decide()."""
        return self.decide(state)

    @abstractmethod
    def decide(self, state: AgentState) -> str:
        """Return the name of the next node to route to."""
        ...
