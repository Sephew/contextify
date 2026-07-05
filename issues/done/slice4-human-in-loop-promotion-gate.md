# Slice 4 — Human-in-the-loop promotion gate

Status: ready-for-agent

## Parent

`.scratch/framework-retrieval-system/PRD.md`

## What to build

Gate new Frameworks entering the store at promotion, not at the act of trying something novel once. Any new Framework enters with a `provisional` status flag and reduced weight relative to seeded Frameworks.

A provisional Framework is promoted to trusted/seeded weight once either of two conditions is met: N=3 validated successful `reflect` calls against it, or an explicit human sign-off action.

## Acceptance criteria

- [x] New Frameworks can be added to the store with a `provisional` status and lowered confidence weight
- [x] Provisional Frameworks are eligible for retrieval (not excluded), just weighted lower than trusted ones
- [x] After 3 validated successful reflections against a provisional Framework, it is automatically promoted to trusted status
- [x] An explicit human sign-off action promotes a provisional Framework to trusted status regardless of reflection count
- [x] A provisional Framework that receives failing reflections does not accumulate toward promotion

## Blocked by

- `slice3-reflect-seam-ground-truth-misfit`

## Outcome

Done. New module `contextify/framework_store/promotion.py`:

- `new_provisional_framework(...)` constructs a Framework at
  `PROVISIONAL_DEFAULT_CONFIDENCE` (0.5, below the 1.0 hand-seeded baseline)
  with `status=PROVISIONAL`; inserted into the store via the existing
  `store.seed([...])` (no new store method needed for insertion — `seed()`
  was already a generic idempotent upsert).
- `promote_framework(store, framework_id)` is the explicit human-sign-off
  entry point: sets status to `SEEDED` and floors confidence at
  `PROMOTED_CONFIDENCE_FLOOR` (0.7), unconditionally — this is also what
  auto-promotion calls once the threshold is met, so there's one promotion
  code path, not two.
- Auto-promotion lives in `reflection/reflect.py`: a successful reflection
  against a still-`PROVISIONAL` Framework increments a new
  `Framework.validated_successes` counter (via
  `store.increment_validated_successes`, mirroring `set_confidence`'s
  pattern); reaching `PROMOTION_THRESHOLD` (3) calls `promote_framework`.
  Failing reflections never touch the counter, satisfying "does not
  accumulate toward promotion."
- "Eligible for retrieval, not excluded, weighted lower": nothing in
  `resolve()`/`read_tree()` filtered by status already, so provisional
  Frameworks were always selectable — but nothing surfaced *confidence* as a
  retrieval-time weight before this slice. Changed
  `resolve()` to scale the returned match confidence by the chosen
  Framework's own `.confidence` (`decision.confidence * framework.confidence`),
  so a provisional pick now visibly reads as less confident than an
  equally-good structural match against a trusted Framework, without
  excluding it. Also surfaced `status`/`confidence` in `llm._render_tree()` so
  the real LLM client sees the same signal the Mock now encodes structurally.
- Added `FrameworkStore.set_status()` / `increment_validated_successes()`
  (same concrete-default-raises-NotImplementedError pattern as
  `set_confidence()`, overridden in `InMemoryGraphStore`).
- `ReflectionResult.promoted: bool` surfaces the promotion event from
  `reflect()`/`areflect()` for callers/demo.

Files changed: `contextify/models.py` (`Framework.validated_successes`,
`ReflectionResult.promoted`), `contextify/framework_store/store.py`,
`contextify/framework_store/promotion.py` (new),
`contextify/framework_store/__init__.py`, `contextify/reflection/reflect.py`,
`contextify/retrieval/resolve.py`, `contextify/llm.py`, `contextify/__init__.py`,
`tests/test_promotion.py` (new).

Next: Slice 5 (path caching for repeated/similar problem schemas) is
unblocked — note its blocker list only names Slice 2, so it was already
unblocked, but Slice 4 finishing means all four prior slices are now done.
