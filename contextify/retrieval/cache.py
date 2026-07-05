"""Path cache: skip the tree-descent LLM call for repeated/similar problem
schemas (PRD user story 9). Keyed on the abstracted :class:`ProblemAbstraction`,
not raw text, so paraphrased-but-equivalent inputs still hit the cache.

The structured fields (``reproducibility``, ``evidence_available``,
``goal_shape``) must match exactly — they're already the categorical axes the
rest of the system matches on. ``symptom`` is free text, so it's compared via
token-overlap (Jaccard) similarity above a threshold rather than requiring an
exact string match. A full embedding-based similarity is deferred: this
repo's earlier Cognee spike needed real network/embedding calls to work at
all, so this keeps caching offline and dependency-free — consistent with
:class:`~contextify.llm.MockLLMClient`'s own light-heuristic word-overlap
tiebreakers, not a new kind of matching mechanism.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..llm import LLMRetrievalDecision
from ..models import ProblemAbstraction

# Deliberately lenient: the structured fields already do most of the work of
# ruling out a genuinely different problem shape (see _same_shape below), so
# symptom similarity only needs to catch "obviously the same story reworded."
_SYMPTOM_SIMILARITY_THRESHOLD = 0.2


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _symptom_similarity(a: str, b: str) -> float:
    tokens_a, tokens_b = _tokenize(a), _tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _same_shape(a: ProblemAbstraction, b: ProblemAbstraction) -> bool:
    return (
        a.reproducibility == b.reproducibility
        and a.goal_shape == b.goal_shape
        and set(a.evidence_available) == set(b.evidence_available)
        and _symptom_similarity(a.symptom, b.symptom) >= _SYMPTOM_SIMILARITY_THRESHOLD
    )


@dataclass
class _CacheEntry:
    abstraction: ProblemAbstraction
    decision: LLMRetrievalDecision


class PathCache:
    """Caches resolved tree-descent decisions, keyed on abstraction similarity.

    Not global by design, same reasoning as :class:`~contextify.reflection.
    history.MatchHistory`: callers thread the same PathCache across a session
    to get caching, and tests get isolation for free by constructing their own.
    """

    def __init__(self) -> None:
        self._entries: list[_CacheEntry] = []

    def lookup(self, abstraction: ProblemAbstraction) -> LLMRetrievalDecision | None:
        """Return a previously-resolved decision for a similar schema, if any."""
        for entry in self._entries:
            if _same_shape(entry.abstraction, abstraction):
                return entry.decision
        return None

    def store(self, abstraction: ProblemAbstraction, decision: LLMRetrievalDecision) -> None:
        self._entries.append(_CacheEntry(abstraction=abstraction, decision=decision))
