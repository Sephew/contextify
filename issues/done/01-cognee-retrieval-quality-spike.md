# 01 — Cognee retrieval-quality spike

Status: done

## Parent

`.scratch/framework-retrieval-system/PRD.md`

## What to build

A standalone spike (no product code) that answers the PRD's biggest open risk before anything else is built on top of Cognee: does Cognee's embedding space handle abstract/structural similarity well, given it's tuned for factual/entity similarity?

Build 15-20 adversarial test cases across the Debugging and Testing branches: false friends (lexically similar problem descriptions that need different Frameworks) and disguised twins (lexically different descriptions that need the same Framework). Query Cognee with the raw problem text and measure whether the correct Framework lands in top-k. Re-run the same cases using a hand-written abstracted schema (the 4-field Problem Abstraction shape from the PRD) instead of raw text, to isolate whether failures are an embedding-space problem or a missing-abstraction problem.

Output is a written go/no-go verdict plus the fixture set itself (reused as regression tests in later slices), not a production module.

## Acceptance criteria

- [x] 15-20 adversarial cases built and documented (which are false-friends, which are disguised-twins, and the correct Framework for each)
- [x] Raw-text-against-Cognee top-k accuracy measured and recorded
- [x] Hand-abstracted-schema-against-Cognee top-k accuracy measured and recorded
- [x] A written conclusion: is the gap (if any) attributable to embedding space or to missing abstraction
- [x] Fixture set saved in a location later slices' test suites can import

## Blocked by

None - can start immediately

## Outcome

Spike built under `spikes/cognee-retrieval-quality/` (frameworks.py, fixtures.py,
run_spike.py, results.json, VERDICT.md, README.md).

- Raw text: 45% top-1 / 85% top-3 (n=20, top_k=3, 6 seeded frameworks).
- Hand-abstracted schema: 85% top-1 / **100% top-3**.
- **Verdict: GO.** Gap is attributable to missing abstraction, not embedding-space
  weakness — Cognee's embedding space resolved every case once given the 4-field
  abstraction. Proceed with issue 02's Problem Abstraction stage as designed.

Key environment notes for whoever picks up issue 02 (see spike README.md for full detail):
- No local OpenAI credits — used OpenRouter (`LLM_ENDPOINT` override) for the LLM and
  local `fastembed` for embeddings (OpenRouter has no embeddings endpoint).
- Windows: Cognee's default data dirs under site-packages exceed MAX_PATH (260 chars)
  once LanceDB's nested paths are appended — override `DATA_ROOT_DIRECTORY` /
  `SYSTEM_ROOT_DIRECTORY` / `CACHE_ROOT_DIRECTORY` to short paths.
- Cognee's pre-flight LLM connection test can time out (30s) against
  OpenAI-compatible proxies even when completions work fine — set
  `COGNEE_SKIP_CONNECTION_TEST=true` after verifying connectivity directly via litellm.
- Low-credit accounts: cap output via `LLM_ARGS={"max_tokens": N}` — passing
  `LLM_MAX_COMPLETION_TOKENS` alone was not sufficient for the entity-extraction call path.
