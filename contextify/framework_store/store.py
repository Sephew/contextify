"""Framework Store — the persistent library retrieval reads from.

The store sits *outside* the input->output line (per the design doc): retrieval
reads the tree, reflection (later) writes back. That independent read/write is
what lets the system accumulate judgment instead of being a fancy prompt.

Two implementations behind one interface:

- :class:`InMemoryGraphStore` — a real parent/child graph held in memory. The
  working default: no external dependency, fully offline.
- :class:`CogneeMemoryStore` — a *working* Cognee-backed alternative, verified
  empirically on this machine via OpenRouter. Built on Cognee's v1 memory API
  (``cognee.remember()`` for seeding, ``cognee.recall()`` for tree reads),
  which sits on Cognee's vector store — a storage system distinct from the
  broken embedded graph backend (Ladybug/Kuzu) that the low-level
  ``add_node``/``add_edge`` graph adapter tripped over. Each Framework is
  stored as one JSON-serialized document tagged with ``node_set=[framework.id]``
  via ``remember()``; ``read_tree()``/``get()`` read it back via
  ``recall(query_type=SearchType.CHUNKS, ...)``, whose ``.text`` carries the
  raw stored document string back out (confirmed live — see
  ``.scratch/cognee-native-framework-store/recall-spike-findings.md``). This is
  the mechanism the upstream Cognee spike
  (``spikes/cognee-retrieval-quality/VERDICT.md``) validated with a 100% top-3
  / 85% top-1 result — confirming Cognee's embedding space handles this
  system's structural-similarity needs, given a good abstraction. Requires
  ``OPENROUTER_API_KEY`` (real network + LLM + embedding calls); not used by
  the default offline test suite for that reason.
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


class CogneeMemoryStore(FrameworkStore):
    """Cognee-backed store on the v1 memory API (``remember()`` + ``recall()``).
    See module docstring for why this path works locally when the low-level
    graph adapter does not.

    Requires ``OPENROUTER_API_KEY`` (or another key already configured against
    ``LLM_API_KEY``/``EMBEDDING_API_KEY``) — every operation makes real network
    calls, so this is not used by the offline default test suite.
    """

    DATASET = "contextify_framework_store"
    # The tree is tiny (a handful of frameworks per branch); a generous fixed
    # top_k covers "return everything in the dataset" without dynamic sizing.
    _READ_TOP_K = 100

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
                "CogneeMemoryStore requires OPENROUTER_API_KEY (cognee needs "
                "real LLM + embedding calls for remember/recall)."
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
                "validated_successes": f.validated_successes,
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
            validated_successes=int(data.get("validated_successes", 0)),
        )

    async def seed(self, frameworks: list[Framework]) -> None:
        self._configure_from_openrouter()
        import cognee

        # Idempotent replace: forget the dataset first, then re-remember. Unlike
        # cognee 1.2.2's old prune.* API (global, no dataset filter), forget() is
        # dataset-scoped and safe — it clears only this dataset, leaving other
        # Cognee data on the machine untouched (confirmed live, see the recall
        # spike findings). forget() on a not-yet-existing dataset is a no-op that
        # returns success, so a first-ever seed() needs no special-casing.
        await cognee.forget(dataset=self.DATASET)
        for f in frameworks:
            await cognee.remember(
                self._to_document(f), dataset_name=self.DATASET, node_set=[f.id]
            )

    async def read_tree(self) -> list[Framework]:
        return await self._recall(node_name=None)

    async def get(self, framework_id: str) -> Framework | None:
        # recall()'s server-side node_name filter narrows to just this
        # framework's chunk, so this is a single scoped read rather than a full
        # read_tree() scan.
        matches = await self._recall(node_name=[framework_id])
        return next((f for f in matches if f.id == framework_id), None)

    async def _recall(self, node_name: list[str] | None) -> list[Framework]:
        """Shared read path for read_tree()/get(). ``node_name=None`` returns the
        whole dataset; a list narrows to those node ids server-side."""
        self._configure_from_openrouter()
        import cognee
        from cognee.modules.data.exceptions.exceptions import DatasetNotFoundError
        from cognee.modules.search.types import SearchType

        try:
            # query_type=CHUNKS is required: recall()'s default auto-route picks
            # GRAPH_COMPLETION, which returns an LLM-synthesized paraphrase rather
            # than the raw stored document. With CHUNKS, entry.text is the exact
            # JSON string passed to remember() (confirmed live in the spike).
            results = await cognee.recall(
                query_text="software debugging and testing framework applicability",
                query_type=SearchType.CHUNKS,
                datasets=[self.DATASET],
                node_name=node_name,
                top_k=self._READ_TOP_K,
            )
        except DatasetNotFoundError:
            # recall() raises rather than returning [] when the dataset has never
            # been seeded (or was forgotten) — treat that as an empty tree.
            return []

        tree: list[Framework] = []
        seen: set[str] = set()
        for entry in results:
            text = getattr(entry, "text", None)
            if not text:
                continue
            try:
                framework = self._from_document(text)
            except (KeyError, ValueError, json.JSONDecodeError) as exc:
                logging.getLogger(__name__).warning(
                    "CogneeMemoryStore._recall(): dropping unparseable document: %s",
                    exc,
                )
                continue
            if framework.id in seen:
                continue
            seen.add(framework.id)
            tree.append(framework)
        return tree

    async def set_confidence(self, framework_id: str, confidence: float) -> None:
        def _apply(f: Framework) -> None:
            f.confidence = confidence

        await self._update(framework_id, _apply)

    async def set_status(self, framework_id: str, status: FrameworkStatus) -> None:
        def _apply(f: Framework) -> None:
            f.status = status

        await self._update(framework_id, _apply)

    async def increment_validated_successes(self, framework_id: str) -> int:
        def _apply(f: Framework) -> int:
            f.validated_successes += 1
            return f.validated_successes

        return await self._update(framework_id, _apply)

    async def _update(self, framework_id: str, apply):
        """Read-modify-write a single Framework: recall its current document,
        apply the mutation, delete the old chunk(s), then re-remember() the
        updated document under the same node_set.

        Delete-then-remember (not a bare re-remember): remember() *appends* a new
        chunk for a node_set rather than replacing the existing one (confirmed
        live), so without deleting the old chunk first, read_tree() could return
        the stale copy. Deleting every data_id found for this id also self-heals
        any prior accumulation. Raises KeyError for an unknown id, matching
        InMemoryGraphStore."""
        self._configure_from_openrouter()
        import cognee
        from cognee.modules.data.exceptions.exceptions import DatasetNotFoundError
        from cognee.modules.search.types import SearchType

        try:
            results = await cognee.recall(
                query_text="software debugging and testing framework applicability",
                query_type=SearchType.CHUNKS,
                datasets=[self.DATASET],
                node_name=[framework_id],
                top_k=self._READ_TOP_K,
            )
        except DatasetNotFoundError:
            results = []

        current: Framework | None = None
        stale_data_ids: list[str] = []
        for entry in results:
            text = getattr(entry, "text", None)
            if not text:
                continue
            try:
                framework = self._from_document(text)
            except (KeyError, ValueError, json.JSONDecodeError):
                continue
            if framework.id != framework_id:
                continue
            if current is None:
                current = framework
            data_id = (getattr(entry, "metadata", None) or {}).get("data_id")
            if data_id:
                stale_data_ids.append(str(data_id))

        if current is None:
            raise KeyError(f"unknown framework id {framework_id!r}")

        result = apply(current)
        for data_id in stale_data_ids:
            await cognee.forget(data_id=uuid.UUID(data_id), dataset=self.DATASET)
        await cognee.remember(
            self._to_document(current), dataset_name=self.DATASET, node_set=[current.id]
        )
        return result
