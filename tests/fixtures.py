"""Adversarial Debugging fixtures: false friends + disguised twins.

Per PRD user story 21: false friends are lexically similar but need different
frameworks; disguised twins are lexically different but need the same one. This
isolates whether retrieval is doing structural matching or just keyword echo.

Each case maps a raw problem description to the framework id it *should* land on
(see contextify/framework_store/seed.py for the four Debugging leaves).
"""

from __future__ import annotations

DEBUGGING_CASES: list[dict] = [
    # --- Bisection: deterministic regression, has a failing test / known-good rev
    {
        "id": "bisect-1",
        "raw_text": (
            "Every single run of the test suite fails the same way since we merged "
            "the dependency bump last night. It used to pass 100% of the time. "
            "There's a failing unit test that reproduces it. I want to find which "
            "commit introduced the regression."
        ),
        "expected": "fw.bisection",
    },
    {
        # disguised twin of bisect-1: different wording, same underlying shape
        "id": "bisect-2-twin",
        "raw_text": (
            "Something we shipped in yesterday's release broke checkout completely "
            "and consistently — it never succeeds now. A CI test catches it every "
            "time. I need to pin down exactly which change caused this."
        ),
        "expected": "fw.bisection",
    },
    # --- Differential diagnosis: intermittent / environment-specific
    {
        "id": "diff-1",
        "raw_text": (
            "This only breaks in the staging environment; it works fine locally. "
            "It's not consistent even in staging — sometimes it goes through. I have "
            "logs from both a passing and a failing attempt and want to know why "
            "they differ."
        ),
        "expected": "fw.differential",
    },
    {
        # false friend of bisect-1: also mentions 'consistently' but is env-specific,
        # not a regression from a known change — should NOT match bisection
        "id": "diff-2-false-friend",
        "raw_text": (
            "On the customer's environment this fails consistently, but on every "
            "other environment we've tried it works fine every time — it's an "
            "environment-specific difference, not a code regression, since nothing "
            "changed in our code recently. I have logs comparing the two "
            "environments and want to understand the difference."
        ),
        "expected": "fw.differential",
    },
    # --- Cache invalidation: stale data symptom
    {
        "id": "cache-1",
        "raw_text": (
            "Users report that after they update their billing address, the invoice "
            "PDF still shows the old address for a while before eventually catching "
            "up. Refreshing the page doesn't help immediately. I just need this "
            "fixed so fresh data shows up."
        ),
        "expected": "fw.cache_invalidation",
    },
    {
        # disguised twin of cache-1
        "id": "cache-2-twin",
        "raw_text": (
            "A customer says the dashboard total is out of date right after they "
            "make a change — it only updates itself some time later on its own. "
            "No error, no crash, just an old value being served. Need it to "
            "propagate correctly."
        ),
        "expected": "fw.cache_invalidation",
    },
    # --- Trace/instrumentation: unreproduced, low evidence
    {
        "id": "trace-1",
        "raw_text": (
            "A user reported that the app crashed once but we've never been able to "
            "reproduce it ourselves. There's no stack trace, no failing test, just "
            "their report. We need to add logging to figure out where this is "
            "even happening before we can guess at a fix."
        ),
        "expected": "fw.trace",
    },
    {
        # false friend of trace-1: mentions 'crash' and 'report' like trace-1, but
        # is actually deterministic + has a failing test -> should be bisection
        "id": "trace-2-false-friend",
        "raw_text": (
            "Support reported a crash, and it turns out it happens every single "
            "time you hit the endpoint after our latest deploy — a new failing test "
            "reproduces it reliably. I want to know which change broke it."
        ),
        "expected": "fw.bisection",
    },
]
