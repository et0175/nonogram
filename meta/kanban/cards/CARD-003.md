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

Implemented on `card/003-random-grid-sourcing`; 110 tests pass
(`./.venv/bin/python -m pytest -q`, includes CARD-001's suite). No blockers.
Touches matched the prediction exactly — `cli.py`, `orchestrator.py`,
`pyproject.toml` and `clues.py` untouched (G-1, G-2).

- `sourcing/random_grid.py` — `generate(size, density, rng) -> list[list[bool]]`
  (ADR-0012 boundary representation, `True` = filled, row-major). Exposes
  `validate_size` / `validate_density` as pure functions so AC-003/AC-004/AC-011
  are testable without argv (ADR-0010), plus `MIN_SIZE`/`MAX_SIZE`,
  `MIN_DENSITY`/`MAX_DENSITY`, `DENSITY_TOLERANCE_POINTS = 3`, `filled_target`
  and `density_of`.
- Density (ADR-0003): the exact target count is computed once
  (`round(size**2 * density / 100)`) and its positions shuffled, so the density
  error is bounded by rounding alone (≤ 0.5 cell, i.e. ≤ 0.5 points even at
  10x10) rather than by a per-cell Bernoulli draw's variance (σ ≈ 4.6 points at
  10x10 / p=0.30, which would miss the ±3-point band ~1/3 of the time).
- `rng` is a required `random.Random` argument with no default (ADR-0015, G-4);
  validation runs before any draw, so a rejected request consumes no randomness
  and cannot shift a shared RNG's state. A test enforces G-4 structurally by
  AST-scanning the whole `sourcing/` package for `random.<fn>(...)` calls.
- `sourcing/__init__.py` — one-row lookup table (`_SOURCES`) with
  `for_mode(mode)`, `MODES`, `RANDOM`. `for_mode` returns the *callable* rather
  than invoking it, because the three modes do not share a parameter list
  (random: size/density; library: key; image: path) — CARD-008/CARD-015 add a
  row and a module, no restructuring. An unregistered mode raises `ValueError`,
  not a `NonogramError`, on purpose: argparse `choices` rejects a user-typed
  mode at the adapter, so one arriving here is a wiring bug, not user input.

Decisions a downstream card should know about:
- Density `0` and `100` are accepted as valid percentages (AC-011 only fixes
  "outside 0-100" as invalid); the resulting empty/full grids are degenerate
  puzzles that CARD-005's uniqueness and difficulty stages judge on their own
  terms.
- `size=None` / `density=None` (i.e. `--size`/`--density` omitted — the parser
  has no defaults) raise `SizeOutOfRange` / `InvalidDensity` rather than
  `TypeError`. Resolving defaults remains CARD-005's job; this only guarantees
  an unresolved value surfaces as a domain error.
- `DENSITY_TOLERANCE_POINTS` lives in `random_grid` — CARD-005's regenerate
  loop should import it rather than restate ADR-0003's constant.

**Review cycle 1 fixes (score 9.0/10, both Important findings resolved):**
`test_the_guardrail_check_would_catch_a_violation` previously re-implemented
the AST-scan logic inline instead of calling `_random_module_calls` —
stubbing that function to `return []` still passed all 110 tests, so the
self-test was proven vacuous. Rewrote it to write a temp file containing a
real `random.shuffle(x)` violation and assert against the function's actual
return value, and added a case for the `from random import shuffle` branch,
which no test had exercised before. Separately, `_random_module_calls` had
confirmed evasion gaps (aliased import `import random as rnd`, aliasing via
plain assignment `r = random`, aliased from-import
`from random import shuffle as sh`); rewrote it as a proper name-resolution
pass — collect the module/member bindings first, then flag any `Call` whose
callable resolves back to one of them — and added targeted tests for each
evasion. `getattr(random, "shuffle")(x)` remains a documented, deliberate
gap in the detector's docstring, not a coverage claim. Also fixed the
related Minor finding: `from random import Random` (a type-annotation
import) is now exempted from the ImportFrom binding so it no longer false-
positives as a G-4 violation. Verified the fix is not vacuous by stubbing
`_random_module_calls` to `return []` and confirming 5 tests then fail (they
passed before the fix). No production code changed by this pass; G-4 still
holds. 116 tests pass (`./.venv/bin/python -m pytest -q`).
