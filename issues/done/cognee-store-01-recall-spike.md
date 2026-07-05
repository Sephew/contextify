# Spike: confirm remember()/recall() live behavior

Status: done

## Parent

`.scratch/cognee-native-framework-store/PRD.md`

## What to build

A throwaway script (not production code) that calls Cognee's live `remember()`/`recall()`/`forget()` API against a real Cognee configuration (OpenRouter-backed, same env-var wiring `CogneeDocumentStore._configure_from_openrouter()` already does) to answer three open questions before any adapter code is built:

1. What does `cognee.recall(query_text=..., node_name=[...], datasets=[...])` actually return? Confirm which `RecallResponse` union variant (`ResponseQAEntry`, `ResponseGraphContextEntry`, `ResponseGraphEntry`, etc.) carries the stored document text back out, and how to extract it.
2. Does `cognee.remember(document, dataset_name=..., node_set=[framework_id])` round-trip correctly — i.e. does a subsequent `recall()` filtered by that `node_name` return the same document?
3. Does `cognee.forget(dataset=...)` cleanly clear a dataset for an idempotent reseed, replacing the old unscoped-prune constraint that forced "accept duplicate documents" in the current `CogneeDocumentStore.seed()`?

Write the findings as a short note (module docstring or a `.scratch/cognee-native-framework-store/recall-spike-findings.md`) so Slice 2 can build against confirmed behavior instead of the current guess.

## Acceptance criteria

- [x] Live call to `cognee.remember()` with a `node_set`-tagged document, confirmed via direct execution (not assumed from docstrings)
- [x] Live call to `cognee.recall()` filtered by that `node_name`, with the exact response shape and field(s) needed to recover the document text documented
- [x] Live call to `cognee.forget(dataset=...)` confirmed to scope-clear only the target dataset, not other Cognee data on the machine
- [x] Findings written down (doc or code comment) in a location Slice 2 will reference
- [x] No production code changed — this is investigation only

## Result

See `.scratch/cognee-native-framework-store/recall-spike-findings.md`. Key findings:
- Must pass `query_type=SearchType.CHUNKS` to `recall()` — default `auto_route` picks `GRAPH_COMPLETION`, which returns an LLM-synthesized paraphrase, not the raw document text.
- With `CHUNKS`, `.text` on the returned `ResponseGraphEntry` is the exact raw document string passed to `remember()`; `node_name` filtering narrows correctly.
- `forget(dataset=...)` is properly scoped (sibling dataset confirmed untouched), but a subsequent `recall()` against the forgotten/never-seeded dataset raises `DatasetNotFoundError` rather than returning `[]` — Slice 2's `read_tree()`/`get()` must catch this.
- Recommend `seed()` do `forget(dataset=DATASET)` then re-`remember()` for idempotent replace, now that `forget()` is scoped.

## Blocked by

- None — can start immediately.
