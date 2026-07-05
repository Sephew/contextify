"""Framework Store — the persistent library retrieval reads from.

The store sits *outside* the input->output line (per the design doc): retrieval
reads the tree, reflection (later) writes back. That independent read/write is
what lets the system accumulate judgment instead of being a fancy prompt.

Two implementations behind one interface:

- :class:`InMemoryGraphStore` — a real parent/child graph held in memory. The
  working default for this slice.
- :class:`CogneeFrameworkStore` — a faithful adapter over Cognee's graph engine
  (the API verified against cognee 1.2.2). It is **not** the default: cognee's
  bundled embedded backend (Ladybug/Kuzu) ships a broken ``add_node`` query on
  this platform, so it stays behind the interface until Cognee is pointed at a
  working graph backend (e.g. Neo4j) or the upstream bug is fixed. Swapping is a
  one-line change at the call site — nothing else in the system knows the
  difference.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from ..models import Branch, Framework, FrameworkStatus


class FrameworkStore(ABC):
    """The contract retrieval depends on. Deliberately tiny."""

    @abstractmethod
    async def seed(self, frameworks: list[Framework]) -> None:
        """Insert framework nodes and their parent/child edges (idempotent)."""

    @abstractmethod
    async def read_tree(self) -> list[Framework]:
        """Return every node. Retrieval feeds the whole (small) tree to one call."""

    @abstractmethod
    async def get(self, framework_id: str) -> Framework | None:
        """Look up a single node by id."""


class InMemoryGraphStore(FrameworkStore):
    """A real graph (nodes + parent/child adjacency), no external backend needed."""

    def __init__(self) -> None:
        self._nodes: dict[str, Framework] = {}
        self._children: dict[str | None, list[str]] = {}

    async def seed(self, frameworks: list[Framework]) -> None:
        for f in frameworks:
            self._nodes[f.id] = f
            self._children.setdefault(f.id, [])
            siblings = self._children.setdefault(f.parent, [])
            if f.id not in siblings:
                siblings.append(f.id)

    async def read_tree(self) -> list[Framework]:
        return list(self._nodes.values())

    async def get(self, framework_id: str) -> Framework | None:
        return self._nodes.get(framework_id)

    async def children_of(self, framework_id: str | None) -> list[Framework]:
        return [self._nodes[c] for c in self._children.get(framework_id, [])]

    async def roots(self) -> list[Framework]:
        return [f for f in self._nodes.values() if f.parent is None]


# Stable namespace so a slug always maps to the same Cognee node UUID.
_SLUG_NAMESPACE = uuid.UUID("6f4b8d2e-1c3a-4e5f-9a7b-0c1d2e3f4a5b")


class CogneeFrameworkStore(FrameworkStore):
    """Cognee graph-engine adapter. See module docstring for why it isn't default.

    Cognee nodes are ``DataPoint`` objects keyed by UUID; our framework ids are
    slugs, so we map ``slug -> uuid5(namespace, slug)`` deterministically and keep
    the slug as a node property to rebuild :class:`Framework` on read.
    """

    def __init__(self) -> None:
        self._engine = None

    async def _get_engine(self):
        if self._engine is None:
            from cognee.infrastructure.databases.graph import get_graph_engine

            self._engine = await get_graph_engine()
        return self._engine

    @staticmethod
    def _uuid(slug: str) -> uuid.UUID:
        return uuid.uuid5(_SLUG_NAMESPACE, slug)

    async def seed(self, frameworks: list[Framework]) -> None:
        from cognee.low_level import DataPoint

        class _FrameworkNode(DataPoint):
            slug: str
            name: str
            branch: str
            parent_slug: str
            applicability: list[str]
            status: str
            confidence: float
            metadata: dict = {"index_fields": ["name"]}

        engine = await self._get_engine()
        for f in frameworks:
            await engine.add_node(
                _FrameworkNode(
                    id=self._uuid(f.id),
                    slug=f.id,
                    name=f.name,
                    branch=f.branch.value,
                    parent_slug=f.parent or "",
                    applicability=list(f.applicability_condition),
                    status=f.status.value,
                    confidence=f.confidence,
                )
            )
        for f in frameworks:
            if f.parent:
                await engine.add_edge(
                    str(self._uuid(f.parent)), str(self._uuid(f.id)), "has_child"
                )

    async def read_tree(self) -> list[Framework]:
        engine = await self._get_engine()
        nodes, _edges = await engine.get_graph_data()
        tree: list[Framework] = []
        for _node_id, props in nodes:
            # Custom fields may live at the top level or under a "properties" bag,
            # depending on adapter — check both.
            data = {**props, **props.get("properties", {})}
            if "slug" not in data:
                continue
            tree.append(
                Framework(
                    id=data["slug"],
                    name=data["name"],
                    branch=Branch(data["branch"]),
                    parent=data.get("parent_slug") or None,
                    applicability_condition=list(data.get("applicability", [])),
                    status=FrameworkStatus(data.get("status", "seeded")),
                    confidence=float(data.get("confidence", 1.0)),
                )
            )
        return tree

    async def get(self, framework_id: str) -> Framework | None:
        for f in await self.read_tree():
            if f.id == framework_id:
                return f
        return None
