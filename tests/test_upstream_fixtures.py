"""Debugging-relevant cases from Slice 01's fixture set, ported.

Issue 02 acceptance criterion: "At least the Debugging-relevant cases from
Slice 01's fixture set pass as automated tests." Slice 01's fixture set is
``spikes/cognee-retrieval-quality/fixtures.py`` (20 cases spanning Debugging +
Testing); this ports its 12 Debugging-branch cases and runs each raw_text
through this package's actual retrieve_framework() seam (not Cognee vector
search, which is how the spike itself measured retrieval — this slice's
mechanism is a single LLM call over the whole tree, per the PRD).

correct_framework values in the spike use flat snake_case ids
(binary_search_bisection, differential_diagnosis, cache_invalidation_checklist)
that don't exist in this package's tree (contextify/framework_store/seed.py
uses fw.bisection / fw.differential / fw.cache_invalidation); _ID_MAP bridges
the two naming schemes rather than renaming either side.
"""

from __future__ import annotations

import pytest

from contextify.framework_store import build_seeded_store
from contextify.llm import MockLLMClient
from contextify.problem_abstraction import abstract
from contextify.retrieval import resolve

_ID_MAP = {
    "binary_search_bisection": "fw.bisection",
    "differential_diagnosis": "fw.differential",
    "cache_invalidation_checklist": "fw.cache_invalidation",
}

# The 12 Debugging-branch cases from spikes/cognee-retrieval-quality/fixtures.py
# (ff1-a/b, ff2-a/b, ff5-a/b, dt1-a/b, dt2-a/b, dt3-a/b). Testing-branch cases
# (ff3/ff4/dt4/dt5) are out of scope for this Debugging-only slice.
UPSTREAM_DEBUGGING_CASES = [
    {
        "id": "ff1-a",
        "raw_text": (
            "The checkout page started throwing a 500 error sometime this week; it was "
            "working fine two weeks ago and I have a list of every deploy in between."
        ),
        "correct_framework": "binary_search_bisection",
    },
    {
        "id": "ff1-b",
        "raw_text": (
            "The checkout page throws a 500 error for some users but not others, on the "
            "same build, and there's no obvious pattern to who's affected."
        ),
        "correct_framework": "differential_diagnosis",
    },
    {
        "id": "ff2-a",
        "raw_text": (
            "After I edit an article, the public page still shows the old text for a "
            "couple minutes, then it updates on its own."
        ),
        "correct_framework": "cache_invalidation_checklist",
    },
    {
        "id": "ff2-b",
        "raw_text": (
            "After a recent deploy, editing an article no longer updates the public page "
            "at all — it used to update instantly last sprint."
        ),
        "correct_framework": "binary_search_bisection",
    },
    {
        "id": "ff5-a",
        "raw_text": (
            "The nightly ETL job silently drops rows sometimes; could be the source DB "
            "timeout, a malformed record, or the downstream write failing quietly — we "
            "don't know which."
        ),
        "correct_framework": "differential_diagnosis",
    },
    {
        "id": "ff5-b",
        "raw_text": (
            "The nightly ETL job's dashboard shows yesterday's numbers even after a "
            "successful run, until someone manually clears the reporting cache."
        ),
        "correct_framework": "cache_invalidation_checklist",
    },
    {
        "id": "dt1-a",
        "raw_text": (
            "Our CI test suite went from 2 minutes to 12 minutes sometime in the last 40 "
            "commits; I can check out any commit to time it."
        ),
        "correct_framework": "binary_search_bisection",
    },
    {
        "id": "dt1-b",
        "raw_text": (
            "The mobile app's cold-start time doubled somewhere between v3.2 and v3.5; "
            "we kept every intermediate release build."
        ),
        "correct_framework": "binary_search_bisection",
    },
    {
        "id": "dt2-a",
        "raw_text": (
            "Random customers report the app logging them out mid-session; could be "
            "token expiry, a load-balancer sticky-session issue, or a race condition on "
            "refresh — no clear pattern yet."
        ),
        "correct_framework": "differential_diagnosis",
    },
    {
        "id": "dt2-b",
        "raw_text": (
            "Some PDF exports come out with garbled fonts; might be a font-embedding "
            "bug, a locale-specific encoding issue, or a corrupted template file — not "
            "sure which."
        ),
        "correct_framework": "differential_diagnosis",
    },
    {
        "id": "dt3-a",
        "raw_text": (
            "The homepage banner still shows last month's promo even after marketing "
            "updated it in the CMS, but it corrects itself overnight."
        ),
        "correct_framework": "cache_invalidation_checklist",
    },
    {
        "id": "dt3-b",
        "raw_text": (
            "A user's shopping cart total is wrong right after they remove an item, but "
            "it's correct again if they log out and back in."
        ),
        "correct_framework": "cache_invalidation_checklist",
    },
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case", UPSTREAM_DEBUGGING_CASES, ids=[c["id"] for c in UPSTREAM_DEBUGGING_CASES]
)
async def test_upstream_debugging_fixture_resolves_correctly(case):
    llm = MockLLMClient()
    store = await build_seeded_store()
    tree = await store.read_tree()

    abstraction = abstract(case["raw_text"], llm)
    match = resolve(abstraction, tree, llm)

    expected_id = _ID_MAP[case["correct_framework"]]
    assert match.framework.id == expected_id, (
        f"case {case['id']!r}: expected {case['correct_framework']!r} "
        f"({expected_id!r}), got {match.framework.id!r} "
        f"(rationale: {match.rationale})"
    )
