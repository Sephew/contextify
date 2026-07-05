"""Core data contracts for the Framework Retrieval System.

Every module imports from here. These types define the two public seams:
``retrieve_framework(raw_input) -> FrameworkMatch`` and (later) ``reflect(...)``.

The four-field :class:`ProblemAbstraction` schema is the load-bearing, highest-risk
piece per the PRD — treat it as a hypothesis, not settled truth.
"""

from __future__ import annotations

import uuid
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


class ReflectionOutcome(str, Enum):
    """Ground-truth ``outcome`` values reflect() accepts (PRD "Reflection ground
    truth"), branch-specific: Debugging is judged by repro pass/fail, Testing by
    mutation-catching/coverage. A Debugging outcome against a Testing-branch match
    (or vice versa) is a caller bug — reflect() rejects it rather than silently
    treating it as a generic success/failure bit.
    """

    REPRO_NOW_PASSES = "repro_now_passes"      # Debugging success
    REPRO_STILL_FAILS = "repro_still_fails"    # Debugging failure
    MUTATION_CAUGHT = "mutation_caught"        # Testing success
    COVERAGE_INCREASED = "coverage_increased"  # Testing success
    NO_IMPROVEMENT = "no_improvement"          # Testing failure


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
    # Leading misfit signal: True when the top candidates scored ambiguously
    # close together, so this match should be treated as a flagged guess rather
    # than a confident pick.
    low_confidence: bool = False
    # Identifies this match for a later reflect(match_id, outcome) call.
    match_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def framework_name(self) -> str:
        return self.framework.name

    @property
    def branch(self) -> Branch:
        return self.framework.branch


@dataclass
class ReflectionResult:
    """Result of the reflect seam (write-back)."""

    match_id: str
    outcome: str
    store_changed: bool = False
    note: str = ""
    success: bool = False
    confidence_before: float = 0.0
    confidence_after: float = 0.0
    # Lagging misfit signal: True when this success followed 3+ distinct
    # Frameworks tried for the same problem (retrying the same Framework
    # doesn't count — that's an execution issue, not a fit issue).
    misfit_detected: bool = False
    # Tree distance from the first-tried Framework to the one that eventually
    # succeeded; only meaningful when misfit_detected is True.
    tree_distance: int | None = None
