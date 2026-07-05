"""The hand-authored Debugging seed set (v1).

Per the PRD, the store starts from a small human-authored taxonomy (cold start),
not frameworks invented from nothing. This slice seeds the **Debugging** branch
only: one branch root plus four leaf frameworks.

Each leaf's ``applicability_condition`` is a checklist tested *structurally*
against a :class:`~contextify.models.ProblemAbstraction`. The checklist lines
deliberately embed the schema's own vocabulary (the enum values such as
``deterministic``, ``failing_test``, ``root_cause``) so a matcher can test the
abstraction against them token-for-token rather than by fuzzy similarity.
"""

from __future__ import annotations

from ..models import Branch, Framework, FrameworkStatus

# Branch root ---------------------------------------------------------------- #
DEBUGGING_ROOT = Framework(
    id="fw.debugging",
    name="Debugging",
    branch=Branch.DEBUGGING,
    parent=None,
    applicability_condition=["branch root: any software debugging problem"],
    status=FrameworkStatus.SEEDED,
)

# Leaf frameworks ------------------------------------------------------------ #
BISECTION = Framework(
    id="fw.bisection",
    name="Binary Search / Bisection",
    branch=Branch.DEBUGGING,
    parent="fw.debugging",
    applicability_condition=[
        "reproducibility: deterministic — the bug reproduces on essentially every run",
        "a previously working behavior regressed after some known change (regression)",
        "evidence: failing_test, or a known-good version exists to bisect against",
        "goal_shape: root_cause — isolate which change introduced the break",
    ],
    status=FrameworkStatus.SEEDED,
)

DIFFERENTIAL = Framework(
    id="fw.differential",
    name="Differential Diagnosis",
    branch=Branch.DEBUGGING,
    parent="fw.debugging",
    applicability_condition=[
        "reproducibility: intermittent or environment-specific behavior",
        "works in one environment but not another (works on my machine / prod-only)",
        "evidence: logs comparing a working case against a failing case",
        "goal_shape: root_cause — explain the difference between the two cases",
    ],
    status=FrameworkStatus.SEEDED,
)

CACHE_CHECKLIST = Framework(
    id="fw.cache_invalidation",
    name="Cache Invalidation Checklist",
    branch=Branch.DEBUGGING,
    parent="fw.debugging",
    applicability_condition=[
        "symptom: stale or inconsistent data — an old value is served after an update",
        "outdated content that only refreshes after a delay or manual reload",
        "evidence: report_only or logs of a value that failed to update",
        "goal_shape: fix — invalidate/propagate correctly so fresh data is served",
    ],
    status=FrameworkStatus.SEEDED,
)

TRACE_INSTRUMENTATION = Framework(
    id="fw.trace",
    name="Trace / Instrumentation",
    branch=Branch.DEBUGGING,
    parent="fw.debugging",
    applicability_condition=[
        "reproducibility: unreproduced — cannot reproduce reliably yet",
        "low evidence: report_only, with no stack_trace or failing_test in hand",
        "you need to add logging/tracing to narrow where the problem occurs",
        "goal_shape: root_cause — gather evidence before hypothesising a fix",
    ],
    status=FrameworkStatus.SEEDED,
)

DEBUGGING_FRAMEWORKS: list[Framework] = [
    DEBUGGING_ROOT,
    BISECTION,
    DIFFERENTIAL,
    CACHE_CHECKLIST,
    TRACE_INSTRUMENTATION,
]
