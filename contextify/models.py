"""Core data contracts for the Framework Retrieval System.

Every module imports from here. These types define the two public seams:
``retrieve_framework(raw_input) -> FrameworkMatch`` and (later) ``reflect(...)``.

The four-field :class:`ProblemAbstraction` schema is the load-bearing, highest-risk
piece per the PRD — treat it as a hypothesis, not settled truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Branch(str, Enum):
    """Top-level branches of the software-development domain. v1 = Debugging only."""

    DEBUGGING = "debugging"
    TESTING = "testing"  # seeded in a later slice; kept here so the schema is stable


class Reproducibility(str, Enum):
    """How reliably the problem can be reproduced."""

    DETERMINISTIC = "deterministic"
    INTERMITTENT = "intermittent"
    UNREPRODUCED = "unreproduced"


class EvidenceType(str, Enum):
    """Kinds of evidence the developer already has in hand."""

    STACK_TRACE = "stack_trace"
    LOGS = "logs"
    FAILING_TEST = "failing_test"
    REPORT_ONLY = "report_only"


class GoalShape(str, Enum):
    """What outcome the developer is actually after."""

    ROOT_CAUSE = "root_cause"
    FIX = "fix"
    COVERAGE_INCREASE = "coverage_increase"
    REGRESSION_PREVENTION = "regression_prevention"


class FrameworkStatus(str, Enum):
    """Trust weight of a framework node in the store."""

    SEEDED = "seeded"          # hand-authored, trusted
    PROVISIONAL = "provisional"  # improvised, needs validation before it's trusted


@dataclass
class ProblemAbstraction:
    """Raw problem text distilled into a structured, comparable schema.

    This is what retrieval matches against — never the raw text — so matching is
    structural, not lexical.
    """

    symptom: str  # observed-vs-expected delta, in one sentence
    reproducibility: Reproducibility
    evidence_available: list[EvidenceType]
    goal_shape: GoalShape

    def to_prompt_block(self) -> str:
        """Render as a compact block for inclusion in the retrieval LLM call."""
        evidence = ", ".join(e.value for e in self.evidence_available) or "none"
        return (
            f"- symptom: {self.symptom}\n"
            f"- reproducibility: {self.reproducibility.value}\n"
            f"- evidence_available: {evidence}\n"
            f"- goal_shape: {self.goal_shape.value}"
        )


@dataclass
class Framework:
    """One node in the Framework Store tree.

    ``applicability_condition`` is a checklist tested against a
    :class:`ProblemAbstraction` — a structural test, not a similarity description.
    """

    id: str
    name: str
    branch: Branch
    parent: str | None  # id of parent node; None for a branch root
    applicability_condition: list[str] = field(default_factory=list)
    status: FrameworkStatus = FrameworkStatus.SEEDED
    confidence: float = 1.0

    @property
    def is_root(self) -> bool:
        return self.parent is None


@dataclass
class FrameworkMatch:
    """Result of the retrieve seam: the chosen framework plus how we got there."""

    framework: Framework
    path: list[str]  # node names root -> leaf, e.g. ["Debugging", "Bisection"]
    confidence: float
    abstraction: ProblemAbstraction
    rationale: str = ""

    @property
    def framework_name(self) -> str:
        return self.framework.name

    @property
    def branch(self) -> Branch:
        return self.framework.branch


@dataclass
class ReflectionResult:
    """Result of the reflect seam (write-back). Stubbed in this slice."""

    match_id: str
    outcome: str
    store_changed: bool = False
    note: str = ""
