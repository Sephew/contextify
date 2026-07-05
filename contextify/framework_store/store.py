"""Framework Store — the persistent library retrieval reads from.

The store sits *outside* the input->output line (per the design doc): retrieval
reads the tree, reflection (later) writes back. That independent read/write is
what lets the system accumulate judgment instead of being a fancy prompt.

Three implementations behind one interface:

- :class:`InMemoryGraphStore` — a real parent/child graph held in memory. The
  working default for this slice: no external dependency, fully offline.
- :class:`CogneeFrameworkStore` — a direct adapter over Cognee's low-level graph
  engine (``add_node``/``add_edge``, API verified against cognee 1.2.2). **Not
  usable on this platform**: cognee's bundled embedded backend (Ladybug/Kuzu)
  emits a query (``MERGE ... SET n += {map}``) its own parser rejects, so
  ``add_node`` fails outright here. Kept behind the interface for when Cognee
  ships a working embedded backend or points at an external one (Neo4j, etc).
- :class:`CogneeDocumentStore` — a *working* Cognee-backed alternative,
  verified empirically on this machine via OpenRouter. Rather than the broken
  low-level graph API, it drives Cognee's own ingestion pipeline
  (``cognee.add`` + ``cognee.cognify``), which internally batches its graph
  writes through a different path that does not hit the same bug. Each
  Framework is stored as one JSON-serialized document tagged with
  ``node_set=[framework.id]``; ``read_tree()`` reads it back via
  ``cognee.search(SearchType.CHUNKS)``. This is the mechanism the upstream
  Cognee spike (``spikes/cognee-retrieval-quality/VERDICT.md``) validated with
  a 100% top-3 / 85% top-1 result — confirming Cognee's embedding space does
  handle this system's structural-similarity needs, given a good abstraction.
  Requires ``OPENROUTER_API_KEY`` (real network + LLM + embedding calls); not
  used by the default offline test suite for that reason.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from abc import ABC, abstractmethod

from ..llm import DEFAULT_MODEL
from ..models import Branch, Framework, FrameworkStatus


class FrameworkStore(ABC):
    """The contract retrieval depends on. Deliberately tiny."""

    @abstractmethod
    async def seed(self, frameworks: list[Framework]) -> None:
        """Insert framework nodes and their parent/child edges (idempotent)."""

    @abstractmethod
    async def read_tree(self) -> list[Framework]:
        """Return every node. Retrieval feeds the whole (small) tree to one call."""

    async def get(self, framework_id: str) -> Framework | None:
        """Look up a single node by id. Default: linear scan over read_tree();
        override for a faster path (see InMemoryGraphStore's dict lookup)."""
        for f in await self.read_tree():
            if f.id == framework_id:
                return f
        return None

    async def set_confidence(self, framework_id: str, confidence: float) -> None:
        """Update a Framework node's confidence weight in place (reflect()'s
        write-back). Default: unsupported; override where the backend can
        actually mutate node state (see InMemoryGraphStore)."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support confidence write-back"
        )

    async def set_status(self, framework_id: str, status: FrameworkStatus) -> None:
        """Update a Framework node's status in place (promotion write-back).
        Default: unsupported; override where the backend can actually mutate
        node state (see InMemoryGraphStore)."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support status write-back"
        )

    async def increment_validated_successes(self, framework_id: str) -> int:
        """Bump a provisional Framework's validated-success counter and return
        the new count (promotion's auto-trigger). Default: unsupported;
        override where the backend can actually mutate node state (see
        InMemoryGraphStore)."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support validated-success tracking"
        )


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

    async def set_confidence(self, framework_id: str, confidence: float) -> None:
        node = self._nodes.get(framework_id)
        if node is None:
            raise KeyError(f"unknown framework id {framework_id!r}")
        node.confidence = confidence

    async def set_status(self, framework_id: str, status: FrameworkStatus) -> None:
        node = self._nodes.get(framework_id)
        if node is None:
            raise KeyError(f"unknown framework id {framework_id!r}")
        node.status = status

    async def increment_validated_successes(self, framework_id: str) -> int:
        node = self._nodes.get(framework_id)
        if node is None:
            raise KeyError(f"unknown framework id {framework_id!r}")
        node.validated_successes += 1
        return node.validated_successes

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


class CogneeDocumentStore(FrameworkStore):
    """Cognee-backed store via the ingestion pipeline (``add`` + ``cognify``),
    read back through vector search. See module docstring for why this path
    works locally when the low-level graph adapter does not.

    Requires ``OPENROUTER_API_KEY`` (or another key already configured against
    ``LLM_API_KEY``/``EMBEDDING_API_KEY``) — every operation makes real network
    calls, so this is not used by the offline default test suite.
    """

    DATASET = "contextify_framework_store"

    def __init__(self) -> None:
        self._configured = False

    def _configure_from_openrouter(self) -> None:
        """Point cognee's LLM + embedding config at OpenRouter via its own env
        vars (LLM_*/EMBEDDING_*), distinct from this package's OPENROUTER_API_KEY."""
        if self._configured:
            return
        from dotenv import load_dotenv

        load_dotenv()
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError(
                "CogneeDocumentStore requires OPENROUTER_API_KEY (cognee needs "
                "real LLM + embedding calls for cognify/search)."
            )
        endpoint = "https://openrouter.ai/api/v1"
        os.environ.setdefault("LLM_PROVIDER", "openai")
        os.environ.setdefault("LLM_MODEL", os.getenv("CONTEXTIFY_MODEL", DEFAULT_MODEL))
        os.environ.setdefault("LLM_ENDPOINT", endpoint)
        os.environ.setdefault("LLM_API_KEY", key)
        os.environ.setdefault("EMBEDDING_PROVIDER", "openai")
        os.environ.setdefault("EMBEDDING_MODEL", "openai/text-embedding-3-small")
        os.environ.setdefault("EMBEDDING_ENDPOINT", endpoint)
        os.environ.setdefault("EMBEDDING_API_KEY", key)
        os.environ.setdefault("EMBEDDING_DIMENSIONS", "1536")
        self._configured = True

    @staticmethod
    def _to_document(f: Framework) -> str:
        return json.dumps(
            {
                "id": f.id,
                "name": f.name,
                "branch": f.branch.value,
                "parent": f.parent,
                "applicability_condition": f.applicability_condition,
                "status": f.status.value,
                "confidence": f.confidence,
            }
        )

    @staticmethod
    def _from_document(text: str) -> Framework:
        data = json.loads(text)
        return Framework(
            id=data["id"],
            name=data["name"],
            branch=Branch(data["branch"]),
            parent=data.get("parent"),
            applicability_condition=list(data.get("applicability_condition", [])),
            status=FrameworkStatus(data.get("status", "seeded")),
            confidence=float(data.get("confidence", 1.0)),
        )

    async def seed(self, frameworks: list[Framework]) -> None:
        self._configure_from_openrouter()
        import cognee

        # Deliberately no cognee.prune.* call here: cognee 1.2.2's prune API takes
        # no dataset filter (prune_data()/prune_system() are global), so calling it
        # would wipe every Cognee dataset on the machine, not just this one. Calling
        # seed() more than once may accumulate duplicate documents in this dataset
        # instead — an acceptable v1 tradeoff over a data-loss footgun.
        for f in frameworks:
            await cognee.add(
                [self._to_document(f)], dataset_name=self.DATASET, node_set=[f.id]
            )
        await cognee.cognify(datasets=[self.DATASET])
        self._seeded_ids = [f.id for f in frameworks]

    async def read_tree(self) -> list[Framework]:
        self._configure_from_openrouter()
        import cognee
        from cognee.modules.search.types import SearchType

        seeded_ids = getattr(self, "_seeded_ids", [])
        top_k = max(len(seeded_ids) * 2, 10)
        results = await cognee.search(
            query_text="software debugging framework applicability",
            query_type=SearchType.CHUNKS,
            datasets=[self.DATASET],
            top_k=top_k,
        )
        chunks = results[0]["search_result"] if results else []
        tree: list[Framework] = []
        seen: set[str] = set()
        for chunk in chunks:
            for node_id in chunk.get("belongs_to_set") or []:
                if node_id in seen:
                    continue
                try:
                    tree.append(self._from_document(chunk["text"]))
                    seen.add(node_id)
                except (KeyError, ValueError, json.JSONDecodeError) as exc:
                    logging.getLogger(__name__).warning(
                        "CogneeDocumentStore.read_tree(): dropping unparseable "
                        "document for node_set %r: %s", node_id, exc,
                    )
                    continue
        return tree
