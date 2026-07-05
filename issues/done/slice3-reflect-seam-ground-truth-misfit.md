# Slice 3 — reflect seam: ground truth + lagging misfit + tree-distance severity

Status: ready-for-agent

## Parent

`.scratch/framework-retrieval-system/PRD.md`

## What to build

Implement the second seam, `reflect(match_id, outcome) -> ReflectionResult`, called after a real-world outcome is known for a prior `retrieve_framework` match.

Branch-specific ground truth: for Debugging, success means the previously-failing reproduction case now passes; for Testing, success means the generated tests caught a seeded mutation or increased coverage of a previously-uncovered branch.

On each reflection, write back to the Framework Store: adjust the matched Framework's confidence weight (via Cognee's Memify layer). Detect the lagging misfit signal — 3+ *distinct* Frameworks tried for the same underlying problem (as opposed to retrying the same Framework, which is an execution issue, not a fit issue). When a misfit is detected, log the tree distance between the initially-matched Framework and the Framework that eventually succeeded, as a severity metric.

## Acceptance criteria

- [x] `reflect(match_id, outcome)` accepts a Debugging outcome (repro pass/fail) and updates confidence accordingly
- [x] `reflect(match_id, outcome)` accepts a Testing outcome (mutation caught / coverage delta) and updates confidence accordingly
- [x] Confidence weight in the store visibly changes after a reflection call (strengthens on success, weakens on failure)
- [x] Lagging misfit signal fires when 3+ distinct Frameworks are tried for the same problem, and does NOT fire when the same Framework is retried
- [x] Tree distance between initial match and eventually-successful match is computed and logged when misfit is detected
- [x] Reflection stage can report "this Framework's assumption didn't hold" distinctly from a plausible-looking-but-wrong output

## Blocked by

- `slice2-testing-branch-leading-misfit-signal`

## Outcome

Done. `reflect(match_id, outcome, store=, history=)` (async core `areflect`) is
implemented in `contextify/reflection/reflect.py`. Key decisions:

- **Ground truth typed as `ReflectionOutcome`** (models.py): 5 values, 2
  Debugging (`repro_now_passes`/`repro_still_fails`), 3 Testing
  (`mutation_caught`/`coverage_increased`/`no_improvement`). reflect() rejects
  a Debugging outcome against a Testing-branch match and vice versa — that's
  the "assumption didn't hold" vs. "caller error" distinction from the last
  acceptance criterion; a mismatched outcome raises `ValueError` rather than
  being silently coerced into a generic success/failure bit.
- **Confidence**: ±0.1 on success / -0.15 on failure, clamped to [0.1, 1.0].
  Seeded frameworks start at the 1.0 ceiling, so a lone success can't show a
  rise — tests weaken first, then confirm a success visibly strengthens it
  back (see `tests/test_reflect.py`).
- **"Same problem" for the lagging misfit signal is an explicit `problem_id`**
  the caller threads through repeated `retrieve_framework()` calls (new
  optional param), not inferred from text/schema similarity — that similarity
  matching is Slice 5's job (path caching) and deliberately not duplicated
  here. Added `contextify/reflection/history.py` (`MatchHistory`) to log
  match_id -> (problem_id, framework_id) across calls, since that mapping
  didn't exist before this slice and reflect() needs it to resolve match_id
  at all.
- **Tree distance** (`contextify/reflection/tree_distance.py`) computed via a
  virtual super-root shared by both Branch roots, so distance is well-defined
  even when the misfit crosses branches (initially matched Debugging, Testing
  framework eventually worked) — covered by
  `test_cross_branch_tree_distance_when_the_wrong_branch_was_tried_first`.
- Added `FrameworkStore.set_confidence()` (concrete default raises
  `NotImplementedError`; overridden in `InMemoryGraphStore`) and
  `FrameworkMatch.match_id` (uuid4, auto-generated).
- Replaced `aretrieve_framework`'s "fresh store per call" default with a
  lazily-built process-lifetime default store/history in `api.py`, so a bare
  `retrieve_framework()` → `reflect()` sequence works without the caller
  threading state by hand — this was a latent gap from Slice 1 that reflect()
  needing to find its own matches now forces a fix for. Tests still pass
  explicit store/history for isolation, same convention as before.

Files changed: `contextify/models.py`, `contextify/api.py`,
`contextify/framework_store/store.py`,
`contextify/reflection/{__init__,reflect,history,tree_distance}.py`,
`contextify/__init__.py`, `tests/test_api.py`, `tests/test_reflect.py` (new).

Next: Slice 4 (human-in-the-loop promotion gate) is unblocked.
