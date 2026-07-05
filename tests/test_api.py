import pytest

from contextify import retrieve_framework
from contextify.models import Branch

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


def test_reflect_seam_is_stubbed_not_silently_passing():
    from contextify import reflect

    with pytest.raises(NotImplementedError):
        reflect("some-match-id", "fixed")
