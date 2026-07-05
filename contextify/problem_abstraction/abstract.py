"""Problem Abstraction — raw text -> structured 4-field schema, in one LLM call.

Per the PRD this is the hardest, most load-bearing stage: retrieval matches
against this schema, never the raw text, so matching is structural not lexical.
The actual field extraction lives behind the :class:`~contextify.llm.LLMClient`
seam so it can be a real model (OpenRouter) or a deterministic mock.
"""

from __future__ import annotations

from ..llm import LLMClient
from ..models import ProblemAbstraction


def abstract(raw_text: str, llm: LLMClient) -> ProblemAbstraction:
    """Distil a raw problem description into a :class:`ProblemAbstraction`."""
    if not raw_text or not raw_text.strip():
        raise ValueError("raw_text must be a non-empty problem description")
    return llm.abstract_problem(raw_text)
