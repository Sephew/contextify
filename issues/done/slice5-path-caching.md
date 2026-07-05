# Slice 5 — Path caching for repeated/similar problem schemas

Status: ready-for-agent

## Parent

`.scratch/framework-retrieval-system/PRD.md`

## What to build

Cache resolved tree paths in `retrieve_framework`, keyed on abstracted-schema similarity (not raw text), so repeated or similar problem shapes skip the LLM descent call and the system gets cheaper/faster as the store matures.

## Acceptance criteria

- [x] A second call to `retrieve_framework` with a schema similar to a previously-resolved one hits the cache instead of issuing a new descent LLM call
- [x] Cache key is derived from the abstracted schema, not raw input text, so paraphrased-but-equivalent inputs still hit the cache
- [x] A genuinely novel problem schema still triggers a fresh descent call (no false-positive cache hits)
- [x] Cache hit/miss is observable (e.g. logged or returned in the result) for demo purposes

## Blocked by

- `slice2-testing-branch-leading-misfit-signal`

## Outcome

Done. New `contextify/retrieval/cache.py` (`PathCache`) sits between
abstraction and the tree-descent call in `resolve()`: on a hit it reuses the
cached `LLMRetrievalDecision` instead of calling `llm.resolve_framework()`; on
a miss it resolves fresh and stores the result.

Key decisions:

- **Similarity, not exact equality.** The three structured
  `ProblemAbstraction` fields (`reproducibility`, `goal_shape`,
  `evidence_available`) must match exactly — they're already the categorical
  axes the rest of the system matches on, so an exact match there does most of
  the "same problem shape" work. `symptom` is free text, so it's compared via
  Jaccard token-overlap similarity (threshold 0.2, deliberately lenient since
  the structured fields already gate out unrelated problems) rather than
  string equality — this is what makes paraphrased-but-equivalent inputs hit
  the cache per the acceptance criteria, without needing an embedding model
  (this repo's earlier Cognee spike needed real network/API calls just to get
  embeddings working; keeping the cache offline and dependency-free matches
  how `MockLLMClient` already does its own light-heuristic word-overlap
  tiebreaking, rather than introducing a second, heavier kind of matching).
- **Only the descent call is cached, not abstraction.** Per the PRD phrasing
  ("keyed on abstracted-schema similarity"), the abstraction LLM call still
  runs every time — you need the schema before you can know if it matches
  something cached. Only the second (tree-descent) call is skippable.
- **Observability**: added `FrameworkMatch.cache_hit: bool`, verified in tests
  both by the flag itself and by wrapping `MockLLMClient` in a call-counting
  spy to confirm the descent call was actually skipped, not just that the
  result happened to match.
- Added `cache: PathCache | None = None` to `resolve()` and
  `aretrieve_framework`/`retrieve_framework`, with the same process-lifetime
  default-singleton pattern as `store`/`history` from Slices 3-4 (tests pass
  their own `PathCache` for isolation).

Files changed: `contextify/models.py` (`FrameworkMatch.cache_hit`),
`contextify/retrieval/cache.py` (new), `contextify/retrieval/resolve.py`,
`contextify/retrieval/__init__.py`, `contextify/api.py`,
`contextify/__init__.py`, `tests/test_path_cache.py` (new).

All five slices in the Framework Retrieval System PRD are now done.
