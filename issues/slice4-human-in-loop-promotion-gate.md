# Slice 4 — Human-in-the-loop promotion gate

Status: ready-for-agent

## Parent

`.scratch/framework-retrieval-system/PRD.md`

## What to build

Gate new Frameworks entering the store at promotion, not at the act of trying something novel once. Any new Framework enters with a `provisional` status flag and reduced weight relative to seeded Frameworks.

A provisional Framework is promoted to trusted/seeded weight once either of two conditions is met: N=3 validated successful `reflect` calls against it, or an explicit human sign-off action.

## Acceptance criteria

- [ ] New Frameworks can be added to the store with a `provisional` status and lowered confidence weight
- [ ] Provisional Frameworks are eligible for retrieval (not excluded), just weighted lower than trusted ones
- [ ] After 3 validated successful reflections against a provisional Framework, it is automatically promoted to trusted status
- [ ] An explicit human sign-off action promotes a provisional Framework to trusted status regardless of reflection count
- [ ] A provisional Framework that receives failing reflections does not accumulate toward promotion

## Blocked by

- `slice3-reflect-seam-ground-truth-misfit`
