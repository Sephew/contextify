"""reflect() seam: branch-specific ground truth, confidence write-back, and the
lagging misfit signal (Slice 3).

Uses areflect() directly with an explicit store + MatchHistory rather than
going through retrieve_framework()'s heuristic resolution, so these cases stay
deterministic and independent of MockLLMClient's scoring — the seam under test
is reflect() itself, not retrieval.
"""

from __future__ import annotations

import pytest

from contextify import areflect
from contextify.framework_store import build_seeded_store
from contextify.reflection import MatchHistory


@pytest.mark.asyncio
async def test_debugging_success_increases_confidence():
    # Seeded frameworks start at confidence 1.0 (the ceiling), so a lone success
    # has no headroom to show a rise — weaken it with a failure first, then
    # confirm a success visibly strengthens it back up.
    store = await build_seeded_store()
    history = MatchHistory()
    history.record("m1", "problem-1", "fw.bisection")
    history.record("m2", "problem-1", "fw.bisection")
    await areflect("m1", "repro_still_fails", store=store, history=history)

    result = await areflect("m2", "repro_now_passes", store=store, history=history)

    assert result.success is True
    assert result.confidence_after > result.confidence_before
    framework = await store.get("fw.bisection")
    assert framework.confidence == result.confidence_after


@pytest.mark.asyncio
async def test_debugging_failure_decreases_confidence():
    store = await build_seeded_store()
    history = MatchHistory()
    history.record("m1", "problem-1", "fw.bisection")

    result = await areflect("m1", "repro_still_fails", store=store, history=history)

    assert result.success is False
    assert result.confidence_after < result.confidence_before
    framework = await store.get("fw.bisection")
    assert framework.confidence == result.confidence_after


@pytest.mark.asyncio
async def test_testing_mutation_caught_increases_confidence():
    # Same ceiling issue as the Debugging case above: weaken first, then confirm
    # a success strengthens it back up.
    store = await build_seeded_store()
    history = MatchHistory()
    history.record("m1", "problem-1", "fw.boundary_value")
    history.record("m2", "problem-1", "fw.boundary_value")
    await areflect("m1", "no_improvement", store=store, history=history)

    result = await areflect("m2", "mutation_caught", store=store, history=history)

    assert result.success is True
    assert result.confidence_after > result.confidence_before


@pytest.mark.asyncio
async def test_testing_coverage_increased_counts_as_success():
    store = await build_seeded_store()
    history = MatchHistory()
    history.record("m1", "problem-1", "fw.equivalence_partitioning")

    result = await areflect("m1", "coverage_increased", store=store, history=history)

    assert result.success is True


@pytest.mark.asyncio
async def test_testing_no_improvement_decreases_confidence():
    store = await build_seeded_store()
    history = MatchHistory()
    history.record("m1", "problem-1", "fw.boundary_value")

    result = await areflect("m1", "no_improvement", store=store, history=history)

    assert result.success is False
    assert result.confidence_after < result.confidence_before


@pytest.mark.asyncio
async def test_debugging_outcome_rejected_for_testing_branch_match():
    store = await build_seeded_store()
    history = MatchHistory()
    history.record("m1", "problem-1", "fw.boundary_value")

    with pytest.raises(ValueError):
        await areflect("m1", "repro_now_passes", store=store, history=history)


@pytest.mark.asyncio
async def test_testing_outcome_rejected_for_debugging_branch_match():
    store = await build_seeded_store()
    history = MatchHistory()
    history.record("m1", "problem-1", "fw.bisection")

    with pytest.raises(ValueError):
        await areflect("m1", "mutation_caught", store=store, history=history)


@pytest.mark.asyncio
async def test_reflect_rejects_unrecognized_outcome_string():
    store = await build_seeded_store()
    history = MatchHistory()
    history.record("m1", "problem-1", "fw.bisection")

    with pytest.raises(ValueError):
        await areflect("m1", "vibes-are-good", store=store, history=history)


@pytest.mark.asyncio
async def test_reflect_rejects_unknown_match_id():
    store = await build_seeded_store()
    history = MatchHistory()

    with pytest.raises(ValueError):
        await areflect("no-such-match", "repro_now_passes", store=store, history=history)


@pytest.mark.asyncio
async def test_lagging_misfit_fires_on_three_distinct_frameworks_and_reports_tree_distance():
    store = await build_seeded_store()
    history = MatchHistory()
    history.record("m1", "problem-1", "fw.bisection")
    history.record("m2", "problem-1", "fw.differential")
    history.record("m3", "problem-1", "fw.trace")

    await areflect("m1", "repro_still_fails", store=store, history=history)
    await areflect("m2", "repro_still_fails", store=store, history=history)
    result = await areflect("m3", "repro_now_passes", store=store, history=history)

    assert result.misfit_detected is True
    # fw.bisection -> fw.debugging -> fw.trace: 2 edges
    assert result.tree_distance == 2


@pytest.mark.asyncio
async def test_lagging_misfit_does_not_fire_when_same_framework_is_retried():
    store = await build_seeded_store()
    history = MatchHistory()
    history.record("m1", "problem-1", "fw.bisection")
    history.record("m2", "problem-1", "fw.bisection")
    history.record("m3", "problem-1", "fw.bisection")

    await areflect("m1", "repro_still_fails", store=store, history=history)
    await areflect("m2", "repro_still_fails", store=store, history=history)
    result = await areflect("m3", "repro_now_passes", store=store, history=history)

    assert result.misfit_detected is False
    assert result.tree_distance is None


@pytest.mark.asyncio
async def test_lagging_misfit_does_not_fire_with_only_two_distinct_frameworks():
    store = await build_seeded_store()
    history = MatchHistory()
    history.record("m1", "problem-1", "fw.bisection")
    history.record("m2", "problem-1", "fw.differential")

    await areflect("m1", "repro_still_fails", store=store, history=history)
    result = await areflect("m2", "repro_now_passes", store=store, history=history)

    assert result.misfit_detected is False
    assert result.tree_distance is None


@pytest.mark.asyncio
async def test_lagging_misfit_is_scoped_per_problem_id():
    store = await build_seeded_store()
    history = MatchHistory()
    # Three distinct frameworks, but split across two unrelated problems —
    # neither problem alone hits the 3-distinct threshold.
    history.record("m1", "problem-1", "fw.bisection")
    history.record("m2", "problem-1", "fw.differential")
    history.record("m3", "problem-2", "fw.trace")

    await areflect("m1", "repro_still_fails", store=store, history=history)
    result = await areflect("m2", "repro_now_passes", store=store, history=history)

    assert result.misfit_detected is False


@pytest.mark.asyncio
async def test_cross_branch_tree_distance_when_the_wrong_branch_was_tried_first():
    store = await build_seeded_store()
    history = MatchHistory()
    history.record("m1", "problem-1", "fw.bisection")
    history.record("m2", "problem-1", "fw.cache_invalidation")
    history.record("m3", "problem-1", "fw.boundary_value")

    await areflect("m1", "repro_still_fails", store=store, history=history)
    await areflect("m2", "repro_still_fails", store=store, history=history)
    result = await areflect("m3", "mutation_caught", store=store, history=history)

    assert result.misfit_detected is True
    # fw.bisection -> fw.debugging -> [virtual root] -> fw.testing -> fw.boundary_value
    assert result.tree_distance == 4
