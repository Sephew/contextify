import asyncio

import pytest

from contextify import reflect, retrieve_framework
from contextify.framework_store import build_seeded_store
from contextify.models import Branch
from contextify.reflection import MatchHistory

from .fixtures import DEBUGGING_CASES


def test_retrieve_framework_end_to_end_with_default_mock_client():
    case = DEBUGGING_CASES[0]
    match = retrieve_framework(case["raw_text"])
    assert match.framework.id == case["expected"]
    assert match.branch == Branch.DEBUGGING


def test_retrieve_framework_picks_testing_branch_for_testing_goal_problem():
    raw_text = (
        "We want to make sure the discount calculator handles cart totals of "
        "exactly $0, exactly the max allowed $10,000, and one cent over the max."
    )
    match = retrieve_framework(raw_text)
    assert match.framework.id == "fw.boundary_value"
    assert match.branch == Branch.TESTING


def test_retrieve_framework_rejects_empty_input():
    with pytest.raises(ValueError):
        retrieve_framework("   ")


def test_reflect_rejects_unknown_match_id():
    with pytest.raises(ValueError):
        reflect("some-match-id", "fixed", store=asyncio.run(build_seeded_store()), history=MatchHistory())


def test_reflect_round_trips_a_real_retrieve_framework_match():
    store = asyncio.run(build_seeded_store())
    history = MatchHistory()
    case = DEBUGGING_CASES[0]

    match = retrieve_framework(case["raw_text"], store=store, history=history)
    result = reflect(match.match_id, "repro_now_passes", store=store, history=history)

    # Seeded frameworks start at confidence 1.0 (the ceiling); a lone success
    # has no headroom to rise, but the store must still reflect the outcome.
    assert result.success is True
    assert result.confidence_after == result.confidence_before == 1.0
