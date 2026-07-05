"""Leading misfit signal: ambiguously-close top candidates flag low confidence.

Slice 2 acceptance criterion: "Ambiguously-close top candidates produce a
flagged low-confidence result rather than a silent guess."
"""

from __future__ import annotations

import pytest

from contextify.framework_store import build_seeded_store
from contextify.llm import MockLLMClient
from contextify.models import (
    Branch,
    EvidenceType,
    Framework,
    FrameworkStatus,
    GoalShape,
    ProblemAbstraction,
    Reproducibility,
)
from contextify.problem_abstraction import abstract
from contextify.retrieval import resolve

from .fixtures import DEBUGGING_CASES


@pytest.mark.asyncio
async def test_clear_cut_match_is_not_flagged_low_confidence():
    llm = MockLLMClient()
    store = await build_seeded_store()
    tree = await store.read_tree()
    case = DEBUGGING_CASES[0]

    abstraction = abstract(case["raw_text"], llm)
    match = resolve(abstraction, tree, llm)

    assert match.low_confidence is False


def test_ambiguously_close_top_candidates_are_flagged_low_confidence():
    llm = MockLLMClient()
    abstraction = ProblemAbstraction(
        symptom="something is wrong",
        reproducibility=Reproducibility.DETERMINISTIC,
        evidence_available=[EvidenceType.FAILING_TEST],
        goal_shape=GoalShape.ROOT_CAUSE,
    )
    # Two leaves with identical applicability checklists against this
    # abstraction: neither can dominate, so the match must be flagged rather
    # than silently guessing one over the other.
    root = Framework(
        id="fw.root", name="Root", branch=Branch.DEBUGGING, parent=None,
        status=FrameworkStatus.SEEDED,
    )
    leaf_a = Framework(
        id="fw.leaf_a", name="Leaf A", branch=Branch.DEBUGGING, parent="fw.root",
        applicability_condition=[
            "reproducibility: deterministic",
            "evidence: failing_test",
            "goal_shape: root_cause",
        ],
        status=FrameworkStatus.SEEDED,
    )
    leaf_b = Framework(
        id="fw.leaf_b", name="Leaf B", branch=Branch.DEBUGGING, parent="fw.root",
        applicability_condition=[
            "reproducibility: deterministic",
            "evidence: failing_test",
            "goal_shape: root_cause",
        ],
        status=FrameworkStatus.SEEDED,
    )
    tree = [root, leaf_a, leaf_b]

    match = resolve(abstraction, tree, llm)

    assert match.low_confidence is True
