# Contextify

A Framework Retrieval System: retrieve the right *way of thinking* about a
problem (a reasoning framework), not similar facts. Slices 1-3 are built:
both the **Debugging** and **Testing** branches, single-call branch+leaf
resolution with a leading misfit signal, and the `reflect()` write-back seam
(ground truth, confidence updates, lagging misfit, tree-distance severity).

Full design context: [`.scratch/framework-retrieval-system/PRD.md`](.scratch/framework-retrieval-system/PRD.md),
[`framework-retrieval-system.md`](framework-retrieval-system.md), glossary in
[`CONTEXT.md`](CONTEXT.md). Issue tracker: [`issues/done/`](issues/done/).

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env   # add your OPENROUTER_API_KEY
```

No Cognee account needed — it's a local library. `.env` is git-ignored.

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

## Tests

```bash
pytest                 # offline suite (mock LLM, in-memory store) — always runs
```

`tests/test_cognee_document_store.py` is a live integration test (real
network/LLM/embedding calls); it self-skips unless `OPENROUTER_API_KEY` is set.

## Architecture

- `models.py` — the four-field `ProblemAbstraction` schema + `Framework`/`FrameworkMatch`.
- `llm.py` — the `LLMClient` seam: `OpenRouterClient` (live) and `MockLLMClient`
  (deterministic, offline, used by the default test suite).
- `problem_abstraction/` — raw text → `ProblemAbstraction`, one LLM call.
- `framework_store/` — the persistent tree retrieval reads from. See below.
- `retrieval/` — resolves the abstracted problem to a `FrameworkMatch`, one LLM
  call over the whole (small) tree.
- `reflection/` — the write-back seam: `reflect(match_id, outcome)` checks a
  branch-specific ground truth (Debugging: repro pass/fail; Testing: mutation
  caught / coverage delta), strengthens/weakens the matched Framework's
  confidence, and detects the lagging misfit signal (3+ distinct Frameworks
  tried for the same problem) with tree-distance severity.
- `api.py` — the two public seams: `retrieve_framework()` and `reflect()`,
  both built, with async (`aretrieve_framework`/`areflect`) and sync facades.

### Framework Store: a finding worth knowing

The issue asked for a "Cognee-backed" store. Three implementations exist behind
one `FrameworkStore` interface:

| Store | Status | Notes |
|---|---|---|
| `InMemoryGraphStore` | **default**, fully offline | Real parent/child graph, no external dependency. Used by the offline test suite. |
| `CogneeFrameworkStore` | built, **not usable here** | Drives Cognee's low-level graph engine (`add_node`/`add_edge`) directly. On this platform, Cognee 1.2.2's bundled embedded backend (Ladybug/Kuzu) emits a `MERGE ... SET n += {map}` query its own parser rejects — `add_node` fails outright. Kept behind the interface for when Cognee ships a working embedded backend or is pointed at an external one (Neo4j, etc). |
| `CogneeDocumentStore` | built, **validated working** | Drives Cognee's own ingestion pipeline (`cognee.add` + `cognee.cognify`), which batches its graph writes through a different internal path that doesn't hit the bug above. Each framework is stored as a JSON document tagged `node_set=[framework.id]`; read back via `cognee.search(SearchType.CHUNKS)`. Verified empirically end-to-end through OpenRouter (LLM + embeddings). Requires `OPENROUTER_API_KEY`; not used by the default offline suite for that reason. |

This lines up with upstream's own Cognee spike
(`spikes/cognee-retrieval-quality/VERDICT.md`): **GO**, 100% top-3 / 85% top-1
accuracy — via the same `cognify()` + `search(CHUNKS)` mechanism, not the raw
graph engine. Their spike measured retrieval quality with vector search
directly; this slice's retrieval mechanic is different (one LLM call resolves
the whole tree path at once, per the PRD), so `CogneeDocumentStore` is used
purely as a working *store*, with `read_tree()` returning the full tree for the
single-call resolver — not per-query vector ranking.

## Fixtures

`tests/test_upstream_fixtures.py` ports all 20 cases (12 Debugging + 8 Testing)
from the canonical Slice 0 spike fixture set
(`spikes/cognee-retrieval-quality/fixtures.py`) and runs each raw_text through
this package's actual `retrieve_framework()` seam (not Cognee vector search —
this slice's retrieval mechanism is a single LLM call over the whole tree).
`tests/fixtures.py` holds additional hand-authored adversarial cases (false
friends / disguised twins). `tests/test_misfit.py` and `tests/test_reflect.py`
cover the leading/lagging misfit signals and the reflection write-back
respectively.

## Known gaps (out of scope so far)

- Human-in-the-loop promotion gate for provisional frameworks (Slice 4).
- Path caching for repeated/similar problem schemas (Slice 5).
- The 4-field abstraction schema is a first-cut hypothesis (per the PRD), not a
  fully solved classifier — `MockLLMClient`'s heuristic needed several rounds of
  real fixes (not fixture rewording) against the upstream + hand-authored
  adversarial sets to stop defaulting to the wrong framework on under-specified
  reports. The live LLM path (`OpenRouterClient`) handles the same cases more
  robustly but isn't infallible either — it also missed a narrow pair
  (deterministic-but-environment-specific vs. self-resolving-stale-data) that is
  a genuine schema-expressiveness edge, not a bug.
