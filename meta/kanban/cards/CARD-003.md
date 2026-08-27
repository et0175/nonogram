# CARD-003: Random grid sourcing with size and density validation

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/003-random-grid-sourcing
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-1
**Idea:** —
**Wave:** 2
**Depends on:** CARD-001
**Touches:** src/nonogram/sourcing/__init__.py, src/nonogram/sourcing/random_grid.py, tests/test_sourcing_random.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

COMP-003 (Grid Sourcing), **random path only**. The other two modes are later cards
(library: CARD-008, image: CARD-015), so create `sourcing/` as a package with a small
dispatch surface and one implementation behind it.

1. `sourcing/random_grid.py` — produce a `list[list[bool]]` of the requested size with an
   approximate fill density. Size range 10..50 inclusive, density 0..100 exclusive of
   nonsense values; both are **domain** validations raising the `errors.py` types
   (`SizeOutOfRange`, `InvalidDensity`) — the CLI only converts them to messages
   (ADR-0010; see trace.yml's FR-001 note).
2. Density tolerance is fixed by ADR-0003 at ±3 percentage points — the sampler must be
   accurate enough that AC-010 holds at the smallest supported size, so a per-cell Bernoulli
   draw alone is not sufficient at 10x10; sample the exact target count of filled cells and
   shuffle, or equivalent.
3. **Seeded RNG (ADR-0015).** The generator takes an injected `random.Random` rather than
   calling the module-level `random` functions. This card owns that seam: the same seed
   plus the same size/density must reproduce the same grid, which is what makes CARD-005's
   retry loop and CARD-004's property test deterministically reproducible. The `--seed` flag
   already exists on the parser (CARD-001); wiring it through the orchestrator is CARD-005.
4. `sourcing/__init__.py` — the mode dispatch surface (`for_mode(mode, ...)` or equivalent).
   Keep it a thin table so CARD-008 and CARD-015 add a row rather than restructure it.

## Acceptance criteria

- **AC-001** (happy) — given a request for a 20x20 random grid, when the grid is generated,
  then a 20x20 black/white grid is produced.
  *test:* `TestGenerateRandom_ProducesRequestedSize`
- **AC-002** (boundary) — given a request for the maximum supported size, 50x50, when the
  grid is generated, then a 50x50 grid is produced without error.
  *test:* `TestGenerateRandom_AcceptsMaxSize50`
- **AC-003** (negative) — given a request for a 60x60 grid (above the supported range), when
  generation is requested, then the request is rejected with a size-range error and no grid
  is produced.
  *test:* `TestGenerateRandom_RejectsSizeAbove50`
- **AC-004** (negative) — given a request for a 9x9 grid (below the supported range), when
  generation is requested, then the request is rejected with a size-range error and no grid
  is produced.
  *test:* `TestGenerateRandom_RejectsSizeBelow10`
- **AC-010** (happy) — given a requested density of 30%, when a random grid is generated,
  then the fraction of filled cells is within ±3 percentage points of 30% (ADR-0003).
  *test:* `TestGenerateRandom_RespectsDensityParameter`
- **AC-011** (negative) — given a requested density of 150% (outside the valid 0-100%
  range), when generation is requested, then the request is rejected with an error and no
  grid is produced.
  *test:* `TestGenerateRandom_RejectsInvalidDensity`

## Guardrails

- G-1: Do not edit `src/nonogram/clues.py` — owned by CARD-002 this wave
- G-2: Do not edit `src/nonogram/cli.py`, `src/nonogram/orchestrator.py`,
  `pyproject.toml` — CARD-001's deliverable; the `--size`/`--density`/`--seed` flags
  already exist and the orchestrator body is CARD-005
- G-3: Out of scope — no built-in image library (FR-002, deferred to CARD-008) and no
  uploaded-image conversion (FR-003, deferred to CARD-015). This card is the random path
  and the dispatch seam only
- G-4: No module-level `random` usage — the RNG is injected (ADR-0015). A grid produced from
  an explicit seed must be reproducible; that seam is what makes every retry-loop test
  downstream deterministic

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-001, FR-004
- **NFR:** —
- **ADR:** ADR-0003, ADR-0010, ADR-0012, ADR-0015
- **Components:** COMP-003 (Grid Sourcing — random path), COMP-001 (validation ownership)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
