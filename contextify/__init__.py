"""Contextify — a Framework Retrieval System.

Retrieve the right *way of thinking* about a problem (a reasoning framework),
not similar facts. v1 scope: the Debugging branch of software development.

Public API::

    from contextify import retrieve_framework
    match = retrieve_framework("my bug description ...")
    print(match.framework_name, match.path)
"""

from __future__ import annotations

from .api import aretrieve_framework, areflect, reflect, retrieve_framework
from .framework_store import new_provisional_framework, promote_framework
from .llm import LLMClient, MockLLMClient, OpenRouterClient
from .models import (
    Branch,
    EvidenceType,
    Framework,
    FrameworkMatch,
    FrameworkStatus,
    GoalShape,
    ProblemAbstraction,
    ReflectionOutcome,
    ReflectionResult,
    Reproducibility,
)
from .reflection import MatchHistory
from .retrieval import PathCache

__version__ = "0.1.0"

__all__ = [
    # seams
    "retrieve_framework",
    "aretrieve_framework",
    "reflect",
    "areflect",
    # llm clients
    "LLMClient",
    "MockLLMClient",
    "OpenRouterClient",
    # models
    "Branch",
    "EvidenceType",
    "Framework",
    "FrameworkMatch",
    "FrameworkStatus",
    "GoalShape",
    "MatchHistory",
    "PathCache",
    "ProblemAbstraction",
    "ReflectionOutcome",
    "ReflectionResult",
    "Reproducibility",
    "new_provisional_framework",
    "promote_framework",
    "__version__",
]
