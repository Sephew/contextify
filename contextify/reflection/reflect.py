"""Reflection — the write-back seam. Stubbed in this slice (#3 is retrieve-only).

The seam exists now so the public API shape is stable; the real implementation
(ground-truth outcome check + Framework Store write-back, provisional->trusted
promotion, misfit signals) lands in a later slice.
"""

from __future__ import annotations

from ..models import ReflectionResult


def reflect(match_id: str, outcome: str, store=None) -> ReflectionResult:
    """Record whether an applied framework actually resolved the problem.

    Not implemented in this slice — retrieval is the #3 deliverable. Calling this
    raises so callers get an honest signal rather than a silent no-op.
    """
    raise NotImplementedError(
        "reflect() lands in a later slice; this slice delivers retrieve_framework(). "
        "The seam is defined so the public API is stable."
    )
