from contextify.models import (
    Branch,
    EvidenceType,
    Framework,
    FrameworkStatus,
    GoalShape,
    ProblemAbstraction,
    Reproducibility,
)


def test_problem_abstraction_prompt_block_contains_all_fields():
    pa = ProblemAbstraction(
        symptom="Report page throws on load",
        reproducibility=Reproducibility.DETERMINISTIC,
        evidence_available=[EvidenceType.STACK_TRACE, EvidenceType.FAILING_TEST],
        goal_shape=GoalShape.ROOT_CAUSE,
    )
    block = pa.to_prompt_block()
    assert "Report page throws on load" in block
    assert "deterministic" in block
    assert "stack_trace" in block and "failing_test" in block
    assert "root_cause" in block


def test_framework_root_has_no_parent():
    root = Framework(
        id="fw.debugging",
        name="Debugging",
        branch=Branch.DEBUGGING,
        parent=None,
        status=FrameworkStatus.SEEDED,
    )
    assert root.is_root is True

    leaf = Framework(
        id="fw.bisection",
        name="Bisection",
        branch=Branch.DEBUGGING,
        parent="fw.debugging",
    )
    assert leaf.is_root is False
