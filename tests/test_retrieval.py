import pytest

from contextify.framework_store import build_seeded_store
from contextify.llm import MockLLMClient
from contextify.problem_abstraction import abstract
from contextify.retrieval import resolve

from .fixtures import DEBUGGING_CASES


@pytest.mark.asyncio
@pytest.mark.parametrize("case", DEBUGGING_CASES, ids=[c["id"] for c in DEBUGGING_CASES])
async def test_retrieval_resolves_correct_debugging_framework(case):
    llm = MockLLMClient()
    store = await build_seeded_store()
    tree = await store.read_tree()

    abstraction = abstract(case["raw_text"], llm)
    match = resolve(abstraction, tree, llm)

    assert match.framework.id == case["expected"], (
        f"case {case['id']!r}: expected {case['expected']!r}, "
        f"got {match.framework.id!r} (rationale: {match.rationale})"
    )
    assert match.path[0] == "Debugging"
    assert match.path[-1] == match.framework.name


@pytest.mark.asyncio
async def test_resolve_raises_on_empty_tree():
    llm = MockLLMClient()
    abstraction = abstract("something broke", llm)
    with pytest.raises(ValueError):
        resolve(abstraction, [], llm)
