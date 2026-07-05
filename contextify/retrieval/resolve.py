"""Framework Retrieval — walk the tree to the best-fit framework in ONE LLM call.

The whole (small) tree plus each node's applicability checklist is handed to a
single call that returns the resolved root->leaf path at once — retrieval cost
does not scale with tree depth (PRD user story 8). This module only assembles the
call's decision into a :class:`FrameworkMatch`; the judgment lives behind the
:class:`~contextify.llm.LLMClient` seam.
"""

from __future__ import annotations

from ..llm import LLMClient
from ..models import Framework, FrameworkMatch, ProblemAbstraction


def resolve(
    abstraction: ProblemAbstraction,
    tree: list[Framework],
    llm: LLMClient,
) -> FrameworkMatch:
    """Resolve the abstracted problem to a single best-fit framework."""
    if not tree:
        raise ValueError("cannot resolve against an empty framework tree")

    decision = llm.resolve_framework(abstraction, tree)  # the single retrieval call

    by_id = {f.id: f for f in tree}
    framework = by_id.get(decision.chosen_id)
    if framework is None:
        raise ValueError(
            f"retrieval returned unknown framework id {decision.chosen_id!r}; "
            f"known ids: {sorted(by_id)}"
        )

    return FrameworkMatch(
        framework=framework,
        path=decision.path,
        confidence=decision.confidence,
        abstraction=abstraction,
        rationale=decision.rationale,
        low_confidence=decision.ambiguous,
    )
