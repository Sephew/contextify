import pytest

from contextify.framework_store import DEBUGGING_FRAMEWORKS, build_seeded_store
from contextify.framework_store.store import InMemoryGraphStore
from contextify.models import FrameworkStatus


@pytest.mark.asyncio
async def test_seeded_store_contains_both_branch_roots_and_all_leaves():
    store = await build_seeded_store()
    tree = await store.read_tree()
    assert len(tree) == 9  # 2 roots (debugging + testing) + 4 + 3 leaves

    debugging_root = await store.get("fw.debugging")
    testing_root = await store.get("fw.testing")
    assert debugging_root is not None and debugging_root.is_root
    assert testing_root is not None and testing_root.is_root

    debugging_leaves = [f for f in tree if f.parent == "fw.debugging"]
    testing_leaves = [f for f in tree if f.parent == "fw.testing"]
    assert len(debugging_leaves) == 4
    assert len(testing_leaves) == 3
    for leaf in [*debugging_leaves, *testing_leaves]:
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
