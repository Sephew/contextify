"""Framework Store package: the persistent, structured library of frameworks."""

from __future__ import annotations

from .seed import DEBUGGING_FRAMEWORKS
from .store import (
    CogneeFrameworkStore,
    FrameworkStore,
    InMemoryGraphStore,
)


async def build_seeded_store(store: FrameworkStore | None = None) -> FrameworkStore:
    """Return a store seeded with the Debugging branch. Defaults to in-memory."""
    store = store if store is not None else InMemoryGraphStore()
    await store.seed(DEBUGGING_FRAMEWORKS)
    return store


__all__ = [
    "FrameworkStore",
    "InMemoryGraphStore",
    "CogneeFrameworkStore",
    "DEBUGGING_FRAMEWORKS",
    "build_seeded_store",
]
