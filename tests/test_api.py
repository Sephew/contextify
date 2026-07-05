import pytest

from contextify import retrieve_framework
from contextify.models import Branch

from .fixtures import DEBUGGING_CASES


def test_retrieve_framework_end_to_end_with_default_mock_client():
    case = DEBUGGING_CASES[0]
    match = retrieve_framework(case["raw_text"])
    assert match.framework.id == case["expected"]
    assert match.branch == Branch.DEBUGGING


def test_retrieve_framework_rejects_empty_input():
    with pytest.raises(ValueError):
        retrieve_framework("   ")


def test_reflect_seam_is_stubbed_not_silently_passing():
    from contextify import reflect

    with pytest.raises(NotImplementedError):
        reflect("some-match-id", "fixed")
