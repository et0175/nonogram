# CARD-008: Built-in image library sourcing

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/008-library-sourcing
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-2
**Idea:** —
**Wave:** 6
**Depends on:** CARD-003, CARD-006, CARD-007
**Touches:** src/nonogram/sourcing/library.py, src/nonogram/sourcing/__init__.py, src/nonogram/sourcing/templates/, src/nonogram/cli.py, src/nonogram/orchestrator.py, tests/test_sourcing_library.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

COMP-003's second grid source, and the lowest-risk card of Increment 2 — it reuses the
increment-1 pipeline wholesale with a different grid origin.

1. `sourcing/library.py` — a fixed, in-package library of named templates: at minimum
   `cat`, `house`, `heart`, `moon`. ADR-0007 **rejected** an entry-point plugin registry:
   the set is fixed in-package, so "extensible" means adding a template file, not
   registering a hook. Store templates as package data under `sourcing/templates/`.
2. Scale the template to the requested grid size. A template is a shape, not a fixed-size
   bitmap: `--size 20` with key `cat` must yield a 20x20 grid.
3. Unknown key → `UnknownLibraryImage` (from `errors.py`), a domain error raised inward of
   the CLI (ADR-0010), listing the available keys in the message.
4. Register `library` in `sourcing/__init__.py`'s mode dispatch table (one row), add
   `library` to `--mode`'s choices and a `--library-key` flag in `cli.py`, and let the
   orchestrator route mode `library` through POL-001's regenerate loop exactly as random
   mode does — the retry regenerates from the same template with a different tie-break, it
   does not switch key.

## Acceptance criteria

- **AC-005** (happy) — given the built-in library key `"cat"`, when a grid is requested from
  the library, then a grid matching the cat template at the target size is produced.
  *test:* `TestGenerateLibrary_ProducesCatGrid`
- **AC-006** (negative) — given an unknown library key `"dragon"` not present in the built-in
  library, when a grid is requested from the library, then the request is rejected with an
  unknown-library-image error and no grid is produced.
  *test:* `TestGenerateLibrary_RejectsUnknownKey`

## Guardrails

- G-1: Do not edit `src/nonogram/difficulty.py` — owned by CARD-009 this wave
- G-2: Do not edit `src/nonogram/export/**` — owned by CARD-012 and CARD-013 this wave
- G-3: Do not edit `src/nonogram/solver/**`, `src/nonogram/clues.py`, `pyproject.toml` —
  Increment 2 is additive on top of Increment 1: revert must be possible without touching
  the solver or the orchestrator's core generation logic (handoff Increment 2 Rollback)
- G-4: The orchestrator's core generation logic is unchanged — this card adds a dispatch row
  and a mode branch, it does not restructure the pipeline or the retry loop
  (test: TestRegenerate_FiresOnUniquenessFailure, TestRetryLoop_BoundedIterations)
- G-5: No plugin registry, entry-point hook or dynamic template discovery — the library set
  is fixed in-package by decision (ADR-0007, trace.yml FR-002 note)
- G-6: No new dependency — templates are package data read with stdlib/Pillow only
  (ADR-0006)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-002
- **NFR:** —
- **ADR:** ADR-0007, ADR-0010
- **Components:** COMP-003 (Grid Sourcing — library path)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

[Follow-up from CARD-003 review, cycle 2] The G-4 structural test guard in
tests/test_sourcing_random.py (`_random_module_calls`) has two known Minor gaps worth
checking your module against before assuming the guard covers it: (1) `from random
import Random`/`SystemRandom` is unconditionally exempted, which also silently
un-flags `Random().shuffle(x)` — a real violation via a different import spelling than
`random.Random()`. (2) `from random import *` is not detected at all. If this card adds
any RNG usage, prefer the `random.Random(...)` / `import random` spellings the guard
does catch, or tighten the guard as part of this card if it's cheap.
