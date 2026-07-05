"""Framework Store package: the persistent, structured library of frameworks."""

from __future__ import annotations

from .promotion import (
    PROMOTED_CONFIDENCE_FLOOR,
    PROMOTION_THRESHOLD,
    PROVISIONAL_DEFAULT_CONFIDENCE,
    new_provisional_framework,
    promote_framework,
)
from .seed import ALL_FRAMEWORKS, DEBUGGING_FRAMEWORKS, TESTING_FRAMEWORKS
from .store import (
    CogneeDocumentStore,
    CogneeFrameworkStore,
    FrameworkStore,
    InMemoryGraphStore,
)


async def build_seeded_store(store: FrameworkStore | None = None) -> FrameworkStore:
    """Return a store seeded with both branches. Defaults to in-memory."""
    store = store if store is not None else InMemoryGraphStore()
    await store.seed(ALL_FRAMEWORKS)
    return store


__all__ = [
    "FrameworkStore",
    "InMemoryGraphStore",
    "CogneeFrameworkStore",
    "CogneeDocumentStore",
    "DEBUGGING_FRAMEWORKS",
    "TESTING_FRAMEWORKS",
    "ALL_FRAMEWORKS",
    "build_seeded_store",
    "new_provisional_framework",
    "promote_framework",
    "PROVISIONAL_DEFAULT_CONFIDENCE",
    "PROMOTED_CONFIDENCE_FLOOR",
    "PROMOTION_THRESHOLD",
]
