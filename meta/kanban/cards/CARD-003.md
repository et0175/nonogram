# CARD-003: Random grid sourcing with size and density validation

**Status:** review
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/003-random-grid-sourcing
**Worktree:** ../PythonProject4-card-003
**Source:** meta/architecture/handoff.md#increment-1
**Idea:** —
**Wave:** 2
**Depends on:** CARD-001
**Touches:** src/nonogram/sourcing/__init__.py, src/nonogram/sourcing/random_grid.py, tests/test_sourcing_random.py
**Review score:** 9.5 (cycle 2/3)
**Started:** 2026-08-27T15:25:27Z
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

[Scope] src/nonogram/sourcing/__init__.py, src/nonogram/sourcing/random_grid.py, tests/test_sourcing_random.py — matches predicted Touches exactly.
[Build gate] PASSED (full, independently re-run by orchestrator: 110 passed, 0 failed)
[Review 1/3] Score: 9.0 — crit: 0, imp: 2. Guardrails G-1..G-4 all ✓ holds. ADR-0003 ±3pp tolerance PROVEN exhaustively (all 4141 size/density combos, worst case 0.41pp — 6x margin). ADR-0015 reproducibility proven via 3 independent behavioral tests. Important findings (severity gate blocks despite score ≥8): (I-1) the G-4 structural AST guard's own self-test never calls the real detector against a violating file — mutation-proven non-functional (neutering the detector still passes all 110 tests). (I-2) the AST guard has evasion gaps for aliased random imports (`import random as rnd`) — mutation-confirmed missed by the guard itself, though currently caught in practice by the behavioral reproducibility tests (real backstop today; risk is CARD-008/015's future modules won't have an equivalent behavioral backstop). Reviewer's own prose framed these as "not a blocker", but per the severity gate Important findings route to a fix cycle regardless of score. → routed to fix cycle.
[Fix 1] Both Important findings resolved: I-1's self-test now writes a temp file with a real violation and asserts against `_random_module_calls`' actual return (proven non-vacuous: stubbing the detector to `return []` now fails 5 tests, was 0). I-2's detector rewritten as a name-resolution pass covering aliased import/assignment/from-import evasions, with `getattr(random, ...)` left as a documented deliberate gap, not a coverage claim. Minor false-positive on `from random import Random` also fixed. No production code touched; G-4 unaffected. 116/116 passed, independently re-verified by orchestrator.
[Review 2/3] Score: 9.5 ✓ — crit: 0, imp: 0. Both cycle-1 findings independently re-derived as resolved (reviewer built its own scratch mutation of the detector to `return []`, got the exact same 5 failures claimed; hand-verified all 3 evasions now caught). Guardrails G-1..G-4 all ✓ holds. 5 new Minor/Info findings, none gating: (NEW-1) the `Random`/`SystemRandom` false-positive exemption is unconditionally unconditional — it also silently un-flags `from random import Random; Random().shuffle(x)`, a real G-4 violation via a different import spelling; one-line fix available (the exemption isn't even needed — annotations are never Call nodes). (NEW-2) `from random import *` evades the detector. (NEW-3) the docstring's "known gap" list understates remaining blind spots (re-aliasing via assignment, AnnAssign, tuple-target, importlib.import_module, passing-not-calling). (NEW-4/5) info-level test hygiene notes. Final verdict: PASS — ready to merge.
