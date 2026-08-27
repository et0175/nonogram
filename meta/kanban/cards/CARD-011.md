# CARD-011: Puzzle naming (auto-generated and --name override)

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/011-puzzle-naming
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-2
**Idea:** —
**Wave:** 6
**Depends on:** CARD-005, CARD-006, CARD-007
**Touches:** src/nonogram/orchestrator.py, src/nonogram/cli.py, tests/test_naming.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`name` becomes an attribute of the `Puzzle` aggregate (AGG-001), set once at creation. It
lands in COMP-002 because COMP-002 owns the aggregate and constructs it once per run
(ADR-0007's single-enforcement-point rule) — COMP-003 produces grids, not `Puzzle`
instances, so it is not the home for naming even though the library key that seeds the
auto-name comes from its mode (trace.yml FR-015 note).

1. **Auto-generation.** Library mode → the library key verbatim (`"cat"`). Random and image
   modes → `<mode>-<YYYY-MM-DD>-<HHMM>`, e.g. `random-2026-08-27-1430`. ADR-0018 fixes
   **minute** precision plus an incrementing counter suffix when two puzzles are created in
   the same minute — that collision branch is the one AC-042 most needs a **fixed-clock**
   test for, so inject the clock rather than calling `datetime.now()` inline.
2. **`--name` override.** The flag is carried through by `cli.py` (parsing only). An empty
   string is rejected with `InvalidPuzzleName` and **no puzzle is created** — AC-045 is
   domain validation and stays inward of argparse (ADR-0010), mirroring how FR-001's size
   range is handled. Do not implement it as `argparse` `type=`.
3. The name is set at creation and does not change across regenerate/resample/nudge
   retries — the aggregate is not re-created per retry (aggregates.yml AGG-001).
4. The name is an attribute of the aggregate only. Its consumers are later cards — the PDF
   header (CARD-014) and the `<name>-<difficulty>.pdf` filename (ADR-0016) — and they read
   it off the `Puzzle`. This card writes it nowhere on disk.

## Acceptance criteria

- **AC-042** (happy) — given a random-mode generation request with no `--name` flag, run on
  2026-08-27 at 14:30, when the puzzle is created, then the puzzle's name is auto-generated
  as `"random-2026-08-27-1430"`.
  *test:* `TestPuzzleName_AutoGeneratesModeTimestampForRandomMode`
- **AC-043** (happy) — given a library-mode generation request for library key `"cat"` with
  no `--name` flag, when the puzzle is created, then the puzzle's name is auto-generated as
  `"cat"`.
  *test:* `TestPuzzleName_AutoGeneratesFromLibraryKey`
- **AC-044** (happy) — given a generation request with `--name "my-cat-puzzle"` supplied,
  when the puzzle is created, then the puzzle's name is set to `"my-cat-puzzle"`, overriding
  the auto-generated default.
  *test:* `TestPuzzleName_OverrideViaFlag`
- **AC-045** (negative) — given a generation request with `--name ""` (an empty string)
  supplied, when the puzzle is created, then the request is rejected with an invalid-name
  error and no puzzle is created.
  *test:* `TestPuzzleName_RejectsEmptyName`

## Guardrails

- G-1: Do not edit `src/nonogram/sourcing/**` — owned by CARD-008 this wave
- G-2: Do not edit `src/nonogram/difficulty.py` — owned by CARD-009 this wave
- G-3: Do not edit `src/nonogram/export/**` — owned by CARD-012 and CARD-013 this wave. The
  name is an aggregate attribute; nothing on the export path changes for it in this card
- G-4: Do not edit `src/nonogram/solver/**`, `src/nonogram/clues.py` — Increment 2 is
  additive on top of Increment 1; naming must be revertible without touching the solver or
  the orchestrator's core generation logic (handoff Increment 2 Rollback)
- G-5: `--name` validation stays inward of argparse (ADR-0010). `cli.py` carries the flag
  through; the empty-name rejection is a domain error raised by COMP-002
- G-6: The name is set once at creation and is stable across retries — do not regenerate it
  inside the regenerate/resample loops (AGG-001: the aggregate is not re-created per retry)
  (test: TestRegenerate_FiresOnUniquenessFailure)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-015
- **NFR:** —
- **ADR:** ADR-0007, ADR-0010, ADR-0018
- **Components:** COMP-002 (Pipeline Orchestrator — AGG-001 attribute), COMP-001 (flag)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
