# Slice 5 — Path caching for repeated/similar problem schemas

Status: ready-for-agent

## Parent

`.scratch/framework-retrieval-system/PRD.md`

## What to build

Cache resolved tree paths in `retrieve_framework`, keyed on abstracted-schema similarity (not raw text), so repeated or similar problem shapes skip the LLM descent call and the system gets cheaper/faster as the store matures.

## Acceptance criteria

- [ ] A second call to `retrieve_framework` with a schema similar to a previously-resolved one hits the cache instead of issuing a new descent LLM call
- [ ] Cache key is derived from the abstracted schema, not raw input text, so paraphrased-but-equivalent inputs still hit the cache
- [ ] A genuinely novel problem schema still triggers a fresh descent call (no false-positive cache hits)
- [ ] Cache hit/miss is observable (e.g. logged or returned in the result) for demo purposes

## Blocked by

- `slice2-testing-branch-leading-misfit-signal`
