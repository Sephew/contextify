Before drafting, quick codebase check — nothing new to explore since this is a fresh standalone codebase (confirmed earlier, no existing framework-retrieval code). One prefactor opportunity worth flagging: the PRD's own Further Notes calls the Problem Abstraction schema and Cognee's embedding-space fit the two biggest unvalidated risks — the source doc even has a dedicated test plan for the Cognee question (§6). That should run before building on top of it, not as slice N.

Proposed breakdown:

Slice 0 — Cognee retrieval-qualityfailure from missing-abstraction failure. Output: a go/no-go signal on the architecture, plus a reusable fixture set for later slices' tests.
- Blocked by: none
- Covers: user stories 21, 22

Slice 1 — Debugging-only retrieve_framework tracer bullet
Cognee-backed store seeded with 3-4 Debugging frameworks (graph layer). Problem Abstraction (4-field schema) for raw input. Single-LLM-call tree descent, Debugging branch only. Returns a FrameworkMatch. Demoable: feed a raw bug description, get the right framework back.
- Blocked by: Slice 0
- Covers: stories 1-4, 6-9 (Debugging-only)

Slice 2 — Add Testing branch + leading misfit signal
Extend the store with a seeded Testing branch, extend retrieval to choose between branches, add the leading misfit si
Slice 4 — Human-in-the-loop promotion gate
Provisional flag on new frameworks; promotion to trusted status after N=3 validated reflections or explicit sign-off.
- Blocked by: Slice 3
- Covers: stories 13, 14

Slice 5 — Path caching
Cache resolved tree paths keyed on abstracted-schema similarity; demonstrate reduced LLM calls on repeat/similar inputs.
- Blocked by: Slice 2
- Covers: story 9 (already partly covered in Slice 1, this is the caching half)

Does this granularity work, or should any of these merge/split? And does the Slice-0-before-everything ordering match what you want, given hackathon time pressure — or would you rather skip the spike and build Slice 1 straight into Cognee, treating a failure there as something to discover mid-build?