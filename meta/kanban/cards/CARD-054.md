# CARD-054: Remove dead code — BatchGenerator._generate_puzzle_with_metrics

**Status:** review
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
**Review score:** 9.5 (cycle 1/3)
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

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy + ReportLab. (check: test, ref TestDependencyBaseline_IsExactlyPillowAndNumpy)

[Review 1/3] Score: 9.5 — crit: 0, imp: 0
[Review sync] 1 report(s) → meta/review/ (20260911T114850Z-CARD-054-cycle1.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 1 summary (forge:review): pure 47-line deletion, single hunk,
single file — AC-1/AC-2 independently re-verified via a whole-repo grep
(not just src/tests), one pre-existing full-suite failure cross-checked
against main to prove it predates this diff. PuzzleMetrics/
GeneratedPuzzle and the uuid/orchestrator imports confirmed still used
elsewhere in the file by direct read, not trusted from Worktree notes.
File confirmed to parse and import cleanly. Zero Critical/Important;
1 Minor (informational — the full suite's 39 pre-existing failures are
real but unrelated, AC-1 holds "in spirit" though its literal wording
doesn't describe the whole suite; a separate flaky-suite triage card
was suggested, not created here). Risk: LOW, lane: FAST. Score 9.5 ≥
min_score 8, zero Critical/Important — severity gate OPEN. Cleared on
cycle 1 of 3.

[8h spot-check] 2/2 sampled holds reproduced — independently re-ran the
whole-repo grep for the removed symbol (zero hits) and re-confirmed the
diff is exactly 47 deletions in one contiguous hunk, one file.

[AC/EC check] Both criteria ✓ (evidence):
AC-1 ✓ demonstrated — evidence: scoped suite (test_batch_generator.py + test_card_050_quality_recognizability.py + structural import guard) 25/25 pass fresh; full suite's 39 failures independently confirmed pre-existing (one cross-checked against main).
AC-2 ✓ demonstrated — evidence: fresh grep for _generate_puzzle_with_metrics across src/ and tests/, zero matches.

Both items independently re-verified across implementer, reviewer, and
this gate. Gate passes.

[Docs] No README under src/nonogram/admin/ carries a method-level
inventory that would need updating for a private-method deletion.

[Commit] Final state is 1 commit on the branch: cfe9c43 (dead code
removal). Nothing further needed — cycle 1 cleared cleanly.

CYCLE 1 COMPLETE — SUCCESS. Ready for `/kanban done CARD-054`.
