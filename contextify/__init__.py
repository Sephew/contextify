"""Contextify — a Framework Retrieval System.

Retrieve the right *way of thinking* about a problem (a reasoning framework),
not similar facts. v1 scope: the Debugging branch of software development.

Public API::

    from contextify import retrieve_framework
    match = retrieve_framework("my bug description ...")
    print(match.framework_name, match.path)
"""

from __future__ import annotations

from .api import aretrieve_framework, reflect, retrieve_framework
from .llm import LLMClient, MockLLMClient, OpenRouterClient
from .models import (
    Branch,
    EvidenceType,
    Framework,
    FrameworkMatch,
    FrameworkStatus,
    GoalShape,
    ProblemAbstraction,
    ReflectionResult,
    Reproducibility,
)

__version__ = "0.1.0"

__all__ = [
    # seams
    "retrieve_framework",
    "aretrieve_framework",
    "reflect",
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
    "ProblemAbstraction",
    "ReflectionResult",
    "Reproducibility",
    "__version__",
]
