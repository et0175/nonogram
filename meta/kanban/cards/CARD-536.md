# CARD-536: The longest-side filter minors from CARD-190, verified first and fixed only where still live

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/536-side-range-minors
**Worktree:** ../PythonProject4-card-536
**Source:** roadmap wave 17, cut 2026-11-24 on the owner's "pick the next no-decision wave from the backlog". IDEA-154.
**Idea:** IDEA-154
**Wave:** 96
**Created wave:** 96
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/puzzle_review.py (comments only, if any), tests/test_admin_filter_side_range_and_name.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-24T07:52Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-190's review left five minors (F-002/F-003, O-001/O-004/O-005): no test pins `PuzzleReviewService._side_bounds`' 10..30 edge (mutants E1/E4, which turn `MIN_SIZE <= low` or `high <= MAX_SIZE` into a strict `<`, survived); the AC-4 API test does not assert the store; the pagination test passes under both meanings of the filter; a stale "either side" comment in `puzzle_review.py`; and no FR traces the review filter. Re-checked on main at the cut: `tests/test_admin_filter_side_range_and_name.py` has grown since (for example `test_an_open_bound_means_the_supported_limit`, `test_a_longest_side_range_asks_about_max_width_height_not_either_side`, `test_the_longest_side_range_pages_its_own_members_and_counts_them`), and the comment by the longest-side branch now reads "max(width, height), not \"either side\"". So some items may be moot.

## What to implement

1. Verify first. For each of the first four items, record live or moot: run E1 and E4 as mutants of `_side_bounds` against `tests/test_admin_filter_side_range_and_name.py`; read the AC-4 API test (`TestPuzzlesApi_SizeRangeUsesLongestSide`) and the pagination tests against a mutant that filters by either side; grep `src/nonogram/admin/puzzle_review.py` for any comment that still describes the filter as "either side".
2. Fix only the live ones, preferring a changed assert in an existing test to a new test.
3. The fifth item (no FR traces the filter) is out of scope: `requirements.yml` and `trace.yml` are written only by the architect pass. Record it in the notes, not here.

## Acceptance criteria

- AC-1: each item has a recorded verdict, live or moot, backed by a run (a mutant, a probe or a test), never by reading code alone. Record the command and its result in `## Worktree notes`.
- AC-2: every live item is fixed, and its fix has one control that fails when the fix is reverted.
- AC-3: owner's test budget: change existing tests rather than add; net test count at most +1; report it.

## Worktree notes
