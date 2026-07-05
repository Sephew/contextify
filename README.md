# Contextify

A Framework Retrieval System: retrieve the right *way of thinking* about a
problem (a reasoning framework), not similar facts. All five slices in the
PRD are built: both the **Debugging** and **Testing** branches, single-call
branch+leaf resolution with a leading misfit signal, the `reflect()`
write-back seam (ground truth, confidence updates, lagging misfit,
tree-distance severity), a human-in-the-loop promotion gate for new
provisional frameworks, and path caching keyed on abstracted-schema
similarity.

Full design context: [`framework-retrieval-system.md`](framework-retrieval-system.md),
glossary in [`CONTEXT.md`](CONTEXT.md).

## Cognee Usage

Cognee is the persistent memory this project's framework store runs on. The
whole framework tree lives as Cognee documents, and every operation Contextify
needs — seed, read, single-item lookup, and write-back — maps onto Cognee's v1
memory API (`remember()` / `recall()` / `forget()`). See
[`framework_store/store.py`](contextify/framework_store/store.py) for the full
`CogneeMemoryStore`.

**Seed — one framework per document, tagged by id.** Each `Framework` is stored
as a JSON document under a `node_set` keyed on its id, so it can be recalled
individually later:

```python
await cognee.forget(dataset=self.DATASET)          # idempotent replace
for f in frameworks:
    await cognee.remember(
        self._to_document(f), dataset_name=self.DATASET, node_set=[f.id]
    )
```

**Read — recall by chunk.** Reads go through `recall()` with an explicit
`query_type=SearchType.CHUNKS`; `.text` returns the exact JSON document that was
stored, which is parsed straight back into `Framework` objects. Passing
`node_name=[framework_id]` narrows the recall server-side to a single framework:

```python
from cognee.modules.search.types import SearchType

results = await cognee.recall(
    query_type=SearchType.CHUNKS,       # required — default auto-route mangles JSON
    node_name=node_name,                # None = whole tree; [id] = one framework
    ...
)
frameworks = [self._from_document(r.text) for r in results]
```

**Write-back — read-modify-write under the same `node_set`.** Confidence
updates, status changes, and validated-success counters are done by recalling
the current document, mutating it, deleting the old chunk, then re-`remember()`ing
it. (A bare re-`remember()` *appends* a chunk rather than replacing it, so the
old one is `forget()`-ed by `data_id` first.)

```python
await cognee.forget(data_id=uuid.UUID(data_id), dataset=self.DATASET)
await cognee.remember(
    self._to_document(current), dataset_name=self.DATASET, node_set=[current.id]
)
```

This is the loop that makes the store *learn*: `reflect()` writes outcomes back
into Cognee, so later retrievals see updated confidence and promoted frameworks
— not a static index. Details and the validated-working status of this backend
are in the [Framework Store](#framework-store-a-finding-worth-knowing) section
below.

## Setup

```bash
pip install -e .
cp .env.example .env   # add your OPENROUTER_API_KEY
```

## Usage

```bash
python -m contextify "my bug description ..."   # live OpenRouter run
python -m contextify --mock "..."                # offline, no key needed
```

```python
from contextify import retrieve_framework
match = retrieve_framework("After the ORM upgrade, every run throws...")
print(match.framework_name, match.path)
```

## Architecture

- `models.py` — the four-field `ProblemAbstraction` schema + `Framework`/`FrameworkMatch`.
- `llm.py` — the `LLMClient` seam: `OpenRouterClient` (live) and `MockLLMClient`
  (deterministic, offline).
- `problem_abstraction/` — raw text → `ProblemAbstraction`, one LLM call.
- `framework_store/` — the persistent tree retrieval reads from. See below.
- `retrieval/` — resolves the abstracted problem to a `FrameworkMatch`, one LLM
  call over the whole (small) tree. `retrieval/cache.py` (`PathCache`) sits in
  front of that descent call: the three structured `ProblemAbstraction` fields
  (`reproducibility`, `goal_shape`, `evidence_available`) must match exactly,
  and `symptom` (free text) is compared via Jaccard token-overlap similarity —
  a cache hit skips the descent LLM call entirely, surfaced as
  `FrameworkMatch.cache_hit`.
- `reflection/` — the write-back seam: `reflect(match_id, outcome)` checks a
  branch-specific ground truth (Debugging: repro pass/fail; Testing: mutation
  caught / coverage delta), strengthens/weakens the matched Framework's
  confidence, and detects the lagging misfit signal (3+ distinct Frameworks
  tried for the same problem) with tree-distance severity. A successful
  reflection against a `provisional` framework also counts toward its
  promotion (see below).
- `framework_store/promotion.py` — the human-in-the-loop promotion gate: new
  frameworks enter via `new_provisional_framework(...)` at reduced confidence
  (`status=PROVISIONAL`); they're still eligible for retrieval (just weighted
  lower — `resolve()` scales match confidence by the framework's own
  confidence), and get promoted to trusted/seeded weight via
  `promote_framework(...)` either automatically after 3 validated successful
  reflections or by explicit human sign-off.
- `api.py` — the two public seams: `retrieve_framework()` and `reflect()`,
  both built, with async (`aretrieve_framework`/`areflect`) and sync facades.

### Framework Store: a finding worth knowing

The issue asked for a "Cognee-backed" store. Two implementations exist behind
one `FrameworkStore` interface:

| Store | Status | Notes |
|---|---|---|
| `InMemoryGraphStore` | **default**, fully offline | Real parent/child graph, no external dependency. |
| `CogneeMemoryStore` | built, **validated working** | Built on Cognee's v1 memory API. `seed()` calls `cognee.remember()` to store each framework as a JSON document tagged `node_set=[framework.id]`; `read_tree()`/`get()` read it back via `cognee.recall(query_type=SearchType.CHUNKS, node_name=[...])`, whose `.text` returns the exact stored document. Write-backs (`set_confidence`/`set_status`/`increment_validated_successes`) delete the old chunk and re-`remember()` the updated document under the same `node_set`. This API sits on Cognee's vector store — distinct from the broken embedded graph backend (Ladybug/Kuzu), whose low-level `add_node`/`add_edge` engine emits a `MERGE ... SET n += {map}` query Cognee 1.2.2's own parser rejects. Verified empirically end-to-end through OpenRouter (LLM + embeddings). Requires `OPENROUTER_API_KEY`. |

This lines up with upstream's own Cognee spike: **GO**, 100% top-3 / 85% top-1
accuracy — over the same vector-store embedding space `recall()` reads from.
That spike measured retrieval quality with vector search directly; this slice's
retrieval mechanic is different (one LLM call resolves the whole tree path at
once, per the PRD), so `CogneeMemoryStore` is used purely as a working *store*,
with `read_tree()` returning the full tree for the single-call resolver — not
per-query vector ranking.

## Known limitations

- The 4-field abstraction schema is a first-cut hypothesis (per the PRD), not a
  fully solved classifier — `MockLLMClient`'s heuristic needed several rounds of
  real fixes (not fixture rewording) against the upstream + hand-authored
  adversarial sets to stop defaulting to the wrong framework on under-specified
  reports. The live LLM path (`OpenRouterClient`) handles the same cases more
  robustly but isn't infallible either — it also missed a narrow pair
  (deterministic-but-environment-specific vs. self-resolving-stale-data) that is
  a genuine schema-expressiveness edge, not a bug.

## License

[MIT](LICENSE) © 2026 sephew
