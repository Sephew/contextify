# Cognee retrieval-quality spike — verdict

Issue: `issues/01-cognee-retrieval-quality-spike.md`. Full numbers in `results.json`; fixture set in `fixtures.py`; frameworks in `frameworks.py`; runner in `run_spike.py`.

## Setup

- 6 seeded Frameworks (3 Debugging: binary search bisection, differential diagnosis, cache invalidation checklist; 3 Testing: boundary value analysis, equivalence partitioning, state transition testing), each added to Cognee as a single `node_set`-tagged document and cognified once.
- 20 hand-built adversarial cases (5 false-friend pairs + 5 disguised-twin pairs), each with a raw problem-text description and a hand-written 4-field Problem Abstraction (`symptom`, `reproducibility`, `evidence_available`, `goal_shape`).
- Retrieval measured via `cognee.search(..., query_type=SearchType.CHUNKS)` (direct vector nearest-neighbor over chunks, not an LLM-graph-completion answer) against `top_k=3` out of 6 candidate frameworks.
- Each case run twice: once querying with `raw_text`, once querying with the serialized abstracted schema.

## Results

| Pass | top-1 accuracy | top-3 accuracy |
|---|---|---|
| Raw text | 45% (9/20) | 85% (17/20) |
| Abstracted schema | 85% (17/20) | **100% (20/20)** |

Breakdown (raw text): Debugging branch top-1 33%, Testing branch top-1 62.5% — Debugging cases (regression-bisection vs. differential-diagnosis vs. cache-staleness) were hardest to tell apart from raw prose alone. False-friend vs. disguised-twin split was roughly even (50% vs 40% top-1 on raw text), so the failure mode isn't "surface-similarity fools it" specifically — it's raw text generally underspecifying structure.

Every one of the 3 cases that missed top-3 entirely on raw text (`ff1-a`, `ff2-b`, `dt2-b`) hit rank 1 or 2 once given the abstracted schema instead.

## Verdict: GO — gap is attributable to missing abstraction, not embedding-space weakness

With a hand-written 4-field abstraction, Cognee's embedding space resolved every single case into the top 3 candidates (100%), and got 85% exactly right on the first guess. That means Cognee's embedding space *does* handle the abstract/structural similarity this system depends on — the PRD's biggest open risk — provided the input text actually encodes the structural signal (reproducibility, evidence, goal shape) instead of leaving it implicit in narrative prose.

The raw-text top-1 failures were not embedding-space confusions between conceptually adjacent frameworks (e.g. mixing up two Testing frameworks); they were cases where the raw description simply never says the words that matter — e.g. `ff1-a` and `ff2-b` both need `binary_search_bisection` but describe the regression narratively ("started throwing an error this week", "no longer updates instantly") without ever surfacing "I have an ordered, bisectable range of commits/deploys," which is exactly the fact the abstraction schema forces into the open.

**Implication for issue 02 (tracer bullet):** proceed with building Problem Abstraction as designed — it is the load-bearing stage the PRD flagged, and this spike shows it earns its keep. Do not spend more effort tuning embeddings/retrieval mechanics before the abstraction stage exists; the 100% top-3 ceiling on abstracted schema suggests retrieval mechanics are already sufficient at this seed-tree size.

## Caveats

- n=20 at a 6-framework tree; accuracy will need re-validation as the tree grows past single-call descent (already noted as deferred in the PRD).
- The 4-field schemas here were hand-written by the same person who wrote the fixtures — this measures the *ceiling* achievable once abstraction is done well, not whether an LLM call can reliably produce equally good abstractions from raw text. That's issue 02's problem to validate.
- `SearchType.CHUNKS` performs its own internal query rewrite before the vector search (visible in logs), so this isn't a raw embedding-distance measurement in the strictest sense — it reflects Cognee's actual retrieval behavior as a system, which is what the PRD's go/no-go question is actually about.
