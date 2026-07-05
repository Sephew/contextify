"""Human-in-the-loop promotion gate (PRD user stories 13-14).

New Frameworks enter the store ``provisional`` and under-weighted relative to
hand-seeded ones — a single improvised success shouldn't silently reshape all
future retrieval. A provisional Framework earns trusted (``seeded``) status
one of two ways:

- automatically, once ``PROMOTION_THRESHOLD`` validated successful
  ``reflect()`` calls land against it (checked from
  ``contextify.reflection.reflect``), or
- immediately, via an explicit human sign-off calling :func:`promote_framework`
  directly — the gate sits at promotion-to-trusted-store, not at the act of
  trying a novel Framework once.
"""

from __future__ import annotations

from dataclasses import replace

from ..models import Branch, Framework, FrameworkStatus
from .store import FrameworkStore

# Below the 1.0 hand-seeded baseline: provisional Frameworks are still eligible
# for retrieval (nothing filters them out of the tree), just weighted lower —
# resolve() multiplies match confidence by the chosen Framework's own
# confidence, so a provisional pick reads as less confident even at an
# otherwise-perfect structural match.
PROVISIONAL_DEFAULT_CONFIDENCE = 0.5

# Promotion sets confidence to at least this floor — trusted, but starting a
# notch below a hand-seeded Framework's 1.0 until it earns more reflections.
PROMOTED_CONFIDENCE_FLOOR = 0.7

# Validated successful reflect() calls required for auto-promotion.
PROMOTION_THRESHOLD = 3


def new_provisional_framework(
    id: str,
    name: str,
    branch: Branch,
    parent: str,
    applicability_condition: list[str] | None = None,
) -> Framework:
    """Construct a new Framework in provisional status at the gate's starting
    weight, ready to be inserted via ``store.seed([...])``."""
    return Framework(
        id=id,
        name=name,
        branch=branch,
        parent=parent,
        applicability_condition=list(applicability_condition or []),
        status=FrameworkStatus.PROVISIONAL,
        confidence=PROVISIONAL_DEFAULT_CONFIDENCE,
    )


async def promote_framework(store: FrameworkStore, framework_id: str) -> Framework:
    """Promote a Framework to trusted/seeded status and weight.

    Idempotent and unconditional — this is the explicit-human-sign-off path
    (PRD: "promoted ... regardless of reflection count"), as well as what
    auto-promotion calls once the reflection threshold is met.
    """
    framework = await store.get(framework_id)
    if framework is None:
        raise ValueError(f"unknown framework id {framework_id!r}")

    new_confidence = max(framework.confidence, PROMOTED_CONFIDENCE_FLOOR)
    await store.set_status(framework_id, FrameworkStatus.SEEDED)
    await store.set_confidence(framework_id, new_confidence)

    return replace(framework, status=FrameworkStatus.SEEDED, confidence=new_confidence)
