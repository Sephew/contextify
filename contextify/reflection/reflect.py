"""Reflection — the write-back seam.

``reflect(match_id, outcome)`` checks a real-world outcome against a prior
``retrieve_framework()`` match and writes it back into the Framework Store: the
matched Framework's confidence strengthens on success and weakens on failure
(a hand-rolled stand-in for Cognee's Memify layer — see
``framework_store/store.py``'s module docstring for why Memify itself isn't
wired up yet).

Ground truth is branch-specific (PRD "Reflection ground truth"):
- Debugging: did the previously-failing reproduction case start passing?
- Testing: did the generated tests catch a seeded mutation, or increase
  coverage of a previously-uncovered branch?
A Debugging outcome applied to a Testing-branch match (or vice versa) is a
caller bug, not a valid reflection — rejected rather than silently coerced
into a generic success/failure bit.

Lagging misfit (PRD user story 11): 3+ *distinct* Frameworks tried for the
same problem is a fit problem; retrying the same Framework repeatedly is an
execution problem, not a misfit signal. This is only checked once an outcome
*succeeds*, since "the Framework that eventually succeeded" is undefined
until then. Tree distance from the first-tried Framework to the one that
worked is logged as severity (PRD user story 12).

"Same problem" is deliberately an explicit ``problem_id`` the caller threads
across retries (see ``api.aretrieve_framework``), not inferred from text or
abstraction similarity — that similarity-based grouping is Slice 5's job
(path caching keyed on abstracted-schema similarity), a distinct concern
deferred on purpose.
"""

from __future__ import annotations

from ..framework_store.store import FrameworkStore
from ..models import Branch, ReflectionOutcome, ReflectionResult
from .history import MatchHistory
from .tree_distance import tree_distance

_DEBUGGING_OUTCOMES = {
    ReflectionOutcome.REPRO_NOW_PASSES,
    ReflectionOutcome.REPRO_STILL_FAILS,
}
_TESTING_OUTCOMES = {
    ReflectionOutcome.MUTATION_CAUGHT,
    ReflectionOutcome.COVERAGE_INCREASED,
    ReflectionOutcome.NO_IMPROVEMENT,
}
_SUCCESS_OUTCOMES = {
    ReflectionOutcome.REPRO_NOW_PASSES,
    ReflectionOutcome.MUTATION_CAUGHT,
    ReflectionOutcome.COVERAGE_INCREASED,
}

_CONFIDENCE_STEP_UP = 0.1
_CONFIDENCE_STEP_DOWN = 0.15
_CONFIDENCE_MIN = 0.1
_CONFIDENCE_MAX = 1.0
_LAGGING_MISFIT_THRESHOLD = 3


async def reflect(
    match_id: str,
    outcome: str,
    store: FrameworkStore,
    history: MatchHistory,
) -> ReflectionResult:
    """Record whether an applied framework actually resolved the problem."""
    record = history.get(match_id)
    if record is None:
        raise ValueError(
            f"unknown match_id {match_id!r}; nothing was retrieved with that id "
            "(reflect() needs the same MatchHistory the matching retrieve_framework "
            "call used)"
        )

    framework = await store.get(record.framework_id)
    if framework is None:
        raise ValueError(
            f"match_id {match_id!r} points at unknown framework "
            f"{record.framework_id!r} (reflect() needs the same FrameworkStore the "
            "matching retrieve_framework call used)"
        )

    try:
        parsed_outcome = ReflectionOutcome(outcome)
    except ValueError as exc:
        raise ValueError(
            f"unrecognized outcome {outcome!r}; expected one of "
            f"{[o.value for o in ReflectionOutcome]}"
        ) from exc

    expected_outcomes = (
        _DEBUGGING_OUTCOMES if framework.branch == Branch.DEBUGGING else _TESTING_OUTCOMES
    )
    if parsed_outcome not in expected_outcomes:
        raise ValueError(
            f"outcome {parsed_outcome.value!r} is not valid for a "
            f"{framework.branch.value}-branch framework ({framework.name!r}); "
            f"expected one of {sorted(o.value for o in expected_outcomes)}"
        )

    success = parsed_outcome in _SUCCESS_OUTCOMES
    confidence_before = framework.confidence
    confidence_after = (
        min(_CONFIDENCE_MAX, confidence_before + _CONFIDENCE_STEP_UP)
        if success
        else max(_CONFIDENCE_MIN, confidence_before - _CONFIDENCE_STEP_DOWN)
    )
    await store.set_confidence(framework.id, confidence_after)

    misfit_detected = False
    distance: int | None = None
    if success:
        tried = history.framework_ids_tried(record.problem_id)
        if len(tried) >= _LAGGING_MISFIT_THRESHOLD:
            misfit_detected = True
            tree = await store.read_tree()
            distance = tree_distance(tree, tried[0], framework.id)

    note = (
        f"{framework.name}'s assumption held ({parsed_outcome.value})"
        if success
        else f"{framework.name}'s assumption didn't hold ({parsed_outcome.value})"
    )

    return ReflectionResult(
        match_id=match_id,
        outcome=outcome,
        store_changed=True,
        note=note,
        success=success,
        confidence_before=confidence_before,
        confidence_after=confidence_after,
        misfit_detected=misfit_detected,
        tree_distance=distance,
    )
