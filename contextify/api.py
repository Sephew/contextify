"""Public API — the two seams the PRD specifies.

``retrieve_framework(raw_input) -> FrameworkMatch`` wraps Problem Abstraction +
Framework Retrieval as one call. ``reflect(...)`` is the later write-back seam
(stubbed this slice). Keeping these as the only entry points is what stops the
system collapsing into a single prompt template.
"""

from __future__ import annotations

import asyncio
import re

from .framework_store import build_seeded_store
from .framework_store.promotion import new_provisional_framework
from .framework_store.store import FrameworkStore
from .llm import LLMClient, MockLLMClient
from .models import Framework, FrameworkMatch, ProblemAbstraction, ReflectionResult
from .problem_abstraction import abstract
from .reflection import MatchHistory
from .reflection import reflect as _reflect
from .retrieval import PathCache, resolve

# When a retrieval lands at or below this derived confidence (or is flagged
# ambiguous), the tree fit the problem poorly — auto_draft mode proposes a new
# provisional framework for that shape rather than silently returning a weak pick.
DRAFT_CONFIDENCE_FLOOR = 0.5


async def _maybe_draft(
    abstraction: ProblemAbstraction,
    match: FrameworkMatch,
    tree: list[Framework],
    store: FrameworkStore,
    llm: LLMClient,
) -> Framework | None:
    """Draft + seed one provisional framework as a sibling of the weak match.

    Returns the new Framework, or None if it couldn't/needn't draft (the match
    is a branch root, drafting failed, or an identically-named framework already
    exists — so repeated low-confidence hits on the same shape don't duplicate)."""
    near = match.framework
    if near.parent is None:  # only ever draft sibling leaves, never a branch root
        return None
    try:
        draft = llm.draft_framework(abstraction, tree, near)
    except Exception:
        return None  # a model/parse hiccup must not fail the retrieval itself
    slug = re.sub(r"[^a-z0-9]+", "_", draft.name.lower()).strip("_")
    if not slug:
        return None
    framework_id = f"fw.{slug}"
    if await store.get(framework_id) is not None:
        return None
    framework = new_provisional_framework(
        id=framework_id,
        name=draft.name,
        branch=near.branch,
        parent=near.parent,
        applicability_condition=draft.applicability_condition,
    )
    await store.seed([framework])
    return framework

# Process-lifetime defaults so a plain `retrieve_framework(...)` followed by
# `reflect(match.match_id, ...)` works with no store/history/cache threaded
# through by hand — mirroring a real persistent Framework Store, which
# outlives any single call. Tests that need isolation construct and pass
# their own store/history/cache explicitly (as the rest of the suite already
# does for store).
_default_store: FrameworkStore | None = None
_default_history = MatchHistory()
_default_path_cache = PathCache()


async def _get_default_store() -> FrameworkStore:
    global _default_store
    if _default_store is None:
        _default_store = await build_seeded_store()
    return _default_store


async def aretrieve_framework(
    raw_input: str,
    llm: LLMClient | None = None,
    store: FrameworkStore | None = None,
    history: MatchHistory | None = None,
    problem_id: str | None = None,
    cache: PathCache | None = None,
    auto_draft: bool = False,
) -> FrameworkMatch:
    """Async core: abstract the problem, read the tree, resolve the framework.

    Defaults to the offline :class:`MockLLMClient` and a process-lifetime seeded
    in-memory store, so it runs with no API key. Pass an ``OpenRouterClient`` for
    a live run.

    ``problem_id`` groups repeated retrievals for reflect()'s lagging misfit
    signal (PRD user story 11): pass the same value across retries against the
    same underlying problem. Defaults to a fresh id per call — i.e. no grouping
    unless the caller opts in, since inferring "same problem" from text/schema
    similarity is the path cache's job (below), a distinct concern.

    ``cache`` lets a similar-enough abstracted schema skip the tree-descent
    call (PRD user story 9); defaults to a process-lifetime PathCache. Check
    ``match.cache_hit`` to see whether a call actually hit it.
    """
    llm = llm if llm is not None else MockLLMClient()
    if store is None:
        store = await _get_default_store()
    if history is None:
        history = _default_history
    if cache is None:
        cache = _default_path_cache

    abstraction = abstract(raw_input, llm)          # stage 1: one LLM call
    tree = await store.read_tree()
    match = resolve(abstraction, tree, llm, cache=cache)  # stage 2: cached or one LLM call
    history.record(match.match_id, problem_id or match.match_id, match.framework.id)

    # Low confidence means the tree had no good-fitting framework. In auto_draft
    # mode, propose one and drop it into the promotion gate (provisional, under-
    # weighted) so it's eligible next time and promotes if it proves out.
    if auto_draft and (match.low_confidence or match.confidence < DRAFT_CONFIDENCE_FLOOR):
        drafted = await _maybe_draft(abstraction, match, tree, store, llm)
        if drafted is not None:
            match.drafted_framework_id = drafted.id
    return match


def retrieve_framework(
    raw_input: str,
    llm: LLMClient | None = None,
    store: FrameworkStore | None = None,
    history: MatchHistory | None = None,
    problem_id: str | None = None,
    cache: PathCache | None = None,
    auto_draft: bool = False,
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
    return asyncio.run(
        aretrieve_framework(
            raw_input,
            llm=llm,
            store=store,
            history=history,
            problem_id=problem_id,
            cache=cache,
            auto_draft=auto_draft,
        )
    )


async def areflect(
    match_id: str,
    outcome: str,
    store: FrameworkStore | None = None,
    history: MatchHistory | None = None,
) -> ReflectionResult:
    """Async core of the reflection write-back seam."""
    if store is None:
        store = await _get_default_store()
    if history is None:
        history = _default_history
    return await _reflect(match_id, outcome, store=store, history=history)


def reflect(
    match_id: str,
    outcome: str,
    store: FrameworkStore | None = None,
    history: MatchHistory | None = None,
) -> ReflectionResult:
    """Synchronous facade over :func:`areflect` for CLI/simple use.

    Raises RuntimeError with actionable guidance if called from inside code that's
    already running an event loop — use ``await areflect(...)`` directly there.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        raise RuntimeError(
            "reflect() cannot be called from inside a running event loop. "
            "Use 'await areflect(...)' instead."
        )
    return asyncio.run(areflect(match_id, outcome, store=store, history=history))
