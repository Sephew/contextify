"""Public API — the two seams the PRD specifies.

``retrieve_framework(raw_input) -> FrameworkMatch`` wraps Problem Abstraction +
Framework Retrieval as one call. ``reflect(...)`` is the later write-back seam
(stubbed this slice). Keeping these as the only entry points is what stops the
system collapsing into a single prompt template.
"""

from __future__ import annotations

import asyncio

from .framework_store import build_seeded_store
from .framework_store.store import FrameworkStore
from .llm import LLMClient, MockLLMClient
from .models import FrameworkMatch, ReflectionResult
from .problem_abstraction import abstract
from .reflection import reflect as _reflect
from .retrieval import resolve


async def aretrieve_framework(
    raw_input: str,
    llm: LLMClient | None = None,
    store: FrameworkStore | None = None,
) -> FrameworkMatch:
    """Async core: abstract the problem, read the tree, resolve the framework.

    Defaults to the offline :class:`MockLLMClient` and a freshly seeded in-memory
    store, so it runs with no API key. Pass an ``OpenRouterClient`` for a live run.
    """
    llm = llm if llm is not None else MockLLMClient()
    if store is None:
        store = await build_seeded_store()

    abstraction = abstract(raw_input, llm)          # stage 1: one LLM call
    tree = await store.read_tree()
    return resolve(abstraction, tree, llm)          # stage 2: one LLM call


def retrieve_framework(
    raw_input: str,
    llm: LLMClient | None = None,
    store: FrameworkStore | None = None,
) -> FrameworkMatch:
    """Synchronous facade over :func:`aretrieve_framework` for CLI/simple use.

    Raises RuntimeError with actionable guidance if called from inside code that's
    already running an event loop (e.g. an async web handler, a notebook cell) —
    use ``await aretrieve_framework(...)`` directly there instead.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass  # no loop running — the expected case, safe to asyncio.run()
    else:
        raise RuntimeError(
            "retrieve_framework() cannot be called from inside a running event "
            "loop. Use 'await aretrieve_framework(...)' instead."
        )
    return asyncio.run(aretrieve_framework(raw_input, llm=llm, store=store))


def reflect(match_id: str, outcome: str, store: FrameworkStore | None = None) -> ReflectionResult:
    """Reflection write-back seam (stubbed this slice)."""
    return _reflect(match_id, outcome, store=store)
