# Spike findings: remember()/recall()/forget() live behavior (cognee 1.2.2)

Confirmed via live calls against OpenRouter (see `recall_spike.py`, `recall_spike2.py`
in this directory — throwaway, not production code). Answers the three open
questions in `issues/cognee-store-01-recall-spike.md` for Slice 2.

## 1. recall() response shape — must pass `query_type=SearchType.CHUNKS`

`cognee.recall()` defaults to `auto_route=True`, which picks `GRAPH_COMPLETION`
for a natural-language query. That mode returns a `ResponseGraphEntry` whose
`text` field is an **LLM-synthesized paraphrase of the graph**, not the raw
stored document:

> "A root cause isolation debugging framework is a concept used in debugging
> practices that focuses on identifying the underlying cause of a reproducible
> bug..."

This is unusable for `read_tree()` — it loses the structured fields entirely
and isn't stable across calls.

Passing `query_type=SearchType.CHUNKS` explicitly returns the real thing: a
`ResponseGraphEntry` with `kind='chunk'` whose `.text` is the exact raw
document string passed to `remember()`, byte-for-byte:

```python
results = await cognee.recall(
    query_text="root cause isolation",
    query_type=SearchType.CHUNKS,
    datasets=[DATASET],
    node_name=["root-cause-isolation"],
    top_k=10,
)
# results[0].text == the exact JSON string given to remember()
```

**Decision for Slice 2**: `CogneeMemoryStore.read_tree()`/`get()` must pass
`query_type=SearchType.CHUNKS` explicitly. Do not rely on `auto_route`.

`SearchType` import is unchanged: `from cognee.modules.search.types import SearchType`.

## 2. remember()/recall() round-trip via node_set/node_name — confirmed

- `cognee.remember(doc, dataset_name=DATASET, node_set=[framework_id])` accepts
  `node_set` as a kwarg (confirmed via `RememberKwargs`, not in the top-level
  signature but passed through `**kwargs`).
- `recall(..., node_name=[framework_id], datasets=[DATASET])` correctly narrows
  to just that framework's chunk when `node_name` is given (1 result out of 2
  seeded docs).
- Omitting `node_name` (just `datasets=[DATASET]`) correctly returns all chunks
  scoped to that dataset (2 results for 2 seeded docs) — safe for `read_tree()`
  which wants everything.
- Each `ResponseGraphEntry.metadata['data_id']` and `.metadata['chunk_id']`
  differ per stored document; `belongs_to_set` (on `.raw`) carries the
  `node_set` list back, mirroring the old `CogneeDocumentStore` chunk-parsing
  convention but no longer requiring the manual loop over `belongs_to_set` —
  `node_name` filtering does that server-side now.

## 3. forget(dataset=...) — scoped correctly, but recall() on a forgotten dataset raises, doesn't return []

- `cognee.forget(dataset=DATASET)` returns
  `{'dataset_id': ..., 'status': 'success'}` and fully clears that dataset
  (data + graph + vector entries).
- Confirmed scoped: a sibling dataset seeded before the `forget()` call was
  **unaffected** (`recall()` against it after the `forget()` still returned
  its data).
- **Gotcha**: calling `recall()` against a dataset that no longer exists
  (freshly forgotten, or never seeded) raises `DatasetNotFoundError` (404) —
  it does **not** return an empty list. `CogneeMemoryStore.read_tree()`/`get()`
  must catch `cognee.modules.data.exceptions.exceptions.DatasetNotFoundError`
  and treat it as an empty tree, or Slice 2's adapter will crash on first read
  before any `seed()` call.

**Decision for Slice 2's `seed()`**: since `forget()` is now dataset-scoped
(unlike the old unscoped `prune.*` API that forced "accept duplicates"),
`seed()` should call `cognee.forget(dataset=DATASET)` before re-`remember()`-ing
for an idempotent replace, instead of accumulating duplicate documents on
repeat calls.

## Other notes

- Each `remember()` call is a real LLM + embedding round trip through
  `add()`+`cognify()`; ~30s per document in this environment. Same cost profile
  as the old `CogneeDocumentStore.seed()` — no regression.
- `RecallResponse` is a discriminated union on `source` (`session`/`graph`);
  everything in this spike came back `source='graph'` as `ResponseGraphEntry`,
  since no `session_id` was used.
