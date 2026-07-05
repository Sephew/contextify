# Slice 1 — Debugging-only retrieve_framework tracer bullet

Status: done

## Parent

`.scratch/framework-retrieval-system/PRD.md`

## What to build

The first end-to-end slice of the product. Scaffold the standalone package (per the PRD's deliverable shape: a library exposing `retrieve_framework()` and `reflect()` as public API, not a hosted service) with the proposed module layout (`problem_abstraction/`, `framework_store/`, `retrieval/`, `reflection/`).

Seed the Cognee-backed Framework Store's graph layer with 3-4 Debugging frameworks only (e.g. binary search bisection, differential diagnosis, cache-invalidation checklist), each with a name, parent/position, and an applicability_condition checklist.

Implement Problem Abstraction: given raw problem text, extract the 4-field schema (`symptom`, `reproducibility`, `evidence_available`, `goal_shape`) via a single LLM call.

Implement Framework Retrieval for the Debugging branch only: one LLM call given the full (small) tree + applicability notes, returning the resolved path as a `FrameworkMatch`.

Wire these into the `retrieve_framework(raw_input) -> FrameworkMatch` seam. Add a thin CLI/demo script that pipes a raw bug description through the seam and prints the match + path.

## Acceptance criteria

- [x] Package scaffold exists with the four proposed modules
- [x] Cognee store seeded with 3-4 Debugging frameworks, each carrying an applicability_condition and tree position
- [x] Problem Abstraction produces the 4-field schema from raw text in one LLM call
- [x] `retrieve_framework(raw_input) -> FrameworkMatch` resolves the correct Debugging framework for a straightforward bug description
- [x] Retrieval resolves the full tree path in a single LLM call (not one call per level)
- [x] CLI/demo script runs a raw bug description through the seam and prints the result
- [x] At least the Debugging-relevant cases from Slice 0's fixture set pass as automated tests (all 12, in `tests/test_upstream_fixtures.py`)

## Completion notes

- Framework Store shipped as three implementations behind one `FrameworkStore` interface: `InMemoryGraphStore` (default, offline), `CogneeFrameworkStore` (graph-engine adapter, not usable on this platform — Cognee 1.2.2's embedded backend emits a query its own parser rejects), `CogneeDocumentStore` (validated working via `cognee.add`/`cognify`/`search`, verified end-to-end through OpenRouter).
- `reflect()` is a stub in this slice (raises `NotImplementedError`) — write-back lands in a later slice per the PRD's seam split.
- See `README.md` for setup/usage/architecture and the Cognee-store finding.

## Blocked by

- `slice0-cognee-retrieval-quality-spike`
