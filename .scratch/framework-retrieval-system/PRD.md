# Framework Retrieval System — PRD

Status: ready-for-agent

## Problem Statement

When a developer hits a debugging or testing problem, competent engineers would reach for different diagnostic lenses depending on the problem's shape — but nothing today retrieves *the right way of thinking* about a problem. AI coding tools retrieve similar code/facts (standard RAG), which is a different thing from retrieving the correct reasoning Framework. Applying the wrong Framework confidently is worse than applying none — it produces a confident answer built on evidence gathered from the wrong place.

## Solution

A Framework Retrieval System scoped to two Branches of the software-development Domain — **Debugging** and **Testing** — that:

1. Abstracts a raw problem description into a structured schema (Problem Abstraction).
2. Walks a tree-structured Framework Store (Cognee-backed) to retrieve the best-fit Framework(s) (Framework Retrieval).
3. Hands the match to a downstream consumer to apply (Output — out of scope here, see below).
4. Checks whether the applied Framework actually resolved the problem, and writes that signal back into the Framework Store so future retrieval improves (Reflection).

Debugging and Testing were chosen as the v1 branch pair specifically because they're adjacent (a failing test is often the entry point to a debugging session) — this adjacency is what generates good false-friend/disguised-twin adversarial test cases, rather than being a liability.

## User Stories

1. As a developer describing a bug, I want the system to abstract my raw description into a structured problem schema, so that retrieval isn't just keyword/lexical matching.
2. As a developer, I want the abstraction to capture the symptom (observed vs. expected behavior), so the system knows what's actually wrong.
3. As a developer, I want the abstraction to capture reproducibility (deterministic / intermittent / unreproduced), so frameworks requiring a reliable repro aren't matched to a flaky bug.
4. As a developer, I want the abstraction to capture what evidence I already have (stack trace, logs, failing test, bug report only), so retrieval doesn't recommend a framework that assumes evidence I don't have.
5. As a developer, I want the abstraction to capture the goal shape (root-cause identification / fix / coverage increase / regression prevention), so a testing-goal problem isn't matched to a debugging-goal framework or vice versa.
6. As the retrieval system, I want Frameworks organized as a parent-child tree under Debugging and Testing Branches, so matching is a coarse-to-fine walk instead of flat comparison against every Framework.
7. As the retrieval system, I want each Framework node to carry a short applicability condition (a checklist against the abstracted schema), so matching is a structural test, not a similarity guess.
8. As the retrieval system, I want to resolve the full tree path in one LLM call (given the whole tree + applicability notes), so retrieval cost doesn't scale with tree depth.
9. As the retrieval system, I want to cache resolved paths for repeated/similar problem schemas, so the system gets cheaper and faster as the store matures.
10. As the retrieval system, I want a leading misfit signal — when top candidate Frameworks score ambiguously close together — so I can flag low-confidence matches before any Output is generated.
11. As the retrieval system, I want a lagging misfit signal — 3+ *different* Frameworks cycled for the same problem — distinguished from retrying the *same* Framework (an execution issue, not a fit issue).
12. As the retrieval system, I want to measure tree distance between the initially retrieved Framework and the one that eventually worked, so "how wrong" a mismatch was is quantifiable, not binary.
13. As a maintainer, I want new Frameworks to enter the store with a provisional/low-confidence flag rather than immediately trusted weight, so a single improvised success doesn't silently reshape all future retrieval.
14. As a maintainer, I want a provisional Framework promoted to trusted status only after multiple validated successful uses (or my explicit sign-off), so promotion is gated at the point of permanent impact, not at the point of improvisation.
15. As the reflection stage, I want a ground-truth signal for Debugging outcomes (does the fix make the previously-failing reproduction case pass), so success/failure isn't judged on plausibility alone.
16. As the reflection stage, I want a ground-truth signal for Testing outcomes (do the generated tests catch a seeded mutation, or increase coverage of a previously-uncovered branch), so test-quality frameworks are judged on catching bugs, not just producing plausible-looking tests.
17. As the reflection stage, I want to be able to say "this Framework's assumption didn't hold" and fall back, rather than only checking whether the output looks plausible.
18. As the Framework Store, I want to be backed by Cognee's graph layer for the parent-child tree structure, so hierarchy and applicability edges are queryable natively.
19. As the Framework Store, I want Cognee's vector layer available for coarse candidate filtering once the tree grows past what fits comfortably in one descent call, so cost stays flat as the store scales (deferred until the v1 seed set outgrows single-call reasoning).
20. As the Framework Store, I want Cognee's Memify layer to drive the reflection write-back (strengthening frequently-successful paths, weakening misfits), so self-improvement is largely pre-built rather than hand-rolled.
21. As a builder validating the architecture, I want a set of 15-20 adversarial test cases — false friends (lexically similar, need different Frameworks) and disguised twins (lexically different, need the same Framework) — spanning Debugging and Testing, so retrieval quality is measured against structure, not surface wording.
22. As a builder, I want the adversarial set run twice — once against raw text, once against hand-written abstracted schemas — so a retrieval failure can be attributed to the embedding space vs. a missing/wrong abstraction.

## Implementation Decisions

- **Domain scope**: software development. **Branches (v1)**: Debugging and Testing only. No other branches (e.g. architecture, code review) in v1.
- **Codebase**: new standalone codebase (not a module inside the existing `backend/` crop-insurance app — unrelated project). Proposed module layout: `problem_abstraction/`, `framework_store/`, `retrieval/`, `reflection/`.
- **Two seams, not one** (temporal separation between retrieval and reflection prevents collapsing to one):
  1. `retrieve_framework(raw_input) -> FrameworkMatch` — wraps Problem Abstraction + Framework Retrieval (tree walk) in a single call.
  2. `reflect(match_id, outcome) -> ReflectionResult` — wraps Reflection + Framework Store write-back, called later once an outcome is known.
- **Problem Abstraction schema (first-cut, highest-risk decision — see Further Notes)**: four fields — `symptom` (observed vs. expected delta), `reproducibility` (deterministic / intermittent / unreproduced), `evidence_available` (stack trace / logs / failing test / report-only), `goal_shape` (root-cause / fix / coverage-increase / regression-prevention).
- **Framework node schema**: id, name, branch, parent, applicability_condition (checklist against the abstraction schema), status (seeded vs. provisional), confidence weight.
- **Retrieval mechanics**: single LLM call given the whole tree + applicability notes, returning the full resolved path at once (not one call per tree level). Embedding-based coarse filtering is deferred until the seed set (~8-12 Frameworks across 2 branches) outgrows single-call reasoning. Resolved paths are cached keyed on abstracted-schema similarity.
- **Misfit detection**: leading signal at retrieval time (top candidates scoring ambiguously close); lagging signal at reflection time (3+ distinct Frameworks tried for one problem, as opposed to retrying the same Framework). Tree distance between initial match and eventually-successful match is logged as a severity metric.
- **Human-in-the-loop gate**: new Frameworks enter with a provisional flag. Promotion to trusted/seeded weight requires either N=3 validated successful reflections or explicit human sign-off. The gate sits at promotion-to-store, not at the act of trying a novel Framework once.
- **Reflection ground truth**:
  - Debugging branch: the previously-failing reproduction case now passes / bug no longer reproduces.
  - Testing branch: generated tests catch a seeded mutation (mutation-testing-style check) or increase coverage of a previously-uncovered branch.
- **Cognee mapping**: graph layer = parent-child Framework tree + applies_to edges; vector layer = coarse filtering (post-v1); Memify = reflection write-back (strengthen/weaken paths); ontology layer = encode the Debugging/Testing taxonomy as explicit domain rules.
- **Adversarial validation set**: 15-20 hand-built false-friend/disguised-twin cases across Debugging + Testing, run against both raw text and hand-abstracted schema, to isolate embedding-space failures from missing-abstraction failures before committing further to the architecture.

## Testing Decisions

- Tests target the two seams as black boxes — input in (raw problem text; match_id + outcome), assert output (FrameworkMatch; store-state change), not the internal tree-walk or LLM prompt construction.
- `retrieve_framework`: run the full adversarial set (false friends + disguised twins) as the core correctness suite; assert correct Branch and Framework land in top-k.
- `reflect`: assert store-state transitions — confidence delta on success/failure, provisional → trusted promotion firing exactly at N=3 validated uses, lagging-misfit signal firing at 3+ distinct Frameworks for one problem.
- Prior art: the existing `backend/tests/` suite (e.g. `test_simulate.py`) tests at the request/response seam rather than internals — same black-box shape applies here, even though this is a separate codebase.
- No UI tests in v1 — no consuming UI/CLI decided yet (Output is out of scope).

## Out of Scope

- The Output stage's actual content generation and any UI/CLI around it — this PRD covers the retrieval infrastructure (Problem Abstraction, Retrieval, Store, Reflection) only; Output is a downstream consumer.
- Branches other than Debugging and Testing (e.g. architecture/design decisions, code review).
- Vector-embedding coarse filtering at scale — deferred until the seed tree outgrows single-call descent.
- Tooling/UI for human review of provisional Frameworks — the process is decided, the interface isn't built.
- Any integration with the existing crop-insurance `backend/`/`frontend/` — fully standalone codebase.

## Further Notes

- The Problem Abstraction schema (4 fields) is a first-cut proposal, not independently stress-tested — per the source doc, abstraction is "the hardest and most load-bearing stage" and "the unsolved core." Treat it as a hypothesis to validate against the adversarial set early, before building more on top of it.
- Source design doc: `framework-retrieval-system.md` (repo root) — full original brainstorm and rationale for all sections above.
- `CONTEXT.md` (repo root) — glossary for this system's vocabulary (Framework, Branch, Domain), built during the grilling session that produced this PRD.
- Reflection's ground-truth signal was the doc's flagged open risk for judgment-heavy domains generally; Debugging/Testing were chosen specifically because both have cheap, checkable signals (test pass/fail, mutation-catching) — this dodges that risk for v1 but means the choice shouldn't be read as "solved" for other domains later.
