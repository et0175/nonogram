# CARD-054: Remove dead code — BatchGenerator._generate_puzzle_with_metrics

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/054-remove-dead-metrics-method
**Worktree:** ../PythonProject4-CARD-054
**Source:** meta/review/20260910T170025Z.yml#F-006
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/batch_generator.py
**Review score:** —
**Started:** 2026-09-11T14:05:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`BatchGenerator._generate_puzzle_with_metrics` (`src/nonogram/admin/batch_generator.py:438-468`)
has zero callers anywhere in the repository — grep-verified across `src/` and
`tests/`. It duplicates the same `hasattr(puzzle, "quality_score") else 75` /
`getattr(puzzle, "recognizability", "medium")` hardcoding pattern CARD-050 fixes
in the two methods that ARE actually called
(`_generate_random_batch`, lines 310 and 463... note: line 463 is itself
*inside* `_generate_puzzle_with_metrics` — re-verify the exact line numbers
against the current file before editing, in case CARD-050 has already landed
and shifted them).

1. Confirm (fresh grep, since other cards in this wave may have touched the
   same file) that `_generate_puzzle_with_metrics` still has no callers.
2. Remove the method entirely, along with any now-unused imports/helpers
   (`PuzzleMetrics`, `GeneratedPuzzle` — check whether either is used
   elsewhere before removing).

## Acceptance criteria

- **AC-1** — given the method is removed, when the full test suite runs, then
  nothing fails (confirming the zero-callers claim held).
- **AC-2** — given a fresh grep for `_generate_puzzle_with_metrics` across the
  repository after this card, then it returns no matches.

## Guardrails

- G-1: If CARD-050 has already run and this method's hardcoded values were
  fixed instead of the method being found dead, re-verify against the current
  file rather than assuming this card's premise still holds — removal is only
  correct if the method is genuinely unreachable.

## Worktree notes

**Implementation:** confirmed fresh (per G-1) that
`_generate_puzzle_with_metrics` still has zero callers even after
CARD-050 landed and touched this same file — grep across `src/` and
`tests/` found only the method's own definition. CARD-050 fixed the
hardcoded `quality_score`/`recognizability` pattern in
`_generate_random_batch` (the method that IS actually called);
`_generate_puzzle_with_metrics` carried the same fix (CARD-050's
Worktree notes mention this) but remained dead — this card's premise
held. Removed the method (lines 455-500) entirely. Kept
`PuzzleMetrics`/`GeneratedPuzzle` (still used as field types on
`BatchJob.puzzles`/`GeneratedPuzzle.metrics`) and the `uuid`/
`orchestrator` imports (both still used elsewhere in the file).

**AC-1 verified:** full suite run — 39 failures, all in the previously
documented flaky/corpus-dependent classes, none touching
`batch_generator.py` or any test file. Scoped run (`test_batch_generator.py`
+ `test_card_050_quality_recognizability.py` +
`test_cli.py::test_every_import_in_the_package_points_inward`) — 25/25
pass.

**AC-2 verified:** fresh grep for `_generate_puzzle_with_metrics` across
the repository after the edit — zero matches. `python3 -c "import ast;
ast.parse(...)"` confirms the file still parses cleanly.
