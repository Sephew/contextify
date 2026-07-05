# Cognee-native Framework Store

Status: ready-for-agent

## Parent

`.scratch/cognee-native-framework-store/PRD.md`

## What to build

Delete the dead `CogneeFrameworkStore` adapter (permanently broken low-level graph engine, zero callers, zero tests). Rebuild the working Cognee path as `CogneeMemoryStore` (renamed from `CogneeDocumentStore`), implementing the unchanged `FrameworkStore` interface via `cognee.remember()`/`cognee.recall()` instead of the legacy `cognee.add()`/`cognee.cognify()`/`cognee.search()` primitives. `InMemoryGraphStore` and the `FrameworkStore` interface itself are untouched.

Spike `cognee.recall()`'s actual response shape first (which `Response*Entry` variant carries the stored document text) — this is the one genuine unknown in an otherwise mechanical adapter swap.

## Acceptance criteria

- [ ] `CogneeFrameworkStore` deleted from `contextify/framework_store/store.py` and its export removed from `contextify/framework_store/__init__.py`
- [ ] `CogneeMemoryStore` implements `seed()` via `cognee.remember(document, dataset_name=..., node_set=[framework.id])`
- [ ] `CogneeMemoryStore` implements `read_tree()`/`get()` via `cognee.recall(query_text=..., node_name=[...], datasets=[...])`, confirmed against a live spike of `recall()`'s response shape
- [ ] `set_confidence()`/`set_status()`/`increment_validated_successes()` work against `CogneeMemoryStore` (re-`remember()` the updated document under the same `node_set`)
- [ ] `tests/test_cognee_document_store.py` updated to reference `CogneeMemoryStore`, keeps its `skipif(not OPENROUTER_API_KEY)` gate, still asserts seed/read_tree round-trip correctness (ids, parent/child structure, non-empty applicability conditions)
- [ ] New test assertion: `set_confidence()` followed by `read_tree()` reflects the updated value against `CogneeMemoryStore`
- [ ] `InMemoryGraphStore` and `tests/test_upstream_fixtures.py` unchanged — no regressions
- [ ] `README.md` Framework Store / Known limitations sections updated: two adapters (not three), `remember()`/`recall()` mechanism (not `cognify()`/`search()`)

## Out of scope

- Routing `reflect()`'s confidence math or `promotion.py`'s validated-success counter through `cognee.improve()`
- Replacing `PathCache`/`MatchHistory` with Cognee session-aware `recall()`
- Changing the default store choice in `build_seeded_store()` (`InMemoryGraphStore` stays default)
- Any change to `contextify/server.py`

## Blocked by

- None — `CogneeFrameworkStore`/`CogneeDocumentStore` already exist and are the code being replaced.
