# Cognee-native Framework Store — PRD

Status: ready-for-agent

## Parent

`.scratch/framework-retrieval-system/PRD.md` (user stories 18-20: Cognee's graph/vector/Memify layers were meant to drive the Framework Store and reflection write-back "largely pre-built rather than hand-rolled." Slice 1 found Cognee 1.2.2's embedded graph backend broken and shipped a hand-rolled fallback instead. This PRD revisits that deferral now that Cognee exposes a higher-level memory API untouched by the original bug.)

## Problem Statement

The Framework Store's `FrameworkStore` interface has three implementations, but only one is real. `InMemoryGraphStore` is the working offline default. `CogneeFrameworkStore` targets Cognee's low-level graph engine (`add_node`/`add_edge`) and is permanently broken on this platform — its own module docstring documents that the embedded backend (Ladybug/Kuzu) rejects a query its own parser emits — and nothing calls it: zero test coverage, zero production callers. `CogneeDocumentStore`, the one working Cognee path, was built against the legacy `cognee.add()`/`cognee.cognify()`/`cognee.search()` primitives before Cognee shipped a higher-level memory API, so it hand-rolls JSON document serialization, a dataset-name constant, and manual `node_set` tagging/parsing to fake capabilities Cognee now provides natively.

Cognee 1.2.2 — already the version pinned in `pyproject.toml` — ships a v1 API (`remember()`/`recall()`/`improve()`/`forget()`) that sits on Cognee's vector store, a storage system distinct from the broken embedded graph backend. This closes the gap the original PRD's Cognee-mapping user stories (18-20) called for, without needing Cognee to fix the low-level bug.

## Solution

Delete the permanently-broken, uncalled `CogneeFrameworkStore` adapter. Rebuild the working Cognee path as `CogneeMemoryStore`, implementing the existing `FrameworkStore` interface via `cognee.remember()` (seeding) and `cognee.recall()` (tree reads), instead of hand-rolled JSON + `cognify()`/`search()`. `InMemoryGraphStore` stays the untouched offline default. The `FrameworkStore` interface itself does not change — this is an adapter-level swap behind an existing seam, not a new one.

## User Stories

1. As a maintainer, I want the dead `CogneeFrameworkStore` adapter removed, so the codebase doesn't carry a permanently-broken, zero-caller class that no test exercises.
2. As a maintainer, I want the working Cognee adapter renamed to `CogneeMemoryStore`, so its name reflects that it's built on Cognee's `remember`/`recall` memory API, not the old document/chunk search mechanism.
3. As `CogneeMemoryStore`, I want `seed()` to call `cognee.remember(document, dataset_name=..., node_set=[framework.id])` per Framework, so seeding drops the hand-rolled JSON-document convention in favor of `remember()`'s native `node_set` tagging.
4. As `CogneeMemoryStore`, I want `read_tree()`/`get()` to call `cognee.recall(query_text=..., node_name=[...], datasets=[...])`, so tree reads use `recall()`'s native node-name filtering instead of the hand-rolled `belongs_to_set` chunk-parsing loop `CogneeDocumentStore.read_tree()` currently does.
5. As `CogneeMemoryStore`, I want `set_confidence()`/`set_status()`/`increment_validated_successes()` to still mutate stored Framework state, so `reflect()`'s existing write-back path works unchanged against this adapter.
6. As a developer running the offline test suite, I want `InMemoryGraphStore` untouched by this change, so existing tests against it keep passing with no modification.
7. As a developer running the live Cognee integration test, I want it updated to import `CogneeMemoryStore` instead of `CogneeDocumentStore` and to assert the same round-trip behavior (seed 3-4 Debugging Frameworks, read them back with correct parent/child structure and non-empty applicability conditions), so the existing test's intent survives the rename with no loss of coverage.
8. As a maintainer, I want `README.md`'s Framework Store section and "Known limitations" section updated to describe two adapters (not three) and the `remember()`/`recall()` mechanism (not `cognify()`/`search()`), so the docs match the shipped code.
9. As a builder, I want a short spike step to confirm `recall()`'s actual response shape (which of its `Response*Entry` variants carries the stored document text back out) before wiring the parsing logic, so `read_tree()`/`get()` aren't built against a guessed shape.

## Implementation Decisions

- **Seam unchanged**: `FrameworkStore`'s abstract contract (`seed`, `read_tree`, `get`, `set_confidence`, `set_status`, `increment_validated_successes`) is not modified. This PRD only replaces one adapter's internals and deletes another.
- **Delete `CogneeFrameworkStore`** entirely from `contextify/framework_store/store.py` and its export from `contextify/framework_store/__init__.py`. Recoverable from git history if Cognee ever ships a working embedded graph backend.
- **New adapter `CogneeMemoryStore`** replaces `CogneeDocumentStore` (rename, not an addition — one class, not two).
  - `seed(frameworks)`: for each Framework, JSON-serialize (same document shape `CogneeDocumentStore._to_document` already produces) and call `cognee.remember(document, dataset_name=DATASET, node_set=[framework.id])`. Keep the existing "no unscoped prune call" constraint — `cognee.forget()` replaces the old `prune.*` API and does take dataset/id-scoped filters (`forget(dataset=...)`, `forget(data_id=..., dataset_id=...)`), so re-seeding can now optionally `forget(dataset=DATASET)` first for a clean reseed instead of accepting duplicate-document accumulation — decide during implementation which behavior `seed()` should have (idempotent replace vs. accept duplicates), since the old constraint that forced "accept duplicates" (prune being unscoped/global) no longer holds with `forget()`'s scoped filters.
  - `read_tree()`/`get()`: call `cognee.recall(query_text=..., node_name=[...], datasets=[DATASET], top_k=...)`. Exact response parsing depends on the spike in User Story 9 — `recall()` returns a list of `RecallResponse` union variants (`ResponseQAEntry`, `ResponseGraphContextEntry`, `ResponseGraphEntry`, etc.), and which variant carries the raw document text is not yet confirmed against a live call.
  - `set_confidence`/`set_status`/`increment_validated_successes`: re-serialize the updated Framework and `remember()` it again under the same `node_set`, mirroring `seed()`'s per-Framework document convention. Routing these through `cognee.improve()`'s feedback-weight pipeline instead is explicitly out of scope (see below).
  - Configuration (`_configure_from_openrouter`, pointing Cognee's own `LLM_*`/`EMBEDDING_*` env vars at OpenRouter) carries over unchanged from `CogneeDocumentStore`.
- **Naming**: `CogneeMemoryStore` (confirmed). `DATASET` constant and `_configure_from_openrouter`/`_to_document`/`_from_document` helper names carry over from `CogneeDocumentStore` unless the recall() spike forces a shape change.

## Testing Decisions

- Tests assert observable behavior through the `FrameworkStore` interface (seed → read_tree round-trip correctness: right ids, right parent/child structure, non-empty applicability conditions) — not internal Cognee call shapes. This is the same standard `tests/test_cognee_document_store.py` already applies.
- **Prior art**: `tests/test_cognee_document_store.py` — update in place (rename references to `CogneeMemoryStore`), keep its `skipif(not OPENROUTER_API_KEY)` gate and `load_dotenv()`-before-skip-check pattern, since `remember()`/`recall()` still require real LLM + embedding network calls.
- `InMemoryGraphStore` and the existing offline fixture suite (`tests/test_upstream_fixtures.py`) are untouched — no new tests needed there, since neither the interface nor that adapter changes.
- Add one new assertion to the updated live test: a `set_confidence()` call followed by a `read_tree()` reflects the updated value — this path didn't exist in the same form under `CogneeDocumentStore` (which never had `set_confidence` support wired up; confirm current status before assuming it's untested) and is new surface this PRD adds.

## Out of Scope

- Routing `reflect()`'s confidence step-up/step-down math or `promotion.py`'s validated-success counter through `cognee.improve()`'s feedback-weight stage. Flagged as a separate, speculative follow-up in the architecture review — only worth pursuing once `CogneeMemoryStore` is live, and the current hand-rolled math is small, tested, and not causing friction on its own.
- Replacing `PathCache`'s hand-rolled Jaccard-similarity matching or `MatchHistory`'s process-lifetime globals with Cognee's session-aware `recall()`. Flagged as "worth exploring" in the same review, but a larger architectural shift (network-dependent similarity in place of a working offline 15-line module) than this PRD's scope.
- Changing `InMemoryGraphStore` or the default store choice in `build_seeded_store()`. It remains the default; `CogneeMemoryStore` remains opt-in via explicit construction, same as `CogneeDocumentStore` today.
- Any change to the hosted API server (`contextify/server.py`) — it uses whichever store `build_seeded_store()` defaults to and is unaffected by this adapter-level change.

## Further Notes

- This PRD directly answers user stories 18-20 of the parent PRD (Cognee's graph/vector/Memify layers driving the Framework Store), which Slice 1 deferred after finding the embedded graph backend broken. The deferral reason (broken low-level graph engine) never applied to `remember()`/`recall()`, since those sit on Cognee's vector store — a separate storage system in Cognee's own dual-storage architecture.
- `cognee.improve()`'s docstring describes a four-stage pipeline including "apply feedback weights" (session entries with feedback scores update `feedback_weight` on graph nodes) — this is the mechanism referenced in the Out of Scope section's deferred follow-up, not something this PRD wires up.
- The recall() response-shape spike (User Story 9) should happen early in implementation — it's the one genuine unknown in an otherwise mechanical adapter swap, and getting it wrong silently (parsing the wrong `Response*Entry` field) is the main risk here.
