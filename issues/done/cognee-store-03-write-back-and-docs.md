# Confidence/status write-back + docs sync for CogneeMemoryStore

Status: ready-for-agent

## Parent

`.scratch/cognee-native-framework-store/PRD.md`

## What to build

Implement `set_confidence()`, `set_status()`, and `increment_validated_successes()` on `CogneeMemoryStore` by re-serializing the updated Framework and calling `cognee.remember()` again under the same `node_set`, mirroring `seed()`'s per-Framework document convention from Slice 2. This is what lets `reflect()`'s existing write-back path (confidence step-up/down, promotion gate) work unchanged against this adapter.

Routing these writes through `cognee.improve()`'s feedback-weight pipeline instead is explicitly out of scope for this slice (and the parent PRD) — stick to the re-`remember()` approach.

Update `README.md`'s Framework Store section and "Known limitations" section to describe two adapters (not three) and the `remember()`/`recall()` mechanism (not `cognify()`/`search()`), so the docs match the shipped code.

## Acceptance criteria

- [ ] `set_confidence()` on `CogneeMemoryStore` re-`remember()`s the updated document under the same `node_set`
- [ ] `set_status()` and `increment_validated_successes()` implemented the same way
- [ ] New test: `set_confidence()` followed by `read_tree()` (or `get()`) reflects the updated value against `CogneeMemoryStore`
- [ ] `README.md` Framework Store section updated: two adapters, not three
- [ ] `README.md` "Known limitations" section updated: no mention of the deleted `CogneeFrameworkStore`; describes `remember()`/`recall()`, not `cognify()`/`search()`
- [ ] Full test suite (offline + live, with `OPENROUTER_API_KEY` set) passes

## Blocked by

- `cognee-store-02-seed-and-read-tree.md`
