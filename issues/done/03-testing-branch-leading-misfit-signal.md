# 03 — Add Testing branch + leading misfit signal

Status: ready-for-agent

## Parent

`.scratch/framework-retrieval-system/PRD.md`

## What to build

Extend the Framework Store with a seeded Testing branch (3-4 frameworks, e.g. boundary value analysis, equivalence partitioning), sibling to the existing Debugging branch.

Extend Framework Retrieval so the single-LLM-call descent chooses the correct top-level branch before resolving within it, using both branches' applicability conditions together (still one call, not one per branch).

Add the leading misfit signal: when the top candidate Frameworks score ambiguously close together, `retrieve_framework` returns a low-confidence flag instead of a confident single match.

## Acceptance criteria

- [ ] Testing branch seeded with 3-4 frameworks, each with applicability_condition and tree position
- [ ] `retrieve_framework` correctly picks Testing-branch frameworks for testing-goal problems and Debugging-branch frameworks for debugging-goal problems
- [ ] Branch selection happens within the same single LLM call as leaf resolution
- [ ] Ambiguously-close top candidates produce a flagged low-confidence result rather than a silent guess
- [ ] Slice 01's full adversarial fixture set (false friends + disguised twins across both branches) runs as an automated regression suite and passes

## Blocked by

- `02-debugging-retrieve-framework-tracer-bullet`
