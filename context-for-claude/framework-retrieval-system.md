# Framework Retrieval System — Design Summary

## Overarching Goal

Build an AI system that remembers **ways of thinking** (reasoning frameworks, mental models, diagnostic lenses) instead of just retrieving similar content. Standard RAG retrieves *facts*; this system retrieves *judgment* — the correct lens to apply to a given problem, based on the problem's underlying structure rather than its surface content.

The core thesis: in domains where competent experts would reasonably reach for different frameworks on the same input — and that choice visibly changes the outcome (therapy, diagnosis, debugging, sales, strategy, law) — matching the right framework matters more than accessing more information. This system aims to make that matching process explicit, retrievable, and self-improving over time.

This is a real research direction (case-based reasoning, cognitive architectures like ACT-R/Soar, recent work on thought-template retrieval, procedural memory RAG, experiential learning agents) but not yet productized as a general, closed-loop pipeline the way RAG has been. The goal is to build that missing infrastructure layer.

---

## The Pipeline

```
Input → Problem Abstraction → Framework Retrieval → Output → Reflection
              ↑                        ↕                          |
              └────────────── Framework Store ←───────────────────┘
```

- **Input** — user input, files, context window.
- **Problem Abstraction (P.A.)** — convert raw input into an abstracted problem schema (type, constraints, goal shape), not just a label. This is the hardest and most load-bearing stage.
- **Framework Retrieval (F.R.)** — match the abstracted problem to the best-fit framework(s) from the store, ideally via tree traversal (coarse-to-fine) rather than flat comparison against every framework.
- **Output** — generate content applying the chosen framework.
- **Reflection** — verify whether the output solved the input; decide whether the framework was actually a good fit; if not, adapt or propose a new framework.
- **Framework Store** — a persistent, structured library (not a flat corpus) that Retrieval reads from and Reflection writes back into. This is what makes the system improve over time instead of just recalling.

**Key structural insight:** the store must sit *outside* the input→output line, with independent read/write arrows. Without that, this is just a fancier prompt template — same behavior every run. With it, the system accumulates judgment across uses.

---

## Key Problems Identified (and how to address them)

### 1. How does the AI abstract a problem?
- Seed the system with a small hand-authored set of frameworks to start (cold start via human-authored taxonomy, not invented from nothing).
- Organize frameworks as a **parent-child tree**, not a flat list. Each node needs:
  - A short **applicability condition** (a checklist to test the input against, not just a similarity description).
  - Its position in the hierarchy.
- Matching becomes a tree walk (coarse → fine) rather than comparing input against every framework — cheaper and more structurally accurate.
- Analogical reasoning

### 2. How does the AI know a framework doesn't fit?
- **Lagging signal:** repeated cycling across 3+ *different* frameworks for the same problem — but distinguish this from retrying the *same* framework (usually an execution issue, not a framework-fit issue).
- **Leading signal (cheaper):** at retrieval time, if top candidates all score ambiguously low/close together, that's an early misfit warning before any output is generated.
- **Tree distance as a severity proxy:** if every sibling under a branch fails, the problem likely needs a different top-level paradigm, not a neighboring leaf — "how far off" the proposed fix is can be measured as distance across the tree.

### 3. Human-in-the-loop for new frameworks
- The risk isn't the AI improvising once for a single case — that's low-stakes.
- The risk is that improvisation getting **permanently written into the shared store**, silently shaping all future retrievals.
- Gate the human checkpoint at **promotion to the store**, not at the act of trying something novel.
- New frameworks should enter with a provisional/low-confidence flag and require multiple validated uses (or explicit sign-off) before being trusted at the same weight as the seeded set.

### 4. Cost of the tree walk
Naive one-LLM-call-per-tree-level is expensive. Mitigations:
- Do the full descent in **one LLM call** (give the model the whole tree + short applicability notes, ask for the full path at once).
- Use **embeddings for coarse filtering**, reserving LLM judgment only for genuinely ambiguous forks.
- **Cache** resolved paths for repeated/similar problem types so the system gets cheaper and faster as the store matures — this is where the compounding benefit actually shows up.

### 5. Choosing infrastructure (Cognee)
Cognee's hybrid graph + vector store maps well onto this design:
- **Graph layer** → the parent-child framework tree.
- **Vector layer** → cheap coarse filtering before expensive reasoning.
- **Memify (self-improvement)** → the reflection write-back loop (strengthens frequently-successful paths, prunes misfits) — largely pre-built rather than hand-rolled.
- **Ontology layer** → a natural place to encode the seeded framework taxonomy as explicit domain rules.

**What Cognee does *not* solve:** it's built to retrieve similar facts/entities, not to recognize which abstract lens applies. The abstraction step (turning raw input into a comparable schema), the applicability-condition logic, and the misfit-detection signals above all still need to be built on top of it.

### 6. Untested assumption: does Cognee's embedding space handle abstract/structural similarity well, given it's tuned for factual/entity similarity?
Test plan before committing the architecture to it:
1. Build ~15–20 adversarial test cases: **false friends** (lexically similar, need different frameworks) and **disguised twins** (lexically different, need the same framework).
2. Query Cognee with raw text and measure whether the correct framework lands in top-k, specifically checking these adversarial pairs.
3. Re-run the same test using a hand-written abstracted schema instead of raw text, to isolate whether failures are an embedding-space problem or a missing-abstraction problem.
4. Compare vector similarity retrieval against explicit graph-relationship traversal (e.g. an `applies_to` edge type) to see which carries structural matching better.

---

## Open Risks to Keep Honest About
- **Problem abstraction is the unsolved core.** No off-the-shelf solution exists; this is genuine research territory, not just engineering.
- **Reflection needs a ground-truth signal**, which is easy in narrow/verifiable domains (code, chess) and much harder in judgment-heavy domains (therapy, marketing) where "did this actually work" arrives late, noisily, or not at all. Without a good answer here, the store risks accumulating confident noise instead of real judgment.
- **A wrong framework applied confidently is worse than no framework** — it produces a confident answer built on evidence gathered from the wrong place. Reflection needs to be able to say "my framework's assumption didn't hold" and fall back, not just check whether the output looks plausible.




