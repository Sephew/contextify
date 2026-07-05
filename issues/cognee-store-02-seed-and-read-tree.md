# Seed + read the Framework tree via CogneeMemoryStore

Status: ready-for-agent

## Parent

`.scratch/cognee-native-framework-store/PRD.md`

## What to build

Delete the dead `CogneeFrameworkStore` adapter (permanently broken low-level graph engine, zero callers, zero tests) from `contextify/framework_store/store.py` and its export from `contextify/framework_store/__init__.py`.

Rebuild the working Cognee path as `CogneeMemoryStore`, replacing `CogneeDocumentStore` (a rename plus an internals swap, not a new class alongside the old one). Implement `seed()` via `cognee.remember(document, dataset_name=..., node_set=[framework.id])` and `read_tree()`/`get()` via `cognee.recall(query_text=..., node_name=[...], datasets=[...])`, using the confirmed response shape from the recall spike (Slice 1). The `FrameworkStore` interface itself is unchanged — this is an adapter-level swap behind the existing seam.

Decide, using Slice 1's `forget()` findings, whether `seed()` does an idempotent replace (via `forget(dataset=...)` before reseeding) or keeps accepting duplicate documents as before.

## Acceptance criteria

- [ ] `CogneeFrameworkStore` deleted from `contextify/framework_store/store.py` and its export removed from `contextify/framework_store/__init__.py`
- [ ] `CogneeMemoryStore` implements `seed()` via `cognee.remember()` with `node_set=[framework.id]` per Framework
- [ ] `CogneeMemoryStore` implements `read_tree()`/`get()` via `cognee.recall()`, parsing the response shape confirmed in Slice 1
- [ ] `tests/test_cognee_document_store.py` updated to reference `CogneeMemoryStore`, keeps its `skipif(not OPENROUTER_API_KEY)` gate and `load_dotenv()`-before-skip-check pattern
- [ ] Live round-trip test passes: seed 3-4 Debugging Frameworks, read them back with correct ids, correct parent/child structure, non-empty applicability conditions
- [ ] `InMemoryGraphStore` and `tests/test_upstream_fixtures.py` unchanged — full existing suite still passes

## Blocked by

- `cognee-store-01-recall-spike.md`
