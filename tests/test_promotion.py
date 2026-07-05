"""Human-in-the-loop promotion gate (Slice 4): provisional entry, weighted
retrieval, auto-promotion at N=3 validated successes, and explicit sign-off.
"""

from __future__ import annotations

import pytest

from contextify import areflect
from contextify.framework_store import (
    PROMOTED_CONFIDENCE_FLOOR,
    PROVISIONAL_DEFAULT_CONFIDENCE,
    build_seeded_store,
    new_provisional_framework,
    promote_framework,
)
from contextify.models import (
    Branch,
    Framework,
    FrameworkStatus,
    GoalShape,
    ProblemAbstraction,
    Reproducibility,
)
from contextify.reflection import MatchHistory
from contextify.retrieval import resolve


def _make_provisional() -> Framework:
    return new_provisional_framework(
        id="fw.provisional_probe",
        name="Provisional Probe",
        branch=Branch.DEBUGGING,
        parent="fw.debugging",
        applicability_condition=["reproducibility: deterministic"],
    )


@pytest.mark.asyncio
async def test_new_framework_enters_provisional_with_lowered_confidence():
    store = await build_seeded_store()
    await store.seed([_make_provisional()])

    framework = await store.get("fw.provisional_probe")

    assert framework.status == FrameworkStatus.PROVISIONAL
    assert framework.confidence == PROVISIONAL_DEFAULT_CONFIDENCE
    assert framework.confidence < 1.0  # below a hand-seeded Framework's baseline


@pytest.mark.asyncio
async def test_provisional_framework_is_eligible_for_retrieval_but_weighted_lower():
    store = await build_seeded_store()
    await store.seed([_make_provisional()])
    tree = await store.read_tree()

    abstraction = ProblemAbstraction(
        symptom="whatever",
        reproducibility=Reproducibility.DETERMINISTIC,
        evidence_available=[],
        goal_shape=GoalShape.ROOT_CAUSE,
    )

    class _StubLLM:
        def resolve_framework(self, abstraction, tree):
            from contextify.llm import LLMRetrievalDecision

            return LLMRetrievalDecision(
                chosen_id="fw.provisional_probe",
                path=["Debugging", "Provisional Probe"],
                confidence=0.9,
                rationale="stub",
            )

    match = resolve(abstraction, tree, _StubLLM())

    assert match.framework.id == "fw.provisional_probe"  # selectable, not excluded
    assert match.confidence == pytest.approx(0.9 * PROVISIONAL_DEFAULT_CONFIDENCE)
    assert match.confidence < 0.9  # reads less confident than a trusted match would


@pytest.mark.asyncio
async def test_three_validated_successes_auto_promote():
    store = await build_seeded_store()
    await store.seed([_make_provisional()])
    history = MatchHistory()
    history.record("m1", "problem-1", "fw.provisional_probe")
    history.record("m2", "problem-1", "fw.provisional_probe")
    history.record("m3", "problem-1", "fw.provisional_probe")

    r1 = await areflect("m1", "repro_now_passes", store=store, history=history)
    r2 = await areflect("m2", "repro_now_passes", store=store, history=history)
    assert r1.promoted is False
    assert r2.promoted is False

    r3 = await areflect("m3", "repro_now_passes", store=store, history=history)

    assert r3.promoted is True
    framework = await store.get("fw.provisional_probe")
    assert framework.status == FrameworkStatus.SEEDED
    assert framework.confidence >= PROMOTED_CONFIDENCE_FLOOR


@pytest.mark.asyncio
async def test_human_signoff_promotes_regardless_of_reflection_count():
    store = await build_seeded_store()
    await store.seed([_make_provisional()])

    promoted = await promote_framework(store, "fw.provisional_probe")

    assert promoted.status == FrameworkStatus.SEEDED
    assert promoted.confidence >= PROMOTED_CONFIDENCE_FLOOR
    framework = await store.get("fw.provisional_probe")
    assert framework.status == FrameworkStatus.SEEDED


@pytest.mark.asyncio
async def test_failing_reflections_do_not_accumulate_toward_promotion():
    store = await build_seeded_store()
    await store.seed([_make_provisional()])
    history = MatchHistory()
    history.record("m1", "problem-1", "fw.provisional_probe")
    history.record("m2", "problem-1", "fw.provisional_probe")
    history.record("m3", "problem-1", "fw.provisional_probe")

    await areflect("m1", "repro_still_fails", store=store, history=history)
    await areflect("m2", "repro_still_fails", store=store, history=history)
    result = await areflect("m3", "repro_still_fails", store=store, history=history)

    assert result.promoted is False
    framework = await store.get("fw.provisional_probe")
    assert framework.status == FrameworkStatus.PROVISIONAL
    assert framework.validated_successes == 0
