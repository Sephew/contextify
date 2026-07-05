# Framework Retrieval System

A system that retrieves the correct reasoning framework — not facts — to apply to an incoming problem. V1 is scoped to software development problems, specifically the **Debugging** and **Testing** branches.

## Language

**Framework**:
A reusable reasoning pattern / mental model / diagnostic lens applicable to a class of problems. Stored as a node in the Framework Store's tree, carrying an Applicability Condition and a position in the hierarchy.
_Avoid_: Template, strategy, approach (when used loosely)

**Branch**:
A top-level subtree of the Framework Store, grouping frameworks that share a problem shape. V1 has two: **Debugging** (diagnostic/eliminative frameworks — e.g. binary search bisection, differential diagnosis) and **Testing** (coverage/design frameworks — e.g. boundary value analysis, equivalence partitioning). Chosen as a pair specifically so tree-distance can demonstrate misfit severity.
_Avoid_: Domain, category

**Domain**:
The overall problem space the system operates over. Fixed to **software development** for v1 (as opposed to therapy, law, sales, etc. from the original design brainstorm).
