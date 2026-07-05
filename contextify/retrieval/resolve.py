"""Framework Retrieval — walk the tree to the best-fit framework in ONE LLM call.

The whole (small) tree plus each node's applicability checklist is handed to a
single call that returns the resolved root->leaf path at once — retrieval cost
does not scale with tree depth (PRD user story 8). This module only assembles the
call's decision into a :class:`FrameworkMatch`; the judgment lives behind the
:class:`~contextify.llm.LLMClient` seam.

A :class:`~contextify.retrieval.cache.PathCache` lets a similar-enough
abstracted schema skip that descent call entirely (PRD user story 9) — see
that module for what "similar enough" means.
"""

from __future__ import annotations

from ..llm import LLMClient
from ..models import Framework, FrameworkMatch, ProblemAbstraction
from .cache import PathCache


def resolve(
    abstraction: ProblemAbstraction,
    tree: list[Framework],
    llm: LLMClient,
    cache: PathCache | None = None,
) -> FrameworkMatch:
    """Resolve the abstracted problem to a single best-fit framework.

    Checks ``cache`` (if given) for a similar previously-resolved schema before
    issuing a fresh tree-descent LLM call; a fresh call's result is stored back
    into the cache for future lookups.
    """
    if not tree:
        raise ValueError("cannot resolve against an empty framework tree")

    decision = cache.lookup(abstraction) if cache is not None else None
    cache_hit = decision is not None
    if decision is None:
        decision = llm.resolve_framework(abstraction, tree)  # the single retrieval call
        if cache is not None:
            cache.store(abstraction, decision)

    by_id = {f.id: f for f in tree}
    framework = by_id.get(decision.chosen_id)
    if framework is None:
        raise ValueError(
            f"retrieval returned unknown framework id {decision.chosen_id!r}; "
            f"known ids: {sorted(by_id)}"
        )

    # Provisional Frameworks are eligible for retrieval, not excluded — but
    # scaling by the Framework's own trust weight means an equally-good
    # structural match still reads as less confident until it's promoted
    # (PRD user story 13).
    return FrameworkMatch(
        framework=framework,
        path=decision.path,
        confidence=decision.confidence * framework.confidence,
        abstraction=abstraction,
        rationale=decision.rationale,
        low_confidence=decision.ambiguous,
        cache_hit=cache_hit,
    )
