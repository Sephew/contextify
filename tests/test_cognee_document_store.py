"""Live integration test for the Cognee-backed store.

Skipped unless OPENROUTER_API_KEY is set: cognee.remember()/recall() make real
LLM + embedding network calls, so this is opt-in rather than part of the
default offline suite (see contextify/framework_store/store.py for why this
path works locally when the low-level graph adapter does not).
"""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

from contextify.framework_store import DEBUGGING_FRAMEWORKS, CogneeMemoryStore
from contextify.models import FrameworkStatus

load_dotenv()

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="requires OPENROUTER_API_KEY for real remember/recall calls",
)


@pytest.mark.asyncio
async def test_cognee_memory_store_round_trips_the_debugging_tree():
    store = CogneeMemoryStore()
    await store.seed(DEBUGGING_FRAMEWORKS)
    tree = await store.read_tree()

    ids = {f.id for f in tree}
    expected = {f.id for f in DEBUGGING_FRAMEWORKS}
    assert ids == expected

    root = next(f for f in tree if f.id == "fw.debugging")
    assert root.parent is None
    leaves = [f for f in tree if f.id != "fw.debugging"]
    assert all(leaf.parent == "fw.debugging" for leaf in leaves)
    assert all(len(leaf.applicability_condition) > 0 for leaf in leaves)


@pytest.mark.asyncio
async def test_cognee_memory_store_get_reads_a_single_node():
    store = CogneeMemoryStore()
    await store.seed(DEBUGGING_FRAMEWORKS)

    got = await store.get("fw.bisection")
    assert got is not None
    assert got.id == "fw.bisection"
    assert got.parent == "fw.debugging"
    assert len(got.applicability_condition) > 0

    assert await store.get("fw.does_not_exist") is None


@pytest.mark.asyncio
async def test_cognee_memory_store_write_back_persists():
    store = CogneeMemoryStore()
    await store.seed(DEBUGGING_FRAMEWORKS)

    await store.set_confidence("fw.bisection", 0.42)
    got = await store.get("fw.bisection")
    assert got is not None and got.confidence == 0.42

    await store.set_status("fw.bisection", FrameworkStatus.PROVISIONAL)
    got = await store.get("fw.bisection")
    assert got is not None and got.status is FrameworkStatus.PROVISIONAL
    # the earlier confidence write-back survived the status write-back
    assert got.confidence == 0.42

    n1 = await store.increment_validated_successes("fw.bisection")
    n2 = await store.increment_validated_successes("fw.bisection")
    assert (n1, n2) == (1, 2)
    got = await store.get("fw.bisection")
    assert got is not None and got.validated_successes == 2

    # write-back replaces rather than accumulates: still exactly the seeded set
    tree = await store.read_tree()
    assert {f.id for f in tree} == {f.id for f in DEBUGGING_FRAMEWORKS}

    with pytest.raises(KeyError):
        await store.set_confidence("fw.does_not_exist", 0.1)
