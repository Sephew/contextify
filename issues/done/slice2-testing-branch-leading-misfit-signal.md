# Slice 2 — Add Testing branch + leading misfit signal

Status: ready-for-agent

## Parent

`.scratch/framework-retrieval-system/PRD.md`

## What to build

Extend the Framework Store with a seeded Testing branch (3-4 frameworks, e.g. boundary value analysis, equivalence partitioning), sibling to the existing Debugging branch.

Extend Framework Retrieval so the single-LLM-call descent chooses the correct top-level branch before resolving within it, using both branches' applicability conditions together (still one call, not one per branch).

Add the leading misfit signal: when the top candidate Frameworks score ambiguously close together, `retrieve_framework` returns a low-confidence flag instead of a confident single match.

## Acceptance criteria

- [x] Testing branch seeded with 3-4 frameworks, each with applicability_condition and tree position
- [x] `retrieve_framework` correctly picks Testing-branch frameworks for testing-goal problems and Debugging-branch frameworks for debugging-goal problems
- [x] Branch selection happens within the same single LLM call as leaf resolution
- [x] Ambiguously-close top candidates produce a flagged low-confidence result rather than a silent guess
- [x] Slice 0's full adversarial fixture set (false friends + disguised twins across both branches) runs as an automated regression suite and passes

## Blocked by

- `slice1-debugging-retrieve-framework-tracer-bullet`

## Outcome

Done. Testing branch (Boundary Value Analysis, Equivalence Partitioning, State
Transition Testing) seeded alongside Debugging in `ALL_FRAMEWORKS`; the single
retrieval call scores leaves from both branches together (`resolve_framework`
receives the whole tree, not per-branch). `LLMRetrievalDecision.ambiguous` /
`FrameworkMatch.low_confidence` fire when the runner-up leaf scores within
`_AMBIGUITY_MARGIN` of the top pick.

Found and fixed a scoring bug while porting Slice 0's Testing-branch fixture
cases as an automated suite (`tests/test_upstream_fixtures.py`): Boundary
Value's checklist said "not distinct input categories" to rule itself out of
category-shaped problems, but the Testing-branch category bonus in
`MockLLMClient._score` does substring matching, not negation-aware matching,
so the word "categories" in that negation made Boundary Value tie with
Equivalence Partitioning on category-shaped inputs (ff4-b: three player
types). Reworded the checklist to "a choice between separate inputs handled
by different logic" to drop the shared vocabulary. All 20 of Slice 0's
fixture cases (12 Debugging + 8 Testing) now pass via
`test_upstream_fixtures.py`; added `test_resolve_flags_low_confidence_*` tests
in `tests/test_retrieval.py` for the misfit signal itself.

Files changed: `contextify/framework_store/seed.py`,
`contextify/framework_store/__init__.py`, `contextify/llm.py`,
`contextify/models.py`, `contextify/retrieval/resolve.py`,
`tests/test_store.py`, `tests/test_upstream_fixtures.py`,
`tests/test_retrieval.py`.

Next: Slice 3 (reflect seam) is unblocked.
