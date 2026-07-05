"""Seed Framework set for the Cognee retrieval-quality spike.

Small tree (3 Debugging + 3 Testing) matching the PRD's proposed v1 seed
size (.scratch/framework-retrieval-system/PRD.md). Each entry's `description`
doubles as the applicability_condition text that gets embedded/cognified —
this is what Cognee actually indexes and searches against.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Framework:
    id: str
    branch: str  # "debugging" | "testing"
    name: str
    description: str


FRAMEWORKS: list[Framework] = [
    Framework(
        id="binary_search_bisection",
        branch="debugging",
        name="Binary search bisection",
        description=(
            "Binary search bisection: use when a regression was introduced somewhere "
            "in a known, ordered range (commits, deploys, versions, input sizes) and you "
            "have a reproducible way to test any point in that range. Repeatedly halve "
            "the range between a known-good and known-bad point to isolate the exact "
            "change that introduced the regression. Requires deterministic reproduction "
            "and an enumerable sequence to bisect across."
        ),
    ),
    Framework(
        id="differential_diagnosis",
        branch="debugging",
        name="Differential diagnosis",
        description=(
            "Differential diagnosis: use when there are multiple plausible, unconfirmed "
            "causes for an observed symptom and no single reproducible trigger has been "
            "pinned down yet. Enumerate every plausible cause, then systematically gather "
            "evidence to rule each one out until the true cause remains. Borrowed from "
            "medical diagnostic reasoning. Best suited to intermittent or unexplained "
            "symptoms where the trigger isn't yet known."
        ),
    ),
    Framework(
        id="cache_invalidation_checklist",
        branch="debugging",
        name="Cache invalidation checklist",
        description=(
            "Cache invalidation checklist: use when the symptom is stale or out-of-date "
            "data being shown to users, and the problem self-corrects after a delay, a "
            "manual refresh, a restart, or a cache clear. Walk through the layers where "
            "stale data could be cached (CDN, application cache, browser cache, database "
            "read replica lag) and verify each layer's invalidation trigger fires "
            "correctly on write."
        ),
    ),
    Framework(
        id="boundary_value_analysis",
        branch="testing",
        name="Boundary value analysis",
        description=(
            "Boundary value analysis: use when testing a function or form that accepts a "
            "numeric or ordered range of input, to make sure the exact edges of that "
            "range are covered. Write tests for the minimum allowed value, the maximum "
            "allowed value, and the values just inside and just outside those limits "
            "(off-by-one cases). Focused on edge values of a single range, not on "
            "distinct categories of input."
        ),
    ),
    Framework(
        id="equivalence_partitioning",
        branch="testing",
        name="Equivalence partitioning",
        description=(
            "Equivalence partitioning: use when input can be split into distinct "
            "categories or classes that are each handled by different code paths (e.g. "
            "different account types, address types, or payment methods). Pick one "
            "representative test case per class instead of testing every possible value, "
            "since values within a class are assumed to behave the same way. Focused on "
            "input category coverage, not edge values."
        ),
    ),
    Framework(
        id="state_transition_testing",
        branch="testing",
        name="State transition testing",
        description=(
            "State transition testing: use when a bug or coverage gap depends on the "
            "order or sequence of actions/events, not just individual input values. Model "
            "the system as states and transitions, then write tests for specific "
            "sequences of actions (especially ones a user is unlikely to try but that are "
            "technically reachable) to catch order-dependent and sequence-dependent "
            "defects."
        ),
    ),
]
