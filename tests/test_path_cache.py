"""Path cache (Slice 5): skip the tree-descent LLM call for repeated/similar
problem schemas, keyed on the abstracted schema rather than raw text.
"""

from __future__ import annotations

import pytest

from contextify import aretrieve_framework
from contextify.framework_store import build_seeded_store
from contextify.llm import MockLLMClient
from contextify.reflection import MatchHistory
from contextify.retrieval import PathCache


class _CountingLLM:
    """Wraps MockLLMClient and counts resolve_framework calls, so tests can
    assert a cache hit skipped the descent call rather than just inferring it
    from the result."""

    def __init__(self) -> None:
        self._inner = MockLLMClient()
        self.resolve_calls = 0

    def abstract_problem(self, raw_text):
        return self._inner.abstract_problem(raw_text)

    def resolve_framework(self, abstraction, tree):
        self.resolve_calls += 1
        return self._inner.resolve_framework(abstraction, tree)


@pytest.mark.asyncio
async def test_paraphrased_input_hits_the_cache_and_skips_the_descent_call():
    store = await build_seeded_store()
    cache = PathCache()
    history = MatchHistory()
    llm = _CountingLLM()

    first = await aretrieve_framework(
        "The checkout page keeps crashing after the update.",
        llm=llm, store=store, history=history, cache=cache,
    )
    second = await aretrieve_framework(
        "The checkout page keeps failing after the update.",
        llm=llm, store=store, history=history, cache=cache,
    )

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.framework.id == first.framework.id
    assert llm.resolve_calls == 1  # second call never re-ran the descent


@pytest.mark.asyncio
async def test_cache_key_is_the_abstracted_schema_not_the_raw_text():
    # Different raw text entirely, but the MockLLMClient's heuristic
    # abstraction lands on the same structured fields and an overlapping
    # symptom shape — the cache should key off that, not string equality of
    # the raw input.
    store = await build_seeded_store()
    cache = PathCache()
    history = MatchHistory()
    llm = _CountingLLM()

    await aretrieve_framework(
        "The dashboard widget breaks after saving.",
        llm=llm, store=store, history=history, cache=cache,
    )
    second = await aretrieve_framework(
        "The dashboard widget breaks after saving changes.",
        llm=llm, store=store, history=history, cache=cache,
    )

    assert second.cache_hit is True
    assert llm.resolve_calls == 1


@pytest.mark.asyncio
async def test_genuinely_novel_schema_is_a_cache_miss():
    store = await build_seeded_store()
    cache = PathCache()
    history = MatchHistory()
    llm = _CountingLLM()

    await aretrieve_framework(
        "The checkout page keeps crashing after the update.",
        llm=llm, store=store, history=history, cache=cache,
    )
    # Unrelated symptom, different implied goal_shape (coverage vs root-cause)
    second = await aretrieve_framework(
        "We want to make sure the discount calculator handles cart totals of "
        "exactly $0, exactly the max allowed $10,000, and one cent over the max.",
        llm=llm, store=store, history=history, cache=cache,
    )

    assert second.cache_hit is False
    assert llm.resolve_calls == 2  # both calls actually ran the descent


@pytest.mark.asyncio
async def test_cache_hit_and_miss_are_observable_on_the_match():
    store = await build_seeded_store()
    cache = PathCache()
    history = MatchHistory()
    llm = _CountingLLM()

    miss = await aretrieve_framework(
        "The checkout page keeps crashing after the update.",
        llm=llm, store=store, history=history, cache=cache,
    )
    hit = await aretrieve_framework(
        "The checkout page keeps failing after the update.",
        llm=llm, store=store, history=history, cache=cache,
    )

    assert hasattr(miss, "cache_hit") and hasattr(hit, "cache_hit")
    assert miss.cache_hit is False
    assert hit.cache_hit is True
