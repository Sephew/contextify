# Seed + read the Framework tree via CogneeMemoryStore

Status: done

## Parent

`.scratch/cognee-native-framework-store/PRD.md`

## What to build

Delete the dead `CogneeFrameworkStore` adapter (permanently broken low-level graph engine, zero callers, zero tests) from `contextify/framework_store/store.py` and its export from `contextify/framework_store/__init__.py`.

Rebuild the working Cognee path as `CogneeMemoryStore`, replacing `CogneeDocumentStore` (a rename plus an internals swap, not a new class alongside the old one). Implement `seed()` via `cognee.remember(document, dataset_name=..., node_set=[framework.id])` and `read_tree()`/`get()` via `cognee.recall(query_text=..., node_name=[...], datasets=[...])`, using the confirmed response shape from the recall spike (Slice 1). The `FrameworkStore` interface itself is unchanged — this is an adapter-level swap behind the existing seam.

Decide, using Slice 1's `forget()` findings, whether `seed()` does an idempotent replace (via `forget(dataset=...)` before reseeding) or keeps accepting duplicate documents as before.

## Acceptance criteria

- [x] `CogneeFrameworkStore` deleted from `contextify/framework_store/store.py` and its export removed from `contextify/framework_store/__init__.py`
- [x] `CogneeMemoryStore` implements `seed()` via `cognee.remember()` with `node_set=[framework.id]` per Framework
- [x] `CogneeMemoryStore` implements `read_tree()`/`get()` via `cognee.recall()`, parsing the response shape confirmed in Slice 1
- [x] `tests/test_cognee_document_store.py` updated to reference `CogneeMemoryStore`, keeps its `skipif(not OPENROUTER_API_KEY)` gate and `load_dotenv()`-before-skip-check pattern
- [x] Live round-trip test passes: seed 3-4 Debugging Frameworks, read them back with correct ids, correct parent/child structure, non-empty applicability conditions
- [x] `InMemoryGraphStore` and `tests/test_upstream_fixtures.py` unchanged — full existing suite still passes

## Blocked by

- `cognee-store-01-recall-spike.md`

## Result

Live test `tests/test_cognee_document_store.py` passes (2 passed, 4m11s against real Cognee/OpenRouter): seed→read_tree round-trip + a get() single-node read.

Key decisions:
- `seed()` does an **idempotent replace**: `cognee.forget(dataset=DATASET)` then per-framework `remember()`. `forget()` is dataset-scoped (safe; a sibling dataset was confirmed untouched in Slice 1) and is a no-op returning success on a not-yet-existing dataset, so first-ever seed needs no special-casing.
- `read_tree()`/`get()` share a `_recall()` helper passing `query_type=SearchType.CHUNKS` (required — default auto-route returns an LLM paraphrase, not raw doc text) and catching `DatasetNotFoundError` → `[]` (recall raises rather than returning empty on a never-seeded dataset).
- `get()` uses recall's server-side `node_name` filter for a scoped single-node read instead of a full `read_tree()` scan.
- `set_confidence`/`set_status`/`increment_validated_successes` write-back deferred to Slice 3 (issue 03) as scoped.

Note: README still references the old adapter names — updating it is explicitly Slice 3's acceptance criterion, left untouched here.
