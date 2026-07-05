# Slice 3 — reflect seam: ground truth + lagging misfit + tree-distance severity

Status: ready-for-agent

## Parent

`.scratch/framework-retrieval-system/PRD.md`

## What to build

Implement the second seam, `reflect(match_id, outcome) -> ReflectionResult`, called after a real-world outcome is known for a prior `retrieve_framework` match.

Branch-specific ground truth: for Debugging, success means the previously-failing reproduction case now passes; for Testing, success means the generated tests caught a seeded mutation or increased coverage of a previously-uncovered branch.

On each reflection, write back to the Framework Store: adjust the matched Framework's confidence weight (via Cognee's Memify layer). Detect the lagging misfit signal — 3+ *distinct* Frameworks tried for the same underlying problem (as opposed to retrying the same Framework, which is an execution issue, not a fit issue). When a misfit is detected, log the tree distance between the initially-matched Framework and the Framework that eventually succeeded, as a severity metric.

## Acceptance criteria

- [ ] `reflect(match_id, outcome)` accepts a Debugging outcome (repro pass/fail) and updates confidence accordingly
- [ ] `reflect(match_id, outcome)` accepts a Testing outcome (mutation caught / coverage delta) and updates confidence accordingly
- [ ] Confidence weight in the store visibly changes after a reflection call (strengthens on success, weakens on failure)
- [ ] Lagging misfit signal fires when 3+ distinct Frameworks are tried for the same problem, and does NOT fire when the same Framework is retried
- [ ] Tree distance between initial match and eventually-successful match is computed and logged when misfit is detected
- [ ] Reflection stage can report "this Framework's assumption didn't hold" distinctly from a plausible-looking-but-wrong output

## Blocked by

- `slice2-testing-branch-leading-misfit-signal`
