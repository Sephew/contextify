import pytest

from contextify.framework_store import DEBUGGING_FRAMEWORKS, build_seeded_store
from contextify.framework_store.store import InMemoryGraphStore
from contextify.models import FrameworkStatus


@pytest.mark.asyncio
async def test_seeded_store_contains_root_and_four_leaves():
    store = await build_seeded_store()
    tree = await store.read_tree()
    assert len(tree) == 5  # 1 root + 4 leaves

    root = await store.get("fw.debugging")
    assert root is not None
    assert root.is_root

    leaves = [f for f in tree if not f.is_root]
    assert len(leaves) == 4
    for leaf in leaves:
        assert leaf.parent == "fw.debugging"
        assert len(leaf.applicability_condition) > 0
        assert leaf.status == FrameworkStatus.SEEDED


@pytest.mark.asyncio
async def test_seed_matches_the_seed_module_exactly():
    store = InMemoryGraphStore()
    await store.seed(DEBUGGING_FRAMEWORKS)
    tree = await store.read_tree()
    ids = {f.id for f in tree}
    assert ids == {
        "fw.debugging",
        "fw.bisection",
        "fw.differential",
        "fw.cache_invalidation",
        "fw.trace",
    }


@pytest.mark.asyncio
async def test_children_of_root_are_the_four_leaves():
    store = InMemoryGraphStore()
    await store.seed(DEBUGGING_FRAMEWORKS)
    children = await store.children_of("fw.debugging")
    assert {c.id for c in children} == {
        "fw.bisection",
        "fw.differential",
        "fw.cache_invalidation",
        "fw.trace",
    }
