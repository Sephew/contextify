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
        "reproducibility: intermittent, or multiple plausible unconfirmed causes with "
        "no single trigger pinned down yet (e.g. 'could be X, Y, or Z', 'no discernible "
        "pattern yet', 'not sure which')",
        "works in one environment but not another, or affects some users/machines but "
        "not others on the same build (works on my machine / prod-only)",
        "the symptom is a working case versus a failing case that otherwise look "
        "alike, and the goal is explaining why they differ",
        "evidence: logs comparing a working case against a failing case",
        "goal_shape: root_cause — rule out candidate causes to find which one is real",
    ],
    status=FrameworkStatus.SEEDED,
)

CACHE_CHECKLIST = Framework(
    id="fw.cache_invalidation",
    name="Cache Invalidation Checklist",
    branch=Branch.DEBUGGING,
    parent="fw.debugging",
    applicability_condition=[
        "symptom: stale, outdated, or old data/content is shown right after a write or "
        "update — the value was correct before the change and wrong immediately after",
        "the problem self-corrects on its own without further code changes: after a "
        "delay, a manual refresh/reload, a cache clear, a restart, or logging out and "
        "back in — the SAME data becomes fresh again with no fix applied, which is the "
        "signature that rules out a real logic bug (a broken calculation would still "
        "be wrong after a refresh/relogin)",
        "evidence: report_only or logs of a value that failed to update immediately",
        "goal_shape: fix — invalidate/propagate correctly so fresh data is served "
        "immediately, without needing a delay/refresh/relogin workaround",
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
