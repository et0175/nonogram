# CARD-054: Remove dead code — BatchGenerator._generate_puzzle_with_metrics

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/054-remove-dead-metrics-method
**Worktree:** —
**Source:** meta/review/20260910T170025Z.yml#F-006
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/batch_generator.py
**Review score:** —
**Started:** —
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
