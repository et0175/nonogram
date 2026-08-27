# ADR-0007: Internal module architecture within the single Puzzle Creation context

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

contexts.yml deliberately settles on a single bounded context (CTX-001, Puzzle Creation) covering all five capabilities of the tool, and explicitly parks three technical seams — image conversion, solver/scorer, and export renderers — as "internal module seams, not context boundaries." That decision leaves open how those seams are actually realized in code: what the module or package boundaries are inside the one context, which module owns the Puzzle aggregate and its lifecycle, and how the five capabilities (CAP-001 sourcing, CAP-002 clue derivation, CAP-003 solving/verification, CAP-004 difficulty scoring, CAP-005 export) compose into a single generation run.

Several constraints bear directly on this choice. CON-005 makes solver correctness mandatory, so the solver's boundaries and testability matter more than for the other capabilities. INV-002 (the export gate — a puzzle must be verified unique-solution before it can be exported) and INV-003 (the retry/nudge counter bound) are invariants that must hold across the whole run, not just within one capability, which means something has to own enforcing them end-to-end. NFR-002 bounds the regenerate/resample retry loop, which spans multiple capabilities (sourcing, solving, difficulty scoring) in sequence. The tool is a single local process with no network and no persistence beyond file export (vision.md, CON-003), so the architecture question is purely about in-process module structure, not deployment topology. Whatever structure is chosen also has to make the eventual kanban card decomposition and trace.yml mapping (CAP-XXX to code) tractable, since CTX-001 is the only context in the model.

## Decision

We adopt the layered pipeline package: one installable package with a module per capability seam — `sourcing/`, `clues.py`, `solver/`, `difficulty.py`, `export/` — plus a thin pipeline orchestrator that owns the Puzzle aggregate and drives the generation policies (POL-001 through POL-005: regenerate, pixel-nudge, resample, and related retry loops), and a `cli.py` adapter that only parses arguments and calls the orchestrator. Dependencies point inward only: `cli.py` depends on the orchestrator, the orchestrator depends on the capability modules, and capability modules never import `cli.py` or each other laterally — a capability module's only outward-facing contact is the orchestrator that composes it into a run.

This satisfies CTX-001's framing of the three seams as internal module boundaries rather than context boundaries: each module maps 1:1 onto one CAP-XXX, which keeps trace.yml and future kanban card cutting mechanical instead of requiring a separate mapping layer. It also gives INV-002 and INV-003 a single home — the orchestrator — which is exactly where invariants that span multiple capabilities (the export gate, the retry/nudge counter) need to live, rather than being scattered across call sites in each module. Because the orchestrator is the only thing composing capabilities together, the solver stays a pure function of clues with no I/O, so CON-005's mandatory correctness property and EC-001's property test can target it directly.

## Alternatives considered

### strategy_plugin_registry

Keeps the same module set, but treats sourcing modes (random/library/image) and export formats (png/svg/json/csv) as plugins discovered via entry points, so new modes or formats could be added without touching the orchestrator. This was rejected because all three sourcing modes and all four export formats are known up front, fixed by FR-002 and FR-011, and shipped in the same package — entry-point discovery is real machinery solving a problem (late, out-of-tree extension) this tool does not have yet. The indirection would also make the pipeline harder to read and harder to trace back to CAP-XXX, and CON-002/CON-003 currently exclude the deferred capabilities (color nonograms, interactive output) that would be the actual justification for this generality.

### single_module_script

Everything in one flat module, or a handful of files with no declared layering, functions calling functions directly. This was rejected because the solver is both the largest and the most correctness-critical piece of the system (CON-005 is the model's one mandatory-severity constraint), and burying it in an undifferentiated script makes its property test awkward to isolate and degenerates the eventual C4 component view to nothing. It also leaves no natural place for the orchestrator to own INV-002 and INV-003 — those invariants would get scattered across whatever call sites happen to touch the aggregate — and every future kanban card would touch the same file or files, eliminating any possibility of parallel work during decomposition.

## Consequences

### Positive
- Each module maps 1:1 to a CAP-XXX capability, making trace.yml construction and future kanban card cutting mechanical rather than requiring a separate translation step between the domain model and the code layout.
- INV-002 (export gate) and INV-003 (retry/nudge counter) each get exactly one enforcement point — the orchestrator — instead of being duplicated or drifting across multiple call sites.
- The solver (`solver/`) stays a pure function of clues with no filesystem or CLI dependency, which lets EC-001's mandatory property test (PropertyTest_Solver_NeverFalsePositiveUniqueness) exercise it directly and cheaply.
- The whole pipeline is testable without touching argv or the filesystem, since `cli.py` is a thin adapter and every capability module and the orchestrator itself can be exercised as plain function/class calls.

### Negative
- The inward-only dependency rule (cli → orchestrator → capability modules, no lateral imports) has to be actively maintained; nothing in the language enforces it automatically, so a future contributor could accidentally introduce a lateral import between, say, `solver/` and `export/` unless this is checked (e.g. via lint rule or import-linter contract).
- The orchestrator becomes a concentration point for cross-cutting logic (both invariants plus all five POL-XXX policies), so it is the one module at real risk of growing into a second, informally-layered mess if new cross-capability behavior keeps landing there without its own internal structure.

### Neutral
- This ADR fixes the module/package structure only; it does not decide the third-party dependency baseline (DEC-006), the packaging/distribution mechanism (DEC-008), or the solver's internal algorithm choice (DEC-009) — those decisions build on top of this module layout and DEC-006/DEC-008 explicitly depend on it.
- Because capability modules never import each other laterally, any future capability that needs data from two existing modules (e.g. a hypothetical CAP that needs both difficulty and export state) will need to go through the orchestrator, which is a constraint future extensions should expect rather than work around.

## References

- DEC-007 (resolved by this ADR)
- CTX-001 (the single bounded context whose internal seams this ADR structures)
- CAP-001, CAP-002, CAP-003, CAP-004, CAP-005 (capabilities mapped 1:1 to modules)
- CON-005 (mandatory solver correctness, satisfied by keeping the solver a pure, isolated module)
- NFR-002 (the retry/resample bound the orchestrator enforces via INV-003)
- DEC-006, DEC-008 (dependency baseline and packaging, both dependent on this module layout)

## History

- 2026-08-27: Created — adopted the layered pipeline package (one module per capability plus a thin orchestrator and cli.py adapter) over the strategy/plugin-registry and single-module-script alternatives.
